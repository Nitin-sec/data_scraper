import os
import logging
import hashlib
import aiohttp
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import DatabaseManager, JobHash, Job, PlatformEnum, SearchQuery
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JoobleEngine")

class JoobleJob:
    def __init__(self, title: str, company: str, location: str, description: str, 
                 apply_link: Optional[str] = None, posted_at: Optional[datetime] = None, 
                 source: str = "jooble", external_id: Optional[str] = None):
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

class JoobleEngine:
    def __init__(self):
        load_dotenv()
        
        # Load credentials from .env
        self.api_key = os.getenv('JOOBLE_API_KEY')
        self.base_url = f"https://jooble.org/api/{self.api_key}"
        
        # Initialize database
        db_url = os.getenv('DATABASE_URL', 'sqlite:///jobs.db')
        self.db = DatabaseManager(db_url)
        self.db.create_tables()
    
    async def connect(self):
        """Validate API key presence"""
        try:
            if not self.api_key:
                raise RuntimeError("JOOBLE_API_KEY not found in .env")
            logger.info("Jooble connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Jooble: {e}")
            return False
    
    async def get_last_db_timestamp(self) -> datetime:
        """Get the timestamp of the most recent job from database"""
        session = self.db.get_session()
        try:
            latest_job = session.query(Job).filter(
                Job.source == PlatformEnum.JOOBLE
            ).order_by(Job.posted_at_source.desc()).first()
            
            if latest_job and latest_job.posted_at_source:
                return latest_job.posted_at_source
            else:
                # If no Jooble jobs exist, fetch from last 24 hours
                return datetime.now() - timedelta(hours=24)
        finally:
            session.close()
    
    async def fetch_jobs(self, keywords: str, location: str, since_timestamp: datetime) -> List[JoobleJob]:
        """Fetch jobs from Jooble API"""
        jobs = []
        try:
            logger.info(f"Query found: {keywords}, {location}")
            
            payload = {
                "keywords": keywords,
                "location": location,
                "page": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        job_list = data.get('jobs', [])
                        
                        for job_data in job_list:
                            job = self._parse_job(job_data)
                            if job and self._is_job_newer(job, since_timestamp):
                                jobs.append(job)
                        
                        logger.info(f"Jobs fetched: {len(jobs)}")
                    else:
                        logger.error(f"Jooble API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error fetching from Jooble: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> Optional[JoobleJob]:
        """Parse a Jooble job into normalized Job schema"""
        try:
            title = job_data.get('title', 'Job Posting')[:100]
            company = job_data.get('company', 'Unknown Company')
            location = job_data.get('location', 'Unknown Location')
            description = job_data.get('snippet', '')
            apply_link = job_data.get('link')
            
            # Generate external_id from link hash if no id provided
            external_id = job_data.get('id')
            if not external_id and apply_link:
                external_id = hashlib.md5(apply_link.encode()).hexdigest()[:16]
            
            # Parse posted date if available
            posted_at = None
            if job_data.get('updated'):
                try:
                    posted_at = datetime.fromisoformat(job_data['updated'].replace('Z', '+00:00'))
                except:
                    posted_at = datetime.now()
            else:
                posted_at = datetime.now()
            
            return JoobleJob(
                title=title,
                company=company,
                location=location,
                description=description,
                apply_link=apply_link,
                posted_at=posted_at,
                external_id=external_id
            )
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None
    
    def _is_job_newer(self, job: JoobleJob, since_timestamp: datetime) -> bool:
        """Check if job is newer than the given timestamp"""
        if not job.posted_at:
            return True  # Include jobs without timestamp
        return job.posted_at.replace(tzinfo=None) > since_timestamp.replace(tzinfo=None)
    
    def save_jobs_to_db(self, jobs: List[JoobleJob]) -> tuple[int, int]:
        """Save jobs to database with deduplication"""
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
                        source=PlatformEnum.JOOBLE,
                        external_id=job.external_id,
                        title=job.title[:500],
                        company=job.company[:255],
                        location=job.location[:255],
                        apply_link=job.apply_link,
                        description_html=job.description,
                        posted_at_source=job.posted_at,
                        raw_data={'external_id': job.external_id}
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
                logger.info(f"New jobs inserted: {inserted_count}")
            
            if duplicate_count > 0:
                logger.info(f"Duplicates skipped: {duplicate_count}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
        finally:
            session.close()
        
        return inserted_count, duplicate_count

async def run_jooble_engine():
    """Single entry function that performs one full fetch cycle"""
    engine = JoobleEngine()
    
    # Connect to Jooble
    if not await engine.connect():
        return
    
    try:
        # Get last timestamp from database
        last_timestamp = await engine.get_last_db_timestamp()
        
        # Load queries from search_queries table
        session = engine.db.get_session()
        queries = session.query(SearchQuery).filter(
            SearchQuery.platform == PlatformEnum.JOOBLE,
            SearchQuery.is_active == True
        ).all()
        session.close()
        
        all_jobs = []
        
        # Fetch from all queries
        for query in queries:
            jobs = await engine.fetch_jobs(query.value, query.location or "", last_timestamp)
            all_jobs.extend(jobs)
            await asyncio.sleep(1)  # Rate limiting
        
        # Save to database
        inserted, duplicates = engine.save_jobs_to_db(all_jobs)
        
        logger.info(f"Jooble cycle complete - Inserted: {inserted}, Duplicates: {duplicates}")
        
    except Exception as e:
        logger.error(f"Error in Jooble engine: {e}")

if __name__ == "__main__":
    asyncio.run(run_jooble_engine())