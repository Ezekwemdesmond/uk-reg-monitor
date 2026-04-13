"""Tests for uk_reg_monitor.client."""

import pytest
import responses

from uk_reg_monitor.client import APIError, analyse_act, check_all_acts


@responses.activate
def test_analyse_act_success():
    """Successful API call returns parsed JSON."""
    responses.post(
        "https://api.example.com/analyse",
        json={"act": "Equality Act 2010", "material_change": True, "summary": "New provision added."},
    )
    result = analyse_act(
        "https://api.example.com",
        "https://legislation.gov.uk/2010/15",
        "Equality Act 2010",
    )
    assert result["material_change"] is True
    assert result["act"] == "Equality Act 2010"


@responses.activate
def test_analyse_act_strips_trailing_slash():
    """Base URL trailing slash is handled."""
    responses.post(
        "https://api.example.com/analyse",
        json={"material_change": False},
    )
    result = analyse_act(
        "https://api.example.com/",
        "https://legislation.gov.uk/1996/18",
        "Some Act",
    )
    assert result["material_change"] is False


@responses.activate
def test_analyse_act_sends_correct_payload():
    """Payload contains url and min_confidence=0.75, nothing else."""
    responses.post(
        "https://api.example.com/analyse",
        json={"material_change": False},
    )
    analyse_act("https://api.example.com", "https://leg.gov.uk/1", "Test Act")
    body = responses.calls[0].request.body
    assert b'"url"' in body
    assert b"0.75" in body
    assert b"act_url" not in body
    assert b"act_name" not in body


@responses.activate
def test_analyse_act_retries_on_failure():
    """Retries with backoff on failure, succeeds on final attempt."""
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post(
        "https://api.example.com/analyse",
        json={"material_change": True, "summary": "ok"},
    )
    result = analyse_act(
        "https://api.example.com",
        "https://leg.gov.uk/1",
        "Retry Act",
        max_retries=3,
        backoff_base=0.01,  # fast for tests
    )
    assert result["material_change"] is True
    assert len(responses.calls) == 3


@responses.activate
def test_analyse_act_raises_after_all_retries():
    """APIError raised when all retries are exhausted."""
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    with pytest.raises(APIError, match="All 3 retries failed"):
        analyse_act(
            "https://api.example.com",
            "https://leg.gov.uk/1",
            "Failing Act",
            max_retries=3,
            backoff_base=0.01,
        )


@responses.activate
def test_check_all_acts_filters_material():
    """Only acts with material_change=True are returned."""
    responses.post(
        "https://api.example.com/analyse",
        json={"act": "Act A", "material_change": True, "summary": "Changed."},
    )
    responses.post(
        "https://api.example.com/analyse",
        json={"act": "Act B", "material_change": False},
    )

    config = {
        "api": {"base_url": "https://api.example.com", "timeout": 5},
        "acts": [
            {"url": "https://leg.gov.uk/a", "name": "Act A"},
            {"url": "https://leg.gov.uk/b", "name": "Act B"},
        ],
    }
    results = check_all_acts(config)
    assert len(results) == 1
    assert results[0]["act"] == "Act A"


@responses.activate
def test_check_all_acts_handles_api_error():
    """APIError for one act doesn't block others."""
    # 3 failures for act A (all retries exhausted)
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    responses.post("https://api.example.com/analyse", body=ConnectionError("fail"))
    # success for act B
    responses.post(
        "https://api.example.com/analyse",
        json={"act": "Act B", "material_change": True, "summary": "Update."},
    )

    config = {
        "api": {"base_url": "https://api.example.com", "timeout": 5},
        "acts": [
            {"url": "https://leg.gov.uk/a", "name": "Act A"},
            {"url": "https://leg.gov.uk/b", "name": "Act B"},
        ],
    }
    results = check_all_acts(config)
    assert len(results) == 1
    assert results[0]["act"] == "Act B"
