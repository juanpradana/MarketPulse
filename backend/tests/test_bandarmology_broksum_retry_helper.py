import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.bandarmology import _fetch_broksum_with_deferred_retry


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_retries_then_succeeds(monkeypatch):
    call_counter = {"count": 0}

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    async def fake_fetch(ticker, date_str):
        call_counter["count"] += 1
        if call_counter["count"] < 3:
            return None, Exception("429 Too Many Requests"), {
                "ticker": ticker,
                "date": date_str,
            }
        return {"buy": [{"code": "YB", "lot": "100"}], "sell": []}, None, {
            "ticker": ticker,
            "date": date_str,
        }

    status = {
        "retrying_items": [],
        "retry_waiting_count": 0,
        "non_retryable_skips": [],
        "retry_exhausted": [],
        "broksum_fetch_stats": {
            "success": 0,
            "retried_success": 0,
            "non_retryable": 0,
            "exhausted": 0,
        },
    }

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is not None
    assert call_counter["count"] == 3


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_supports_two_tuple_contract(monkeypatch):
    call_counter = {"count": 0}

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    async def fake_fetch(_ticker, _date_str):
        call_counter["count"] += 1
        if call_counter["count"] < 3:
            return None, "429"
        return {"buy": [{"code": "YB", "lot": "100"}], "sell": []}, None

    status = {
        "retrying_items": [],
        "retry_waiting_count": 0,
        "non_retryable_skips": [],
        "retry_exhausted": [],
        "broksum_fetch_stats": {
            "success": 0,
            "retried_success": 0,
            "non_retryable": 0,
            "exhausted": 0,
        },
    }

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is not None
    assert call_counter["count"] == 3


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_preserves_passed_empty_status_dict(monkeypatch):
    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    async def fake_fetch(ticker, date_str):
        return {"buy": [{"code": "YB", "lot": "100"}], "sell": []}, None, {
            "ticker": ticker,
            "date": date_str,
        }

    status = {}
    status_ref = status

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is not None
    assert status is status_ref
    assert status["broksum_fetch_stats"]["success"] == 1


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_normalizes_non_dict_context(monkeypatch):
    call_counter = {"count": 0}

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    async def fake_fetch(ticker, date_str):
        call_counter["count"] += 1
        if call_counter["count"] == 1:
            return None, "429", "not-a-dict"
        return {
            "buy": [{"code": "YB", "lot": "100"}],
            "sell": [{"code": "CC", "lot": "50"}],
        }, None, {
            "ticker": ticker,
            "date": date_str,
        }

    status = {
        "retrying_items": [],
        "retry_waiting_count": 0,
        "non_retryable_skips": [],
        "retry_exhausted": [],
        "broksum_fetch_stats": {
            "success": 0,
            "retried_success": 0,
            "non_retryable": 0,
            "exhausted": 0,
        },
    }

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is not None
    assert call_counter["count"] == 2


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_non_retryable_no_data_stops_immediately():
    call_counter = {"count": 0}

    async def fake_fetch(ticker, date_str):
        call_counter["count"] += 1
        return None, None, {
            "ticker": ticker,
            "date": date_str,
            "source": "explicit_no_data",
            "reason": "no_data",
            "message": "No broker summary rows",
        }

    status = {
        "retrying_items": [],
        "retry_waiting_count": 0,
        "non_retryable_skips": [],
        "retry_exhausted": [],
        "broksum_fetch_stats": {
            "success": 0,
            "retried_success": 0,
            "non_retryable": 0,
            "exhausted": 0,
        },
    }

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is None
    assert call_counter["count"] == 1
    assert len(status["non_retryable_skips"]) == 1
    assert status["non_retryable_skips"][0]["attempt"] == 1
    assert status["broksum_fetch_stats"]["non_retryable"] == 1


@pytest.mark.asyncio
async def test_fetch_broksum_with_deferred_retry_retryable_failure_exhausts_at_ten_attempts(monkeypatch):
    call_counter = {"count": 0}

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    async def fake_fetch(_ticker, _date_str):
        call_counter["count"] += 1
        return None, Exception("429 Too Many Requests"), {
            "status": 429,
            "message": "Rate limited",
        }

    status = {
        "retrying_items": [],
        "retry_waiting_count": 0,
        "non_retryable_skips": [],
        "retry_exhausted": [],
        "broksum_fetch_stats": {
            "success": 0,
            "retried_success": 0,
            "non_retryable": 0,
            "exhausted": 0,
        },
    }

    result = await _fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker="BBCA",
        date_str="2026-04-03",
        status=status,
    )

    assert result is None
    assert call_counter["count"] == 10
    assert len(status["retry_exhausted"]) == 1
    assert status["retry_exhausted"][0]["attempts"] == 10
    assert status["broksum_fetch_stats"]["exhausted"] == 1
