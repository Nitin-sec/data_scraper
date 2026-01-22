from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()

class PlatformEnum(enum.Enum):
    TELEGRAM = 'telegram'
    JOOBLE = 'jooble'
    REMOTIVE = 'remotive'
    WELLFOUND = 'wellfound'
    NAUKRI = 'naukri'
    LINKEDIN = 'linkedin'
    INDEED = 'indeed'

class JobHash(Base):
    __tablename__ = 'job_hashes'
    
    id = Column(BigInteger, primary_key=True)
    content_hash = Column(String(64), unique=True, nullable=False)
    
    jobs = relationship("Job", back_populates="hash_ref")

class SearchQuery(Base):
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True)
    platform = Column(Enum(PlatformEnum), nullable=False)
    value = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(BigInteger, primary_key=True)
    hash_id = Column(BigInteger, ForeignKey('job_hashes.id'), nullable=False)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    hash_ref = relationship("JobHash", back_populates="jobs")

class DatabaseManager:
    def __init__(self, connection_string):
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        return self.SessionLocal()