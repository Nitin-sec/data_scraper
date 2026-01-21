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
    
    # 3. Add Seed Data
    queries = [
        # Telegram Channels
        SearchQuery(platform=PlatformEnum.TELEGRAM, value='@jobsearchindia', is_active=True),
        SearchQuery(platform=PlatformEnum.TELEGRAM, value='@techjobsindia', is_active=True),
        
        # Scraper Keywords
        SearchQuery(platform=PlatformEnum.INDEED, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.NAUKRI, value='devops engineer', location='Bangalore', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='backend developer', location='Mumbai', is_active=True),
        
        # Jooble Keywords
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='Delhi', is_active=True),
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