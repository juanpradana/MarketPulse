import os
import sqlite3
import tempfile
import asyncio

from db.connection import DatabaseConnection
from db.bandarmology_repository import BandarmologyRepository
from db.neobdm_repository import NeoBDMRepository
from routes.bandarmology import get_stock_detail


def _create_temp_db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_stock_detail_broker_summary_and_deep_cache_totals_are_synchronized(monkeypatch):
    db_path = _create_temp_db_path()

    try:
        # Isolated DB schema
        DatabaseConnection(db_path=db_path)

        # Force repositories in route to use temp DB
        monkeypatch.setattr("db.connection.BaseRepository.__init__", lambda self, db_path=None: setattr(self, "db_path", db_path or db_path_for_test))

        # Helper variable for lambda closure
        db_path_for_test = db_path

        band_repo = BandarmologyRepository(db_path=db_path)
        neo_repo = NeoBDMRepository(db_path=db_path)

        ticker = "SMGA"
        analysis_date = "2026-03-31"
        newer_date = "2026-04-02"

        # Minimal deep cache for analysis date (contains old broker summary totals)
        band_repo.save_deep_cache(
            ticker=ticker,
            analysis_date=analysis_date,
            data={
                "deep_score": 30,
                "deep_trade_type": "WATCH",
                "broksum_total_buy_lot": 1000,
                "broksum_total_sell_lot": 900,
                "broksum_avg_buy_price": 120,
                "broksum_avg_sell_price": 119,
            },
        )

        # Broker summary on analysis date
        neo_repo.save_broker_summary_batch(
            ticker=ticker,
            trade_date=analysis_date,
            buy_data=[{"broker": "PD", "nlot": 1000, "nval": 1.2, "savg": 120}],
            sell_data=[{"broker": "CC", "nlot": 900, "nval": 1.1, "savg": 119}],
        )

        # Newer broker summary date (route currently prefers latest)
        neo_repo.save_broker_summary_batch(
            ticker=ticker,
            trade_date=newer_date,
            buy_data=[{"broker": "PD", "nlot": 2000, "nval": 2.4, "savg": 110}],
            sell_data=[{"broker": "CC", "nlot": 1500, "nval": 1.7, "savg": 111}],
        )

        # Monkeypatch analyzer to avoid heavy dependencies and force base result
        class _FakeAnalyzer:
            broker_classes = {}

            def _resolve_date(self, date):
                return date

            @staticmethod
            def _parse_broksum_num(value):
                if value is None or value == "":
                    return 0.0
                return float(value)

            def analyze(self, target_date=None, profile=None):
                return [{
                    "symbol": ticker,
                    "total_score": 55,
                    "max_score": 100,
                    "trade_type": "SWING",
                    "price": 100,
                    "pct_1d": 1.0,
                    "ma_above_count": 3,
                    "pinky": False,
                    "crossing": False,
                    "unusual": False,
                    "likuid": True,
                    "confluence_status": "NONE",
                    "scores": {},
                    "w_4": 0,
                    "w_3": 0,
                    "w_2": 0,
                    "w_1": 0,
                    "d_0_mm": 0,
                    "d_0_nr": 0,
                    "d_0_ff": 0,
                }]

        monkeypatch.setattr("modules.bandarmology_analyzer.BandarmologyAnalyzer", _FakeAnalyzer)

        # Call route directly
        result = asyncio.run(get_stock_detail(ticker, date=analysis_date, profile="balanced"))

        assert not hasattr(result, "status_code")

        # Validate route chose newer broker summary
        assert result["broker_summary_date"] == newer_date

        buy_sum = sum(float(x.get("nlot") or 0) for x in result["broker_summary"]["buy"])
        sell_sum = sum(float(x.get("nlot") or 0) for x in result["broker_summary"]["sell"])

        # Expected synchronized totals with displayed broker_summary list
        assert result["broksum_total_buy_lot"] == buy_sum
        assert result["broksum_total_sell_lot"] == sell_sum

        # Avg prices should also reflect broker_summary date data (newer_date)
        assert result["broksum_avg_buy_price"] == 12000
        assert result["broksum_avg_sell_price"] == 11333

    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_stock_detail_clears_stale_broksum_metrics_when_broker_summary_empty(monkeypatch):
    db_path = _create_temp_db_path()

    try:
        DatabaseConnection(db_path=db_path)

        monkeypatch.setattr("db.connection.BaseRepository.__init__", lambda self, db_path=None: setattr(self, "db_path", db_path or db_path_for_test))
        db_path_for_test = db_path

        band_repo = BandarmologyRepository(db_path=db_path)

        ticker = "SMGA"
        analysis_date = "2026-03-31"

        # Deep cache has stale broker-summary-derived metrics
        band_repo.save_deep_cache(
            ticker=ticker,
            analysis_date=analysis_date,
            data={
                "deep_score": 30,
                "deep_trade_type": "WATCH",
                "broksum_total_buy_lot": 9999,
                "broksum_total_sell_lot": 8888,
                "broksum_avg_buy_price": 12345,
                "broksum_avg_sell_price": 12000,
                "broksum_floor_price": 12100,
                "broksum_top_buyers": [{"broker": "PD", "nlot": 9999, "avg_price": 12345}],
                "broksum_top_sellers": [{"broker": "CC", "nlot": 8888, "avg_price": 12000}],
                "broksum_net_institutional": 777,
                "broksum_net_foreign": 666,
            },
        )

        # No broker summary rows inserted -> response broker_summary should be empty

        class _FakeAnalyzer:
            broker_classes = {}

            def _resolve_date(self, date):
                return date

            @staticmethod
            def _parse_broksum_num(value):
                if value is None or value == "":
                    return 0.0
                return float(value)

            def analyze(self, target_date=None, profile=None):
                return [{
                    "symbol": ticker,
                    "total_score": 55,
                    "max_score": 100,
                    "trade_type": "SWING",
                    "price": 100,
                    "pct_1d": 1.0,
                    "ma_above_count": 3,
                    "pinky": False,
                    "crossing": False,
                    "unusual": False,
                    "likuid": True,
                    "confluence_status": "NONE",
                    "scores": {},
                    "w_4": 0,
                    "w_3": 0,
                    "w_2": 0,
                    "w_1": 0,
                    "d_0_mm": 0,
                    "d_0_nr": 0,
                    "d_0_ff": 0,
                }]

        monkeypatch.setattr("modules.bandarmology_analyzer.BandarmologyAnalyzer", _FakeAnalyzer)

        result = asyncio.run(get_stock_detail(ticker, date=analysis_date, profile="balanced"))

        assert not hasattr(result, "status_code")
        assert result["broker_summary"] == {"buy": [], "sell": []}

        # Broker-summary-derived metrics must match empty broker_summary, not stale deep-cache values
        assert result["broksum_total_buy_lot"] == 0
        assert result["broksum_total_sell_lot"] == 0
        assert result["broksum_avg_buy_price"] == 0
        assert result["broksum_avg_sell_price"] == 0
        assert result["broksum_floor_price"] == 0
        assert result["broksum_top_buyers"] == []
        assert result["broksum_top_sellers"] == []
        assert result["broksum_net_institutional"] == 0
        assert result["broksum_net_foreign"] == 0

    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
