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
logger = logging.getLogger("AdzunaEngine")

class AdzunaJob:
    def __init__(self, title: str, company: str, location: str, description: str, 
                 apply_link: Optional[str] = None, posted_at: Optional[datetime] = None, 
                 source: str = "adzuna", external_id: Optional[str] = None):
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

class AdzunaEngine:
    def __init__(self):
        load_dotenv()
        
        # Load credentials from .env
        self.app_id = os.getenv('ADZUNA_APP_ID')
        self.app_key = os.getenv('ADZUNA_APP_KEY')
        
        # Initialize database
        db_url = os.getenv('DATABASE_URL', 'sqlite:///jobs.db')
        self.db = DatabaseManager(db_url)
        self.db.create_tables()
    
    async def connect(self):
        """Validate API keys presence"""
        try:
            if not self.app_id or not self.app_key:
                raise RuntimeError("ADZUNA_APP_ID or ADZUNA_APP_KEY not found in .env")
            logger.info("Adzuna connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Adzuna: {e}")
            return False
    
    async def get_last_db_timestamp(self) -> datetime:
        """Get the timestamp of the most recent job from database"""
        session = self.db.get_session()
        try:
            latest_job = session.query(Job).filter(
                Job.source == PlatformEnum.ADZUNA
            ).order_by(Job.posted_at_source.desc()).first()
            
            if latest_job and latest_job.posted_at_source:
                return latest_job.posted_at_source
            else:
                # If no Adzuna jobs exist, fetch from last 24 hours
                return datetime.now() - timedelta(hours=24)
        finally:
            session.close()
    
    async def fetch_jobs(self, keywords: str, location: str, since_timestamp: datetime) -> List[AdzunaJob]:
        """Fetch jobs from Adzuna API"""
        jobs = []
        try:
            logger.info(f"Query found: {keywords}, {location}")
            
            # Determine country code from location
            country = "in"  # default
            if location.lower() in ['worldwide', 'global', '']:
                country = "us"  # Use US for worldwide searches
            
            # Build dynamic base URL
            base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            
            # Map location for Adzuna API
            api_location = location
            if location.lower() in ['worldwide', 'global']:
                api_location = ""
            elif location.lower() == 'remote':
                api_location = "remote"
            
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "what": keywords,
                "where": api_location,
                "results_per_page": 50,
                "content-type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        job_list = data.get('results', [])
                        
                        for job_data in job_list:
                            job = self._parse_job(job_data)
                            if job and self._is_job_newer(job, since_timestamp):
                                jobs.append(job)
                        
                        logger.info(f"Jobs fetched: {len(jobs)}")
                    else:
                        logger.error(f"Adzuna API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error fetching from Adzuna: {e}")
        
        return jobs
    
    def _parse_job(self, job_data: dict) -> Optional[AdzunaJob]:
        """Parse an Adzuna job into normalized Job schema"""
        try:
            title = job_data.get('title', 'Job Posting')[:100]
            
            # Handle company field
            company_data = job_data.get('company', {})
            if isinstance(company_data, dict):
                company = company_data.get('display_name', 'Unknown Company')
            else:
                company = str(company_data) if company_data else 'Unknown Company'
            
            # Handle location field
            location_data = job_data.get('location', {})
            if isinstance(location_data, dict):
                location = location_data.get('display_name', 'Unknown Location')
            else:
                location = str(location_data) if location_data else 'Unknown Location'
            
            description = job_data.get('description', '')
            apply_link = job_data.get('redirect_url')
            external_id = str(job_data.get('id', ''))
            
            # Parse posted date
            posted_at = None
            if job_data.get('created'):
                try:
                    # Adzuna uses ISO format dates
                    posted_at = datetime.fromisoformat(job_data['created'].replace('Z', '+00:00'))
                except:
                    posted_at = datetime.now()
            else:
                posted_at = datetime.now()
            
            return AdzunaJob(
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
    
    def _is_job_newer(self, job: AdzunaJob, since_timestamp: datetime) -> bool:
        """Always return True - timestamp filtering temporarily disabled"""
        return True
    
    def save_jobs_to_db(self, jobs: List[AdzunaJob]) -> tuple[int, int]:
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
                        source=PlatformEnum.ADZUNA,
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

async def run_adzuna_engine():
    """Single entry function that performs one full fetch cycle"""
    engine = AdzunaEngine()
    
    # Connect to Adzuna
    if not await engine.connect():
        return
    
    try:
        # Get last timestamp from database
        last_timestamp = await engine.get_last_db_timestamp()
        
        # Load queries from search_queries table
        session = engine.db.get_session()
        queries = session.query(SearchQuery).filter(
            SearchQuery.platform == PlatformEnum.ADZUNA,
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
        
        logger.info(f"Adzuna cycle complete - Inserted: {inserted}, Duplicates: {duplicates}")
        
    except Exception as e:
        logger.error(f"Error in Adzuna engine: {e}")

if __name__ == "__main__":
    asyncio.run(run_adzuna_engine())