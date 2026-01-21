from curl_cffi import requests as currequests
from bs4 import BeautifulSoup
import json
import re
import time
import random
import os
import logging
from typing import List
from .base import BaseAdapter, UnifiedJob

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self):
        proxy_list = os.getenv('PROXY_LIST', '')
        self.proxies = [p.strip() for p in proxy_list.split(',') if p.strip()]
        self.index = 0
        
    def get_proxy(self):
        if not self.proxies:
            return None
        proxy = self.proxies[self.index]
        self.index = (self.index + 1) % len(self.proxies)
        return {'http': f'http://{proxy}', 'https': f'http://{proxy}'}

class HTTPClient:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.session = currequests.Session(impersonate="chrome110")
        
    def request(self, method, url, **kwargs):
        proxy_dict = self.proxy_manager.get_proxy()
        if proxy_dict:
            kwargs['proxies'] = proxy_dict
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        return self.session.request(method, url, **kwargs)

class JoobleAdapter(BaseAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.http_client = HTTPClient()
        
    async def fetch(self, query) -> List[UnifiedJob]:
        jobs = []
        if not self.api_key:
            logger.error("Jooble API Key missing.")
            return []

        payload = {'keywords': query.value, 'location': query.location or ''}
        try:
            response = self.http_client.request('POST', f'https://jooble.org/api/{self.api_key}', json=payload)
            if response.status_code != 200:
                logger.error(f"Jooble API returned status {response.status_code}")
                return []
                
            data = response.json()
            for job_data in data.get('jobs', []):
                jobs.append(UnifiedJob(
                    title=job_data.get('title', ''),
                    company=job_data.get('company', ''),
                    location=job_data.get('location', ''),
                    description=job_data.get('snippet', ''),
                    apply_link=job_data.get('link', ''),
                    raw_data=job_data
                ))
            time.sleep(1)
        except Exception as e:
            logger.error(f"Jooble fetch error: {e}")
        return jobs

class NaukriAdapter(BaseAdapter):
    def __init__(self):
        self.http_client = HTTPClient()
        
    async def fetch(self, query) -> List[UnifiedJob]:
        jobs = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'appid': '109',
            'systemid': '109'
        }
        params = {'noOfResults': 20, 'keyword': query.value, 'location': query.location or ''}
        
        try:
            response = self.http_client.request('GET', 'https://www.naukri.com/jobapi/v3/search', params=params, headers=headers)
            data = response.json()
            for job_data in data.get('jobDetails', []):
                salary_min, salary_max = self._parse_naukri_salary(job_data.get('salaryDetail', {}).get('label', ''))
                jobs.append(UnifiedJob(
                    title=job_data.get('title', ''),
                    company=job_data.get('companyName', ''),
                    location=', '.join(job_data.get('placeholders', [])),
                    description=job_data.get('jobDescription', ''),
                    external_id=job_data.get('jobId'),
                    apply_link=f"https://www.naukri.com/job-listings-{job_data.get('jobId', '')}",
                    salary_min=salary_min,
                    salary_max=salary_max,
                    raw_data=job_data
                ))
            
            delay = random.uniform(45, 90)
            logger.info(f"Naukri request complete. Pausing for {delay:.1f}s (anti-bot protection)")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Naukri fetch error: {e}")
        return jobs
    
    def _parse_naukri_salary(self, salary_text: str) -> tuple:
        if not salary_text: return None, None
        pattern = r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(lacs?|crores?)'
        match = re.search(pattern, salary_text.lower())
        if match:
            min_val, max_val = float(match.group(1)), float(match.group(2))
            multiplier = 100000 if 'lac' in match.group(3) else 10000000
            return int(min_val * multiplier), int(max_val * multiplier)
        return None, None

class LinkedInAdapter(BaseAdapter):
    def __init__(self):
        self.http_client = HTTPClient()
        
    async def fetch(self, query) -> List[UnifiedJob]:
        jobs = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        params = {'keywords': query.value, 'location': query.location or ''}
        
        try:
            response = self.http_client.request('GET', 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search', params=params, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            for card in soup.find_all('li'):
                title = card.find('h3', class_='base-search-card__title')
                company = card.find('h4', class_='base-search-card__subtitle')
                location = card.find('span', class_='job-search-card__location')
                link = card.find('a', class_='base-card__full-link')
                urn = card.get('data-entity-urn')
                
                if title and company and urn:
                    jobs.append(UnifiedJob(
                        title=title.get_text(strip=True),
                        company=company.get_text(strip=True),
                        location=location.get_text(strip=True) if location else "",
                        description='',
                        external_id=urn,
                        apply_link=link.get('href') if link else None,
                        raw_data={'data_entity_urn': urn}
                    ))
            
            delay = random.uniform(45, 90)
            logger.info(f"LinkedIn request complete. Pausing for {delay:.1f}s")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"LinkedIn fetch error: {e}")
        return jobs

class IndeedAdapter(BaseAdapter):
    def __init__(self):
        self.http_client = HTTPClient()
        
    async def fetch(self, query) -> List[UnifiedJob]:
        jobs = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        params = {'q': query.value, 'l': query.location or ''}
        
        try:
            response = self.http_client.request('GET', 'https://www.indeed.com/jobs', params=params, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            script = soup.find('script', {'id': 'mosaic-data'})
            if script and script.string:
                data = json.loads(script.string)
                results = data.get('metaData', {}).get('mosaicProviderJobCardsModel', {}).get('results', [])
                
                for r in results:
                    salary_min, salary_max = self._parse_indeed_salary(r.get('salarySnippet', {}).get('text', ''))
                    jobs.append(UnifiedJob(
                        title=r.get('title', ''),
                        company=r.get('company', ''),
                        location=r.get('formattedLocation', ''),
                        description=r.get('summary', ''),
                        external_id=r.get('jobkey'),
                        apply_link=f"https://www.indeed.com/viewjob?jk={r.get('jobkey', '')}",
                        salary_min=salary_min,
                        salary_max=salary_max,
                        currency='USD',
                        raw_data=r
                    ))
            
            delay = random.uniform(45, 90)
            logger.info(f"Indeed request complete. Pausing for {delay:.1f}s")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Indeed fetch error: {e}")
        return jobs

    def _parse_indeed_salary(self, text: str) -> tuple:
        if not text: return None, None
        match = re.search(r'\$([\d,]+)\s*-\s*\$([\d,]+)', text)
        if match:
            return int(match.group(1).replace(',', '')), int(match.group(2).replace(',', ''))
        return None, None