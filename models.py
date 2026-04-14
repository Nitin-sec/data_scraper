from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone
import hashlib
import re


@dataclass
class UnifiedJob:
    title: str
    company: str
    location: str
    description: str
    platform: str = "unknown"
    apply_link: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = 'INR'
    external_id: Optional[str] = None
    posted_at: Optional[datetime] = None
    raw_data: Optional[dict] = field(default=None)

    def get_content_hash(self) -> str:
        title_norm = re.sub(r'\s+', ' ', self.title.lower().strip()) if self.title else ""
        company_norm = re.sub(r'\s+', ' ', self.company.lower().strip()) if self.company else ""
        location_norm = re.sub(r'\s+', ' ', self.location.lower().strip()) if self.location else ""
        platform_norm = self.platform.lower().strip()
        apply_url_norm = self.apply_link.lower().strip() if self.apply_link else ""

        hash_input = f"{title_norm}|{company_norm}|{location_norm}|{platform_norm}|{apply_url_norm}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


@dataclass
class QueryModel:
    platform: str
    value: str
    location: Optional[str] = None


class BaseAdapter(ABC):
    @abstractmethod
    async def fetch(self, query: QueryModel) -> List[UnifiedJob]:
        pass
