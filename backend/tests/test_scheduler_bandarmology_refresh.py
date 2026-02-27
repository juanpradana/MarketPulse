import sys
import types

from modules import scheduler


def test_run_bandarmology_market_summary_returns_latest_date(monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "_generate_latest_bandarmology_market_summary",
        lambda: ([{"symbol": "SMGA"}], "2026-02-18"),
    )

    result = scheduler.run_bandarmology_market_summary()

    assert result["status"] == "success"
    assert result["total_stocks"] == 1
    assert result["date"] == "2026-02-18"


def test_run_deep_analyze_all_refreshes_summary_and_uses_fresh_rows(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        scheduler,
        "_generate_latest_bandarmology_market_summary",
        lambda: (
            [
                {"symbol": "SMGA"},
                {"symbol": "BBCA"},
                {"symbol": ""},
                {},
            ],
            "2026-02-18",
        ),
    )

    fake_routes = types.ModuleType("routes")
    fake_bandarmology = types.ModuleType("routes.bandarmology")

    async def _fake_run_deep_analysis(tickers, actual_date, base_results, concurrency=12):
        captured["tickers"] = tickers
        captured["date"] = actual_date
        captured["base_results"] = base_results
        captured["concurrency"] = concurrency

    fake_bandarmology._run_deep_analysis = _fake_run_deep_analysis

    monkeypatch.setitem(sys.modules, "routes", fake_routes)
    monkeypatch.setitem(sys.modules, "routes.bandarmology", fake_bandarmology)

    result = scheduler.run_deep_analyze_all()

    assert result["status"] == "success"
    assert result["total_stocks"] == 2
    assert result["date"] == "2026-02-18"

    assert captured["tickers"] == ["SMGA", "BBCA"]
    assert captured["date"] == "2026-02-18"
    assert len(captured["base_results"]) == 4
    assert captured["concurrency"] == 12


def test_generate_market_summary_placeholder_returns_skipped(monkeypatch):
    fake_db = types.ModuleType("db")

    class _NewsRepo:
        def __init__(self, *args, **kwargs):
            pass

        def get_news(self, *args, **kwargs):
            import pandas as pd
            return pd.DataFrame()

    class _NeoRepo:
        def __init__(self, *args, **kwargs):
            pass

        def get_latest_hot_signals(self):
            return []

    fake_db.NewsRepository = _NewsRepo
    fake_db.NeoBDMRepository = _NeoRepo
    monkeypatch.setitem(sys.modules, "db", fake_db)

    fake_price_module = types.ModuleType("db.price_volume_repository")

    class _PriceRepo:
        def detect_unusual_volumes(self, *args, **kwargs):
            return []

    fake_price_module.price_volume_repo = _PriceRepo()
    monkeypatch.setitem(sys.modules, "db.price_volume_repository", fake_price_module)

    result = scheduler.generate_market_summary()

    assert result["status"] == "skipped"
    assert result["reason"] == "placeholder_no_data"
    assert "summary" in result


def test_generate_market_summary_returns_success_with_narrative(monkeypatch):
    fake_db = types.ModuleType("db")

    class _NewsRepo:
        def __init__(self, *args, **kwargs):
            pass

        def get_news(self, *args, **kwargs):
            import pandas as pd
            return pd.DataFrame([
                {
                    "ticker": "BBCA",
                    "title": "Banking sentiment improves",
                    "sentiment_label": "Bullish",
                    "sentiment_score": 0.71,
                    "url": "https://www.cnbcindonesia.com/market/abc",
                    "timestamp": "2026-02-27 09:00:00",
                },
                {
                    "ticker": "GOTO",
                    "title": "Tech outlook weakens",
                    "sentiment_label": "Bearish",
                    "sentiment_score": -0.52,
                    "url": "https://investor.id/market/xyz",
                    "timestamp": "2026-02-27 08:30:00",
                },
            ])

    class _NeoRepo:
        def __init__(self, *args, **kwargs):
            pass

        def get_latest_hot_signals(self):
            return [
                {
                    "symbol": "BBCA",
                    "signal_score": 88,
                    "signal_strength": "STRONG",
                    "flow": 120.5,
                    "change": 1.2,
                    "confluence_status": "ALIGNED",
                }
            ]

    fake_db.NewsRepository = _NewsRepo
    fake_db.NeoBDMRepository = _NeoRepo
    monkeypatch.setitem(sys.modules, "db", fake_db)

    fake_price_module = types.ModuleType("db.price_volume_repository")

    class _PriceRepo:
        def detect_unusual_volumes(self, *args, **kwargs):
            return [
                {"ticker": "BBCA", "date": "2026-02-27", "ratio": 2.8, "price_change": 1.2, "category": "elevated"}
            ]

    fake_price_module.price_volume_repo = _PriceRepo()
    monkeypatch.setitem(sys.modules, "db.price_volume_repository", fake_price_module)

    result = scheduler.generate_market_summary()

    assert result["status"] == "success"
    summary = result["summary"]
    assert len(summary["top_positive_news"]) >= 1
    assert len(summary["top_negative_news"]) >= 1
    assert len(summary["unusual_volume_tickers"]) >= 1
    assert len(summary["strong_accumulation"]) >= 1
    assert summary["narrative"]["headline"]
    assert summary["narrative"]["newsletter"]
