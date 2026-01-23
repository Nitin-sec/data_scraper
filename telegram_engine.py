import os
import logging
import hashlib
import sys
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import DatabaseManager, JobHash, Job, PlatformEnum
import asyncio
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
# Set console handler encoding for Windows
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        handler.stream.reconfigure(encoding='utf-8', errors='replace')
logger = logging.getLogger("TelegramEngine")

class TelegramJob:
    def __init__(self, title: str, company: str, location: str, description: str, 
                 apply_link: Optional[str] = None, posted_at: Optional[datetime] = None, 
                 source: str = "telegram", external_id: Optional[str] = None):
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.apply_link = apply_link
        self.posted_at = posted_at
        self.source = source
        self.external_id = external_id
    
    def get_content_hash(self) -> str:
        # Include title, company, apply_link (if exists), and first 200 chars of description
        content_parts = [
            self.title.lower().strip(),
            self.company.lower().strip(),
            self.apply_link.lower().strip() if self.apply_link else "",
            self.description[:200].lower().strip()
        ]
        content = "".join(content_parts)
        return hashlib.sha256(content.encode()).hexdigest()

class TelegramEngine:
    def __init__(self):
        load_dotenv()
        
        # Load credentials from .env
        self.api_id = int(os.getenv('TELEGRAM_API_ID'))
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.session_string = os.getenv('TELEGRAM_SESSION_STRING')
        self.groups = [g.strip() for g in os.getenv('TELEGRAM_GROUPS', '').split(',') if g.strip()]
        
        # Initialize Telethon client with StringSession
        self.client = TelegramClient(StringSession(self.session_string), self.api_id, self.api_hash)
        
        # Initialize database
        db_url = os.getenv('DATABASE_URL', 'sqlite:///jobs.db')
        self.db = DatabaseManager(db_url)
        self.db.create_tables()
    
    async def connect(self):
        """Connect to Telegram"""
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError("Invalid or expired TELEGRAM_SESSION_STRING. Regenerate session.")
            logger.info("Telegram connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False
    
    async def get_last_db_timestamp(self) -> datetime:
        """Get the timestamp of the most recent job from database"""
        session = self.db.get_session()
        try:
            latest_job = session.query(Job).filter(
                Job.source == PlatformEnum.TELEGRAM
            ).order_by(Job.posted_at_source.desc()).first()
            
            if latest_job and latest_job.posted_at_source:
                return latest_job.posted_at_source
            else:
                # If no Telegram jobs exist, fetch from last 24 hours
                return datetime.now() - timedelta(hours=24)
        finally:
            session.close()
    
    def _sanitize_for_log(self, text: str) -> str:
        """Sanitize text for safe logging by removing problematic Unicode characters"""
        if not text:
            return text
        # Replace common problematic Unicode characters
        return text.encode('ascii', errors='replace').decode('ascii')
    
    async def resolve_group_entity(self, group_name: str):
        """Resolve group string to entity using display name, username, or ID"""
        try:
            # First try direct entity resolution (for @username or ID)
            try:
                entity = await self.client.get_entity(group_name)
                title = getattr(entity, 'title', getattr(entity, 'username', str(entity.id)))
                safe_title = self._sanitize_for_log(title)
                logger.info(f"Resolved Telegram group: {safe_title} (id={entity.id})")
                return entity
            except:
                pass
            
            # Clean group name for comparison - safely handle None
            group_clean = group_name.replace('@', '').lower() if group_name else ""
            
            # Search through dialogs for display name match
            async for dialog in self.client.iter_dialogs():
                if not hasattr(dialog, 'entity') or not dialog.entity:
                    continue
                    
                dialog_title = getattr(dialog.entity, 'title', None)
                dialog_username = getattr(dialog.entity, 'username', None)
                
                # Skip if no title or username available
                if not dialog_title and not dialog_username:
                    continue
                
                # Exact display name match - safely handle None
                if dialog_title and dialog_title.lower() == group_name.lower():
                    safe_title = self._sanitize_for_log(dialog_title)
                    logger.info(f"Resolved Telegram group: {safe_title} (id={dialog.entity.id})")
                    return dialog.entity
                
                # Partial display name match - safely handle None
                if dialog_title and group_name.lower() in dialog_title.lower():
                    safe_title = self._sanitize_for_log(dialog_title)
                    logger.info(f"Resolved Telegram group: {safe_title} (id={dialog.entity.id})")
                    return dialog.entity
                
                # Username match - safely handle None
                if dialog_username and dialog_username.lower() == group_clean:
                    safe_title = self._sanitize_for_log(dialog_title or dialog_username)
                    logger.info(f"Resolved Telegram group: {safe_title} (id={dialog.entity.id})")
                    return dialog.entity
            
            logger.error(f"Telegram group not found: {group_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving group {group_name}: {e}")
            return None
    async def fetch_messages_from_group(self, group_name: str, since: datetime) -> List[TelegramJob]:
        """Fetch messages from a specific group newer than the given timestamp"""
        jobs = []
        try:
            # Resolve group entity first
            entity = await self.resolve_group_entity(group_name)
            if not entity:
                return jobs
            
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=500):
                message_count += 1
                
                # Stop if message is older than our timestamp
                if message.date.replace(tzinfo=None) < since.replace(tzinfo=None):
                    break
                
                if message.text:
                    job = self._parse_message(message, group_name)
                    if job:
                        jobs.append(job)
            
            logger.info(f"Messages scanned: {message_count}")
            
        except FloodWaitError as e:
            logger.warning(f"Flood wait for {group_name}: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error fetching from {group_name}: {e}")
        
        return jobs
    
    def _parse_message(self, message, group_name: str) -> Optional[TelegramJob]:
        """Parse a Telegram message into a normalized Job schema"""
        text = message.text.strip()
        if not text:
            return None
        
        lines = text.split('\n')
        
        # Extract title (first line, truncated to 100 chars)
        title = lines[0][:100] if lines else "Job Posting"
        
        # Extract apply link (first URL found)
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        apply_link = urls[0] if urls else None
        
        # Company = "Telegram: " + group_name
        company = f"Telegram: {group_name}"
        
        return TelegramJob(
            title=title,
            company=company,
            location="Remote/Telegram",
            description=text,
            apply_link=apply_link,
            posted_at=message.date,
            external_id=str(message.id)
        )
    
    def save_jobs_to_db(self, jobs: List[TelegramJob]) -> tuple[int, int]:
        """Save jobs to MySQL database with deduplication"""
        if not jobs:
            return 0, 0
        
        session = self.db.get_session()
        inserted_count = 0
        duplicate_count = 0
        
        try:
            for job in jobs:
                content_hash = job.get_content_hash()
                
                # Check for duplicates
                existing_hash = session.query(JobHash).filter_by(content_hash=content_hash).first()
                if existing_hash:
                    duplicate_count += 1
                    continue
                
                try:
                    # Insert hash
                    job_hash = JobHash(content_hash=content_hash)
                    session.add(job_hash)
                    session.flush()
                    
                    # Insert job
                    job_entry = Job(
                        hash_id=job_hash.id,
                        source=PlatformEnum.TELEGRAM,
                        external_id=job.external_id,
                        title=job.title[:500],
                        company=job.company[:255],
                        location=job.location[:255],
                        apply_link=job.apply_link,
                        description_html=job.description,
                        posted_at_source=job.posted_at,
                        raw_data={'message_id': job.external_id}
                    )
                    session.add(job_entry)
                    inserted_count += 1
                    
                except IntegrityError:
                    session.rollback()
                    duplicate_count += 1
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error saving job: {e}")
            
            if inserted_count > 0:
                session.commit()
                logger.info(f"DB INSERT CONFIRMED: {inserted_count} rows added to jobs table")
            
            if duplicate_count > 0:
                logger.info(f"Duplicates skipped: {duplicate_count}")
                
            # Verify data was actually saved
            total_jobs = session.query(Job).count()
            logger.info(f"Total jobs in database: {total_jobs}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
        finally:
            session.close()
        
        return inserted_count, duplicate_count

async def run_telegram_engine():
    """Single entry function that performs one full fetch cycle"""
    engine = TelegramEngine()
    
    # Connect to Telegram
    if not await engine.connect():
        return
    
    try:
        # Get last timestamp from database
        last_timestamp = await engine.get_last_db_timestamp()
        
        all_jobs = []
        
        # Fetch from all groups
        for group in engine.groups:
            if group:
                jobs = await engine.fetch_messages_from_group(group, last_timestamp)
                all_jobs.extend(jobs)
        
        # Save to database
        inserted, duplicates = engine.save_jobs_to_db(all_jobs)
        
        logger.info(f"Telegram cycle complete - Inserted: {inserted}, Duplicates: {duplicates}")
        
    except Exception as e:
        logger.error(f"Error in Telegram engine: {e}")
    finally:
        await engine.client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_telegram_engine())