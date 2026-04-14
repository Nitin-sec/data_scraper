import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

from telegram_engine import run_telegram_engine
from linkedin_engine import run_linkedin_engine
from indeed_engine import run_indeed_engine

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Scheduler")


ENGINES = [
    ("Telegram", run_telegram_engine),
    ("LinkedIn", run_linkedin_engine),
    ("Indeed", run_indeed_engine),
]


class Scheduler:
    def __init__(self):
        self.running = True
        interval_ms = int(os.getenv('SCHEDULE_INTERVAL_MS', 21600000))
        self.interval_seconds = interval_ms / 1000

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info(f"Scheduler initialized - interval={self.interval_seconds / 3600:.1f}h")
        self._log_engine_status()

    def _log_engine_status(self):
        status = []
        if os.getenv('TELEGRAM_API_ID') and os.getenv('TELEGRAM_SESSION_STRING'):
            status.append("Telegram: enabled")
        else:
            status.append("Telegram: disabled (missing credentials)")

        status.append("LinkedIn: enabled (jobspy)")
        status.append("Indeed: enabled (jobspy)")

        for s in status:
            logger.info(s)

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal received")
        self.running = False

    async def _run_cycle(self):
        start = datetime.now(timezone.utc)

        for name, engine_fn in ENGINES:
            logger.info(f"Starting {name} engine")
            try:
                await engine_fn()
                logger.info(f"{name} engine finished")
            except Exception as e:
                logger.error(f"{name} engine failed: {e}")

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        next_run = start + timedelta(seconds=self.interval_seconds + elapsed)
        logger.info(f"Cycle complete in {elapsed:.1f}s - next run at {next_run.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    async def _sleep(self, seconds: float):
        end = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        while datetime.now(timezone.utc) < end and self.running:
            await asyncio.sleep(1)

    async def start(self):
        logger.info("Scheduler started")
        while self.running:
            try:
                await self._run_cycle()
                await self._sleep(self.interval_seconds)
            except Exception as e:
                logger.error(f"Unexpected scheduler error: {e}")
                await self._sleep(60)

        logger.info("Scheduler stopped")


async def main():
    scheduler = Scheduler()
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopped by user")


if __name__ == "__main__":
    asyncio.run(main())
