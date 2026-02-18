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

    async def _fake_run_deep_analysis(tickers, actual_date, base_results):
        captured["tickers"] = tickers
        captured["date"] = actual_date
        captured["base_results"] = base_results

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
