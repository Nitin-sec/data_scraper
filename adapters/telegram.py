from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from datetime import datetime, timedelta
import asyncio
import re
import os
from typing import List
from .base import BaseAdapter, UnifiedJob

class TelegramAdapter(BaseAdapter):
    def __init__(self, api_id: int, api_hash: str, session_string: str = None):
        # FIX: Use StringSession if session_string is provided
        if session_string:
            self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
        else:
            # Fallback to a file-based session if no string is provided (useful for local dev)
            self.client = TelegramClient('job_scraper_session', api_id, api_hash)
        
    async def fetch(self, query) -> List[UnifiedJob]:
        jobs = []
        try:
            await self.client.start()
            
            # Use query.value (which holds the group name from DB) or iterate env var groups
            # The scheduler passes a QueryModel, so we should use query.value
            group_to_scrape = query.value
            
            time_limit = datetime.now() - timedelta(hours=24)
            
            # Safety check
            if not group_to_scrape:
                return []

            print(f"   Fetching Telegram: {group_to_scrape}...")

            async for message in self.client.iter_messages(group_to_scrape, limit=50):
                if message.date.replace(tzinfo=None) < time_limit.replace(tzinfo=None):
                    break
                
                if message.text:
                    job = self._parse_message(message, group_to_scrape)
                    if job:
                        jobs.append(job)
                        
        except FloodWaitError as e:
            print(f"   Telegram FloodWait: Sleeping {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"   Telegram error on {query.value}: {e}")
            
        return jobs
    
    def _parse_message(self, message, group_name) -> UnifiedJob:
        text = message.text.strip()
        lines = text.split('\n')
        
        # Title = First line (truncated to 100 chars)
        title = lines[0][:100] if lines else "Job Posting"
        
        # Apply Link = Extract first URL found in text
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, text)
        apply_link = urls[0] if urls else None
        
        # Company = "Telegram: " + group_name
        company = f"Telegram: {group_name}"
        
        return UnifiedJob(
            title=title,
            company=company,
            location="Remote/Telegram",
            description=text,
            external_id=str(message.id),
            apply_link=apply_link,
            posted_at_source=message.date,
            raw_data={'message_id': message.id, 'chat_id': message.chat_id}
        )