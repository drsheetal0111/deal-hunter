#!/usr/bin/env python3
"""
Deal Hunter Scheduler v2 - 4 Posts Daily
Runs deals_agent.py automatically 4 times every day:
  9:00 AM IST  - Morning
  1:00 PM IST  - Afternoon
  5:00 PM IST  - Evening
  9:00 PM IST  - Night

HOW TO TEST RIGHT NOW:
    python scheduler.py --test morning
    python scheduler.py --test afternoon
    python scheduler.py --test evening
    python scheduler.py --test night

HOW TO RUN DAILY (leave this window open):
    python scheduler.py
"""

import sys
import logging
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)


# ==============================================================================
#  SCHEDULE - 4 posts daily in IST
# ==============================================================================

SCHEDULE = [
    {"slot": "morning",   "hour": 9,  "minute": 0},
    {"slot": "afternoon", "hour": 13, "minute": 0},
    {"slot": "evening",   "hour": 17, "minute": 0},
    {"slot": "night",     "hour": 21, "minute": 0},
]


def run_slot(slot_name):
    """Runs deals_agent.py with the given slot name."""
    log.info("Running slot: " + slot_name)
    try:
        result = subprocess.run(
            [sys.executable, "deals_agent.py", slot_name],
            capture_output=False,
        )
        if result.returncode == 0:
            log.info("Slot " + slot_name + " completed OK")
        else:
            log.error("Slot " + slot_name + " failed with exit code " + str(result.returncode))
    except Exception as ex:
        log.error("Slot " + slot_name + " error: " + str(ex))


def make_job(slot_name):
    """Creates a job function for a given slot."""
    def job():
        log.info("Scheduled trigger fired for: " + slot_name)
        run_slot(slot_name)
    job.__name__ = "job_" + slot_name
    return job


if __name__ == "__main__":

    # --test flag: run a specific slot immediately and exit
    if "--test" in sys.argv:
        valid = ["morning", "afternoon", "evening", "night"]
        if len(sys.argv) < 3 or sys.argv[2] not in valid:
            print("Usage: python scheduler.py --test [morning|afternoon|evening|night]")
            print("Example: python scheduler.py --test afternoon")
            sys.exit(1)
        slot = sys.argv[2]
        log.info("=== TEST MODE - running " + slot + " slot now ===")
        run_slot(slot)
        log.info("=== TEST complete - check your Telegram channel ===")
        sys.exit(0)

    # Normal mode - schedule all 4 slots daily
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    for s in SCHEDULE:
        scheduler.add_job(
            make_job(s["slot"]),
            CronTrigger(hour=s["hour"], minute=s["minute"], timezone="Asia/Kolkata"),
            id="job_" + s["slot"],
            name=s["slot"] + " deals",
            replace_existing=True,
        )
        log.info("Scheduled: " + s["slot"] + " at " + str(s["hour"]) + ":00 IST")

    log.info("")
    log.info("All 4 slots scheduled:")
    log.info("  9:00 AM - Morning")
    log.info("  1:00 PM - Afternoon")
    log.info("  5:00 PM - Evening")
    log.info("  9:00 PM - Night")
    log.info("")
    log.info("Leave this window open to keep scheduler running")
    log.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")
