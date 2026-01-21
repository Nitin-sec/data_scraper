import asyncio
import sys
import os
import logging
import random
import signal
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from database import DatabaseManager, SearchQuery, JobHash, Job, PlatformEnum
from adapters.telegram import TelegramAdapter
from adapters.http_adapters import JoobleAdapter, NaukriAdapter, LinkedInAdapter, IndeedAdapter
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Load configuration
load_dotenv()

# Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Scheduler")

class JobIngestionSystem:
    def __init__(self):
        # Initialize Database
        db_url = os.getenv('DATABASE_URL')
        if not db_url and os.getenv('MYSQL_USER'):
             db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
        
        self.db = DatabaseManager(db_url or "sqlite:///jobs.db")
        self.db.create_tables()
        self.running = True

        # Graceful Shutdown Handler
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum, frame):
        logger.info("Shutdown signal received. Stopping all engines...")
        self.running = False

    async def start(self):
        """Main Entry Point: Launches all engines in parallel."""
        logger.info("Initializing Multi-Engine Ingestion System...")
        
        # Define the engines to run
        tasks = [
            self.engine_telegram(interval_hours=6),
            self.engine_jooble(interval_hours=12),
            self.engine_scrapers(interval_hours=6), # Scrapers run every 6h cycle
            self.task_cleanup(interval_hours=24)
        ]
        
        # Run them all concurrently
        await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # ENGINE 1: TELEGRAM
    # ------------------------------------------------------------------
    async def engine_telegram(self, interval_hours):
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        session_str = os.getenv('TELEGRAM_SESSION_STRING')

        if not (api_id and api_hash and session_str):
            logger.warning("Telegram Engine DISABLED: Missing credentials in .env")
            return

        adapter = TelegramAdapter(int(api_id), api_hash, session_str)
        logger.info(f"Telegram Engine STARTED (Interval: {interval_hours}h)")

        while self.running:
            try:
                logger.info("[Telegram] Checking for new messages...")
                session = self.db.get_session()
                
                queries = session.query(SearchQuery).filter(
                    SearchQuery.platform == PlatformEnum.TELEGRAM,
                    SearchQuery.is_active == True
                ).all()

                for query in queries:
                    if not self.running: break
                    jobs = await adapter.fetch(query)
                    self._save_jobs(session, jobs, PlatformEnum.TELEGRAM)
                
                session.close()
            except Exception as e:
                logger.error(f"[Telegram] Error: {e}")

            # Wait for next cycle
            await self._smart_sleep(interval_hours * 3600)

    # ------------------------------------------------------------------
    # ENGINE 2: JOOBLE
    # ------------------------------------------------------------------
    async def engine_jooble(self, interval_hours):
        api_key = os.getenv('JOOBLE_API_KEY')
        
        if not api_key:
            logger.warning("Jooble Engine DISABLED: Missing JOOBLE_API_KEY in .env")
            return

        adapter = JoobleAdapter(api_key)
        logger.info(f"Jooble Engine STARTED (Interval: {interval_hours}h)")

        while self.running:
            try:
                logger.info("[Jooble] Fetching jobs via API...")
                session = self.db.get_session()
                
                queries = session.query(SearchQuery).filter(
                    SearchQuery.platform == PlatformEnum.JOOBLE,
                    SearchQuery.is_active == True
                ).all()

                for query in queries:
                    if not self.running: break
                    jobs = await adapter.fetch(query)
                    self._save_jobs(session, jobs, PlatformEnum.JOOBLE)
                    await asyncio.sleep(2) # Polite API delay
                
                session.close()
            except Exception as e:
                logger.error(f"[Jooble] Error: {e}")

            await self._smart_sleep(interval_hours * 3600)

    # ------------------------------------------------------------------
    # ENGINE 3: SCRAPERS (Naukri, Indeed, LinkedIn)
    # ------------------------------------------------------------------
    async def engine_scrapers(self, interval_hours):
        # Initialize adapters
        adapters = {
            PlatformEnum.NAUKRI: NaukriAdapter(),
            PlatformEnum.LINKEDIN: LinkedInAdapter(),
            PlatformEnum.INDEED: IndeedAdapter()
        }
        
        logger.info(f"Scraper Engine STARTED (Targeting: Naukri, LinkedIn, Indeed)")

        while self.running:
            try:
                logger.info("[Scrapers] Starting safe scrape cycle...")
                session = self.db.get_session()
                
                queries = session.query(SearchQuery).filter(
                    SearchQuery.platform.in_(adapters.keys()),
                    SearchQuery.is_active == True
                ).all()

                for query in queries:
                    if not self.running: break
                    
                    adapter = adapters.get(query.platform)
                    if adapter:
                        logger.info(f"[Scrapers] Fetching {query.platform.value}: {query.value}")
                        jobs = await adapter.fetch(query)
                        self._save_jobs(session, jobs, query.platform)
                        
                        # ANTI-BLOCKING MECHANISM
                        # Sleep 45-90 seconds between queries to mimic human behavior
                        sleep_time = random.uniform(45, 90)
                        logger.info(f"[Scrapers] Cooling down for {sleep_time:.1f}s")
                        await asyncio.sleep(sleep_time)

                session.close()
            except Exception as e:
                logger.error(f"[Scrapers] Error: {e}")

            logger.info(f"[Scrapers] Cycle complete. Sleeping for {interval_hours} hours.")
            await self._smart_sleep(interval_hours * 3600)

    # ------------------------------------------------------------------
    # UTILITIES & HELPERS
    # ------------------------------------------------------------------
    async def task_cleanup(self, interval_hours):
        """Background task to remove old data."""
        while self.running:
            try:
                session = self.db.get_session()
                # Remove jobs older than 100 hours
                cutoff = datetime.now(timezone.utc) - timedelta(hours=100)
                # Ensure compatibility with naive timestamps if necessary
                cutoff_naive = cutoff.replace(tzinfo=None)
                
                deleted = session.query(Job).filter(Job.created_at < cutoff_naive).delete()
                session.commit()
                if deleted:
                    logger.info(f"[Cleanup] Removed {deleted} expired jobs.")
                session.close()
            except Exception as e:
                logger.error(f"[Cleanup] Error: {e}")
            
            await self._smart_sleep(interval_hours * 3600)

    async def _smart_sleep(self, seconds):
        """Sleeps in short bursts to allow for rapid shutdown."""
        end_time = datetime.now() + timedelta(seconds=seconds)
        while datetime.now() < end_time and self.running:
            await asyncio.sleep(1)

    def _save_jobs(self, session: Session, jobs, platform) -> int:
        if not jobs: return 0
        count = 0
        for job in jobs:
            try:
                content_hash = job.get_content_hash()
                
                # Deduplication: Check if exists
                if session.query(JobHash).filter_by(content_hash=content_hash).first():
                    continue

                # Insert Hash
                job_hash = JobHash(content_hash=content_hash)
                session.add(job_hash)
                session.flush()

                # Insert Job
                job_entry = Job(
                    hash_id=job_hash.id,
                    source=platform,
                    external_id=job.external_id,
                    title=job.title[:500],
                    company=job.company[:255],
                    location=job.location[:255],
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    currency=job.currency,
                    apply_link=job.apply_link,
                    description_html=job.description,
                    raw_data=job.raw_data,
                    posted_at_source=job.posted_at_source
                )
                session.add(job_entry)
                count += 1
            except IntegrityError:
                session.rollback()
            except Exception:
                session.rollback()
        
        if count > 0:
            logger.info(f"   [DB] Saved {count} new jobs from {platform.value}")
            session.commit()
        return count

if __name__ == "__main__":
    system = JobIngestionSystem()
    try:
        asyncio.run(system.start())
    except KeyboardInterrupt:
        # Should be handled by signal handler, but just in case
        pass