import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum, text
try:
    from sqlalchemy.orm import declarative_base
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import enum
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()


class PlatformEnum(enum.Enum):
    TELEGRAM = 'telegram'
    LINKEDIN = 'linkedin'
    INDEED = 'indeed'
    GLASSDOOR = 'glassdoor'
    REMOTIVE = 'remotive'
    ADZUNA = 'adzuna'
    JOOBLE = 'jooble'


class JobHash(Base):
    __tablename__ = 'job_hashes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)

    jobs = relationship("Job", back_populates="hash_ref")


class SearchQuery(Base):
    __tablename__ = 'search_queries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    value = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_id = Column(Integer, ForeignKey('job_hashes.id'), nullable=False)
    source = Column(Enum(PlatformEnum), nullable=False)
    external_id = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String(10), default='INR')
    apply_link = Column(Text, nullable=True)
    description_html = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True)
    posted_at_source = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    hash_ref = relationship("JobHash", back_populates="jobs")


class DatabaseManager:
    def __init__(self, connection_string=None):
        if connection_string is None:
            connection_string = self._get_database_url()

        if connection_string.startswith('mysql'):
            self.engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_recycle=1800,
                echo=False
            )
            logger.info("Connected to MySQL")
        else:
            self.engine = create_engine(connection_string)
            logger.info("Connected to SQLite")

        self.SessionLocal = sessionmaker(bind=self.engine)

    def _get_database_url(self):
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()

        if db_type == 'mysql':
            host = os.getenv('MYSQL_HOST', 'localhost')
            port = os.getenv('MYSQL_PORT', '3306')
            user = os.getenv('MYSQL_USER')
            password = os.getenv('MYSQL_PASSWORD')
            database = os.getenv('MYSQL_DB')

            if not all([user, password, database]):
                logger.warning("MySQL credentials incomplete, falling back to SQLite")
                return "sqlite:///jobs.db"

            password_encoded = quote_plus(password)
            return f"mysql+pymysql://{user}:{password_encoded}@{host}:{port}/{database}?charset=utf8mb4"

        return os.getenv('DATABASE_URL', 'sqlite:///jobs.db')

    def create_tables(self):
        try:
            if self.engine.url.drivername == 'mysql+pymysql':
                self._ensure_mysql_database_exists()
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables ready")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def _ensure_mysql_database_exists(self):
        url = self.engine.url
        db_name = url.database

        # Validate db_name is a safe identifier before using in DDL
        if not db_name or not db_name.replace('_', '').isalnum():
            raise ValueError(f"Unsafe database name: {db_name!r}")

        temp_url = url.set(database=None)
        temp_engine = create_engine(temp_url)

        try:
            with temp_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :db"),
                    {"db": db_name}
                )
                if not result.fetchone():
                    # db_name is validated above as alphanumeric+underscore only
                    conn.execute(text(
                        f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    ))
                    logger.info(f"Created MySQL database: {db_name}")
                else:
                    logger.info(f"MySQL database already exists: {db_name}")
        finally:
            temp_engine.dispose()

    def get_session(self):
        return self.SessionLocal()
