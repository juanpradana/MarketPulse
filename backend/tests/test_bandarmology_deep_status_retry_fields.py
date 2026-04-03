import sys
from pathlib import Path
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
