"""Configuration loader — reads config.yaml and provides typed, validated access."""

from pathlib import Path

import yaml

VALID_FREQUENCIES = ("hourly", "daily", "weekly")

VALID_DAYS = (
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
)

EMAIL_REQUIRED_FIELDS = ("smtp_host", "smtp_port", "from_addr", "to_addrs")
SLACK_REQUIRED_FIELDS = ("webhook_url",)
WEBHOOK_REQUIRED_FIELDS = ("url",)

CHANNEL_REQUIRED_FIELDS = {
    "email": EMAIL_REQUIRED_FIELDS,
    "slack": SLACK_REQUIRED_FIELDS,
    "webhook": WEBHOOK_REQUIRED_FIELDS,
}


class Config:
    """Typed wrapper around the parsed config.yaml dictionary.

    Attributes:
        data: The raw parsed configuration dictionary.
    """

    def __init__(self, data: dict) -> None:
        """Initialise Config with a validated configuration dictionary.

        Args:
            data: Parsed and validated config dictionary.
        """
        self.data = data

    @property
    def api_base_url(self) -> str:
        """Return the base URL for the detector API."""
        return self.data["api"]["base_url"]

    @property
    def api_timeout(self) -> int:
        """Return the API request timeout in seconds."""
        return self.data["api"].get("timeout", 30)

    @property
    def schedule_frequency(self) -> str:
        """Return the schedule frequency: hourly, daily, or weekly."""
        return self.data["schedule"]["frequency"]

    @property
    def schedule_time(self) -> str | None:
        """Return the scheduled time (HH:MM) or None if not set."""
        return self.data["schedule"].get("time")

    @property
    def schedule_day(self) -> str | None:
        """Return the scheduled day of week or None if not set."""
        return self.data["schedule"].get("day")

    @property
    def acts(self) -> list[dict]:
        """Return the list of act dictionaries to monitor."""
        return self.data["acts"]

    @property
    def notifications(self) -> dict:
        """Return the notifications configuration section."""
        return self.data["notifications"]

    def enabled_channels(self) -> list[str]:
        """Return names of notification channels that are enabled."""
        channels = []
        for name, cfg in self.notifications.items():
            if isinstance(cfg, dict) and cfg.get("enabled"):
                channels.append(name)
        return channels

    def summary(self) -> str:
        """Return a human-readable summary of the configuration.

        Returns:
            Multi-line string summarising the loaded config.
        """
        lines = [
            f"API:        {self.api_base_url}",
            f"Timeout:    {self.api_timeout}s",
            f"Schedule:   {self.schedule_frequency}",
        ]
        if self.schedule_frequency in ("daily", "weekly"):
            lines.append(f"Time:       {self.schedule_time}")
        if self.schedule_frequency == "weekly":
            lines.append(f"Day:        {self.schedule_day}")
        lines.append(f"Acts:       {len(self.acts)}")
        for act in self.acts:
            lines.append(f"  - {act['name']} ({act['url']})")
        channels = self.enabled_channels()
        lines.append(f"Notify via: {', '.join(channels) if channels else 'none'}")
        return "\n".join(lines)


def load_config(path: str = "config.yaml") -> Config:
    """Load, validate, and return a Config object from a YAML file.

    Args:
        path: Path to the config.yaml file.

    Returns:
        Validated Config instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the file is not valid YAML.
        ValueError: If validation fails.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _validate(data)
    return Config(data)


def _validate(data: dict) -> None:
    """Validate the parsed configuration dictionary.

    Checks:
        - Required top-level keys are present
        - api.base_url is a non-empty string
        - At least one act is specified, each with url and name
        - schedule.frequency is one of: hourly, daily, weekly
        - daily/weekly schedules have required time/day fields
        - Enabled notification channels have all required fields

    Args:
        data: The parsed configuration dictionary.

    Raises:
        ValueError: If any validation check fails.
    """
    required_keys = ["api", "schedule", "acts", "notifications"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required config key: {key}")

    # API validation
    base_url = data["api"].get("base_url")
    if not base_url or not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("api.base_url must be a non-empty string")

    # Acts validation
    if not data["acts"]:
        raise ValueError("At least one act must be configured")
    for i, act in enumerate(data["acts"]):
        if not isinstance(act, dict):
            raise ValueError(f"acts[{i}] must be a mapping with 'url' and 'name' keys")
        if "url" not in act or not act["url"]:
            raise ValueError(f"acts[{i}].url is required")
        if "name" not in act or not act["name"]:
            raise ValueError(f"acts[{i}].name is required")

    # Schedule validation
    frequency = data["schedule"].get("frequency")
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(
            f"schedule.frequency must be one of {VALID_FREQUENCIES}, got: {frequency!r}"
        )
    if frequency in ("daily", "weekly"):
        time_str = data["schedule"].get("time")
        if not time_str:
            raise ValueError(f"schedule.time is required for frequency={frequency!r}")
        parts = time_str.split(":")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"schedule.time must be HH:MM format, got: {time_str!r}")
    if frequency == "weekly":
        day = data["schedule"].get("day")
        if not day or day.lower() not in VALID_DAYS:
            raise ValueError(
                f"schedule.day must be one of {VALID_DAYS}, got: {day!r}"
            )

    # Notification channel validation
    notifications = data.get("notifications", {})
    for channel_name, channel_cfg in notifications.items():
        if not isinstance(channel_cfg, dict):
            continue
        if not channel_cfg.get("enabled"):
            continue
        required = CHANNEL_REQUIRED_FIELDS.get(channel_name, ())
        for field in required:
            value = channel_cfg.get(field)
            if not value:
                raise ValueError(
                    f"notifications.{channel_name}.{field} is required when {channel_name} is enabled"
                )
