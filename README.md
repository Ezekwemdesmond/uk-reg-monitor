# uk-reg-monitor

[![PyPI version](https://badge.fury.io/py/uk-reg-monitor.svg)](https://pypi.org/project/uk-reg-monitor/)

**uk-reg-monitor** is an open-source Python package that monitors UK employment legislation for material changes on a schedule. It acts as a companion client to the [UK Employment Law Change Detector API](#the-uk-employment-law-change-detector-api): you configure which Acts of Parliament to watch and how often to check, and uk-reg-monitor handles the scheduling, calls the API on each cycle, and routes any detected changes to your team via email, Slack, or a generic webhook.

Available on PyPI: https://pypi.org/project/uk-reg-monitor/

---

## Installation

```bash
pip install uk-reg-monitor
```

For development (editable install with test dependencies):

```bash
git clone https://github.com/example/uk-reg-monitor.git
cd uk-reg-monitor
pip install -e ".[dev]"
```

Requires Python 3.9 or later.

---

## Quickstart

### Step 1 — Run the setup wizard

```bash
uk-reg-monitor init
```

The wizard guides you through choosing which Acts to monitor, how often to check, and how to receive notifications. It writes `config.yaml` to your working directory and validates it automatically.

**Prefer to configure manually?** Create `config.yaml` by hand:

```yaml
api:
  base_url: "https://uk-employment-law-change-detector.onrender.com"
  timeout: 30

schedule:
  frequency: "daily"   # hourly | daily | weekly
  time: "08:00"        # HH:MM — used by daily and weekly
  day: "monday"        # day of week — used by weekly only

acts:
  - url: "https://www.legislation.gov.uk/ukpga/1996/18"
    name: "Employment Rights Act 1996"
  - url: "https://www.legislation.gov.uk/ukpga/2010/15"
    name: "Equality Act 2010"
  - url: "https://www.legislation.gov.uk/ukpga/1992/52"
    name: "Trade Union and Labour Relations (Consolidation) Act 1992"

notifications:
  email:
    enabled: false
    smtp_host: "smtp.example.com"
    smtp_port: 587
    use_tls: true
    username: ""
    password: ""
    from_addr: "monitor@example.com"
    to_addrs:
      - "team@example.com"

  slack:
    enabled: false
    webhook_url: ""

  webhook:
    enabled: false
    url: ""
    method: "POST"
    headers:
      Content-Type: "application/json"
```

Then run `uk-reg-monitor validate` to check it.

### Step 2 — Start the monitor

```bash
uk-reg-monitor start
```

The monitor runs an immediate check on startup, then repeats on the configured schedule. Press `Ctrl+C` to stop.

---

## CLI Commands

### `uk-reg-monitor init`

Runs the interactive setup wizard. Guides you through choosing Acts, schedule frequency, and notification channels, then writes `config.yaml` and validates it automatically. Passwords are collected without echoing to the terminal.

```bash
uk-reg-monitor init
uk-reg-monitor init --config /path/to/config.yaml
```

### `uk-reg-monitor start`

Starts the scheduled monitor. Runs an immediate check, then repeats according to `schedule.frequency`.

```bash
uk-reg-monitor start
uk-reg-monitor start --config /path/to/config.yaml
uk-reg-monitor start --verbose
```

### `uk-reg-monitor check`

Runs a single immediate check across all configured Acts and prints the results to the terminal. Does not start the scheduler.

```bash
uk-reg-monitor check
uk-reg-monitor check --config /path/to/config.yaml
```

### `uk-reg-monitor validate`

Validates `config.yaml` and prints a summary. Exits with a non-zero code if validation fails. Use this to verify configuration before deploying.

```bash
uk-reg-monitor validate
uk-reg-monitor validate --config /path/to/config.yaml
```

### Global flags

| Flag | Description |
|---|---|
| `--config PATH` | Path to `config.yaml` (default: `./config.yaml`) |
| `--verbose` | Enable debug logging |

---

## Schedule options

| `frequency` | Requires | Behaviour |
|---|---|---|
| `hourly` | — | Runs every 60 minutes |
| `daily` | `time: "HH:MM"` | Runs once per day at the specified time |
| `weekly` | `time: "HH:MM"`, `day: "<weekday>"` | Runs once per week on the specified day and time |

---

## Notification channels

Enable any combination of channels in `config.yaml`. Notifications are only sent when at least one Act has a material change.

- **Email** — plain-text email via SMTP (supports TLS)
- **Slack** — POST to a Slack incoming webhook URL
- **Webhook** — POST raw JSON to any HTTP endpoint

---

## The UK Employment Law Change Detector API

uk-reg-monitor delegates all intelligence to the **UK Employment Law Change Detector API**. That API analyses legislation pages and determines whether a material legislative change has occurred. uk-reg-monitor provides the scheduling, configuration, and notification layer on top.

The package connects to the **live hosted API** at `https://uk-employment-law-change-detector.onrender.com` by default — no additional setup is required. Interactive API documentation is available at [https://uk-employment-law-change-detector.onrender.com/docs](https://uk-employment-law-change-detector.onrender.com/docs).

If you need to point at a different instance, set `api.base_url` in your `config.yaml`.

---

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=uk_reg_monitor
```

---

## License

MIT
