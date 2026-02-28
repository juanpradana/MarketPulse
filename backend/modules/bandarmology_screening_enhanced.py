"""
Bandarmology Screening Enhanced Module

Provides batch fetching of Yahoo Finance data for screening results.
Integrates float analysis, power scores, volume metrics, and earnings data.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import config

logger = logging.getLogger(__name__)


class BandarmologyScreeningEnhanced:
    """
    Enhanced screening data provider with Yahoo Finance integration.

    Provides batch fetching capabilities for efficient screening table display
    of Yahoo Finance metrics including float control, power scores,
    volume anomalies, and earnings timing.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def enrich_screening_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch and combine Yahoo Finance data for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to Yahoo Finance screening data
        """
        if not tickers:
            return {}

        # Batch fetch all data types
        float_data = self._batch_get_float_data(tickers)
        power_scores = self._batch_get_power_scores(tickers)
        volume_metrics = self._batch_get_volume_metrics(tickers)
        earnings_data = self._batch_get_earnings(tickers)

        # Combine into unified structure
        results = {}
        for ticker in tickers:
            results[ticker] = self._combine_data(
                ticker,
                float_data.get(ticker),
                power_scores.get(ticker),
                volume_metrics.get(ticker),
                earnings_data.get(ticker)
            )

        return results

    def _combine_data(
        self,
        ticker: str,
        float_data: Optional[Dict],
        power_score: Optional[Dict],
        volume_metrics: Optional[Dict],
        earnings_data: Optional[Dict]
    ) -> Dict[str, Any]:
        """Combine all data sources into unified screening data structure."""
        result = {
            'ticker': ticker,
            'float_control_pct': None,
            'float_level': None,
            'power_score': None,
            'power_rating': None,
            'volume_ratio': None,
            'volume_signal': None,
            'days_to_earnings': None,
            'earnings_signal': None
        }

        # Float data
        if float_data:
            result['float_control_pct'] = float_data.get('bandar_float_pct')
            result['float_level'] = float_data.get('control_level')

        # Power score
        if power_score:
            result['power_score'] = power_score.get('score')
            result['power_rating'] = power_score.get('rating')

        # Volume metrics
        if volume_metrics:
            result['volume_ratio'] = volume_metrics.get('volume_ratio')
            result['volume_signal'] = volume_metrics.get('signal')

        # Earnings data
        if earnings_data:
            result['days_to_earnings'] = earnings_data.get('days_until')
            result['earnings_signal'] = earnings_data.get('signal')

        return result

    def _batch_get_float_data(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Batch fetch float data from cache/db for multiple tickers.

        Returns:
            Dict mapping ticker to float control data
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            results = {}

            # Get from bandarmology_deep_cache (most reliable source)
            placeholders = ','.join(['?' for _ in tickers])
            cursor.execute(f"""
                SELECT ticker, bandar_float_pct, float_control_level
                FROM bandarmology_deep_cache
                WHERE ticker IN ({placeholders})
                AND bandar_float_pct IS NOT NULL
                AND bandar_float_pct > 0
                ORDER BY analysis_date DESC
            """, tickers)

            seen = set()
            for row in cursor.fetchall():
                ticker = row['ticker']
                if ticker not in seen:
                    results[ticker] = {
                        'bandar_float_pct': row['bandar_float_pct'],
                        'control_level': row['float_control_level']
                    }
                    seen.add(ticker)

            # Fallback to stock_float_data for remaining tickers
            remaining = [t for t in tickers if t not in results]
            if remaining:
                cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                placeholders = ','.join(['?' for _ in remaining])
                cursor.execute(f"""
                    SELECT ticker, float_shares, float_ratio, cached_at
                    FROM stock_float_data
                    WHERE ticker IN ({placeholders})
                    AND cached_at > ?
                """, remaining + [cutoff])

                for row in cursor.fetchall():
                    ticker = row['ticker']
                    if ticker not in results:
                        results[ticker] = {
                            'float_shares': row['float_shares'],
                            'float_ratio': row['float_ratio'],
                            'source': 'float_data_table'
                        }

            return results
        finally:
            conn.close()

    def _batch_get_power_scores(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Batch fetch power scores from cache for multiple tickers.

        Returns:
            Dict mapping ticker to power score data
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            results = {}

            # Get from bandarmology_deep_cache
            placeholders = ','.join(['?' for _ in tickers])
            cursor.execute(f"""
                SELECT ticker, bandar_power_score, bandar_power_rating
                FROM bandarmology_deep_cache
                WHERE ticker IN ({placeholders})
                AND bandar_power_score IS NOT NULL
                AND bandar_power_score > 0
                ORDER BY analysis_date DESC
            """, tickers)

            seen = set()
            for row in cursor.fetchall():
                ticker = row['ticker']
                if ticker not in seen:
                    results[ticker] = {
                        'score': row['bandar_power_score'],
                        'rating': row['bandar_power_rating']
                    }
                    seen.add(ticker)

            # Fallback to bandar_power_scores table
            remaining = [t for t in tickers if t not in results]
            if remaining:
                cutoff = (datetime.now() - timedelta(days=1)).isoformat()
                placeholders = ','.join(['?' for _ in remaining])
                cursor.execute(f"""
                    SELECT ticker, score, rating
                    FROM bandar_power_scores
                    WHERE ticker IN ({placeholders})
                    AND calculated_at > ?
                """, remaining + [cutoff])

                for row in cursor.fetchall():
                    ticker = row['ticker']
                    if ticker not in results:
                        results[ticker] = {
                            'score': row['score'],
                            'rating': row['rating']
                        }

            return results
        finally:
            conn.close()

    def _batch_get_volume_metrics(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Batch fetch volume metrics for multiple tickers.

        Returns:
            Dict mapping ticker to volume metrics
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            results = {}

            # Get from volume_daily_records
            placeholders = ','.join(['?' for _ in tickers])
            cutoff = (datetime.now() - timedelta(days=1)).isoformat()

            cursor.execute(f"""
                SELECT ticker, volume_ratio, volume_signal, trade_date
                FROM volume_daily_records
                WHERE ticker IN ({placeholders})
                AND fetched_at > ?
                ORDER BY trade_date DESC
            """, tickers + [cutoff])

            seen = set()
            for row in cursor.fetchall():
                ticker = row['ticker']
                if ticker not in seen:
                    results[ticker] = {
                        'volume_ratio': row['volume_ratio'],
                        'signal': row['volume_signal']
                    }
                    seen.add(ticker)

            return results
        finally:
            conn.close()

    def _batch_get_earnings(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Batch fetch earnings data for multiple tickers.

        Returns:
            Dict mapping ticker to earnings data
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            results = {}

            today = datetime.now().strftime('%Y-%m-%d')
            future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

            placeholders = ','.join(['?' for _ in tickers])
            cursor.execute(f"""
                SELECT ticker, earnings_date
                FROM earnings_calendar
                WHERE ticker IN ({placeholders})
                AND earnings_date >= ?
                AND earnings_date <= ?
                ORDER BY earnings_date
            """, tickers + [today, future_date])

            for row in cursor.fetchall():
                ticker = row['ticker']
                earnings_date = datetime.strptime(row['earnings_date'], '%Y-%m-%d')
                days_until = (earnings_date - datetime.now()).days

                # Determine signal based on timing
                signal = self._classify_earnings_signal(days_until)

                results[ticker] = {
                    'days_until': days_until,
                    'earnings_date': row['earnings_date'],
                    'signal': signal
                }

            return results
        finally:
            conn.close()

    def _classify_earnings_signal(self, days_until: int) -> str:
        """Classify earnings signal based on days until earnings."""
        if days_until < 7:
            return 'PRE_EARNINGS_URGENT'
        elif days_until < 14:
            return 'PRE_EARNINGS_ACCUM'
        else:
            return 'WATCH'

    def get_screening_with_yahoo_finance(
        self,
        screening_results: List[Dict],
        include_yahoo: bool = True
    ) -> List[Dict]:
        """
        Enrich screening results with Yahoo Finance data.

        Args:
            screening_results: List of screening result dicts
            include_yahoo: Whether to include Yahoo Finance data

        Returns:
            Enriched screening results
        """
        if not include_yahoo or not screening_results:
            return screening_results

        # Extract tickers
        tickers = [r.get('symbol') for r in screening_results if r.get('symbol')]

        # Fetch Yahoo Finance data
        yahoo_data = self.enrich_screening_data(tickers)

        # Merge into results
        for result in screening_results:
            ticker = result.get('symbol')
            if ticker and ticker in yahoo_data:
                result['yahoo_finance'] = yahoo_data[ticker]
            else:
                # Add empty structure to maintain consistent schema
                result['yahoo_finance'] = {
                    'ticker': ticker,
                    'float_control_pct': None,
                    'float_level': None,
                    'power_score': None,
                    'power_rating': None,
                    'volume_ratio': None,
                    'volume_signal': None,
                    'days_to_earnings': None,
                    'earnings_signal': None
                }

        return screening_results


# Singleton instance
_screening_enhanced: Optional[BandarmologyScreeningEnhanced] = None


def get_screening_enhanced(db_path: Optional[str] = None) -> BandarmologyScreeningEnhanced:
    """Get or create singleton instance of BandarmologyScreeningEnhanced."""
    global _screening_enhanced
    if _screening_enhanced is None:
        _screening_enhanced = BandarmologyScreeningEnhanced(db_path)
    return _screening_enhanced
