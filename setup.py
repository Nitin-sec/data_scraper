import os
from dotenv import load_dotenv
from database import DatabaseManager, SearchQuery, PlatformEnum

load_dotenv()


def setup_database():
    db_manager = DatabaseManager()
    db_manager.create_tables()

    session = db_manager.get_session()

    queries = [
        # --- LINKEDIN ---
        # India - core tech roles
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='backend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='frontend engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='full stack developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='python developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='java developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='data scientist', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='data analyst', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='data engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='machine learning engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='devops engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='cloud engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='product manager', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='ui ux designer', location='India', is_active=True),
        # India - major cities
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Bangalore', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Hyderabad', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Pune', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Mumbai', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Delhi', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Chennai', is_active=True),
        # Remote
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='software engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='data scientist', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.LINKEDIN, value='devops engineer', location='Remote', is_active=True),

        # --- INDEED ---
        SearchQuery(platform=PlatformEnum.INDEED, value='software engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='backend developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='frontend developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='python developer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='data scientist', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='data analyst', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='devops engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='cloud engineer', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='product manager', location='India', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='software engineer', location='Bangalore', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='software engineer', location='Hyderabad', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='software engineer', location='Pune', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='software engineer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='python developer', location='Remote', is_active=True),
        SearchQuery(platform=PlatformEnum.INDEED, value='data scientist', location='Remote', is_active=True),
    ]

    added = 0
    skipped = 0
    for query in queries:
        existing = session.query(SearchQuery).filter(
            SearchQuery.platform == query.platform,
            SearchQuery.value == query.value,
            SearchQuery.location == query.location
        ).first()

        if not existing:
            session.add(query)
            added += 1
        else:
            skipped += 1

    session.commit()
    session.close()
    print(f"Database setup complete. Added: {added}, Skipped (already exist): {skipped}")


if __name__ == "__main__":
    setup_database()
