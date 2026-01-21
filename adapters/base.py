from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import hashlib

@dataclass
class UnifiedJob:
    title: str
    company: str
    location: str
    description: str
    external_id: Optional[str] = None
    apply_link: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = 'INR'
    posted_at_source: Optional[datetime] = None
    raw_data: Optional[dict] = None
    
    def get_content_hash(self) -> str:
        content = f"{self.title.lower().strip()}{self.company.lower().strip()}{self.location.lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()

class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, query) -> List[UnifiedJob]:
        pass