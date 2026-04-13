"""Tests for uk_reg_monitor.scheduler."""

from unittest.mock import patch

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from uk_reg_monitor.scheduler import _build_trigger, run_check


def _make_config(frequency="daily", time="08:00", day="monday"):
    """Build a minimal config dict for scheduler tests."""
    return {
        "api": {"base_url": "https://api.example.com", "timeout": 5},
        "acts": [{"url": "https://leg.gov.uk/1", "name": "Test Act"}],
        "notifications": {},
        "schedule": {"frequency": frequency, "time": time, "day": day},
    }


@patch("uk_reg_monitor.scheduler.notify")
@patch("uk_reg_monitor.scheduler.check_all_acts")
def test_run_check_calls_notify(mock_check, mock_notify):
    """run_check passes API results to notify."""
    mock_check.return_value = [{"act": "Test Act", "material_change": True}]
    config = _make_config()
    run_check(config)
    mock_check.assert_called_once_with(config)
    mock_notify.assert_called_once_with(config, mock_check.return_value)


@patch("uk_reg_monitor.scheduler.notify")
@patch("uk_reg_monitor.scheduler.check_all_acts")
def test_run_check_returns_changes(mock_check, mock_notify):
    """run_check returns the list of changes."""
    expected = [{"act": "Test", "material_change": True}]
    mock_check.return_value = expected
    result = run_check(_make_config())
    assert result == expected


@patch("uk_reg_monitor.scheduler.notify")
@patch("uk_reg_monitor.scheduler.check_all_acts")
def test_run_check_no_changes(mock_check, mock_notify):
    """run_check still calls notify when no changes found."""
    mock_check.return_value = []
    config = _make_config()
    run_check(config)
    mock_notify.assert_called_once_with(config, [])


def test_build_trigger_hourly():
    """Hourly frequency builds an IntervalTrigger."""
    trigger = _build_trigger(_make_config(frequency="hourly"))
    assert isinstance(trigger, IntervalTrigger)


def test_build_trigger_daily():
    """Daily frequency builds a CronTrigger at the specified time."""
    trigger = _build_trigger(_make_config(frequency="daily", time="09:30"))
    assert isinstance(trigger, CronTrigger)


def test_build_trigger_weekly():
    """Weekly frequency builds a CronTrigger on the specified day and time."""
    trigger = _build_trigger(_make_config(frequency="weekly", time="14:00", day="friday"))
    assert isinstance(trigger, CronTrigger)
