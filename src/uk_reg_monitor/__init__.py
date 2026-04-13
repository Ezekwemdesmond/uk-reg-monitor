"""uk-reg-monitor — UK regulatory change monitoring client.

Public API:
    Config   — load and validate config.yaml
    Monitor  — orchestrate scheduled checks
    Notifier — route change notifications to enabled channels
"""

__version__ = "0.1.0"

from uk_reg_monitor.config import Config, load_config
from uk_reg_monitor.notifier import Notifier
from uk_reg_monitor.scheduler import run_check, start_scheduler


class Monitor:
    """High-level API for running regulatory change checks.

    Combines configuration, API calls, and notification dispatch
    into a single interface.

    Attributes:
        config: A Config instance with validated settings.
        notifier: A Notifier instance bound to the same config.
    """

    def __init__(self, config: Config) -> None:
        """Initialise the Monitor with a Config instance.

        Args:
            config: A validated Config instance.
        """
        self.config = config
        self.notifier = Notifier(config)

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Monitor":
        """Create a Monitor by loading a config file.

        Args:
            path: Path to the config.yaml file.

        Returns:
            A configured Monitor instance.
        """
        return cls(load_config(path))

    def check(self) -> list[dict]:
        """Run a single check across all configured acts.

        Returns:
            List of material change result dicts.
        """
        return run_check(self.config)

    def start(self) -> None:
        """Start the blocking scheduled monitor."""
        start_scheduler(self.config)


__all__ = ["Config", "Monitor", "Notifier", "load_config", "__version__"]
