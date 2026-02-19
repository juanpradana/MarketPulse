"""
Watchlist Repository

Manages user's personalized ticker watchlist.
Tracks user's favorite stocks for quick filtering and monitoring.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import sqlite3
from db.connection import BaseRepository


def _parse_num(value: Any, default: float = 0.0) -> float:
    """Parse numeric values that may come as strings with commas/percent symbols."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip().replace(',', '').replace('%', '')
    if not s:
        return default
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def _normalize_list_name(list_name: Optional[str]) -> str:
    """Normalize list name and fallback to Default."""
    cleaned = (list_name or "").strip()
    return cleaned if cleaned else "Default"


class WatchlistRepository(BaseRepository):
    """Repository for user watchlist operations."""

    def add_ticker(self, ticker: str, user_id: str = "default", list_name: str = "Default") -> bool:
        """
        Add a ticker to user's watchlist.

        Args:
            ticker: Stock ticker symbol (e.g., 'BBCA', 'ASII')
            user_id: User identifier (default for single-user mode)

        Returns:
            True if added successfully, False if already exists
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            normalized_list = _normalize_list_name(list_name)

            cursor.execute(
                """INSERT OR IGNORE INTO user_watchlist_lists (user_id, list_name)
                   VALUES (?, ?)""",
                (user_id, normalized_list)
            )

            # Check if already exists
            cursor.execute(
                """SELECT 1 FROM user_watchlist
                   WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                (user_id, normalized_list, ticker.upper())
            )
            if cursor.fetchone():
                return False

            # Add to watchlist
            cursor.execute(
                """INSERT INTO user_watchlist (user_id, list_name, ticker, added_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, normalized_list, ticker.upper(), datetime.now().isoformat())
            )
            cursor.execute(
                """UPDATE user_watchlist_lists
                   SET updated_at = datetime('now')
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, normalized_list)
            )
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def remove_ticker(self, ticker: str, user_id: str = "default", list_name: str = "Default") -> bool:
        """
        Remove a ticker from user's watchlist.

        Args:
            ticker: Stock ticker symbol
            user_id: User identifier

        Returns:
            True if removed, False if not found
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            normalized_list = _normalize_list_name(list_name)

            cursor.execute(
                """DELETE FROM user_watchlist
                   WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                (user_id, normalized_list, ticker.upper())
            )

            if cursor.rowcount > 0:
                cursor.execute(
                    """UPDATE user_watchlist_lists
                       SET updated_at = datetime('now')
                       WHERE user_id = ? AND list_name = ?""",
                    (user_id, normalized_list)
                )
                conn.commit()
                return True
            return False

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            
                conn.close()

    def list_watchlists(self, user_id: str = "default") -> List[Dict[str, Any]]:
        """List all watchlists for a user with ticker counts."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    l.list_name,
                    l.created_at,
                    l.updated_at,
                    COUNT(w.id) AS ticker_count
                FROM user_watchlist_lists l
                LEFT JOIN user_watchlist w
                  ON w.user_id = l.user_id
                 AND w.list_name = l.list_name
                WHERE l.user_id = ?
                GROUP BY l.list_name, l.created_at, l.updated_at
                ORDER BY l.updated_at DESC, l.list_name ASC
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
            if not rows:
                self.create_watchlist("Default", user_id)
                return self.list_watchlists(user_id)

            return [
                {
                    "list_name": row[0],
                    "created_at": row[1],
                    "updated_at": row[2],
                    "ticker_count": row[3],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def create_watchlist(self, list_name: str, user_id: str = "default") -> bool:
        """Create a new watchlist."""
        normalized_list = _normalize_list_name(list_name)
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO user_watchlist_lists (user_id, list_name)
                   VALUES (?, ?)""",
                (user_id, normalized_list)
            )
            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def rename_watchlist(self, old_name: str, new_name: str, user_id: str = "default") -> bool:
        """Rename existing watchlist and migrate all tickers."""
        old_list = _normalize_list_name(old_name)
        new_list = _normalize_list_name(new_name)
        if old_list == new_list:
            return False

        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """SELECT 1 FROM user_watchlist_lists
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, old_list)
            )
            if not cursor.fetchone():
                return False

            cursor.execute(
                """SELECT 1 FROM user_watchlist_lists
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, new_list)
            )
            if cursor.fetchone():
                raise ValueError(f"Watchlist '{new_list}' already exists")

            cursor.execute(
                """UPDATE user_watchlist
                   SET list_name = ?
                   WHERE user_id = ? AND list_name = ?""",
                (new_list, user_id, old_list)
            )
            cursor.execute(
                """UPDATE user_watchlist_lists
                   SET list_name = ?, updated_at = datetime('now')
                   WHERE user_id = ? AND list_name = ?""",
                (new_list, user_id, old_list)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def delete_watchlist(
        self,
        list_name: str,
        user_id: str = "default",
        move_to_list: Optional[str] = None,
    ) -> bool:
        """Delete a watchlist, optionally moving its tickers to another list."""
        source_list = _normalize_list_name(list_name)
        target_list = _normalize_list_name(move_to_list) if move_to_list is not None else None

        if target_list and target_list == source_list:
            raise ValueError("Target list must be different from source list")

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 1 FROM user_watchlist_lists
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, source_list)
            )
            if not cursor.fetchone():
                return False

            if target_list:
                cursor.execute(
                    """INSERT OR IGNORE INTO user_watchlist_lists (user_id, list_name)
                       VALUES (?, ?)""",
                    (user_id, target_list)
                )
                cursor.execute(
                    """UPDATE OR IGNORE user_watchlist
                       SET list_name = ?
                       WHERE user_id = ? AND list_name = ?""",
                    (target_list, user_id, source_list)
                )
                cursor.execute(
                    """UPDATE user_watchlist_lists
                       SET updated_at = datetime('now')
                       WHERE user_id = ? AND list_name = ?""",
                    (user_id, target_list)
                )
                cursor.execute(
                    """DELETE FROM user_watchlist
                       WHERE user_id = ? AND list_name = ?""",
                    (user_id, source_list)
                )
            else:
                cursor.execute(
                    """DELETE FROM user_watchlist
                       WHERE user_id = ? AND list_name = ?""",
                    (user_id, source_list)
                )

            cursor.execute(
                """DELETE FROM user_watchlist_lists
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, source_list)
            )

            cursor.execute(
                """SELECT COUNT(*) FROM user_watchlist_lists WHERE user_id = ?""",
                (user_id,)
            )
            remaining = cursor.fetchone()[0]
            if remaining == 0:
                cursor.execute(
                    """INSERT OR IGNORE INTO user_watchlist_lists (user_id, list_name)
                       VALUES (?, 'Default')""",
                    (user_id,)
                )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def move_ticker(
        self,
        ticker: str,
        from_list_name: str,
        to_list_name: str,
        user_id: str = "default",
    ) -> bool:
        """Move a ticker from one watchlist to another."""
        from_list = _normalize_list_name(from_list_name)
        to_list = _normalize_list_name(to_list_name)

        if from_list == to_list:
            return False

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO user_watchlist_lists (user_id, list_name)
                   VALUES (?, ?)""",
                (user_id, to_list)
            )

            cursor.execute(
                """SELECT added_at FROM user_watchlist
                   WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                (user_id, from_list, ticker.upper())
            )
            existing = cursor.fetchone()
            if not existing:
                return False

            added_at = existing[0]
            cursor.execute(
                """INSERT OR IGNORE INTO user_watchlist (user_id, list_name, ticker, added_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, to_list, ticker.upper(), added_at)
            )
            cursor.execute(
                """DELETE FROM user_watchlist
                   WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                (user_id, from_list, ticker.upper())
            )
            cursor.execute(
                """UPDATE user_watchlist_lists
                   SET updated_at = datetime('now')
                   WHERE user_id = ? AND list_name IN (?, ?)""",
                (user_id, from_list, to_list)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_watchlist(self, user_id: str = "default", list_name: str = "Default") -> List[Dict[str, Any]]:
        """
        Get all tickers in user's watchlist with latest price info.

        Args:
            user_id: User identifier

        Returns:
            List of watchlist items with ticker details
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            normalized_list = _normalize_list_name(list_name)

            # Get watchlist tickers
            cursor.execute(
                """SELECT ticker, added_at, list_name FROM user_watchlist
                   WHERE user_id = ? AND list_name = ?
                   ORDER BY added_at DESC""",
                (user_id, normalized_list)
            )

            results = []
            for row in cursor.fetchall():
                ticker = row[0]

                # Get latest price data
                latest_price = self._get_latest_price(cursor, ticker)

                results.append({
                    "ticker": ticker,
                    "added_at": row[1],
                    "list_name": row[2],
                    "latest_price": latest_price
                })

            return results

        except Exception as e:
            print(f"[*] Error getting watchlist: {e}")
            return []
        finally:
            
                conn.close()

    def _get_latest_price(self, cursor, ticker: str) -> Optional[Dict]:
        """Get latest price data for a ticker."""
        try:
            # Current schema: price_volume(ticker, trade_date, close, volume)
            cursor.execute(
                """SELECT
                       p.close,
                       CASE
                           WHEN prev.close IS NULL OR prev.close = 0 THEN 0
                           ELSE ((p.close - prev.close) / prev.close) * 100
                       END AS change_percent,
                       p.volume,
                       p.trade_date
                   FROM price_volume p
                   LEFT JOIN price_volume prev
                     ON prev.ticker = p.ticker
                    AND prev.trade_date = (
                        SELECT MAX(p2.trade_date)
                        FROM price_volume p2
                        WHERE p2.ticker = p.ticker
                          AND p2.trade_date < p.trade_date
                    )
                   WHERE p.ticker = ?
                   ORDER BY p.trade_date DESC
                   LIMIT 1""",
                (ticker,)
            )

            row = cursor.fetchone()
            if row:
                return {
                    "price": row[0],
                    "change_percent": row[1],
                    "volume": row[2],
                    "date": row[3]
                }

            # Current table exists but has no row for this ticker.
            # Continue to legacy fallback for backward compatibility.
            raise sqlite3.OperationalError("No data in price_volume for ticker")

        except sqlite3.OperationalError:
            # Backward compatibility for older DB schema.
            try:
                cursor.execute(
                    """SELECT close, change_percent, volume, date
                       FROM price_volume_data
                       WHERE ticker = ?
                       ORDER BY date DESC
                       LIMIT 1""",
                    (ticker,)
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "price": row[0],
                        "change_percent": row[1],
                        "volume": row[2],
                        "date": row[3]
                    }
            except Exception:
                pass

            try:
                # Last-resort fallback: derive price/change from latest NeoBDM daily rows.
                # This keeps watchlist cards usable even if OHLCV sync is stale or missing.
                cursor.execute(
                    """SELECT price, pct_1d, scraped_at
                       FROM neobdm_records
                       WHERE UPPER(symbol) = UPPER(?)
                         AND period = 'd'
                         AND method = 'm'
                         AND price IS NOT NULL
                         AND TRIM(CAST(price AS TEXT)) <> ''
                       ORDER BY scraped_at DESC
                       LIMIT 1""",
                    (ticker,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "price": _parse_num(row[0], 0.0),
                        "change_percent": _parse_num(row[1], 0.0),
                        "volume": 0,
                        "date": (row[2] or "")[:10]
                    }
            except Exception:
                pass

            try:
                # Final fallback: use deep-cache derived prices.
                # Useful when watchlist contains manually deep-analyzed tickers with no OHLCV snapshot yet.
                cursor.execute(
                    """SELECT entry_price, bandar_avg_cost, analysis_date
                       FROM bandarmology_deep_cache
                       WHERE UPPER(ticker) = UPPER(?)
                       ORDER BY analysis_date DESC
                       LIMIT 1""",
                    (ticker,)
                )
                row = cursor.fetchone()
                if row:
                    entry_price = _parse_num(row[0], 0.0)
                    avg_cost = _parse_num(row[1], 0.0)
                    price = entry_price if entry_price > 0 else avg_cost
                    if price > 0:
                        return {
                            "price": price,
                            "change_percent": 0.0,
                            "volume": 0,
                            "date": row[2] or ""
                        }
            except Exception:
                return None

            return None

        except Exception:
            return None

    def is_in_watchlist(self, ticker: str, user_id: str = "default", list_name: Optional[str] = "Default") -> bool:
        """Check if a ticker is in user's watchlist."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            if list_name is None:
                cursor.execute(
                    """SELECT 1 FROM user_watchlist
                       WHERE user_id = ? AND ticker = ?""",
                    (user_id, ticker.upper())
                )
            else:
                normalized_list = _normalize_list_name(list_name)
                cursor.execute(
                    """SELECT 1 FROM user_watchlist
                       WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                    (user_id, normalized_list, ticker.upper())
                )
            return cursor.fetchone() is not None

        except Exception:
            return False
        finally:
            
                conn.close()

    def get_watchlist_count(self, user_id: str = "default", list_name: str = "Default") -> int:
        """Get number of tickers in watchlist."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            normalized_list = _normalize_list_name(list_name)
            cursor.execute(
                """SELECT COUNT(*) FROM user_watchlist
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, normalized_list)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

        except Exception:
            return 0
        finally:
            
                conn.close()

    def get_watchlist_tickers(self, user_id: str = "default", list_name: str = "Default") -> List[str]:
        """Get just the ticker symbols as a list."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            normalized_list = _normalize_list_name(list_name)
            cursor.execute(
                """SELECT ticker FROM user_watchlist
                   WHERE user_id = ? AND list_name = ?
                   ORDER BY ticker""",
                (user_id, normalized_list)
            )
            return [row[0] for row in cursor.fetchall()]

        except Exception:
            return []
        finally:
            
                conn.close()

    def reorder_watchlist(self, tickers: List[str], user_id: str = "default", list_name: str = "Default") -> bool:
        """
        Reorder watchlist by updating added_at timestamps.

        Args:
            tickers: List of tickers in desired order
            user_id: User identifier

        Returns:
            True if successful
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            normalized_list = _normalize_list_name(list_name)

            # Update each ticker's added_at to control order
            now = datetime.now()
            for i, ticker in enumerate(reversed(tickers)):
                new_time = datetime.fromtimestamp(now.timestamp() - i)
                cursor.execute(
                    """UPDATE user_watchlist
                       SET added_at = ?
                       WHERE user_id = ? AND list_name = ? AND ticker = ?""",
                    (new_time.isoformat(), user_id, normalized_list, ticker.upper())
                )

            cursor.execute(
                """UPDATE user_watchlist_lists
                   SET updated_at = datetime('now')
                   WHERE user_id = ? AND list_name = ?""",
                (user_id, normalized_list)
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            
                conn.close()
