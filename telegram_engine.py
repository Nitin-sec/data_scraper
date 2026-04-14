import os
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from sqlalchemy.exc import IntegrityError
from database import DatabaseManager, JobHash, Job, PlatformEnum
from models import UnifiedJob
import asyncio
import re

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        try:
            handler.stream.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            pass

logger = logging.getLogger("TelegramEngine")

URL_PATTERN = re.compile(r'https?://\S+')


def _sanitize_log(text: str) -> str:
    if not text:
        return ""
    return text.encode('ascii', errors='replace').decode('ascii')


class TelegramEngine:
    def __init__(self):
        api_id_raw = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        session_string = os.getenv('TELEGRAM_SESSION_STRING')

        if not api_id_raw or not api_hash or not session_string:
            raise RuntimeError("TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION_STRING must all be set")

        self.api_id = int(api_id_raw)
        self.api_hash = api_hash
        self.session_string = session_string
        self.groups = [g.strip() for g in os.getenv('TELEGRAM_GROUPS', '').split(',') if g.strip()]

        self.client = TelegramClient(StringSession(self.session_string), self.api_id, self.api_hash)
        self.db = DatabaseManager()
        self.db.create_tables()

    async def connect(self) -> bool:
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                raise RuntimeError("Invalid or expired TELEGRAM_SESSION_STRING. Regenerate session.")
            logger.info("Telegram connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {e}")
            return False

    async def _get_last_timestamp(self) -> datetime:
        session = self.db.get_session()
        try:
            latest = session.query(Job).filter(
                Job.source == PlatformEnum.TELEGRAM
            ).order_by(Job.posted_at_source.desc()).first()

            if latest and latest.posted_at_source:
                ts = latest.posted_at_source
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                return ts
            return datetime.now(timezone.utc) - timedelta(hours=24)
        finally:
            session.close()

    async def _resolve_entity(self, group_name: str):
        # Try direct resolution first (handles @username and numeric IDs)
        try:
            entity = await self.client.get_entity(group_name)
            title = getattr(entity, 'title', getattr(entity, 'username', str(entity.id)))
            logger.info(f"Resolved group: {_sanitize_log(title)} (id={entity.id})")
            return entity
        except Exception:
            pass

        group_clean = group_name.replace('@', '').lower()

        async for dialog in self.client.iter_dialogs():
            if not hasattr(dialog, 'entity') or not dialog.entity:
                continue

            d_title = getattr(dialog.entity, 'title', None)
            d_username = getattr(dialog.entity, 'username', None)

            if not d_title and not d_username:
                continue

            if d_title and d_title.lower() == group_name.lower():
                logger.info(f"Resolved group by exact name: {_sanitize_log(d_title)}")
                return dialog.entity

            if d_title and group_name.lower() in d_title.lower():
                logger.info(f"Resolved group by partial name: {_sanitize_log(d_title)}")
                return dialog.entity

            if d_username and d_username.lower() == group_clean:
                logger.info(f"Resolved group by username: {_sanitize_log(d_username)}")
                return dialog.entity

        logger.error(f"Telegram group not found: {group_name}")
        return None

    def _parse_message(self, message, group_name: str) -> Optional[UnifiedJob]:
        text = (message.text or "").strip()
        if not text:
            return None

        lines = text.split('\n')
        title = lines[0][:500] if lines else "Job Posting"

        urls = URL_PATTERN.findall(text)
        apply_link = urls[0] if urls else None

        posted_at = message.date
        if posted_at and posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)

        return UnifiedJob(
            title=title,
            company=f"Telegram: {group_name}",
            location="India",
            description=text,
            platform="telegram",
            apply_link=apply_link,
            external_id=str(message.id),
            posted_at=posted_at,
            raw_data={'group': group_name, 'message_id': message.id}
        )

    async def fetch_from_group(self, group_name: str, since: datetime) -> List[UnifiedJob]:
        jobs = []
        entity = await self._resolve_entity(group_name)
        if not entity:
            return jobs

        try:
            scanned = 0
            async for message in self.client.iter_messages(entity, limit=500):
                scanned += 1
                msg_date = message.date
                if msg_date and msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)

                if msg_date and msg_date < since:
                    break

                if message.text:
                    job = self._parse_message(message, group_name)
                    if job:
                        jobs.append(job)

            logger.info(f"[{_sanitize_log(group_name)}] scanned={scanned} parsed={len(jobs)}")

        except FloodWaitError as e:
            logger.warning(f"Flood wait for {group_name}: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error fetching from {group_name}: {e}")

        return jobs

    def save_jobs(self, jobs: List[UnifiedJob]) -> tuple:
        if not jobs:
            return 0, 0

        session = self.db.get_session()
        inserted = 0
        duplicates = 0

        try:
            for job in jobs:
                content_hash = job.get_content_hash()

                if session.query(JobHash).filter_by(content_hash=content_hash).first():
                    duplicates += 1
                    continue

                try:
                    job_hash = JobHash(content_hash=content_hash)
                    session.add(job_hash)
                    session.flush()

                    session.add(Job(
                        hash_id=job_hash.id,
                        source=PlatformEnum.TELEGRAM,
                        external_id=job.external_id,
                        title=job.title[:500],
                        company=job.company[:255],
                        location=job.location[:255],
                        apply_link=job.apply_link,
                        description_html=job.description,
                        posted_at_source=job.posted_at,
                        raw_data=job.raw_data
                    ))
                    inserted += 1
                except IntegrityError:
                    session.rollback()
                    duplicates += 1

            if inserted > 0:
                session.commit()

            logger.info(f"Telegram save: inserted={inserted} duplicates={duplicates}")
        except Exception as e:
            session.rollback()
            logger.error(f"Database error in Telegram engine: {e}")
            raise
        finally:
            session.close()

        return inserted, duplicates


async def run_telegram_engine():
    engine = TelegramEngine()

    if not await engine.connect():
        return

    try:
        since = await engine._get_last_timestamp()
        all_jobs = []

        for group in engine.groups:
            jobs = await engine.fetch_from_group(group, since)
            all_jobs.extend(jobs)

        inserted, duplicates = engine.save_jobs(all_jobs)
        logger.info(f"Telegram cycle complete - inserted={inserted} duplicates={duplicates}")
    except Exception as e:
        logger.error(f"Telegram engine error: {e}")
    finally:
        await engine.client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_telegram_engine())
