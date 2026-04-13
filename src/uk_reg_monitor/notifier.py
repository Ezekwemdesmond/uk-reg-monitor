"""Notifier — routes material changes to email, Slack, or webhook."""

import json
import logging
import smtplib
from email.mime.text import MIMEText

import requests

logger = logging.getLogger(__name__)


class Notifier:
    """Routes material change notifications to all enabled channels.

    Attributes:
        config: A Config instance or raw dict with a notifications section.
    """

    def __init__(self, config) -> None:
        """Initialise with a config that contains notification settings.

        Args:
            config: A Config instance or raw dict.
        """
        self.config = config

    @property
    def _notifications(self) -> dict:
        """Return the notifications section from config."""
        if isinstance(self.config, dict):
            return self.config.get("notifications", {})
        return self.config.notifications

    def send(self, changes: list[dict]) -> None:
        """Send notifications for detected changes via all enabled channels.

        Args:
            changes: List of material change result dicts from the API.
        """
        if not changes:
            logger.info("No material changes — skipping notifications.")
            return

        notif = self._notifications

        if notif.get("email", {}).get("enabled"):
            _send_email(notif["email"], changes)

        if notif.get("slack", {}).get("enabled"):
            _send_slack(notif["slack"], changes)

        if notif.get("webhook", {}).get("enabled"):
            _send_webhook(notif["webhook"], changes)


def notify(config, changes: list[dict]) -> None:
    """Convenience function — wraps Notifier.send for backward compatibility.

    Args:
        config: A Config instance or raw dict.
        changes: List of material change result dicts.
    """
    Notifier(config).send(changes)


def _format_change_summary(changes: list[dict]) -> str:
    """Build a human-readable plain-text summary of detected changes.

    Args:
        changes: List of material change result dicts.

    Returns:
        Formatted text summary.
    """
    lines = [
        "UK Employment Law — Material Changes Detected",
        "=" * 47,
        "",
    ]
    for change in changes:
        act = change.get("act", change.get("act_name", "Unknown Act"))
        summary = change.get("summary", "No summary available.")
        lines.append(f"  {act}")
        lines.append(f"  {summary}")
        lines.append("")
    return "\n".join(lines)


def _send_email(email_cfg: dict, changes: list[dict]) -> None:
    """Send change notification via email using smtplib.

    Args:
        email_cfg: Email notification config section.
        changes: List of material change result dicts.
    """
    body = _format_change_summary(changes)
    msg = MIMEText(body)
    msg["Subject"] = "UK Regulatory Change Alert"
    msg["From"] = email_cfg["from_addr"]
    msg["To"] = ", ".join(email_cfg["to_addrs"])

    try:
        with smtplib.SMTP(email_cfg["smtp_host"], email_cfg["smtp_port"]) as server:
            if email_cfg.get("use_tls"):
                server.starttls()
            if email_cfg.get("username"):
                server.login(email_cfg["username"], email_cfg["password"])
            server.sendmail(
                email_cfg["from_addr"], email_cfg["to_addrs"], msg.as_string()
            )
        logger.info("Email notification sent.")
    except Exception:
        logger.exception("Failed to send email notification.")


def _send_slack(slack_cfg: dict, changes: list[dict]) -> None:
    """Send change notification to a Slack incoming webhook.

    Args:
        slack_cfg: Slack notification config section.
        changes: List of material change result dicts.
    """
    text = _format_change_summary(changes)
    try:
        response = requests.post(
            slack_cfg["webhook_url"],
            json={"text": text},
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Slack notification sent.")
    except requests.RequestException:
        logger.exception("Failed to send Slack notification.")


def _send_webhook(webhook_cfg: dict, changes: list[dict]) -> None:
    """Send change notification to a generic webhook endpoint.

    Args:
        webhook_cfg: Webhook notification config section.
        changes: List of material change result dicts.
    """
    payload = {"changes": changes}
    try:
        response = requests.request(
            method=webhook_cfg.get("method", "POST"),
            url=webhook_cfg["url"],
            headers=webhook_cfg.get("headers", {}),
            data=json.dumps(payload),
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Webhook notification sent.")
    except requests.RequestException:
        logger.exception("Failed to send webhook notification.")
