"""Scheduler — runs analysis during SET market hours (Mon-Fri 9:30-16:30 ICT)."""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def run_scan():
    """Run full watchlist scan."""
    logger.info("Starting scheduled scan at %s", datetime.now().isoformat())
    from agents.orchestrator import scan_watchlist

    try:
        results = scan_watchlist()
        logger.info("Scan complete: %d stocks analyzed", len(results))

        # Check for alerts
        for result in results:
            score = result.get("scoring", {}).get("composite_score", 0)
            symbol = result["symbol"]
            if abs(score) > 60:
                logger.info("ALERT: %s has composite score %s", symbol, score)
                # TODO: Trigger alert via alert_agent
    except Exception as e:
        logger.error("Scheduled scan failed: %s", e)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    scheduler = BlockingScheduler(timezone="Asia/Bangkok")

    # Run every 30 minutes during market hours (Mon-Fri, 9:30-16:30 ICT)
    scheduler.add_job(
        run_scan,
        CronTrigger(
            day_of_week="mon-fri",
            hour="9-16",
            minute="0,30",
            timezone="Asia/Bangkok",
        ),
        id="market_scan",
        name="SET Market Scan",
    )

    logger.info("Scheduler started. Waiting for market hours...")
    logger.info("Schedule: Mon-Fri, every 30 min, 9:00-16:30 ICT")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
