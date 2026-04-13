"""Tests for uk_reg_monitor.cli."""

from unittest.mock import patch, MagicMock

import pytest
import yaml

from uk_reg_monitor.cli import main, _run_wizard


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


# ---------------------------------------------------------------------------
# init / wizard tests
# ---------------------------------------------------------------------------

def test_init_command_registered(monkeypatch, tmp_path):
    """init subcommand is wired into main() and writes a config file."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter(["", "", "", "", save_path])
    monkeypatch.setattr("sys.argv", ["uk-reg-monitor", "init"])
    with patch("builtins.input", side_effect=inputs):
        with patch("uk_reg_monitor.cli.getpass.getpass", return_value=""):
            main()
    assert (tmp_path / "config.yaml").exists()


def test_init_defaults_creates_valid_config(tmp_path):
    """All-default answers (Enter on every prompt) produce a valid config."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter(["", "", "", "", save_path])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    from uk_reg_monitor.config import load_config
    cfg = load_config(save_path)
    assert cfg.schedule_frequency == "daily"
    assert cfg.schedule_time == "08:00"
    assert len(cfg.acts) == 4


def test_init_selects_specific_acts(tmp_path):
    """Entering '1,3' selects Employment Rights Act and Equality Act only."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter(["1,3", "", "", "", save_path])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    from uk_reg_monitor.config import load_config
    cfg = load_config(save_path)
    assert len(cfg.acts) == 2
    assert cfg.acts[0]["name"] == "Employment Rights Act 1996"
    assert cfg.acts[1]["name"] == "Equality Act 2010"


def test_init_hourly_schedule(tmp_path):
    """Choosing [1] produces frequency=hourly with no time field required."""
    save_path = str(tmp_path / "config.yaml")
    # acts → all, frequency → 1 (hourly), notification → skip, save
    inputs = iter(["", "1", "", save_path])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    from uk_reg_monitor.config import load_config
    cfg = load_config(save_path)
    assert cfg.schedule_frequency == "hourly"


def test_init_weekly_schedule(tmp_path):
    """Choosing [3] then wednesday / 09:00 is persisted correctly."""
    save_path = str(tmp_path / "config.yaml")
    # acts, frequency=3, day, time, notification, save
    inputs = iter(["", "3", "wednesday", "09:00", "", save_path])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    from uk_reg_monitor.config import load_config
    cfg = load_config(save_path)
    assert cfg.schedule_frequency == "weekly"
    assert cfg.schedule_day == "wednesday"
    assert cfg.schedule_time == "09:00"


def test_init_email_notification(tmp_path):
    """Email notification details are written to config."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter([
        "",                   # acts → all
        "2",                  # daily
        "08:00",              # time
        "1",                  # email
        "smtp.gmail.com",     # smtp_host
        "587",                # smtp_port
        "user@example.com",   # username
        # getpass → password mocked separately
        "from@example.com",   # from_addr
        "to@example.com",     # to_addr
        save_path,
    ])
    with patch("builtins.input", side_effect=inputs):
        with patch("uk_reg_monitor.cli.getpass.getpass", return_value="secret"):
            _run_wizard("config.yaml")
    with open(save_path) as f:
        data = yaml.safe_load(f)
    email = data["notifications"]["email"]
    assert email["enabled"] is True
    assert email["smtp_host"] == "smtp.gmail.com"
    assert email["smtp_port"] == 587
    assert email["password"] == "secret"
    assert email["to_addrs"] == ["to@example.com"]


def test_init_slack_notification(tmp_path):
    """Slack webhook URL is written to config."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter([
        "", "2", "", "2", "https://hooks.slack.com/test", save_path,
    ])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    with open(save_path) as f:
        data = yaml.safe_load(f)
    slack = data["notifications"]["slack"]
    assert slack["enabled"] is True
    assert slack["webhook_url"] == "https://hooks.slack.com/test"


def test_init_http_webhook_notification(tmp_path):
    """HTTP webhook URL is written to config."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter([
        "", "2", "", "3", "https://example.com/hook", save_path,
    ])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    with open(save_path) as f:
        data = yaml.safe_load(f)
    webhook = data["notifications"]["webhook"]
    assert webhook["enabled"] is True
    assert webhook["url"] == "https://example.com/hook"


def test_init_invalid_then_valid_input(tmp_path, capsys):
    """Invalid inputs trigger re-prompts; wizard eventually succeeds."""
    save_path = str(tmp_path / "config.yaml")
    inputs = iter([
        "bad",      # invalid acts → re-prompt
        "2",        # act 2: National Minimum Wage Act 1998
        "x",        # invalid frequency → re-prompt
        "1",        # hourly
        "9",        # invalid notification → re-prompt
        "4",        # skip
        save_path,
    ])
    with patch("builtins.input", side_effect=inputs):
        _run_wizard("config.yaml")
    from uk_reg_monitor.config import load_config
    cfg = load_config(save_path)
    assert cfg.schedule_frequency == "hourly"
    assert len(cfg.acts) == 1
    assert cfg.acts[0]["name"] == "National Minimum Wage Act 1998"
    captured = capsys.readouterr()
    assert "Invalid" in captured.out
