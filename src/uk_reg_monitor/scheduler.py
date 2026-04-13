"""Scheduler — runs regulatory checks on a configured schedule using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from uk_reg_monitor.client import check_all_acts
from uk_reg_monitor.notifier import notify

logger = logging.getLogger(__name__)

DAY_MAP = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
    "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
}


def run_check(config) -> list[dict]:
    """Execute a single check cycle: analyse all acts, then notify.

    Args:
        config: A Config instance or raw dict.

    Returns:
        List of material change result dicts.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("[%s] Running scheduled check...", timestamp)

    changes = check_all_acts(config)
    notify(config, changes)

    logger.info(
        "[%s] Check complete. %d material change(s) found.",
        timestamp, len(changes),
    )
    return changes


def _build_trigger(config) -> CronTrigger | IntervalTrigger:
    """Build an APScheduler trigger from the config schedule section.

    Args:
        config: A Config instance or raw dict.

    Returns:
        An APScheduler trigger matching the configured frequency.

    Raises:
        ValueError: If the frequency is not recognised.
    """
    if isinstance(config, dict):
        frequency = config["schedule"]["frequency"]
        time_str = config["schedule"].get("time", "08:00")
        day = config["schedule"].get("day", "monday")
    else:
        frequency = config.schedule_frequency
        time_str = config.schedule_time or "08:00"
        day = config.schedule_day or "monday"

    if frequency == "hourly":
        return IntervalTrigger(hours=1)

    hour, minute = time_str.split(":")

    if frequency == "daily":
        return CronTrigger(hour=int(hour), minute=int(minute))

    if frequency == "weekly":
        day_abbr = DAY_MAP[day.lower()]
        return CronTrigger(day_of_week=day_abbr, hour=int(hour), minute=int(minute))

    raise ValueError(f"Unknown schedule frequency: {frequency!r}")


def start_scheduler(config) -> None:
    """Start the blocking scheduler with the configured frequency.

    Runs an immediate check on startup, then schedules recurring checks
    according to the configured frequency (hourly, daily, or weekly).

    Args:
        config: A Config instance or raw dict.
    """
    trigger = _build_trigger(config)
    scheduler = BlockingScheduler()

    # Run immediately on startup
    run_check(config)

    scheduler.add_job(run_check, trigger, args=[config])

    if isinstance(config, dict):
        freq = config["schedule"]["frequency"]
    else:
        freq = config.schedule_frequency
    logger.info("Scheduler started — frequency: %s", freq)
    scheduler.start()
