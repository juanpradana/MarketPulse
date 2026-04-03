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
