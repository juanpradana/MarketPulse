import os
import sqlite3
import tempfile

from db import DatabaseConnection, BandarmologyRepository
from db.watchlist_repository import WatchlistRepository


def _create_temp_db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def test_watchlist_latest_price_uses_price_volume_schema():
    db_path = _create_temp_db_path()
    try:
        DatabaseConnection(db_path=db_path)
        watchlist_repo = WatchlistRepository(db_path=db_path)

        assert watchlist_repo.add_ticker("SMGA", user_id="default") is True

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS price_volume (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, trade_date)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO price_volume (ticker, trade_date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("SMGA", "2026-02-17", 100, 104, 99, 100, 1000000),
            )
            conn.execute(
                """
                INSERT INTO price_volume (ticker, trade_date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("SMGA", "2026-02-18", 102, 106, 101, 110, 1500000),
            )
            conn.commit()
        finally:
            conn.close()

        data = watchlist_repo.get_watchlist("default")
        assert len(data) == 1
        assert data[0]["ticker"] == "SMGA"
        assert data[0]["latest_price"] is not None
        assert data[0]["latest_price"]["price"] == 110
        assert data[0]["latest_price"]["volume"] == 1500000
        assert data[0]["latest_price"]["date"] == "2026-02-18"
        assert round(data[0]["latest_price"]["change_percent"], 2) == 10.00
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_watchlist_latest_price_falls_back_to_neobdm_records():
    db_path = _create_temp_db_path()
    try:
        DatabaseConnection(db_path=db_path)
        watchlist_repo = WatchlistRepository(db_path=db_path)

        assert watchlist_repo.add_ticker("SMGA", user_id="default") is True

        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """
                INSERT INTO neobdm_records (scraped_at, method, period, symbol, price, pct_1d)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("2026-02-18 15:00:00", "m", "d", "SMGA", "116", "2.35"),
            )
            conn.commit()
        finally:
            conn.close()

        data = watchlist_repo.get_watchlist("default")
        assert len(data) == 1
        assert data[0]["latest_price"] is not None
        assert data[0]["latest_price"]["price"] == 116.0
        assert data[0]["latest_price"]["change_percent"] == 2.35
        assert data[0]["latest_price"]["date"] == "2026-02-18"
        assert data[0]["latest_price"]["volume"] == 0
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_bandarmology_stock_summary_supports_deep_only_rows():
    db_path = _create_temp_db_path()
    try:
        DatabaseConnection(db_path=db_path)
        band_repo = BandarmologyRepository(db_path=db_path)

        band_repo.save_deep_cache(
            ticker="SMGA",
            analysis_date="2026-02-18",
            data={
                "deep_score": 26.6,
                "deep_trade_type": "WATCH",
                "accum_phase": "ACCUMULATION",
                "bandar_avg_cost": 116,
            },
        )

        summary = band_repo.get_stock_summary("SMGA")

        assert summary["deep_score"] == 26.6
        assert summary["total_score"] is None
        assert summary["combined_score"] == 26.6
        assert summary["trade_type"] == "WATCH"
        assert summary["deep_trade_type"] == "WATCH"
        assert summary["accum_phase"] == "ACCUMULATION"
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
