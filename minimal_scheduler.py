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
from wellfound_engine import run_wellfound_engine

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
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)
    
    def _shutdown_handler(self, signum, frame):
        logger.info("Shutdown signal received. Stopping scheduler...")
        self.running = False
    
    async def start(self):
        """Main scheduler loop"""
        logger.info(f"Minimal Scheduler started - All engines (Interval: {self.interval_seconds/3600:.1f}h)")
        
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
                
                # Run Wellfound engine
                logger.info("Running Wellfound cycle")
                await run_wellfound_engine()
                
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