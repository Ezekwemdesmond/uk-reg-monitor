"""Tests for uk_reg_monitor.config."""

import pytest
import yaml

from uk_reg_monitor.config import Config, load_config


def _write_config(tmp_path, cfg, filename="config.yaml"):
    """Write a config dict to a YAML file and return its path."""
    path = tmp_path / filename
    path.write_text(yaml.dump(cfg))
    return str(path)


def _valid_cfg(**overrides):
    """Return a minimal valid config dict, with optional overrides."""
    cfg = {
        "api": {"base_url": "https://api.example.com", "timeout": 10},
        "schedule": {"frequency": "daily", "time": "08:00"},
        "acts": [{"url": "https://legislation.gov.uk/1996/18", "name": "ERA 1996"}],
        "notifications": {
            "email": {"enabled": False},
            "slack": {"enabled": False},
            "webhook": {"enabled": False},
        },
    }
    cfg.update(overrides)
    return cfg


# --- Loading ---

def test_load_valid_config(tmp_path):
    """Valid config loads without error and returns a Config instance."""
    path = _write_config(tmp_path, _valid_cfg())
    config = load_config(path)
    assert isinstance(config, Config)
    assert config.api_base_url == "https://api.example.com"
    assert len(config.acts) == 1


def test_missing_file_raises():
    """FileNotFoundError when config file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent.yaml")


def test_missing_key_raises(tmp_path):
    """ValueError when a required top-level key is absent."""
    path = _write_config(tmp_path, {"api": {}})
    with pytest.raises(ValueError, match="Missing required config key"):
        load_config(path)


# --- API validation ---

def test_missing_base_url_raises(tmp_path):
    """ValueError when api.base_url is missing."""
    cfg = _valid_cfg()
    cfg["api"] = {"timeout": 10}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="api.base_url"):
        load_config(path)


def test_empty_base_url_raises(tmp_path):
    """ValueError when api.base_url is empty string."""
    cfg = _valid_cfg()
    cfg["api"]["base_url"] = ""
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="api.base_url"):
        load_config(path)


# --- Acts validation ---

def test_empty_acts_raises(tmp_path):
    """ValueError when acts list is empty."""
    path = _write_config(tmp_path, _valid_cfg(acts=[]))
    with pytest.raises(ValueError, match="At least one act"):
        load_config(path)


def test_act_missing_url_raises(tmp_path):
    """ValueError when an act has no url."""
    path = _write_config(tmp_path, _valid_cfg(acts=[{"name": "Test"}]))
    with pytest.raises(ValueError, match="url is required"):
        load_config(path)


def test_act_missing_name_raises(tmp_path):
    """ValueError when an act has no name."""
    path = _write_config(tmp_path, _valid_cfg(acts=[{"url": "https://example.com"}]))
    with pytest.raises(ValueError, match="name is required"):
        load_config(path)


# --- Schedule validation ---

def test_invalid_frequency_raises(tmp_path):
    """ValueError for unrecognised schedule frequency."""
    cfg = _valid_cfg()
    cfg["schedule"] = {"frequency": "biweekly"}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="frequency"):
        load_config(path)


def test_daily_requires_time(tmp_path):
    """ValueError when daily frequency has no time."""
    cfg = _valid_cfg()
    cfg["schedule"] = {"frequency": "daily"}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="schedule.time"):
        load_config(path)


def test_weekly_requires_day(tmp_path):
    """ValueError when weekly frequency has no day."""
    cfg = _valid_cfg()
    cfg["schedule"] = {"frequency": "weekly", "time": "08:00"}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="schedule.day"):
        load_config(path)


def test_weekly_invalid_day_raises(tmp_path):
    """ValueError when weekly day is not a valid day of week."""
    cfg = _valid_cfg()
    cfg["schedule"] = {"frequency": "weekly", "time": "08:00", "day": "funday"}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="schedule.day"):
        load_config(path)


def test_hourly_does_not_require_time(tmp_path):
    """Hourly frequency loads without time or day."""
    cfg = _valid_cfg()
    cfg["schedule"] = {"frequency": "hourly"}
    path = _write_config(tmp_path, cfg)
    config = load_config(path)
    assert config.schedule_frequency == "hourly"


# --- Notification channel validation ---

def test_enabled_email_missing_field_raises(tmp_path):
    """ValueError when email is enabled but smtp_host is missing."""
    cfg = _valid_cfg()
    cfg["notifications"]["email"] = {"enabled": True}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="email.smtp_host"):
        load_config(path)


def test_enabled_slack_missing_webhook_raises(tmp_path):
    """ValueError when slack is enabled but webhook_url is missing."""
    cfg = _valid_cfg()
    cfg["notifications"]["slack"] = {"enabled": True}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="slack.webhook_url"):
        load_config(path)


def test_enabled_webhook_missing_url_raises(tmp_path):
    """ValueError when webhook is enabled but url is missing."""
    cfg = _valid_cfg()
    cfg["notifications"]["webhook"] = {"enabled": True}
    path = _write_config(tmp_path, cfg)
    with pytest.raises(ValueError, match="webhook.url"):
        load_config(path)


def test_disabled_channel_skips_validation(tmp_path):
    """Disabled channels are not validated for required fields."""
    cfg = _valid_cfg()
    cfg["notifications"]["email"] = {"enabled": False}  # no smtp_host etc.
    path = _write_config(tmp_path, cfg)
    config = load_config(path)
    assert config.enabled_channels() == []


# --- Config properties ---

def test_config_summary(tmp_path):
    """Config.summary() returns a readable string."""
    path = _write_config(tmp_path, _valid_cfg())
    config = load_config(path)
    text = config.summary()
    assert "api.example.com" in text
    assert "ERA 1996" in text
    assert "daily" in text


def test_enabled_channels(tmp_path):
    """enabled_channels() returns only channels with enabled=True."""
    cfg = _valid_cfg()
    cfg["notifications"]["slack"] = {"enabled": True, "webhook_url": "https://hooks.slack.com/x"}
    path = _write_config(tmp_path, cfg)
    config = load_config(path)
    assert "slack" in config.enabled_channels()
    assert "email" not in config.enabled_channels()
