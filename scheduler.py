#!/usr/bin/env python3
"""
Deal Hunter Scheduler
Runs deals_agent.py automatically every day at 9 AM IST.

HOW TO TEST RIGHT NOW:
    python scheduler.py --test
    (fires the agent immediately so you can confirm it works)

HOW TO RUN DAILY:
    python scheduler.py
    (keep this running - posts every day at 9 AM IST automatically)
"""

import sys
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from deals_agent import run_agent

# --- SCHEDULE CONFIG ----------------------------------------------------------
RUN_HOUR   = 9    # 9 AM IST  -- change this to any hour you want e.g. 8 or 10
RUN_MINUTE = 0    # 0 minutes -- change to e.g. 30 for 9:30 AM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


def job():
    log.info("Scheduled trigger fired - running Deal Hunter Agent ...")
    try:
        run_agent()
        log.info("Scheduled run completed OK")
    except Exception as e:
        log.error("Scheduled run failed: " + str(e))


if __name__ == "__main__":

    # --test flag: run immediately once and exit
    if "--test" in sys.argv:
        log.info("=== TEST MODE - running agent right now ===")
        job()
        log.info("=== TEST MODE complete - check your Telegram channel ===")
        sys.exit(0)

    # Normal mode: run daily at configured time
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        job,
        CronTrigger(hour=RUN_HOUR, minute=RUN_MINUTE, timezone="Asia/Kolkata"),
        id="daily_deals",
        name="Daily Deal Hunt",
        replace_existing=True,
    )

    log.info("Scheduler started - runs daily at " + str(RUN_HOUR) + ":00 AM IST")
    log.info("To change time: open scheduler.py in Notepad, change RUN_HOUR value, save")
    log.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
