"""Broker Stalker analyzer for tracking and analyzing broker activity."""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from db import BrokerStalkerRepository, DoneDetailRepository


class BrokerStalkerAnalyzer:
    """Analyzer for broker activity tracking and pattern detection."""
    
    def __init__(self):
        self.stalker_repo = BrokerStalkerRepository()
        self.done_detail_repo = DoneDetailRepository()
    
    def analyze_broker_activity(self, broker_code: str, ticker: str, 
                                lookback_days: int = 30) -> Dict:
        """
        Analyze broker activity on a specific ticker.
        
        Args:
            broker_code: Broker code to analyze
            ticker: Stock symbol
            lookback_days: Number of days to analyze
        
        Returns:
            Analysis dictionary with daily volumes, streak, and status
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            
            daily_activity = []
            total_buy = 0
            total_sell = 0
            
            for days_ago in range(lookback_days):
                trade_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                
                buy_vol, sell_vol = self._calculate_daily_broker_volume(
                    broker_code, ticker, trade_date
                )
                
                if buy_vol > 0 or sell_vol > 0:
                    net_value = buy_vol - sell_vol
                    daily_activity.append({
                        "date": trade_date,
                        "buy_volume": buy_vol,
                        "sell_volume": sell_vol,
                        "net_value": net_value
                    })
                    total_buy += buy_vol
                    total_sell += sell_vol
            
            streak = self.stalker_repo.calculate_streak(broker_code, ticker)
            
            net_total = total_buy - total_sell
            status = self._determine_status(net_total, streak)
            
            return {
                "broker_code": broker_code,
                "ticker": ticker,
                "lookback_days": lookback_days,
                "total_buy": total_buy,
                "total_sell": total_sell,
                "net_value": net_total,
                "streak_days": streak,
                "status": status,
                "daily_activity": daily_activity[::-1]
            }
        except Exception as e:
            print(f"[!] Error analyzing broker activity: {e}")
            return {
                "broker_code": broker_code,
                "ticker": ticker,
                "error": str(e)
            }
    
    def _calculate_daily_broker_volume(self, broker_code: str, ticker: str, 
                                      trade_date: str) -> Tuple[float, float]:
        """
        Calculate daily buy and sell volumes for a broker on a ticker.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
            trade_date: Trade date (YYYY-MM-DD)
        
        Returns:
            Tuple of (buy_volume, sell_volume) in value
        """
        try:
            records = self.done_detail_repo.get_records(ticker, trade_date)
            
            if not records:
                return (0.0, 0.0)
            
            buy_volume = 0.0
            sell_volume = 0.0
            
            for record in records:
                price = record.get('price', 0)
                qty = record.get('qty', 0)
                value = price * qty
                
                buyer_code = record.get('buyer_code', '')
                seller_code = record.get('seller_code', '')
                
                if buyer_code == broker_code.upper():
                    buy_volume += value
                
                if seller_code == broker_code.upper():
                    sell_volume += value
            
            return (buy_volume, sell_volume)
        except Exception as e:
            print(f"[!] Error calculating daily volume: {e}")
            return (0.0, 0.0)
    
    def _determine_status(self, net_value: float, streak: int) -> str:
        """
        Determine broker status based on net value and streak.
        
        Args:
            net_value: Net value (buy - sell)
            streak: Consecutive days streak
        
        Returns:
            Status string
        """
        if abs(streak) >= 3:
            if streak > 0:
                return "STRONG_ACCUMULATION"
            else:
                return "STRONG_DISTRIBUTION"
        elif net_value > 0:
            return "ACCUMULATING"
        elif net_value < 0:
            return "DISTRIBUTING"
        else:
            return "NEUTRAL"
    
    def calculate_power_level(self, broker_code: str, lookback_days: int = 30) -> int:
        """
        Calculate broker power level (0-100) based on trading activity.
        
        Args:
            broker_code: Broker code
            lookback_days: Number of days to analyze
        
        Returns:
            Power level score (0-100)
        """
        try:
            tracking_records = self.stalker_repo.get_broker_tracking(
                broker_code, days=lookback_days
            )
            
            if not tracking_records:
                return 0
            
            total_volume = sum(abs(r['net_value']) for r in tracking_records)
            active_days = len(set(r['trade_date'] for r in tracking_records))
            unique_tickers = len(set(r['ticker'] for r in tracking_records))
            
            volume_score = min(40, (total_volume / 1_000_000_000) * 10)
            activity_score = min(30, (active_days / lookback_days) * 30)
            diversity_score = min(30, unique_tickers * 3)
            
            power_level = int(volume_score + activity_score + diversity_score)
            
            self.stalker_repo.update_power_level(broker_code, power_level)
            
            return power_level
        except Exception as e:
            print(f"[!] Error calculating power level: {e}")
            return 0
    
    def get_daily_chart_data(self, broker_code: str, ticker: str, 
                            days: int = 7) -> List[Dict]:
        """
        Get daily chart data for visualization.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
            days: Number of days
        
        Returns:
            List of daily data points
        """
        try:
            tracking_records = self.stalker_repo.get_broker_tracking(
                broker_code, ticker, days
            )
            
            chart_data = []
            for record in tracking_records:
                chart_data.append({
                    "date": record['trade_date'],
                    "buy": record['total_buy'],
                    "sell": record['total_sell'],
                    "net": record['net_value']
                })
            
            return sorted(chart_data, key=lambda x: x['date'])
        except Exception as e:
            print(f"[!] Error getting chart data: {e}")
            return []
    
    def get_execution_ledger(self, broker_code: str, ticker: str, 
                            limit: int = 10) -> List[Dict]:
        """
        Get recent execution history ledger.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
            limit: Maximum number of records
        
        Returns:
            List of execution records
        """
        try:
            tracking_records = self.stalker_repo.get_broker_tracking(
                broker_code, ticker, days=30
            )
            
            ledger = []
            for record in tracking_records[:limit]:
                ledger.append({
                    "date": record['trade_date'],
                    "action": "BUY" if record['net_value'] > 0 else "SELL",
                    "volume": abs(record['net_value']),
                    "avg_price": record['avg_price'],
                    "status": record['status']
                })
            
            return ledger
        except Exception as e:
            print(f"[!] Error getting execution ledger: {e}")
            return []
    
    def sync_broker_data(self, broker_code: str, ticker: str = None, 
                        days: int = 7) -> Dict:
        """
        Sync broker data from done_detail records to tracking table.
        
        Args:
            broker_code: Broker code to sync
            ticker: Optional ticker filter (if None, sync all tickers)
            days: Number of days to sync
        
        Returns:
            Sync result summary
        """
        try:
            synced_count = 0
            errors = []
            
            if ticker:
                tickers_to_sync = [ticker]
            else:
                tickers_to_sync = self._get_active_tickers(days)
            
            for t in tickers_to_sync:
                for days_ago in range(days):
                    trade_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
                    
                    buy_vol, sell_vol = self._calculate_daily_broker_volume(
                        broker_code, t, trade_date
                    )
                    
                    if buy_vol > 0 or sell_vol > 0:
                        net_value = buy_vol - sell_vol
                        
                        avg_price = self._calculate_avg_price(
                            broker_code, t, trade_date
                        )
                        
                        streak = self.stalker_repo.calculate_streak(broker_code, t)
                        status = self._determine_status(net_value, streak)
                        
                        success = self.stalker_repo.save_tracking_record(
                            broker_code, t, trade_date,
                            buy_vol, sell_vol, net_value,
                            avg_price, streak, status
                        )
                        
                        if success:
                            synced_count += 1
                        else:
                            errors.append(f"{t} on {trade_date}")
            
            power_level = self.calculate_power_level(broker_code, days)
            
            return {
                "broker_code": broker_code,
                "synced_records": synced_count,
                "errors": errors,
                "power_level": power_level,
                "status": "success" if not errors else "partial"
            }
        except Exception as e:
            print(f"[!] Error syncing broker data: {e}")
            return {
                "broker_code": broker_code,
                "error": str(e),
                "status": "failed"
            }
    
    def _get_active_tickers(self, days: int) -> List[str]:
        """
        Get list of active tickers from done_detail records.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of ticker symbols
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            conn = self.done_detail_repo._get_conn()
            try:
                cursor = conn.execute(
                    """SELECT DISTINCT ticker 
                       FROM done_detail_records 
                       WHERE trade_date >= ?
                       ORDER BY ticker""",
                    (cutoff_date,)
                )
                return [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
        except Exception as e:
            print(f"[!] Error getting active tickers: {e}")
            return []
    
    def _calculate_avg_price(self, broker_code: str, ticker: str, 
                            trade_date: str) -> Optional[float]:
        """
        Calculate average execution price for a broker on a ticker.
        
        Args:
            broker_code: Broker code
            ticker: Stock symbol
            trade_date: Trade date
        
        Returns:
            Average price or None
        """
        try:
            records = self.done_detail_repo.get_records(ticker, trade_date)
            
            if not records:
                return None
            
            total_value = 0.0
            total_qty = 0
            
            for record in records:
                buyer_code = record.get('buyer_code', '')
                seller_code = record.get('seller_code', '')
                
                if buyer_code == broker_code.upper() or seller_code == broker_code.upper():
                    price = record.get('price', 0)
                    qty = record.get('qty', 0)
                    total_value += price * qty
                    total_qty += qty
            
            if total_qty > 0:
                return total_value / total_qty
            return None
        except Exception as e:
            print(f"[!] Error calculating avg price: {e}")
            return None
