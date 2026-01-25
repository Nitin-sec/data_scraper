import os
from dotenv import load_dotenv
from database import DatabaseManager, SearchQuery, PlatformEnum

# Load environment variables to match scheduler.py
load_dotenv()

def setup_database():
    # 1. Get the EXACT same DB URL the scheduler uses
    db_url = os.getenv('DATABASE_URL')
    if not db_url and os.getenv('MYSQL_USER'):
         db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"
    
    # Fallback to SQLite if nothing is configured (matches scheduler behavior)
    if not db_url:
        print("WARNING: No DATABASE_URL found. Defaulting to sqlite:///jobs.db")
        db_url = "sqlite:///jobs.db"

    print(f"Connecting to: {db_url}")
    
    # 2. Initialize Database
    db_manager = DatabaseManager(db_url)
    db_manager.create_tables()
    
    session = db_manager.get_session()
    
    # 3. Add Seed Data - India-focused queries
    queries = [
        # JOOBLE - India tech roles
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='backend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='frontend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='full stack engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='python developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='java developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data scientist', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data analyst', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ml engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ai engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='devops engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='cloud engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='security engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='product manager', location='India', is_active=True),
        
        # JOOBLE - Remote roles
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data scientist', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='devops engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='cloud engineer', location='Remote', is_active=True),
        
        # JOOBLE - Major Indian cities
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Bangalore', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Hyderabad', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Pune', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Chennai', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Mumbai', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Delhi', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Noida', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Gurgaon', is_active=True),
        
        # REMOTIVE - Remote roles (India-eligible)
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='software engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='backend engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='frontend engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='data scientist', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='data engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='devops engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='cloud engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='security engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='product manager', location='Remote', is_active=True),
        
        # ADZUNA - India roles
        SearchQuery(platform=PlatformEnum.ADZUNA, value='software engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='backend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='frontend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='python developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data scientist', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data analyst', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='devops engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='cloud engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='security engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='product manager', location='India', is_active=True),
        
        # ADZUNA - Remote roles
        SearchQuery(platform=PlatformEnum.ADZUNA, value='software engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data scientist', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='devops engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='cloud engineer', location='Remote', is_active=True),
    ]
    
    print("Seeding database with queries...")
    count = 0
    for query in queries:
        existing = session.query(SearchQuery).filter(
            SearchQuery.platform == query.platform,
            SearchQuery.value == query.value
        ).first()
        
        if not existing:
            session.add(query)
            count += 1
            print(f"   + Added: {query.platform.value} -> {query.value}")
        else:
            print(f"   . Skipped (Exists): {query.platform.value} -> {query.value}")
    
    session.commit()
    session.close()
    print(f"Database setup complete! Added {count} new queries.")

if __name__ == "__main__":
    setup_database()