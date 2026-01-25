import os
import logging
import hashlib
import aiohttp
import re
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
logger = logging.getLogger("RemotiveEngine")

class RemotiveJob:
    def __init__(self, title: str, company: str, location: str, description: str, 
                 apply_link: Optional[str] = None, posted_at: Optional[datetime] = None, 
                 source: str = "remotive", external_id: Optional[str] = None):
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.apply_link = apply_link
        self.posted_at = posted_at
        self.source = source
        self.external_id = external_id
    
    def get_content_hash(self) -> str:
        """Generate standardized content hash: title + company + location + platform + source_url"""
        # Normalize all components
        title_norm = re.sub(r'\s+', ' ', self.title.lower().strip()) if self.title else ""
        company_norm = re.sub(r'\s+', ' ', self.company.lower().strip()) if self.company else ""
        location_norm = re.sub(r'\s+', ' ', self.location.lower().strip()) if self.location else ""
        platform_norm = "remotive"
        source_url_norm = self.apply_link.lower().strip() if self.apply_link else ""
        
        # Combine all components
        hash_input = f"{title_norm}|{company_norm}|{location_norm}|{platform_norm}|{source_url_norm}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

class RemotiveEngine:
    def __init__(self):
        load_dotenv()
        
        # No API key required for Remotive
        self.base_url = "https://remotive.com/api/remote-jobs"
        
        # Initialize database
        db_url = os.getenv('DATABASE_URL', 'sqlite:///jobs.db')
        self.db = DatabaseManager(db_url)
        self.db.create_tables()
    
    async def connect(self):
        """No API key validation needed for Remotive"""
        try:
            logger.info("Remotive connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Remotive: {e}")
            return False
    
    async def get_last_db_timestamp(self) -> datetime:
        """Get the timestamp of the most recent job from database"""
        session = self.db.get_session()
        try:
            latest_job = session.query(Job).filter(
                Job.source == PlatformEnum.REMOTIVE
            ).order_by(Job.posted_at_source.desc()).first()
            
            if latest_job and latest_job.posted_at_source:
                return latest_job.posted_at_source
            else:
                # If no Remotive jobs exist, fetch from last 24 hours
                return datetime.now() - timedelta(hours=24)
        finally:
            session.close()
    
    async def fetch_jobs(self, keywords: str, location: str, since_timestamp: datetime) -> List[RemotiveJob]:
        """Fetch jobs from Remotive API"""
        jobs = []
        try:
            logger.info(f"Query found: {keywords}, {location}")
            
            params = {
                "search": keywords
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        job_list = data.get('jobs', [])
                        
                        for job_data in job_list:
                            job = self._parse_job(job_data)
                            if job and self._is_job_newer(job, since_timestamp):
                                jobs.append(job)
                        
                        logger.info(f"Jobs fetched: {len(jobs)}")
                    else:
                        logger.error(f"Remotive API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error fetching from Remotive: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> Optional[RemotiveJob]:
        """Parse a Remotive job into normalized Job schema"""
        try:
            title = job_data.get('title', 'Job Posting')[:100]
            company = job_data.get('company_name', 'Unknown Company')
            location = job_data.get('candidate_required_location', 'Remote')
            description = job_data.get('description', '')
            apply_link = job_data.get('url')
            external_id = str(job_data.get('id', ''))
            
            # Parse posted date
            posted_at = None
            if job_data.get('publication_date'):
                try:
                    posted_at = datetime.fromisoformat(job_data['publication_date'].replace('Z', '+00:00'))
                except:
                    posted_at = datetime.now()
            else:
                posted_at = datetime.now()
            
            return RemotiveJob(
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
    
    def _is_job_newer(self, job: RemotiveJob, since_timestamp: datetime) -> bool:
        """Always return True - timestamp filtering temporarily disabled"""
        return True
    
    def save_jobs_to_db(self, jobs: List[RemotiveJob]) -> tuple[int, int]:
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
                
                # Insert hash first
                job_hash = JobHash(content_hash=content_hash)
                session.add(job_hash)
                session.flush()  # Get the ID
                
                # Insert job
                job_entry = Job(
                    hash_id=job_hash.id,
                    source=PlatformEnum.REMOTIVE,
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
            
            # Single commit at the end
            if inserted_count > 0:
                session.commit()
                logger.info(f"DB COMMIT SUCCESS: {inserted_count} jobs inserted")
            
            if duplicate_count > 0:
                logger.info(f"Duplicates skipped: {duplicate_count}")
                
            # Post-commit verification
            total_jobs = session.query(Job).count()
            logger.info(f"DB ROW COUNT AFTER REMOTIVE: {total_jobs}")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
        
        return inserted_count, duplicate_count

async def run_remotive_engine():
    """Single entry function that performs one full fetch cycle"""
    engine = RemotiveEngine()
    
    # Connect to Remotive
    if not await engine.connect():
        return
    
    try:
        # Get last timestamp from database
        last_timestamp = await engine.get_last_db_timestamp()
        
        # Load queries from search_queries table
        session = engine.db.get_session()
        queries = session.query(SearchQuery).filter(
            SearchQuery.platform == PlatformEnum.REMOTIVE,
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
        
        logger.info(f"Remotive cycle complete - Inserted: {inserted}, Duplicates: {duplicates}")
        
    except Exception as e:
        logger.error(f"Error in Remotive engine: {e}")

if __name__ == "__main__":
    asyncio.run(run_remotive_engine())