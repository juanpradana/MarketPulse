"""
Earnings Tracker Module

Tracks earnings calendar and detects pre-earnings accumulation patterns.
Provides event-driven analysis for bandar detection.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List

import yfinance as yf
import config
from modules.yahoo_finance_enhanced import get_yahoo_finance_enhanced

logger = logging.getLogger(__name__)


class EarningsTracker:
    """
    Earnings calendar tracker for detecting pre-earnings patterns.

    Provides:
    - Upcoming earnings calendar
    - Pre-earnings accumulation detection
    - Historical earnings surprise analysis
    - Earnings-based signals
    """

    # Days before earnings where accumulation typically occurs
    PRE_EARNINGS_WINDOW_START = 14
    PRE_EARNINGS_WINDOW_END = 7

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")
        self.yf_enhanced = get_yahoo_finance_enhanced(db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_upcoming_earnings(
        self,
        ticker: Optional[str] = None,
        days_ahead: int = 30,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Fetch upcoming earnings dates.

        Args:
            ticker: Specific ticker or None for all cached
            days_ahead: Number of days to look ahead
            force_refresh: Force refresh from Yahoo

        Returns:
            List of earnings events
        """
        if ticker:
            return self._fetch_single_ticker_earnings(ticker, days_ahead, force_refresh)
        else:
            return self._get_all_cached_earnings(days_ahead)

    def _fetch_single_ticker_earnings(
        self,
        ticker: str,
        days_ahead: int = 30,
        force_refresh: bool = False
    ) -> List[Dict]:
        """Fetch earnings for a single ticker."""
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_earnings(ticker, days_ahead)
            if cached:
                return cached

        try:
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)

            # Get earnings dates from calendar
            calendar = stock.calendar
            if calendar is None:
                return []
            # Handle both DataFrame and dict formats
            if hasattr(calendar, 'empty') and calendar.empty:
                return []
            if isinstance(calendar, dict) and not calendar:
                return []

            results = []
            # Handle both DataFrame (iterrows) and dict formats
            if hasattr(calendar, 'iterrows'):
                # It's a DataFrame
                rows = calendar.iterrows()
            elif isinstance(calendar, dict):
                # Convert dict to list of dicts
                rows = enumerate([calendar])
            else:
                rows = []

            for _, row in rows:
                earnings_date = row.get('Earnings Date') if hasattr(row, 'get') else row['Earnings Date']
                if earnings_date:
                    # Handle if earnings_date is a list (sometimes Yahoo returns a range)
                    if isinstance(earnings_date, list) and earnings_date:
                        earnings_date = earnings_date[0]
                    # Handle datetime.date (convert to datetime)
                    if hasattr(earnings_date, 'year') and not isinstance(earnings_date, datetime):
                        earnings_date = datetime.combine(earnings_date, datetime.min.time())
                    # Handle pandas Timestamp
                    elif hasattr(earnings_date, 'to_pydatetime'):
                        earnings_date = earnings_date.to_pydatetime()
                    elif isinstance(earnings_date, str):
                        try:
                            earnings_date = datetime.fromisoformat(earnings_date.replace('Z', '+00:00').replace('+00:00', ''))
                        except ValueError:
                            # Try common date formats
                            for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%m/%d/%Y'):
                                try:
                                    earnings_date = datetime.strptime(earnings_date, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                # If all fail, skip this entry
                                continue
                    elif not isinstance(earnings_date, datetime):
                        # Skip if we can't parse the date
                        continue

                    # Check if within lookahead window
                    days_until = (earnings_date - datetime.now()).days
                    if days_until > days_ahead:
                        continue

                    result = {
                        'ticker': ticker,
                        'earnings_date': earnings_date.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'fiscal_quarter': self._get_fiscal_quarter(earnings_date),
                        'eps_estimate': row.get('EPS Estimate'),
                        'revenue_estimate': row.get('Revenue Estimate'),
                        'fetched_at': datetime.now().isoformat()
                    }

                    # Add historical context
                    historical = self._get_earnings_history(ticker)
                    result['historical_surprises'] = [
                        h for h in historical if h.get('surprise_pct') is not None
                    ][:4]  # Last 4 quarters

                    results.append(result)
                    self._cache_earnings(result)

            return results

        except Exception as e:
            logger.error(f"Error fetching earnings for {ticker}: {e}")
            return []

    def _get_cached_earnings(self, ticker: str, days_ahead: int) -> List[Dict]:
        """Get cached earnings data if still valid."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT * FROM earnings_calendar
                WHERE ticker = ? AND fetched_at > ? AND earnings_date <= ?
                ORDER BY earnings_date
            """, (ticker, cutoff, future_date))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                earnings_date = datetime.strptime(result['earnings_date'], '%Y-%m-%d')
                result['days_until'] = (earnings_date - datetime.now()).days
                results.append(result)

            return results
        finally:
            conn.close()

    def _get_all_cached_earnings(self, days_ahead: int) -> List[Dict]:
        """Get all cached upcoming earnings."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            future_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("""
                SELECT * FROM earnings_calendar
                WHERE earnings_date >= ? AND earnings_date <= ?
                ORDER BY earnings_date
            """, (today, future_date))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                result = dict(row)
                earnings_date = datetime.strptime(result['earnings_date'], '%Y-%m-%d')
                result['days_until'] = (earnings_date - datetime.now()).days
                results.append(result)

            return results
        finally:
            conn.close()

    def _cache_earnings(self, data: Dict):
        """Cache earnings data to database."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO earnings_calendar
                (ticker, earnings_date, fiscal_quarter, eps_estimate, revenue_estimate, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['ticker'],
                data['earnings_date'],
                data.get('fiscal_quarter'),
                data.get('eps_estimate'),
                data.get('revenue_estimate'),
                data['fetched_at']
            ))
            conn.commit()
        finally:
            conn.close()

    def _get_fiscal_quarter(self, date: datetime) -> str:
        """Determine fiscal quarter from date."""
        quarter = (date.month - 1) // 3 + 1
        return f"Q{quarter} {date.year}"

    def _get_earnings_history(self, ticker: str) -> List[Dict]:
        """Get historical earnings data for surprise analysis."""
        try:
            yf_ticker = f"{ticker}.JK"
            stock = yf.Ticker(yf_ticker)

            # Get earnings history
            earnings = stock.earnings_dates
            if earnings is None or earnings.empty:
                return []

            results = []
            for index, row in earnings.iterrows():
                result = {
                    'ticker': ticker,
                    'earnings_date': index.strftime('%Y-%m-%d') if hasattr(index, 'strftime') else str(index),
                    'eps_estimate': row.get('EPS Estimate'),
                    'eps_actual': row.get('Reported EPS'),
                    'surprise_pct': row.get('Surprise(%)'),
                }
                results.append(result)

            return results

        except Exception as e:
            logger.warning(f"Error getting earnings history for {ticker}: {e}")
            return []

    def detect_pre_earnings_pattern(self, ticker: str) -> Optional[Dict]:
        """
        Detect if bandar is accumulating before upcoming earnings.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with pattern detection results or None
        """
        # Get upcoming earnings
        upcoming = self.fetch_upcoming_earnings(ticker, days_ahead=30)
        if not upcoming:
            return None

        next_earnings = upcoming[0]
        days_until = next_earnings.get('days_until', 999)

        # Check if within pre-earnings window
        if days_until > self.PRE_EARNINGS_WINDOW_START:
            return {
                'ticker': ticker,
                'signal': 'TOO_EARLY',
                'days_until': days_until,
                'earnings_date': next_earnings['earnings_date'],
                'message': 'Earnings too far away for pattern detection'
            }

        if days_until < 0:
            return {
                'ticker': ticker,
                'signal': 'PASSED',
                'days_until': days_until,
                'earnings_date': next_earnings['earnings_date'],
                'message': 'Earnings date has passed'
            }

        # Get bandar activity data
        bandar_activity = self._get_bandar_activity(ticker)

        # Determine signal
        signal = self._classify_pre_earnings_signal(
            days_until,
            bandar_activity,
            next_earnings.get('historical_surprises', [])
        )

        return {
            'ticker': ticker,
            'signal': signal['signal'],
            'confidence': signal['confidence'],
            'days_until': days_until,
            'earnings_date': next_earnings['earnings_date'],
            'bandar_activity': bandar_activity,
            'historical_pattern': signal.get('historical_pattern'),
            'message': signal.get('message')
        }

    def _get_bandar_activity(self, ticker: str) -> Dict:
        """Get recent bandar activity for a ticker."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Get from deep cache
            cursor.execute("""
                SELECT deep_score, accum_phase, txn_mm_cum, txn_foreign_cum,
                       bandar_total_lot, volume_signal
                FROM bandarmology_deep_cache
                WHERE ticker = ?
                ORDER BY analysis_date DESC
                LIMIT 1
            """, (ticker,))

            row = cursor.fetchone()
            if row:
                return {
                    'deep_score': row['deep_score'],
                    'phase': row['accum_phase'],
                    'mm_flow': row['txn_mm_cum'],
                    'foreign_flow': row['txn_foreign_cum'],
                    'bandar_lot': row['bandar_total_lot'],
                    'volume_signal': row['volume_signal']
                }

            return {}

        except Exception as e:
            logger.warning(f"Error getting bandar activity for {ticker}: {e}")
            return {}
        finally:
            conn.close()

    def _classify_pre_earnings_signal(
        self,
        days_until: int,
        bandar_activity: Dict,
        historical_surprises: List[Dict]
    ) -> Dict:
        """
        Classify the pre-earnings pattern signal.

        Returns:
            Dict with signal, confidence, and message
        """
        phase = bandar_activity.get('phase', '')
        deep_score = bandar_activity.get('deep_score', 0) or 0
        volume_signal = bandar_activity.get('volume_signal', '')

        # Check for accumulation pattern
        is_accumulating = phase in ('ACCUMULATION', 'EARLY_ACCUM', 'MARKUP') or deep_score > 100
        has_volume_confirmation = volume_signal == 'ACCUMULATION'

        # Calculate historical surprise tendency
        positive_surprises = sum(1 for h in historical_surprises if h.get('surprise_pct', 0) > 0)
        total_surprises = len([h for h in historical_surprises if h.get('surprise_pct') is not None])
        surprise_rate = positive_surprises / total_surprises if total_surprises > 0 else 0.5

        # Within optimal window (7-14 days before)
        in_optimal_window = self.PRE_EARNINGS_WINDOW_END <= days_until <= self.PRE_EARNINGS_WINDOW_START

        if in_optimal_window and is_accumulating:
            if has_volume_confirmation and surprise_rate > 0.6:
                return {
                    'signal': 'PRE_EARNINGS_ACCUM',
                    'confidence': 85,
                    'historical_pattern': f'{positive_surprises}/{total_surprises} positive surprises',
                    'message': 'Strong pre-earnings accumulation detected with volume confirmation'
                }
            elif has_volume_confirmation:
                return {
                    'signal': 'PRE_EARNINGS_ACCUM',
                    'confidence': 70,
                    'historical_pattern': f'{positive_surprises}/{total_surprises} positive surprises',
                    'message': 'Pre-earnings accumulation with volume confirmation'
                }
            else:
                return {
                    'signal': 'PRE_EARNINGS_WATCH',
                    'confidence': 60,
                    'historical_pattern': f'{positive_surprises}/{total_surprises} positive surprises',
                    'message': 'Possible pre-earnings accumulation (awaiting volume confirmation)'
                }

        if days_until < self.PRE_EARNINGS_WINDOW_END:
            return {
                'signal': 'EARNINGS_GAP',
                'confidence': 50,
                'message': 'Very close to earnings - gap risk high'
            }

        return {
            'signal': 'WATCH',
            'confidence': 40,
            'message': 'Monitor for accumulation pattern'
        }

    def get_pre_earnings_opportunities(self, min_confidence: int = 60) -> List[Dict]:
        """
        Get list of tickers with pre-earnings accumulation patterns.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            List of opportunity dicts
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Get tickers with upcoming earnings
            future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT DISTINCT ticker FROM earnings_calendar
                WHERE earnings_date <= ?
            """, (future_date,))

            tickers = [row['ticker'] for row in cursor.fetchall()]

            opportunities = []
            for ticker in tickers:
                pattern = self.detect_pre_earnings_pattern(ticker)
                if pattern and pattern.get('confidence', 0) >= min_confidence:
                    opportunities.append(pattern)

            # Sort by confidence descending
            opportunities.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            return opportunities

        finally:
            conn.close()

    def get_earnings_score(self, ticker: str) -> int:
        """
        Get scoring points for earnings timing.

        Used in bandarmology deep analysis scoring.

        Returns:
            Score contribution (0-10)
        """
        pattern = self.detect_pre_earnings_pattern(ticker)
        if not pattern:
            return 0

        signal = pattern.get('signal', '')
        confidence = pattern.get('confidence', 0)

        if signal == 'PRE_EARNINGS_ACCUM':
            if confidence >= 80:
                return 10
            elif confidence >= 70:
                return 8
            else:
                return 6

        if signal == 'PRE_EARNINGS_WATCH':
            return 4

        return 0

    def update_earnings_cache_batch(self, tickers: List[str]) -> Dict[str, bool]:
        """
        Update earnings cache for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to success status
        """
        results = {}
        for ticker in tickers:
            try:
                earnings = self.fetch_upcoming_earnings(ticker, force_refresh=True)
                results[ticker] = len(earnings) > 0
            except Exception as e:
                logger.warning(f"Error updating earnings for {ticker}: {e}")
                results[ticker] = False
        return results


# Singleton instance
_earnings_tracker: Optional[EarningsTracker] = None


def get_earnings_tracker(db_path: Optional[str] = None) -> EarningsTracker:
    """Get or create singleton instance of EarningsTracker."""
    global _earnings_tracker
    if _earnings_tracker is None:
        _earnings_tracker = EarningsTracker(db_path)
    return _earnings_tracker
