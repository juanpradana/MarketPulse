import sys
from datetime import datetime
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes import bandarmology as band_route


@pytest.mark.asyncio
async def test_run_deep_analysis_uses_deferred_retry_and_records_retried_success(monkeypatch):
    analysis_date = datetime.now().strftime("%Y-%m-%d")
    ticker = "SMGA"

    class FakeBandarmologyRepository:
        def __init__(self):
            self.saved_broker_summary = []
            self.saved_deep_cache = []

        def delete_deep_cache(self, _ticker, _date):
            return False

        def get_deep_cache(self, _ticker, _date):
            return None

        def save_inventory_batch(self, *_args, **_kwargs):
            return None

        def save_transaction_chart(self, *_args, **_kwargs):
            return None

        def get_transaction_chart(self, _ticker):
            return {"series": []}

        def save_deep_cache(self, ticker_arg, date_arg, deep_result):
            self.saved_deep_cache.append((ticker_arg, date_arg, deep_result))

        def get_previous_deep_cache(self, _ticker, _date):
            return None

    class FakeNeoBDMRepository:
        def __init__(self):
            self.saved_broker_summary = []

        def get_broker_summary(self, _ticker, _date):
            return None

        def save_broker_summary_batch(self, ticker_arg, date_arg, buy_data, sell_data):
            self.saved_broker_summary.append((ticker_arg, date_arg, buy_data, sell_data))

        def get_broker_summary_multiday(self, _ticker, _date, days=5):
            return {"days": days, "items": []}

    class FakeAnalyzer:
        def detect_controlling_brokers(self, _inv_data, price_series=None, min_brokers=3):
            return {"controlling_brokers": []}

        def analyze_deep(self, ticker_arg, **_kwargs):
            return {"symbol": ticker_arg, "deep_score": 42}

    class FakeApiClient:
        def __init__(self):
            self.broksum_calls = {}

        async def login(self):
            return True

        async def get_inventory(self, _ticker):
            return {"brokers": [{"broker": "PD", "nlot": 100}], "priceSeries": []}

        async def get_transaction_chart(self, _ticker):
            return {"chart": []}

        async def get_broker_summary(self, ticker_arg, date_arg, fast_fail=True):
            key = (ticker_arg, date_arg)
            self.broksum_calls[key] = self.broksum_calls.get(key, 0) + 1
            if self.broksum_calls[key] == 1:
                raise Exception("429 Too Many Requests")
            return {"buy": [{"broker": "PD", "nlot": 500}], "sell": [{"broker": "CC", "nlot": 300}]}

        async def close(self):
            return None

    fake_band_repo = FakeBandarmologyRepository()
    fake_neo_repo = FakeNeoBDMRepository()

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr("routes.bandarmology.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("db.bandarmology_repository.BandarmologyRepository", lambda: fake_band_repo)
    monkeypatch.setattr("db.neobdm_repository.NeoBDMRepository", lambda: fake_neo_repo)
    monkeypatch.setattr("modules.bandarmology_analyzer.BandarmologyAnalyzer", lambda: FakeAnalyzer())
    monkeypatch.setattr("modules.neobdm_api_client.NeoBDMApiClient", lambda: FakeApiClient())

    band_route._deep_analysis_status.clear()
    band_route._deep_analysis_status.update(
        band_route._build_deep_analysis_status(
            total=1,
            requested=1,
            qualified=1,
            analysis_date=analysis_date,
            concurrency=1,
            profile="balanced",
        )
    )

    await band_route._run_deep_analysis(
        tickers=[ticker],
        analysis_date=analysis_date,
        base_results=[{"symbol": ticker}],
        concurrency=1,
        force=False,
    )

    assert any(item[0] == ticker and item[1] == analysis_date for item in fake_neo_repo.saved_broker_summary)
    assert len(fake_band_repo.saved_deep_cache) == 1
    assert band_route._deep_analysis_status["processed"] == 1
    assert band_route._deep_analysis_status["broksum_fetch_stats"]["retried_success"] >= 1
