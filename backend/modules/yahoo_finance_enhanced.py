"""
Yahoo Finance Enhanced Module

Provides enhanced Yahoo Finance data fetching for bandar detection including:
- Float shares analysis
- Volume metrics
- Earnings calendar
- Beta and price position data
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import yfinance as yf

import config

logger = logging.getLogger(__name__)


class YahooFinanceEnhanced:
    """
    Enhanced Yahoo Finance client for bandar detection features.

    Provides:
    - Float data fetching and caching
    - Volume anomaly detection metrics
    - Earnings calendar data
    - Composite scoring data (beta, 52W range, etc.)
    """

    # Cache durations
    FLOAT_CACHE_DAYS = 7
    VOLUME_CACHE_DAYS = 1
    EARNINGS_CACHE_DAYS = 7
    PRICE_STATS_CACHE_DAYS = 1

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_float_data(self, ticker: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Fetch float shares and outstanding shares from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol (e.g., 'BBCA')
            force_refresh: Force fetch from Yahoo even if cache is valid

        Returns:
            Dict with float data or None if unavailable
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_float_data(ticker)
            if cached:
                return cached

        try:
            # Yahoo Finance uses .JK suffix for Indonesian stocks
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            # Extract float data
            shares_outstanding = info.get('sharesOutstanding')
            float_shares = info.get('floatShares')

            if not shares_outstanding and not float_shares:
                logger.warning(f"No float data available for {ticker}")
                return None

            # Calculate float ratio
            float_ratio = None
            if float_shares and shares_outstanding:
                float_ratio = float_shares / shares_outstanding

            result = {
                'ticker': ticker,
                'shares_outstanding': shares_outstanding,
                'float_shares': float_shares,
                'float_ratio': float_ratio,
                'cached_at': datetime.now().isoformat(),
                'source': 'yfinance'
            }

            # Cache the result
            self._cache_float_data(result)

            return result

        except Exception as e:
            logger.error(f"Error fetching float data for {ticker}: {e}")
            return None

    def _get_cached_float_data(self, ticker: str) -> Optional[Dict]:
        """Get cached float data if still valid."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=self.FLOAT_CACHE_DAYS)).isoformat()

            cursor.execute("""
                SELECT ticker, shares_outstanding, float_shares, float_ratio, cached_at, source
                FROM stock_float_data
                WHERE ticker = ? AND cached_at > ?
            """, (ticker, cutoff))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def _cache_float_data(self, data: Dict):
        """Cache float data to database."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO stock_float_data
                (ticker, shares_outstanding, float_shares, float_ratio, cached_at, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['ticker'],
                data.get('shares_outstanding'),
                data.get('float_shares'),
                data.get('float_ratio'),
                data['cached_at'],
                data.get('source', 'yfinance')
            ))
            conn.commit()
        finally:
            conn.close()

    def calculate_bandar_control(
        self,
        ticker: str,
        bandar_lot: float,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Calculate what percentage of float is controlled by bandar.

        Args:
            ticker: Stock ticker symbol
            bandar_lot: Total lots controlled by bandar (from inventory analysis)
            force_refresh: Force refresh float data

        Returns:
            Dict with control metrics or None if float data unavailable
        """
        # Get float data
        float_data = self.fetch_float_data(ticker, force_refresh)
        if not float_data or not float_data.get('float_shares'):
            return None

        float_shares = float_data['float_shares']

        # Convert bandar lots to shares (1 lot = 100 shares)
        bandar_shares = bandar_lot * 100

        # Calculate percentage of float controlled
        bandar_float_pct = (bandar_shares / float_shares) * 100 if float_shares > 0 else 0

        # Determine control level
        control_level = self._get_control_level(bandar_float_pct)

        return {
            'ticker': ticker,
            'shares_outstanding': float_data.get('shares_outstanding'),
            'float_shares': float_shares,
            'float_ratio': float_data.get('float_ratio'),
            'bandar_lots': bandar_lot,
            'bandar_shares': bandar_shares,
            'bandar_float_pct': bandar_float_pct,
            'control_level': control_level,
            'cached_at': datetime.now().isoformat()
        }

    def _get_control_level(self, bandar_float_pct: float) -> str:
        """
        Determine control level based on percentage of float controlled.

        Returns:
            'WEAK', 'MODERATE', 'STRONG', or 'DOMINANT'
        """
        if bandar_float_pct < 5:
            return 'WEAK'
        elif bandar_float_pct < 10:
            return 'MODERATE'
        elif bandar_float_pct < 20:
            return 'STRONG'
        else:
            return 'DOMINANT'

    def get_control_level_score(self, control_level: str) -> int:
        """
        Get scoring points for bandar control level.

        Used in bandarmology deep analysis scoring.
        """
        scores = {
            'WEAK': 0,
            'MODERATE': 5,
            'STRONG': 10,
            'DOMINANT': 15
        }
        return scores.get(control_level, 0)

    def fetch_volume_metrics(self, ticker: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Fetch volume metrics for anomaly detection.

        Returns:
            Dict with volume metrics including 10-day and 3-month averages
        """
        cache_key = f"volume_metrics_{ticker}"

        # Check cache
        if not force_refresh:
            cached = self._get_cached_volume_metrics(ticker)
            if cached:
                return cached

        try:
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            current_volume = info.get('volume')
            avg_volume_10d = info.get('averageVolume10days')
            avg_volume_3m = info.get('averageVolume')

            if not current_volume:
                return None

            # Calculate volume ratio
            volume_ratio = current_volume / avg_volume_10d if avg_volume_10d else None

            result = {
                'ticker': ticker,
                'current_volume': current_volume,
                'avg_volume_10d': avg_volume_10d,
                'avg_volume_3m': avg_volume_3m,
                'volume_ratio': volume_ratio,
                'fetched_at': datetime.now().isoformat()
            }

            self._cache_volume_metrics(result)
            return result

        except Exception as e:
            logger.error(f"Error fetching volume metrics for {ticker}: {e}")
            return None

    def _get_cached_volume_metrics(self, ticker: str) -> Optional[Dict]:
        """Get cached volume metrics if still valid."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            # Get latest record for ticker
            cursor.execute("""
                SELECT * FROM volume_daily_records
                WHERE ticker = ? AND avg_volume_10d IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT 1
            """, (ticker,))

            row = cursor.fetchone()
            if row:
                row_dict = dict(row)
                # Check if cache is still valid (within 1 day)
                fetched_at = row_dict.get('fetched_at')
                if fetched_at:
                    fetched_dt = datetime.fromisoformat(fetched_at.replace('Z', '+00:00').replace('+00:00', ''))
                    if datetime.now() - fetched_dt < timedelta(days=self.VOLUME_CACHE_DAYS):
                        return {
                            'ticker': ticker,
                            'current_volume': row_dict.get('volume'),
                            'avg_volume_10d': row_dict.get('avg_volume_10d'),
                            'avg_volume_3m': row_dict.get('avg_volume_3m'),
                            'volume_ratio': row_dict.get('volume_ratio'),
                            'volume_signal': row_dict.get('volume_signal'),
                            'fetched_at': fetched_at
                        }
            return None
        finally:
            conn.close()

    def _cache_volume_metrics(self, data: Dict):
        """Cache volume metrics to volume_daily_records."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("""
                INSERT OR REPLACE INTO volume_daily_records
                (ticker, trade_date, volume, avg_volume_10d, avg_volume_3m, volume_ratio, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['ticker'],
                today,
                data.get('current_volume'),
                data.get('avg_volume_10d'),
                data.get('avg_volume_3m'),
                data.get('volume_ratio'),
                data['fetched_at']
            ))
            conn.commit()
        finally:
            conn.close()

    def fetch_earnings_calendar(
        self,
        ticker: Optional[str] = None,
        days_ahead: int = 30,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Fetch earnings calendar data.

        Args:
            ticker: Specific ticker or None for all (not supported by yfinance, will need manual fetching)
            days_ahead: Number of days to look ahead
            force_refresh: Force refresh from Yahoo

        Returns:
            List of earnings events
        """
        if ticker:
            return self._fetch_single_ticker_earnings(ticker, force_refresh)
        else:
            # For all tickers, we'd need to iterate through a list
            # This is expensive, so we return cached data
            return self._get_all_cached_earnings(days_ahead)

    def _fetch_single_ticker_earnings(self, ticker: str, force_refresh: bool = False) -> List[Dict]:
        """Fetch earnings for a single ticker."""
        if not force_refresh:
            cached = self._get_cached_earnings(ticker)
            if cached:
                return cached

        try:
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)

            # Get earnings dates
            calendar = stock.calendar
            if calendar is None or calendar.empty:
                return []

            results = []
            for _, row in calendar.iterrows():
                result = {
                    'ticker': ticker,
                    'earnings_date': row.get('Earnings Date'),
                    'eps_estimate': row.get('EPS Estimate'),
                    'revenue_estimate': row.get('Revenue Estimate'),
                    'fetched_at': datetime.now().isoformat()
                }
                results.append(result)
                self._cache_earnings(result)

            return results

        except Exception as e:
            logger.error(f"Error fetching earnings for {ticker}: {e}")
            return []

    def _get_cached_earnings(self, ticker: str) -> List[Dict]:
        """Get cached earnings data."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=self.EARNINGS_CACHE_DAYS)).isoformat()

            cursor.execute("""
                SELECT * FROM earnings_calendar
                WHERE ticker = ? AND fetched_at > ?
                ORDER BY earnings_date
            """, (ticker, cutoff))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _get_all_cached_earnings(self, days_ahead: int) -> List[Dict]:
        """Get all cached earnings within date range."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT * FROM earnings_calendar
                WHERE earnings_date <= ?
                ORDER BY earnings_date
            """, (future_date,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _cache_earnings(self, data: Dict):
        """Cache earnings data."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Determine fiscal quarter from date
            earnings_date = data.get('earnings_date')
            if earnings_date:
                if isinstance(earnings_date, str):
                    earnings_date = datetime.fromisoformat(earnings_date.replace('Z', '+00:00').replace('+00:00', ''))
                quarter = f"Q{(earnings_date.month - 1) // 3 + 1}"
                year = earnings_date.year
                fiscal_quarter = f"{year}-{quarter}"
            else:
                fiscal_quarter = None

            cursor.execute("""
                INSERT OR REPLACE INTO earnings_calendar
                (ticker, earnings_date, fiscal_quarter, eps_estimate, revenue_estimate, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['ticker'],
                earnings_date.strftime('%Y-%m-%d') if earnings_date else None,
                fiscal_quarter,
                data.get('eps_estimate'),
                data.get('revenue_estimate'),
                data['fetched_at']
            ))
            conn.commit()
        finally:
            conn.close()

    def fetch_price_stats(self, ticker: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Fetch price statistics for composite scoring.

        Returns:
            Dict with beta, 52W high/low, current price position, etc.
        """
        if not force_refresh:
            cached = self._get_cached_price_stats(ticker)
            if cached:
                return cached

        try:
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)
            info = stock.info

            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            week_52_high = info.get('fiftyTwoWeekHigh')
            week_52_low = info.get('fiftyTwoWeekLow')
            beta = info.get('beta')
            market_cap = info.get('marketCap')

            # Calculate position in 52W range
            position_pct = None
            if current_price and week_52_high and week_52_low and week_52_high > week_52_low:
                position_pct = (current_price - week_52_low) / (week_52_high - week_52_low)

            result = {
                'ticker': ticker,
                'current_price': current_price,
                'week_52_high': week_52_high,
                'week_52_low': week_52_low,
                'position_pct': position_pct,
                'beta': beta,
                'market_cap': market_cap,
                'fetched_at': datetime.now().isoformat()
            }

            # Cache to market_metadata
            self._cache_price_stats(result)

            return result

        except Exception as e:
            logger.error(f"Error fetching price stats for {ticker}: {e}")
            return None

    def _get_cached_price_stats(self, ticker: str) -> Optional[Dict]:
        """Get cached price stats."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=self.PRICE_STATS_CACHE_DAYS)).isoformat()

            cursor.execute("""
                SELECT symbol as ticker, market_cap, cached_at
                FROM market_metadata
                WHERE symbol = ? AND cached_at > ?
            """, (ticker, cutoff))

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def _cache_price_stats(self, data: Dict):
        """Cache price stats to market_metadata."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_metadata
                (symbol, market_cap, last_price, cached_at, source)
                VALUES (?, ?, ?, ?, 'yfinance')
            """, (
                data['ticker'],
                data.get('market_cap'),
                data.get('current_price'),
                data['fetched_at']
            ))
            conn.commit()
        finally:
            conn.close()


# Singleton instance
_yf_enhanced: Optional[YahooFinanceEnhanced] = None


def get_yahoo_finance_enhanced(db_path: Optional[str] = None) -> YahooFinanceEnhanced:
    """Get or create singleton instance of YahooFinanceEnhanced."""
    global _yf_enhanced
    if _yf_enhanced is None:
        _yf_enhanced = YahooFinanceEnhanced(db_path)
    return _yf_enhanced
