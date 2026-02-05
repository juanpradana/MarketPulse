"""Broker Stalker repository for tracking broker activity."""
import sqlite3
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from .connection import BaseRepository


class BrokerStalkerRepository(BaseRepository):
    """Repository for Broker Stalker watchlist and tracking."""
    
    def add_broker_to_watchlist(self, broker_code: str, broker_name: str = None, description: str = None) -> bool:
        """
        Add a broker to the watchlist.
        
        Args:
            broker_code: Broker code (e.g., 'YP', 'RK')
            broker_name: Full broker name
            description: Optional description
        
        Returns:
            True if added successfully
        """
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO broker_stalker_watchlist 
                   (broker_code, broker_name, description, updated_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (broker_code.upper(), broker_name, description)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error adding broker to watchlist: {e}")
            return False
        finally:
            conn.close()
    
    def remove_broker_from_watchlist(self, broker_code: str) -> bool:
        """
        Remove a broker from the watchlist.
        
        Args:
            broker_code: Broker code to remove
        
        Returns:
            True if removed successfully
        """
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM broker_stalker_watchlist WHERE broker_code = ?",
                (broker_code.upper(),)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error removing broker from watchlist: {e}")
            return False
        finally:
            conn.close()
    
    def get_watchlist(self) -> List[Dict]:
        """
        Get all brokers in the watchlist.
        
        Returns:
            List of broker dictionaries
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT broker_code, broker_name, description, power_level, 
                          created_at, updated_at
                   FROM broker_stalker_watchlist
                   ORDER BY power_level DESC, broker_code ASC"""
            )
            rows = cursor.fetchall()
            return [
                {
                    "broker_code": row[0],
                    "broker_name": row[1],
                    "description": row[2],
                    "power_level": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[!] Error getting watchlist: {e}")
            return []
        finally:
            conn.close()
    
    def update_power_level(self, broker_code: str, power_level: int) -> bool:
        """
        Update broker power level (0-100).
        
        Args:
            broker_code: Broker code
            power_level: Power level score
        
        Returns:
            True if updated successfully
        """
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE broker_stalker_watchlist 
                   SET power_level = ?, updated_at = datetime('now')
                   WHERE broker_code = ?""",
                (power_level, broker_code.upper())
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error updating power level: {e}")
            return False
        finally:
            conn.close()
    
    def save_tracking_record(self, broker_code: str, ticker: str, trade_date: str,
                            total_buy: float, total_sell: float, net_value: float,
                            avg_price: float = None, streak_days: int = 0, 
                            status: str = None) -> bool:
        """
        Save or update a tracking record for a broker's activity on a ticker.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
            trade_date: Trade date (YYYY-MM-DD)
            total_buy: Total buy value
            total_sell: Total sell value
            net_value: Net value (buy - sell)
            avg_price: Average execution price
            streak_days: Consecutive days of activity
            status: Status (e.g., 'ACCUMULATING', 'DISTRIBUTING', 'NEUTRAL')
        
        Returns:
            True if saved successfully
        """
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO broker_stalker_tracking
                   (broker_code, ticker, trade_date, total_buy, total_sell, net_value,
                    avg_price, streak_days, status, calculated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (broker_code.upper(), ticker.upper(), trade_date, total_buy, total_sell,
                 net_value, avg_price, streak_days, status)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"[!] Error saving tracking record: {e}")
            return False
        finally:
            conn.close()
    
    def get_broker_tracking(self, broker_code: str, ticker: str = None, 
                           days: int = 30) -> List[Dict]:
        """
        Get tracking records for a broker.
        
        Args:
            broker_code: Broker code
            ticker: Optional ticker filter
            days: Number of days to look back
        
        Returns:
            List of tracking records
        """
        conn = self._get_conn()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            if ticker:
                query = """
                    SELECT broker_code, ticker, trade_date, total_buy, total_sell,
                           net_value, avg_price, streak_days, status, calculated_at
                    FROM broker_stalker_tracking
                    WHERE broker_code = ? AND ticker = ? AND trade_date >= ?
                    ORDER BY trade_date DESC
                """
                cursor = conn.execute(query, (broker_code.upper(), ticker.upper(), cutoff_date))
            else:
                query = """
                    SELECT broker_code, ticker, trade_date, total_buy, total_sell,
                           net_value, avg_price, streak_days, status, calculated_at
                    FROM broker_stalker_tracking
                    WHERE broker_code = ? AND trade_date >= ?
                    ORDER BY trade_date DESC, ticker ASC
                """
                cursor = conn.execute(query, (broker_code.upper(), cutoff_date))
            
            rows = cursor.fetchall()
            return [
                {
                    "broker_code": row[0],
                    "ticker": row[1],
                    "trade_date": row[2],
                    "total_buy": row[3],
                    "total_sell": row[4],
                    "net_value": row[5],
                    "avg_price": row[6],
                    "streak_days": row[7],
                    "status": row[8],
                    "calculated_at": row[9]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[!] Error getting broker tracking: {e}")
            return []
        finally:
            conn.close()
    
    def calculate_streak(self, broker_code: str, ticker: str) -> int:
        """
        Calculate consecutive days of net buying or selling.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
        
        Returns:
            Streak days (positive for buying, negative for selling)
        """
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """SELECT trade_date, net_value
                   FROM broker_stalker_tracking
                   WHERE broker_code = ? AND ticker = ?
                   ORDER BY trade_date DESC
                   LIMIT 30""",
                (broker_code.upper(), ticker.upper())
            )
            rows = cursor.fetchall()
            
            if not rows:
                return 0
            
            streak = 0
            current_direction = None
            
            for row in rows:
                net_value = row[1]
                
                if net_value == 0:
                    break
                
                direction = 'BUY' if net_value > 0 else 'SELL'
                
                if current_direction is None:
                    current_direction = direction
                    streak = 1
                elif current_direction == direction:
                    streak += 1
                else:
                    break
            
            return streak if current_direction == 'BUY' else -streak
        except Exception as e:
            print(f"[!] Error calculating streak: {e}")
            return 0
        finally:
            conn.close()
    
    def get_broker_portfolio(self, broker_code: str, min_net_value: float = 0) -> List[Dict]:
        """
        Get broker's current portfolio (active positions).
        
        Args:
            broker_code: Broker code
            min_net_value: Minimum net value to include
        
        Returns:
            List of portfolio positions
        """
        conn = self._get_conn()
        try:
            query = """
                SELECT ticker, 
                       SUM(net_value) as total_net_value,
                       COUNT(DISTINCT trade_date) as trading_days,
                       MAX(trade_date) as last_trade_date,
                       AVG(avg_price) as avg_execution_price
                FROM broker_stalker_tracking
                WHERE broker_code = ?
                GROUP BY ticker
                HAVING total_net_value >= ?
                ORDER BY total_net_value DESC
            """
            cursor = conn.execute(query, (broker_code.upper(), min_net_value))
            rows = cursor.fetchall()
            
            return [
                {
                    "ticker": row[0],
                    "total_net_value": row[1],
                    "trading_days": row[2],
                    "last_trade_date": row[3],
                    "avg_execution_price": row[4],
                    "streak_days": self.calculate_streak(broker_code, row[0])
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[!] Error getting broker portfolio: {e}")
            return []
        finally:
            conn.close()
    
    def get_ticker_broker_activity(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        Get all broker activity for a specific ticker.
        
        Args:
            ticker: Stock symbol
            days: Number of days to look back
        
        Returns:
            List of broker activities
        """
        conn = self._get_conn()
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            query = """
                SELECT broker_code, trade_date, total_buy, total_sell, net_value,
                       avg_price, streak_days, status
                FROM broker_stalker_tracking
                WHERE ticker = ? AND trade_date >= ?
                ORDER BY trade_date DESC, ABS(net_value) DESC
            """
            cursor = conn.execute(query, (ticker.upper(), cutoff_date))
            rows = cursor.fetchall()
            
            return [
                {
                    "broker_code": row[0],
                    "trade_date": row[1],
                    "total_buy": row[2],
                    "total_sell": row[3],
                    "net_value": row[4],
                    "avg_price": row[5],
                    "streak_days": row[6],
                    "status": row[7]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[!] Error getting ticker broker activity: {e}")
            return []
        finally:
            conn.close()
