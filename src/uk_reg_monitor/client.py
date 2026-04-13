"""API client — calls the UK Employment Law Change Detector API with retry logic."""

import logging
import time

import requests

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds — retry delays: 2, 4, 8


class APIError(Exception):
    """Raised when all retries are exhausted for an API call."""

    def __init__(self, act_name: str, last_error: Exception) -> None:
        """Initialise with the act name and the last exception encountered.

        Args:
            act_name: Name of the act that failed.
            last_error: The final exception after all retries.
        """
        self.act_name = act_name
        self.last_error = last_error
        super().__init__(
            f"All {MAX_RETRIES} retries failed for '{act_name}': {last_error}"
        )


def analyse_act(
    base_url: str,
    act_url: str,
    act_name: str,
    timeout: int = 30,
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
) -> dict:
    """Call POST /analyse on the detector API for a single Act with retry logic.

    Retries up to max_retries times with exponential backoff on any request
    failure (connection errors, timeouts, non-2xx responses).

    Args:
        base_url: Base URL of the detector API.
        act_url: Legislation.gov.uk URL of the Act.
        act_name: Human-readable name of the Act.
        timeout: Request timeout in seconds.
        max_retries: Number of retry attempts.
        backoff_base: Base delay in seconds for exponential backoff.

    Returns:
        JSON response dictionary from the API.

    Raises:
        APIError: If all retries are exhausted.
    """
    url = f"{base_url.rstrip('/')}/analyse"
    payload = {"url": act_url, "min_confidence": 0.75}
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Analysing '%s' (attempt %d/%d)", act_name, attempt, max_retries)
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = backoff_base ** attempt
                logger.warning(
                    "Attempt %d/%d failed for '%s': %s — retrying in %.1fs",
                    attempt, max_retries, act_name, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "All %d retries exhausted for '%s': %s",
                    max_retries, act_name, exc,
                )

    raise APIError(act_name, last_error)


def check_all_acts(config) -> list[dict]:
    """Run analysis for every configured Act and return material changes.

    Args:
        config: A Config instance or raw dict with api/acts keys.

    Returns:
        List of result dicts for acts where material changes were detected.
    """
    if isinstance(config, dict):
        base_url = config["api"]["base_url"]
        timeout = config["api"].get("timeout", 30)
        acts = config["acts"]
    else:
        base_url = config.api_base_url
        timeout = config.api_timeout
        acts = config.acts

    results = []
    for act in acts:
        act_url = act["url"] if isinstance(act, dict) else act
        act_name = act["name"] if isinstance(act, dict) else act
        try:
            result = analyse_act(base_url, act_url, act_name, timeout=timeout)
            if result.get("material_change"):
                results.append(result)
        except APIError:
            logger.exception("Failed to analyse: %s", act_name)

    return results
