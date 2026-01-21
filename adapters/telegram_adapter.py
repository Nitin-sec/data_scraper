from telethon import TelegramClient
from telethon.errors import FloodWaitError
from datetime import datetime, timedelta
import asyncio
from typing import List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from models import BaseAdapter, UnifiedJob, QueryModel

class TelegramAdapter(BaseAdapter):
    def __init__(self, api_id: int, api_hash: str, session_name: str = 'job_scraper'):
        self.client = TelegramClient(session_name, api_id, api_hash)
        
    async def fetch(self, query: QueryModel) -> List[UnifiedJob]:
        jobs = []
        try:
            await self.client.start()
            
            # Get messages from last 24 hours
            time_limit = datetime.now() - timedelta(hours=24)
            
            async for message in self.client.iter_messages(
                query.value, 
                offset_date=time_limit,
                limit=100
            ):
                if message.text:
                    job = self._parse_message(message)
                    if job:
                        jobs.append(job)
                        
        except FloodWaitError as e:
            print(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Telegram error: {e}")
            
        return jobs
    
    def _parse_message(self, message) -> UnifiedJob:
        text = message.text.strip()
        lines = text.split('\n')
        
        # Extract title (first line, truncated)
        title = lines[0][:100] if lines else "Job Posting"
        
        # Try to extract company and location from text
        company = "Unknown Company"
        location = "Unknown Location"
        
        # Simple parsing - look for common patterns
        for line in lines[1:5]:  # Check first few lines
            line_lower = line.lower()
            if any(word in line_lower for word in ['company:', 'at ', 'hiring']):
                company = line.split(':')[-1].strip() if ':' in line else line.strip()
                break
                
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in ['location:', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai']):
                location = line.split(':')[-1].strip() if ':' in line else line.strip()
                break
        
        return UnifiedJob(
            title=title,
            company=company,
            location=location,
            description=text,
            apply_link=f"https://t.me/{message.chat.username}/{message.id}" if message.chat.username else None,
            raw_data={'message_id': message.id, 'chat_id': message.chat_id, 'date': message.date.isoformat()}
        )