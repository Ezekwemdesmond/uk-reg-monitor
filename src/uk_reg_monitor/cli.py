"""CLI entry point — provides init, start, check, and validate commands."""

import argparse
import getpass
import logging
import sys

import yaml

from uk_reg_monitor.config import load_config
from uk_reg_monitor.scheduler import run_check, start_scheduler

_WIZARD_ACTS = [
    {
        "name": "Employment Rights Act 1996",
        "url": "https://www.legislation.gov.uk/ukpga/1996/18",
    },
    {
        "name": "National Minimum Wage Act 1998",
        "url": "https://www.legislation.gov.uk/ukpga/1998/39",
    },
    {
        "name": "Equality Act 2010",
        "url": "https://www.legislation.gov.uk/ukpga/2010/15",
    },
    {
        "name": "Working Time Regulations 1998",
        "url": "https://www.legislation.gov.uk/uksi/1998/1833",
    },
]

_VALID_DAYS = (
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
)


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        prog="uk-reg-monitor",
        description="Monitor UK employment legislation for material changes.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: ./config.yaml).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    subparsers.add_parser("init", help="Run the interactive setup wizard.")
    subparsers.add_parser("start", help="Start the scheduled monitor.")
    subparsers.add_parser("check", help="Run a single immediate check and print results.")
    subparsers.add_parser("validate", help="Validate config and print a summary.")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "init":
        _cmd_init(args.config)
        return

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("Configuration error: %s", exc)
        sys.exit(1)

    if args.command == "validate":
        _cmd_validate(config)
    elif args.command == "check":
        _cmd_check(config)
    elif args.command == "start":
        _cmd_start(config)


def _cmd_init(config_path: str) -> None:
    """Run the interactive setup wizard to generate config.yaml.

    Args:
        config_path: Default destination path for the generated config file.
    """
    _run_wizard(config_path)


def _run_wizard(config_path: str) -> None:
    """Interactive setup wizard — collects settings and writes config.yaml.

    Prompts the user for Acts to monitor, schedule frequency, notification
    channels, and a save path.  Writes the resulting config and validates it.

    Args:
        config_path: Default destination path for the generated config file.
    """
    print()
    print("Welcome to uk-reg-monitor!")
    print("This wizard will create your config.yaml.  uk-reg-monitor connects")
    print("to the UK Employment Law Change Detector API, monitors Acts of")
    print("Parliament on a schedule, and notifies your team when material")
    print("legislative changes are detected.")
    print()

    # --- Step 2: Acts ---
    print("Which Acts would you like to monitor?")
    for i, act in enumerate(_WIZARD_ACTS, 1):
        print(f"  [{i}] {act['name']}")
    print("  [5] All of the above (default)")
    print()

    while True:
        raw = input("Enter choice(s) separated by commas [5]: ").strip()
        if not raw:
            raw = "5"
        if raw == "5":
            selected_acts = list(_WIZARD_ACTS)
            break
        parts = [p.strip() for p in raw.split(",")]
        try:
            indices = [int(p) for p in parts if p]
        except ValueError:
            print("  Invalid input — enter numbers separated by commas (e.g. 1,3).")
            continue
        if any(i < 1 or i > 5 for i in indices):
            print("  Invalid choice — pick numbers between 1 and 5.")
            continue
        if 5 in indices:
            selected_acts = list(_WIZARD_ACTS)
        else:
            selected_acts = [_WIZARD_ACTS[i - 1] for i in sorted(set(indices))]
        break

    print()

    # --- Step 3: Schedule frequency ---
    print("How often should checks run?")
    print("  [1] Hourly")
    print("  [2] Daily at a specific time (default)")
    print("  [3] Weekly on a specific day")
    print()

    while True:
        raw = input("Enter choice [2]: ").strip()
        if not raw:
            raw = "2"
        if raw in ("1", "2", "3"):
            freq_choice = raw
            break
        print("  Invalid choice — enter 1, 2, or 3.")

    # --- Step 4: Time / day ---
    schedule: dict = {}
    if freq_choice == "1":
        schedule["frequency"] = "hourly"
    elif freq_choice == "2":
        schedule["frequency"] = "daily"
        schedule["time"] = _prompt_time("What time should checks run? (HH:MM) [08:00]: ")
    else:
        schedule["frequency"] = "weekly"
        schedule["day"] = _prompt_day()
        schedule["time"] = _prompt_time("What time should checks run? (HH:MM) [08:00]: ")

    print()

    # --- Step 5: Notifications ---
    notifications: dict = {
        "email": {
            "enabled": False,
            "smtp_host": "",
            "smtp_port": 587,
            "use_tls": True,
            "username": "",
            "password": "",
            "from_addr": "",
            "to_addrs": [],
        },
        "slack": {"enabled": False, "webhook_url": ""},
        "webhook": {
            "enabled": False,
            "url": "",
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
        },
    }

    print("How would you like to be notified?")
    print("  [1] Email")
    print("  [2] Slack webhook")
    print("  [3] HTTP webhook")
    print("  [4] Skip for now (default)")
    print()

    while True:
        raw = input("Enter choice [4]: ").strip()
        if not raw:
            raw = "4"
        if raw in ("1", "2", "3", "4"):
            notif_choice = raw
            break
        print("  Invalid choice — enter 1, 2, 3, or 4.")

    if notif_choice == "1":
        print()
        smtp_host = input("SMTP host: ").strip()
        smtp_port = _prompt_int("SMTP port [587]: ", default=587)
        username = input("SMTP username: ").strip()
        password = getpass.getpass("SMTP password: ")
        from_addr = input("From address: ").strip()
        to_addr = input("To address: ").strip()
        notifications["email"].update({
            "enabled": True,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_addr": from_addr,
            "to_addrs": [to_addr],
        })
    elif notif_choice == "2":
        print()
        webhook_url = input("Slack webhook URL: ").strip()
        notifications["slack"].update({"enabled": True, "webhook_url": webhook_url})
    elif notif_choice == "3":
        print()
        url = input("Webhook URL: ").strip()
        notifications["webhook"].update({"enabled": True, "url": url})

    print()

    # --- Step 6: Save path ---
    raw = input(f"Where should the config be saved? [{config_path}]: ").strip()
    save_path = raw if raw else config_path

    # --- Step 7: Write config ---
    data = {
        "api": {
            "base_url": "https://uk-employment-law-change-detector.onrender.com",
            "timeout": 30,
        },
        "schedule": schedule,
        "acts": selected_acts,
        "notifications": notifications,
    }

    with open(save_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print()
    print(f"Config saved to {save_path}")

    # --- Step 8: Validate ---
    try:
        load_config(save_path)
        print("Configuration is valid.")
    except (FileNotFoundError, ValueError) as exc:
        print(f"Warning: configuration validation failed — {exc}")

    # --- Step 9: Next steps ---
    print()
    print("Next steps:")
    print("  uk-reg-monitor check   — run an immediate check")
    print("  uk-reg-monitor start   — begin scheduled monitoring")


def _prompt_time(prompt: str, default: str = "08:00") -> str:
    """Prompt for a time in HH:MM format, re-prompting on invalid input.

    Args:
        prompt: The prompt string to display.
        default: Default value if the user presses Enter.

    Returns:
        A valid HH:MM time string.
    """
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        parts = raw.split(":")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            return raw
        print("  Invalid time — use HH:MM format (e.g. 08:00).")


def _prompt_day(default: str = "monday") -> str:
    """Prompt for a day of the week, re-prompting on invalid input.

    Args:
        default: Default value if the user presses Enter.

    Returns:
        A lowercase day-of-week string.
    """
    while True:
        raw = input(f"What day of the week? [{default}]: ").strip().lower()
        if not raw:
            return default
        if raw in _VALID_DAYS:
            return raw
        print(f"  Invalid day — choose from: {', '.join(_VALID_DAYS)}.")


def _prompt_int(prompt: str, default: int) -> int:
    """Prompt for an integer, re-prompting on invalid input.

    Args:
        prompt: The prompt string to display.
        default: Default value if the user presses Enter.

    Returns:
        A valid integer.
    """
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        if raw.isdigit():
            return int(raw)
        print("  Invalid value — enter a whole number.")


def _cmd_validate(config) -> None:
    """Print a configuration summary and exit.

    Args:
        config: A validated Config instance.
    """
    print("Configuration is valid.\n")
    print(config.summary())


def _cmd_check(config) -> None:
    """Run a single check across all configured acts and print results.

    Args:
        config: A validated Config instance.
    """
    changes = run_check(config)
    if not changes:
        print("No material changes detected.")
    else:
        print(f"\n{len(changes)} material change(s) detected:\n")
        for change in changes:
            act = change.get("act", change.get("act_name", "Unknown"))
            summary = change.get("summary", "No summary.")
            print(f"  - {act}: {summary}")


def _cmd_start(config) -> None:
    """Start the scheduled monitor.

    Args:
        config: A validated Config instance.
    """
    start_scheduler(config)


if __name__ == "__main__":
    main()
