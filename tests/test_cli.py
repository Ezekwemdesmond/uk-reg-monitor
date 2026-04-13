"""Tests for uk_reg_monitor.cli."""

from unittest.mock import patch, MagicMock

import pytest

from uk_reg_monitor.cli import main


def test_cli_missing_config(monkeypatch):
    """CLI exits with error when config file is missing."""
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "--config", "nonexistent.yaml", "start"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


@patch("uk_reg_monitor.cli.run_check")
@patch("uk_reg_monitor.cli.load_config")
def test_cli_check_command(mock_load, mock_run, monkeypatch):
    """'check' command runs a single check and returns."""
    mock_config = MagicMock()
    mock_load.return_value = mock_config
    mock_run.return_value = []
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "check"])
    main()
    mock_run.assert_called_once_with(mock_config)


@patch("uk_reg_monitor.cli.start_scheduler")
@patch("uk_reg_monitor.cli.load_config")
def test_cli_start_command(mock_load, mock_sched, monkeypatch):
    """'start' command starts the scheduler."""
    mock_config = MagicMock()
    mock_load.return_value = mock_config
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "start"])
    main()
    mock_sched.assert_called_once_with(mock_config)


@patch("uk_reg_monitor.cli.load_config")
def test_cli_validate_command(mock_load, monkeypatch, capsys):
    """'validate' command prints config summary."""
    mock_config = MagicMock()
    mock_config.summary.return_value = "API: https://api.example.com\nActs: 2"
    mock_load.return_value = mock_config
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "validate"])
    main()
    captured = capsys.readouterr()
    assert "valid" in captured.out.lower()
    assert "api.example.com" in captured.out


@patch("uk_reg_monitor.cli.run_check")
@patch("uk_reg_monitor.cli.load_config")
def test_cli_check_prints_changes(mock_load, mock_run, monkeypatch, capsys):
    """'check' command prints detected changes."""
    mock_config = MagicMock()
    mock_load.return_value = mock_config
    mock_run.return_value = [
        {"act": "Equality Act 2010", "summary": "Section 9 amended."},
    ]
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "check"])
    main()
    captured = capsys.readouterr()
    assert "Equality Act 2010" in captured.out


def test_cli_no_command_shows_error(monkeypatch):
    """Missing subcommand causes SystemExit."""
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor"])
    with pytest.raises(SystemExit):
        main()
