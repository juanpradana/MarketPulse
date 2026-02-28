"""
Bandar Power Calculator Module

Calculates composite "bandar attractiveness" score combining:
- Float component (smaller float = easier to control)
- Volume component (trend and activity)
- Beta component (volatility preference)
- Position component (52W range positioning)
- Institutional component (following smart money)

Score range: 0-100
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

import yfinance as yf
import config
from modules.yahoo_finance_enhanced import get_yahoo_finance_enhanced
from modules.volume_analyzer import get_volume_analyzer

logger = logging.getLogger(__name__)


class BandarPowerCalculator:
    """
    Composite scoring calculator for bandar attractiveness.

    Combines 5 components (25/20/20/20/15 weighting) into a 0-100 score
    with EXCELLENT/GOOD/MODERATE/POOR ratings.
    """

    # Weightings for components (must sum to 100)
    WEIGHT_FLOAT = 0.25
    WEIGHT_VOLUME = 0.20
    WEIGHT_BETA = 0.20
    WEIGHT_POSITION = 0.20
    WEIGHT_INSTITUTIONAL = 0.15

    # Score thresholds for ratings
    RATING_EXCELLENT = 80
    RATING_GOOD = 65
    RATING_MODERATE = 50

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")
        self.yf_enhanced = get_yahoo_finance_enhanced(db_path)
        self.volume_analyzer = get_volume_analyzer(db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def calculate_score(self, ticker: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Calculate composite bandar power score for a ticker.

        Args:
            ticker: Stock ticker symbol
            force_refresh: Force recalculation even if cache valid

        Returns:
            Dict with score breakdown or None if calculation fails
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_score(ticker)
            if cached:
                return cached

        try:
            # Fetch all required data
            price_stats = self.yf_enhanced.fetch_price_stats(ticker)
            float_data = self.yf_enhanced.fetch_float_data(ticker)
            volume_metrics = self.volume_analyzer.calculate_volume_metrics(ticker)
            institutional_flow = self._get_institutional_flow(ticker)

            # Calculate component scores
            float_component = self._calculate_float_component(float_data, price_stats)
            volume_component = self._calculate_volume_component(volume_metrics)
            beta_component = self._calculate_beta_component(price_stats)
            position_component = self._calculate_position_component(price_stats)
            institutional_component = self._calculate_institutional_component(institutional_flow)

            # Calculate weighted total
            total_score = int(
                float_component * self.WEIGHT_FLOAT +
                volume_component * self.WEIGHT_VOLUME +
                beta_component * self.WEIGHT_BETA +
                position_component * self.WEIGHT_POSITION +
                institutional_component * self.WEIGHT_INSTITUTIONAL
            )

            # Ensure 0-100 range
            total_score = max(0, min(100, total_score))

            rating = self._get_rating(total_score)

            result = {
                'ticker': ticker,
                'score': total_score,
                'rating': rating,
                'components': {
                    'float': float_component,
                    'volume': volume_component,
                    'beta': beta_component,
                    'position': position_component,
                    'institutional': institutional_component
                },
                'metadata': {
                    'market_cap': price_stats.get('market_cap') if price_stats else None,
                    'float_shares': float_data.get('float_shares') if float_data else None,
                    'beta': price_stats.get('beta') if price_stats else None,
                    'position_52w_pct': price_stats.get('position_pct') if price_stats else None,
                    'foreign_flow_trend': institutional_flow.get('trend') if institutional_flow else None,
                    'volume_ratio': volume_metrics.get('volume_ratio') if volume_metrics else None
                },
                'calculated_at': datetime.now().isoformat()
            }

            # Cache result
            self._cache_score(result)

            return result

        except Exception as e:
            logger.error(f"Error calculating bandar power score for {ticker}: {e}")
            return None

    def _calculate_float_component(
        self,
        float_data: Optional[Dict],
        price_stats: Optional[Dict]
    ) -> int:
        """
        Calculate float component score (0-100).

        Smaller float = easier for bandar to control = higher score.
        """
        # Get market cap
        market_cap = price_stats.get('market_cap') if price_stats else None
        float_shares = float_data.get('float_shares') if float_data else None

        # If we have float shares, use that directly
        if float_shares:
            # Estimate float value
            current_price = price_stats.get('current_price') if price_stats else None
            if current_price:
                float_value = float_shares * current_price
                # Score based on float value (smaller = better for bandar)
                if float_value < 1_000_000_000_000:  # < 1T IDR
                    return 100
                elif float_value < 5_000_000_000_000:  # < 5T IDR
                    return 75
                elif float_value < 10_000_000_000_000:  # < 10T IDR
                    return 50
                else:
                    return 25

        # Fallback to market cap
        if market_cap:
            if market_cap < 1_000_000_000_000:  # < 1T IDR
                return 100
            elif market_cap < 5_000_000_000_000:  # < 5T IDR
                return 75
            elif market_cap < 10_000_000_000_000:  # < 10T IDR
                return 50
            elif market_cap < 50_000_000_000_000:  # < 50T IDR
                return 25
            else:
                return 10

        # Default if no data
        return 50

    def _calculate_volume_component(self, volume_metrics: Optional[Dict]) -> int:
        """
        Calculate volume component score (0-100).

        Prefer increasing volume trend and moderate activity level.
        """
        if not volume_metrics:
            return 50

        volume_ratio = volume_metrics.get('volume_ratio', 1.0) or 1.0
        signal = volume_metrics.get('signal', 'NORMAL')

        # High volume ratio with accumulation = good
        if signal == 'ACCUMULATION':
            if volume_ratio >= 3.0:
                return 100
            elif volume_ratio >= 2.0:
                return 85
            else:
                return 70

        # Distribution = bad
        if signal == 'DISTRIBUTION':
            return 20

        # Normal volume - prefer moderate uptrend
        if volume_ratio >= 1.5:
            return 65
        elif volume_ratio >= 1.0:
            return 50
        else:
            return 35  # Declining volume

    def _calculate_beta_component(self, price_stats: Optional[Dict]) -> int:
        """
        Calculate beta component score (0-100).

        Bandar prefer higher beta for momentum plays.
        """
        if not price_stats:
            return 50

        beta = price_stats.get('beta')
        if beta is None:
            return 50

        if beta > 2.0:
            return 100
        elif beta > 1.5:
            return 85
        elif beta > 1.2:
            return 70
        elif beta > 1.0:
            return 60
        elif beta > 0.8:
            return 45
        else:
            return 30  # Low beta = less attractive for momentum

    def _calculate_position_component(self, price_stats: Optional[Dict]) -> int:
        """
        Calculate position component score (0-100).

        Prefer middle of 52W range (not too hot, not too cold).
        Sweet spot: 30-60% of 52W range.
        """
        if not price_stats:
            return 50

        position_pct = price_stats.get('position_pct')
        if position_pct is None:
            return 50

        # Sweet spot: 30-60% of 52W range
        if 0.30 <= position_pct <= 0.60:
            return 100
        # Good zone: 20-30% or 60-80%
        elif 0.20 <= position_pct < 0.30 or 0.60 < position_pct <= 0.80:
            return 75
        # Early accumulation or near top
        elif 0.10 <= position_pct < 0.20:
            return 60
        elif 0.80 < position_pct <= 0.90:
            return 50
        # Extreme ends
        elif position_pct < 0.10:
            return 40  # Near 52W low, might be value trap
        else:
            return 30  # Near 52W high, limited upside

    def _calculate_institutional_component(self, institutional_flow: Optional[Dict]) -> int:
        """
        Calculate institutional component score (0-100).

        Score based on foreign/institutional flow trend.
        """
        if not institutional_flow:
            return 50

        trend = institutional_flow.get('trend', 'NEUTRAL')

        if trend == 'ACCUMULATING':
            return 100
        elif trend == 'BUYING':
            return 85
        elif trend == 'NEUTRAL':
            return 50
        elif trend == 'SELLING':
            return 35
        elif trend == 'DISTRIBUTING':
            return 20

        return 50

    def _get_institutional_flow(self, ticker: str) -> Dict:
        """Get institutional/foreign flow trend from database."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Try to get from bandarmology_txn_chart
            cursor.execute("""
                SELECT foreign_trend, institution_trend, mm_trend,
                       cum_foreign, cum_foreign_week_ago
                FROM bandarmology_txn_chart
                WHERE ticker = ?
                ORDER BY date_end DESC
                LIMIT 1
            """, (ticker,))

            row = cursor.fetchone()
            if row:
                foreign_trend = row['foreign_trend'] or 'NEUTRAL'
                institution_trend = row['institution_trend'] or 'NEUTRAL'
                mm_trend = row['mm_trend'] or 'NEUTRAL'

                # Calculate trend from data if not set
                if foreign_trend == 'NEUTRAL' and row['cum_foreign'] and row['cum_foreign_week_ago']:
                    change = row['cum_foreign'] - row['cum_foreign_week_ago']
                    if change > 10:
                        foreign_trend = 'ACCUMULATING'
                    elif change > 0:
                        foreign_trend = 'BUYING'
                    elif change < -10:
                        foreign_trend = 'DISTRIBUTING'
                    elif change < 0:
                        foreign_trend = 'SELLING'

                # Combine trends
                trends = [foreign_trend, institution_trend, mm_trend]
                accumulating = trends.count('ACCUMULATING') + trends.count('BUYING')
                distributing = trends.count('DISTRIBUTING') + trends.count('SELLING')

                if accumulating >= 2:
                    combined_trend = 'ACCUMULATING'
                elif distributing >= 2:
                    combined_trend = 'DISTRIBUTING'
                elif accumulating > distributing:
                    combined_trend = 'BUYING'
                elif distributing > accumulating:
                    combined_trend = 'SELLING'
                else:
                    combined_trend = 'NEUTRAL'

                return {
                    'trend': combined_trend,
                    'foreign_trend': foreign_trend,
                    'institution_trend': institution_trend,
                    'mm_trend': mm_trend
                }

            return {'trend': 'NEUTRAL'}

        except Exception as e:
            logger.warning(f"Error getting institutional flow for {ticker}: {e}")
            return {'trend': 'NEUTRAL'}
        finally:
            conn.close()

    def _get_rating(self, score: int) -> str:
        """Convert score to rating."""
        if score >= self.RATING_EXCELLENT:
            return 'EXCELLENT'
        elif score >= self.RATING_GOOD:
            return 'GOOD'
        elif score >= self.RATING_MODERATE:
            return 'MODERATE'
        else:
            return 'POOR'

    def _get_cached_score(self, ticker: str) -> Optional[Dict]:
        """Get cached score if still valid (1 day)."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(days=1)).isoformat()

            cursor.execute("""
                SELECT ticker, score, rating, float_component, volume_component,
                       beta_component, position_component, institutional_component, calculated_at
                FROM bandar_power_scores
                WHERE ticker = ? AND calculated_at > ?
            """, (ticker, cutoff))

            row = cursor.fetchone()
            if row:
                return {
                    'ticker': row['ticker'],
                    'score': row['score'],
                    'rating': row['rating'],
                    'components': {
                        'float': row['float_component'],
                        'volume': row['volume_component'],
                        'beta': row['beta_component'],
                        'position': row['position_component'],
                        'institutional': row['institutional_component']
                    },
                    'calculated_at': row['calculated_at']
                }
            return None
        finally:
            conn.close()

    def _cache_score(self, result: Dict):
        """Cache score to database."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            components = result['components']

            cursor.execute("""
                INSERT OR REPLACE INTO bandar_power_scores
                (ticker, score, rating, float_component, volume_component,
                 beta_component, position_component, institutional_component, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result['ticker'],
                result['score'],
                result['rating'],
                components['float'],
                components['volume'],
                components['beta'],
                components['position'],
                components['institutional'],
                result['calculated_at']
            ))
            conn.commit()
        finally:
            conn.close()

    def get_top_scores(self, limit: int = 50, min_rating: Optional[str] = None) -> List[Dict]:
        """
        Get top rated stocks by bandar power score.

        Args:
            limit: Maximum number of results
            min_rating: Minimum rating filter ('EXCELLENT', 'GOOD', etc.)

        Returns:
            List of score results
        """
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            query = """
                SELECT ticker, score, rating, calculated_at
                FROM bandar_power_scores
                WHERE 1=1
            """
            params = []

            if min_rating:
                rating_scores = {'POOR': 0, 'MODERATE': 50, 'GOOD': 65, 'EXCELLENT': 80}
                min_score = rating_scores.get(min_rating, 0)
                query += " AND score >= ?"
                params.append(min_score)

            query += " ORDER BY score DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting top scores: {e}")
            return []
        finally:
            conn.close()

    def batch_calculate(self, tickers: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Calculate scores for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to score result
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.calculate_score(ticker)
        return results


# Singleton instance
_power_calculator: Optional[BandarPowerCalculator] = None


def get_bandar_power_calculator(db_path: Optional[str] = None) -> BandarPowerCalculator:
    """Get or create singleton instance of BandarPowerCalculator."""
    global _power_calculator
    if _power_calculator is None:
        _power_calculator = BandarPowerCalculator(db_path)
    return _power_calculator
