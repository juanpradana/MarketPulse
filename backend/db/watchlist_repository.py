"""
Watchlist Repository

Manages user's personalized ticker watchlist.
Tracks user's favorite stocks for quick filtering and monitoring.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from db.connection import BaseRepository


class WatchlistRepository(BaseRepository):
    """Repository for user watchlist operations."""

    def add_ticker(self, ticker: str, user_id: str = "default") -> bool:
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

            # Check if already exists
            cursor.execute(
                """SELECT 1 FROM user_watchlist
                   WHERE user_id = ? AND ticker = ?""",
                (user_id, ticker.upper())
            )
            if cursor.fetchone():
                return False

            # Add to watchlist
            cursor.execute(
                """INSERT INTO user_watchlist (user_id, ticker, added_at)
                   VALUES (?, ?, ?)""",
                (user_id, ticker.upper(), datetime.now().isoformat())
            )
            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def remove_ticker(self, ticker: str, user_id: str = "default") -> bool:
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

            cursor.execute(
                """DELETE FROM user_watchlist
                   WHERE user_id = ? AND ticker = ?""",
                (user_id, ticker.upper())
            )

            if cursor.rowcount > 0:
                conn.commit()
                return True
            return False

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            
                conn.close()

    def get_watchlist(self, user_id: str = "default") -> List[Dict[str, Any]]:
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

            # Get watchlist tickers
            cursor.execute(
                """SELECT ticker, added_at FROM user_watchlist
                   WHERE user_id = ?
                   ORDER BY added_at DESC""",
                (user_id,)
            )

            results = []
            for row in cursor.fetchall():
                ticker = row[0]

                # Get latest price data
                latest_price = self._get_latest_price(cursor, ticker)

                results.append({
                    "ticker": ticker,
                    "added_at": row[1],
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
            return None

        except Exception:
            return None

    def is_in_watchlist(self, ticker: str, user_id: str = "default") -> bool:
        """Check if a ticker is in user's watchlist."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT 1 FROM user_watchlist
                   WHERE user_id = ? AND ticker = ?""",
                (user_id, ticker.upper())
            )
            return cursor.fetchone() is not None

        except Exception:
            return False
        finally:
            
                conn.close()

    def get_watchlist_count(self, user_id: str = "default") -> int:
        """Get number of tickers in watchlist."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM user_watchlist WHERE user_id = ?""",
                (user_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0

        except Exception:
            return 0
        finally:
            
                conn.close()

    def get_watchlist_tickers(self, user_id: str = "default") -> List[str]:
        """Get just the ticker symbols as a list."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT ticker FROM user_watchlist
                   WHERE user_id = ?
                   ORDER BY ticker""",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

        except Exception:
            return []
        finally:
            
                conn.close()

    def reorder_watchlist(self, tickers: List[str], user_id: str = "default") -> bool:
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

            # Update each ticker's added_at to control order
            now = datetime.now()
            for i, ticker in enumerate(reversed(tickers)):
                new_time = datetime.fromtimestamp(now.timestamp() - i)
                cursor.execute(
                    """UPDATE user_watchlist
                       SET added_at = ?
                       WHERE user_id = ? AND ticker = ?""",
                    (new_time.isoformat(), user_id, ticker.upper())
                )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise e
        finally:
            
                conn.close()
