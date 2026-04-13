# Changelog

## [0.2.2] - 2026-04-13

### Changed
- `config.yaml`: `api.base_url` updated from placeholder to the live hosted API at `https://uk-employment-law-change-detector.onrender.com`
- `README.md`: noted that the package connects to the live hosted API by default; updated quickstart sample `config.yaml` to use the live URL; added link to live API docs at `https://uk-employment-law-change-detector.onrender.com/docs`

## [0.2.1] - 2026-04-13

### Added
- `README.md` rewritten — description, quickstart (3 steps), full sample `config.yaml`, CLI command reference, schedule and notification channel tables, link to the UK Employment Law Change Detector API
- `.gitignore` — excludes `venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.claude/`, `CLAUDE.md`, `.env`, `*.egg-info/`, `dist/`, `build/`

### Changed
- `pyproject.toml` version bumped to 0.2.1

## [0.2.0] - 2026-04-13

### Changed
- **config.py**: Full validation — api.base_url required, acts must have url+name, schedule frequency must be hourly/daily/weekly, enabled notification channels validated for required fields. New `Config` class with typed properties and `summary()`.
- **client.py**: Retry logic — 3 retries with exponential backoff. New `APIError` exception when all retries fail. Payload now sends `act_url` and `act_name`.
- **scheduler.py**: Supports daily (at time), weekly (on day at time), and hourly frequencies via APScheduler cron/interval triggers. Logs each run with timestamp.
- **notifier.py**: New `Notifier` class wrapping notification dispatch. Backward-compatible `notify()` function retained.
- **cli.py**: Three subcommands — `start` (run scheduler), `check` (single immediate check), `validate` (validate config and print summary).
- **__init__.py**: Public API exposing `Monitor`, `Config`, `Notifier` classes.
- **config.yaml**: Acts now use url+name format. Schedule uses frequency/time/day instead of interval_hours.

### Added
- `Config` class with typed property access and `summary()`
- `Notifier` class for notification dispatch
- `Monitor` class as high-level orchestration API
- `APIError` exception for exhausted retries
- 45 pytest tests covering all modules (up from 17)

## [0.1.0] - 2026-04-13

### Added
- Initial project structure
- Configuration loader (`config.py`) — reads `config.yaml`
- API client (`client.py`) — calls `POST /analyse` on the detector API
- Notifier (`notifier.py`) — email, Slack, and webhook channels
- Scheduler (`scheduler.py`) — APScheduler-based periodic checks
- CLI entry point (`cli.py`) — `uk-reg-monitor start`
- Sample `config.yaml`
- pytest test stubs for all modules
