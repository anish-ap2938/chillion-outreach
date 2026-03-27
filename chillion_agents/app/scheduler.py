"""
Simple scheduler for periodic social scans (local-only, optional).
Run with: `python -m app.scheduler`
"""

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.lead_generation.social.twitter import TwitterScraper
from app.lead_generation.social.reddit import RedditScraper
from app.lead_generation.social.forums import ForumScraper
from app.lead_generation.storage.database import LeadDatabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def run_social_scan():
    db = LeadDatabase()
    db.initialize()
    twitter = TwitterScraper()
    reddit = RedditScraper()
    forums = ForumScraper()

    leads = []
    try:
        leads.extend(twitter.search_all_queries(max_results_per_query=25))
        leads.extend(reddit.search_all_queries(max_results_per_query=25))
        leads.extend(forums.search("accounts receivable automation", max_results=25))
    except Exception as e:
        logger.error(f"Social scan error: {e}")

    if leads:
        result = db.insert_social_leads_batch(leads)
        logger.info(f"Social scan inserted={result['inserted']} duplicates={result['duplicates']}")
    else:
        logger.info("Social scan found no leads")


def start_scheduler():
    sched = AsyncIOScheduler()
    # Every hour
    sched.add_job(lambda: asyncio.ensure_future(run_social_scan()), "interval", minutes=60, next_run_time=datetime.now())
    sched.start()
    logger.info("Scheduler started (hourly social scan)")

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()


if __name__ == "__main__":
    start_scheduler()

