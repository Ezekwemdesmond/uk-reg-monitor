"""CLI entry point — provides start, check, and validate commands."""

import argparse
import logging
import sys

from uk_reg_monitor.config import load_config
from uk_reg_monitor.scheduler import run_check, start_scheduler


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

    subparsers.add_parser("start", help="Start the scheduled monitor.")
    subparsers.add_parser("check", help="Run a single immediate check and print results.")
    subparsers.add_parser("validate", help="Validate config and print a summary.")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

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
