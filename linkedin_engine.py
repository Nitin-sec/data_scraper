import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.exc import IntegrityError
from database import DatabaseManager, JobHash, Job, PlatformEnum, SearchQuery
from models import UnifiedJob

logger = logging.getLogger("LinkedInEngine")


def _to_utc(dt) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return datetime.now(timezone.utc)


def _safe_str(val, max_len: int = 255) -> str:
    if val is None:
        return ""
    return str(val)[:max_len]


class LinkedInEngine:
    def __init__(self):
        self.db = DatabaseManager()
        self.db.create_tables()

    def _get_last_timestamp(self) -> datetime:
        session = self.db.get_session()
        try:
            latest = session.query(Job).filter(
                Job.source == PlatformEnum.LINKEDIN
            ).order_by(Job.posted_at_source.desc()).first()

            if latest and latest.posted_at_source:
                ts = latest.posted_at_source
                return ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
            return datetime.now(timezone.utc) - timedelta(hours=48)
        finally:
            session.close()

    def _fetch_sync(self, keywords: str, location: str, hours_old: int) -> List[UnifiedJob]:
        """
        Synchronous jobspy call - runs in a thread executor.
        jobspy scrapes LinkedIn directly; no API key required.
        """
        try:
            from jobspy import scrape_jobs
            import pandas as pd

            results = scrape_jobs(
                site_name=["linkedin"],
                search_term=keywords,
                location=location,
                results_wanted=50,
                hours_old=hours_old,
                country_indeed="india",
                linkedin_fetch_description=False,  # Faster; descriptions are often blocked anyway
                verbose=0
            )

            if results is None or results.empty:
                return []

            jobs = []
            for _, row in results.iterrows():
                apply_link = _safe_str(row.get('job_url') or row.get('job_url_direct'), 2048)
                if not apply_link:
                    continue

                title = _safe_str(row.get('title'), 500)
                company = _safe_str(row.get('company'), 255) or "Unknown Company"
                loc = _safe_str(row.get('location'), 255) or location

                salary_min = None
                salary_max = None
                try:
                    salary_min = int(row['min_amount']) if pd.notna(row.get('min_amount')) else None
                    salary_max = int(row['max_amount']) if pd.notna(row.get('max_amount')) else None
                except (ValueError, TypeError):
                    pass

                posted_at = _to_utc(row.get('date_posted'))

                jobs.append(UnifiedJob(
                    title=title,
                    company=company,
                    location=loc,
                    description=_safe_str(row.get('description'), 65535),
                    platform="linkedin",
                    apply_link=apply_link,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency='INR',
                    external_id=_safe_str(row.get('id'), 255),
                    posted_at=posted_at,
                    raw_data={'source': 'linkedin', 'location_query': location}
                ))

            return jobs

        except ImportError:
            logger.error("jobspy not installed. Run: pip install python-jobspy")
            return []
        except Exception as e:
            logger.error(f"LinkedIn fetch error [{keywords} / {location}]: {e}")
            return []

    async def fetch_jobs(self, keywords: str, location: str, since: datetime) -> List[UnifiedJob]:
        hours_old = max(24, int((datetime.now(timezone.utc) - since).total_seconds() / 3600) + 1)
        hours_old = min(hours_old, 72)  # Cap at 72h to avoid massive pulls

        loop = asyncio.get_event_loop()
        jobs = await loop.run_in_executor(None, self._fetch_sync, keywords, location, hours_old)
        logger.info(f"LinkedIn [{keywords} / {location}]: fetched {len(jobs)} jobs")
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
                        source=PlatformEnum.LINKEDIN,
                        external_id=job.external_id,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        salary_min=job.salary_min,
                        salary_max=job.salary_max,
                        currency=job.currency,
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

            logger.info(f"LinkedIn save: inserted={inserted} duplicates={duplicates}")
        except Exception as e:
            session.rollback()
            logger.error(f"Database error in LinkedIn engine: {e}")
            raise
        finally:
            session.close()

        return inserted, duplicates


async def run_linkedin_engine():
    engine = LinkedInEngine()
    since = engine._get_last_timestamp()

    session = engine.db.get_session()
    try:
        queries = session.query(SearchQuery).filter(
            SearchQuery.platform == PlatformEnum.LINKEDIN,
            SearchQuery.is_active == True
        ).all()
        query_list = [(q.value, q.location or "India") for q in queries]
    finally:
        session.close()

    all_jobs = []
    for keywords, location in query_list:
        jobs = await engine.fetch_jobs(keywords, location, since)
        all_jobs.extend(jobs)
        await asyncio.sleep(3)  # Be respectful to LinkedIn's rate limits

    inserted, duplicates = engine.save_jobs(all_jobs)
    logger.info(f"LinkedIn cycle complete - inserted={inserted} duplicates={duplicates}")


if __name__ == "__main__":
    asyncio.run(run_linkedin_engine())
