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
        # JOOBLE - Worldwide tech roles (location="" for global)
        SearchQuery(platform=PlatformEnum.JOOBLE, value='software engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='backend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='frontend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='full stack engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='python developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='java developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='golang developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='rust developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='mobile developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='android developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ios developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data scientist', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='data engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ml engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ai engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='devops engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='cloud engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='site reliability engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='security engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='soc analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='penetration tester', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='blockchain developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='web developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='game developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='embedded engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='robotics engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='iot engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='firmware engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='database administrator', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='solutions architect', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='platform engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='infrastructure engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='network engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='systems engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='quant developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='research engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='technical product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='business analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='program manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='project manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='technical writer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ui designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='ux designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='product designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='sales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='solutions consultant', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='presales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='support engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.JOOBLE, value='it consultant', location='', is_active=True),
        
        # REMOTIVE - Remote roles (location="" for global)
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='software engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='backend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='frontend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='full stack engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='python developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='java developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='golang developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='rust developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='mobile developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='android developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='ios developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='data scientist', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='data analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='data engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='ml engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='ai engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='devops engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='cloud engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='site reliability engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='security engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='soc analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='penetration tester', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='blockchain developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='web developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='game developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='embedded engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='robotics engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='iot engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='firmware engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='database administrator', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='solutions architect', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='platform engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='infrastructure engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='network engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='systems engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='quant developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='research engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='technical product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='business analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='program manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='project manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='technical writer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='ui designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='ux designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='product designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='sales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='solutions consultant', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='presales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='support engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.REMOTIVE, value='it consultant', location='', is_active=True),
        
        # ADZUNA - Worldwide roles (location="" for global)
        SearchQuery(platform=PlatformEnum.ADZUNA, value='software engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='backend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='frontend engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='full stack engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='python developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='java developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='golang developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='rust developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='mobile developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='android developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='ios developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data scientist', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='data engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='ml engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='ai engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='devops engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='cloud engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='site reliability engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='security engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='soc analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='penetration tester', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='blockchain developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='web developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='game developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='embedded engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='robotics engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='iot engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='firmware engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='database administrator', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='solutions architect', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='platform engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='infrastructure engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='network engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='systems engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='quant developer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='research engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='technical product manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='business analyst', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='program manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='project manager', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='technical writer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='ui designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='ux designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='product designer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='sales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='solutions consultant', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='presales engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='support engineer', location='', is_active=True),
        SearchQuery(platform=PlatformEnum.ADZUNA, value='it consultant', location='', is_active=True),
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