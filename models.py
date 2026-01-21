from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import hashlib

@dataclass
class UnifiedJob:
    title: str
    company: str
    location: str
    description: str
    apply_link: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = 'INR'
    raw_data: Optional[dict] = None
    
    def get_content_hash(self) -> str:
        content = f"{self.title}{self.company}{self.location}".lower().strip()
        return hashlib.sha256(content.encode()).hexdigest()

@dataclass
class QueryModel:
    platform: str
    value: str
    location: Optional[str] = None

class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, query: QueryModel) -> List[UnifiedJob]:
        pass