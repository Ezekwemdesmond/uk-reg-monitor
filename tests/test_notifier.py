"""Tests for uk_reg_monitor.notifier."""

import logging

import responses

from uk_reg_monitor.notifier import Notifier, _format_change_summary, notify


def _make_config(email=False, slack=False, webhook=False, webhook_url="https://hook.example.com"):
    """Build a minimal config dict with the given notification channels enabled."""
    return {
        "notifications": {
            "email": {
                "enabled": email,
                "smtp_host": "smtp.example.com",
                "smtp_port": 587,
                "use_tls": False,
                "username": "",
                "password": "",
                "from_addr": "test@example.com",
                "to_addrs": ["dest@example.com"],
            },
            "slack": {
                "enabled": slack,
                "webhook_url": "https://hooks.slack.com/test",
            },
            "webhook": {
                "enabled": webhook,
                "url": webhook_url,
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
            },
        }
    }


SAMPLE_CHANGES = [
    {"act": "Equality Act 2010", "material_change": True, "summary": "Section 9 amended."},
]


def test_format_change_summary():
    """Summary includes act name and description."""
    text = _format_change_summary(SAMPLE_CHANGES)
    assert "Equality Act 2010" in text
    assert "Section 9 amended." in text


def test_format_change_summary_includes_header():
    """Summary starts with a descriptive header."""
    text = _format_change_summary(SAMPLE_CHANGES)
    assert "Material Changes Detected" in text


def test_notify_no_changes_does_nothing(caplog):
    """No notifications sent when changes list is empty."""
    config = _make_config(email=True)
    with caplog.at_level(logging.INFO):
        notify(config, [])
    assert "skipping" in caplog.text.lower()


@responses.activate
def test_notify_slack():
    """Slack webhook is called when enabled."""
    responses.post("https://hooks.slack.com/test", status=200)
    config = _make_config(slack=True)
    notify(config, SAMPLE_CHANGES)
    assert len(responses.calls) == 1


@responses.activate
def test_notify_webhook():
    """Generic webhook is called when enabled."""
    responses.post("https://hook.example.com", status=200)
    config = _make_config(webhook=True)
    notify(config, SAMPLE_CHANGES)
    assert len(responses.calls) == 1


@responses.activate
def test_notifier_class_send():
    """Notifier class sends to enabled channels."""
    responses.post("https://hooks.slack.com/test", status=200)
    config = _make_config(slack=True)
    notifier = Notifier(config)
    notifier.send(SAMPLE_CHANGES)
    assert len(responses.calls) == 1


def test_notifier_class_send_no_changes(caplog):
    """Notifier.send() skips when no changes."""
    config = _make_config()
    notifier = Notifier(config)
    with caplog.at_level(logging.INFO):
        notifier.send([])
    assert "skipping" in caplog.text.lower()
