import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from telegram_engine import run_telegram_engine
from jooble_engine import run_jooble_engine
from remotive_engine import run_remotive_engine
# from wellfound_engine import run_wellfound_engine  # Disabled: API blocked
from adzuna_engine import run_adzuna_engine

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Scheduler")

class MinimalScheduler:
    def __init__(self):
        self.running = True
        self.interval_ms = int(os.getenv('SCHEDULE_INTERVAL_MS', 21600000))  # Default 6 hours
        self.interval_seconds = self.interval_ms / 1000
        
        # Log environment loading
        logger.info("Loaded environment variables from .env")
        self._log_enabled_engines()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
    
    def _log_enabled_engines(self):
        """Log which engines are enabled based on available API keys"""
        enabled_engines = []
        
        # Check Telegram
        if os.getenv('TELEGRAM_API_ID') and os.getenv('TELEGRAM_API_HASH') and os.getenv('TELEGRAM_SESSION_STRING'):
            enabled_engines.append('Telegram')
        
        # Check Jooble
        if os.getenv('JOOBLE_API_KEY'):
            enabled_engines.append('Jooble')
        
        # Remotive and Adzuna don't need keys
        enabled_engines.extend(['Remotive', 'Adzuna'])
        
        # Wellfound disabled (403, will be re-enabled during scraping phase)
        logger.info("Wellfound disabled (403, will be re-enabled during scraping phase)")
        
        logger.info(f"Enabled engines: {', '.join(enabled_engines)}")
    
    def _shutdown_handler(self, signum, frame):
        logger.info("Shutdown signal received. Stopping scheduler...")
        self.running = False
    
    async def start(self):
        """Main scheduler loop"""
        logger.info(f"Minimal Scheduler started - Active engines (Interval: {self.interval_seconds/3600:.1f}h)")
        
        while self.running:
            try:
                # Log start
                start_time = datetime.now()
                
                # Run Telegram engine
                logger.info("Running Telegram cycle")
                await run_telegram_engine()
                
                # Run Jooble engine
                logger.info("Running Jooble cycle")
                await run_jooble_engine()
                
                # Run Remotive engine
                logger.info("Running Remotive cycle")
                await run_remotive_engine()
                
                # Wellfound disabled (403, will be re-enabled during scraping phase)
                # logger.info("Running Wellfound cycle")
                # await run_wellfound_engine()
                
                # Run Adzuna engine
                logger.info("Running Adzuna cycle")
                await run_adzuna_engine()
                
                # Log end and next run time
                end_time = datetime.now()
                next_run = end_time + timedelta(seconds=self.interval_seconds)
                logger.info(f"All cycles completed in {(end_time - start_time).total_seconds():.1f}s")
                logger.info(f"Next run in {self.interval_seconds/3600:.1f} hours at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Sleep until next cycle
                await self._smart_sleep(self.interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in scheduler cycle: {e}")
                # Wait a bit before retrying
                await self._smart_sleep(60)
    
    async def _smart_sleep(self, seconds):
        """Sleep in short bursts to allow for rapid shutdown"""
        end_time = datetime.now() + timedelta(seconds=seconds)
        while datetime.now() < end_time and self.running:
            await asyncio.sleep(1)

async def main():
    scheduler = MinimalScheduler()
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    finally:
        logger.info("Scheduler shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())