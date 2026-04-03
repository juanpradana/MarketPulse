import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from routes import bandarmology as band_route


def test_deep_status_includes_retry_fields_when_idle():
    client = TestClient(app)

    # Reset status to known baseline
    band_route._deep_analysis_status.clear()
    band_route._deep_analysis_status.update(
        band_route._build_deep_analysis_status(
            total=0,
            requested=0,
            qualified=0,
            analysis_date="2026-04-03",
            concurrency=1,
            profile="balanced",
        )
    )
    band_route._deep_analysis_status["running"] = False

    response = client.get("/api/bandarmology/deep-status")
    assert response.status_code == 200
    data = response.json()

    assert "retry_policy" in data
    assert data["retry_policy"]["delay_seconds"] == 120
    assert data["retry_policy"]["max_attempts"] == 10
    assert "retrying_items" in data
    assert "retry_waiting_count" in data
    assert "non_retryable_skips" in data
    assert "retry_exhausted" in data
    assert "broksum_fetch_stats" in data


@pytest.mark.asyncio
async def test_deep_status_exposes_retry_fields_during_retry_lifecycle(monkeypatch):
    client = TestClient(app)

    ticker = "SMGA"
    date_str = "2026-04-03"
    attempts = {"count": 0}
    lifecycle_snapshot = {}

    band_route._deep_analysis_status.clear()
    band_route._deep_analysis_status.update(
        band_route._build_deep_analysis_status(
            total=1,
            requested=1,
            qualified=1,
            analysis_date=date_str,
            concurrency=1,
            profile="balanced",
        )
    )

    async def fake_sleep(_seconds):
        response = client.get("/api/bandarmology/deep-status")
        assert response.status_code == 200
        payload = response.json()

        assert payload["retry_policy"]["delay_seconds"] == 120
        assert payload["retry_policy"]["max_attempts"] == 10
        assert payload["retry_waiting_count"] == 1
        assert len(payload["retrying_items"]) == 1
        assert payload["retrying_items"][0]["ticker"] == ticker
        assert payload["retrying_items"][0]["date"] == date_str
        assert payload["retrying_items"][0]["attempt"] == 1

        lifecycle_snapshot.update(payload)
        return None

    async def fake_fetch(fetch_ticker, fetch_date):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise Exception("429 Too Many Requests")
        return {"buy": [{"broker": "PD", "nlot": 100}], "sell": []}

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)

    result = await band_route._fetch_broksum_with_deferred_retry(
        fetch_fn=fake_fetch,
        ticker=ticker,
        date_str=date_str,
        status=band_route._deep_analysis_status,
        status_lock=None,
    )

    assert result is not None
    assert lifecycle_snapshot["retry_waiting_count"] == 1
    assert lifecycle_snapshot["retrying_items"][0]["ticker"] == ticker

    final_response = client.get("/api/bandarmology/deep-status")
    assert final_response.status_code == 200
    final_payload = final_response.json()

    assert final_payload["retry_waiting_count"] == 0
    assert final_payload["retrying_items"] == []
    assert final_payload["broksum_fetch_stats"]["retried_success"] >= 1
