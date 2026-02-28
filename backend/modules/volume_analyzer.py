"""
Volume Analyzer Module

Analyzes volume patterns for anomaly detection and signal classification.
Provides volume-based confirmation signals for bandar detection.
"""
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

import config
from modules.yahoo_finance_enhanced import YahooFinanceEnhanced, get_yahoo_finance_enhanced

logger = logging.getLogger(__name__)


class VolumeAnalyzer:
    """
    Volume analysis engine for detecting anomalies and classifying signals.

    Provides:
    - Volume ratio calculations (today vs averages)
    - Volume anomaly detection
    - Volume signal classification (ACCUMULATION/DISTRIBUTION/NORMAL)
    - Volume trend analysis
    """

    # Thresholds for volume anomaly detection
    VOLUME_SPIKE_THRESHOLD = 2.0  # 2x average = spike
    VOLUME_STRONG_SPIKE_THRESHOLD = 3.0  # 3x average = strong spike

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")
        self.yf_enhanced = get_yahoo_finance_enhanced(db_path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def calculate_volume_metrics(self, ticker: str) -> Optional[Dict]:
        """
        Calculate comprehensive volume metrics for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with volume metrics or None if data unavailable
        """
        # First try to get from Yahoo Finance
        yf_metrics = self.yf_enhanced.fetch_volume_metrics(ticker)

        if yf_metrics:
            return self._enrich_volume_metrics(ticker, yf_metrics)

        # Fallback: calculate from local database
        return self._calculate_from_local_data(ticker)

    def _enrich_volume_metrics(self, ticker: str, yf_metrics: Dict) -> Dict:
        """Enrich Yahoo Finance volume metrics with additional analysis."""
        volume_ratio = yf_metrics.get('volume_ratio', 0) or 0
        current_volume = yf_metrics.get('current_volume', 0) or 0
        avg_10d = yf_metrics.get('avg_volume_10d', 0) or 0

        # Determine if this is a spike
        is_spike = volume_ratio >= self.VOLUME_SPIKE_THRESHOLD
        is_strong_spike = volume_ratio >= self.VOLUME_STRONG_SPIKE_THRESHOLD

        # Get price change for context
        price_change = self._get_recent_price_change(ticker)

        # Classify signal (need price change for full classification)
        signal = 'NORMAL'
        confidence = 50

        if is_spike and price_change is not None:
            signal, confidence = self._classify_volume_signal(
                volume_ratio, price_change, is_strong_spike
            )

        return {
            'ticker': ticker,
            'current_volume': current_volume,
            'avg_volume_10d': avg_10d,
            'avg_volume_3m': yf_metrics.get('avg_volume_3m'),
            'volume_ratio': volume_ratio,
            'is_spike': is_spike,
            'is_strong_spike': is_strong_spike,
            'price_change': price_change,
            'signal': signal,
            'confidence': confidence,
            'signal_description': self._get_signal_description(signal, volume_ratio),
            'calculated_at': datetime.now().isoformat()
        }

    def _calculate_from_local_data(self, ticker: str) -> Optional[Dict]:
        """Calculate volume metrics from local database when Yahoo data unavailable."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Get last 10 days of volume data
            cursor.execute("""
                SELECT trade_date, volume, close_price
                FROM volume_daily_records
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT 11
            """, (ticker,))

            rows = cursor.fetchall()
            if len(rows) < 5:  # Need at least 5 days of data
                return None

            volumes = [row['volume'] for row in rows]
            prices = [row['close_price'] for row in rows if row['close_price']]

            current_volume = volumes[0]
            avg_10d = sum(volumes[1:11]) / len(volumes[1:11]) if len(volumes) > 1 else current_volume

            volume_ratio = current_volume / avg_10d if avg_10d > 0 else 1.0

            # Calculate price change
            price_change = None
            if len(prices) >= 2:
                price_change = ((prices[0] - prices[1]) / prices[1]) * 100

            is_spike = volume_ratio >= self.VOLUME_SPIKE_THRESHOLD
            is_strong_spike = volume_ratio >= self.VOLUME_STRONG_SPIKE_THRESHOLD

            signal = 'NORMAL'
            confidence = 50

            if is_spike and price_change is not None:
                signal, confidence = self._classify_volume_signal(
                    volume_ratio, price_change, is_strong_spike
                )

            return {
                'ticker': ticker,
                'current_volume': current_volume,
                'avg_volume_10d': avg_10d,
                'avg_volume_3m': None,
                'volume_ratio': volume_ratio,
                'is_spike': is_spike,
                'is_strong_spike': is_strong_spike,
                'price_change': price_change,
                'signal': signal,
                'confidence': confidence,
                'signal_description': self._get_signal_description(signal, volume_ratio),
                'calculated_at': datetime.now().isoformat(),
                'source': 'local'
            }

        except Exception as e:
            logger.error(f"Error calculating local volume metrics for {ticker}: {e}")
            return None
        finally:
            conn.close()

    def _get_recent_price_change(self, ticker: str) -> Optional[float]:
        """Get recent price change percentage."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()

            # Try NeoBDM records first
            cursor.execute("""
                SELECT pct_1d FROM neobdm_records
                WHERE symbol = ? AND scraped_at >= date('now', '-1 day')
                ORDER BY scraped_at DESC
                LIMIT 1
            """, (ticker,))

            row = cursor.fetchone()
            if row and row['pct_1d']:
                try:
                    return float(row['pct_1d'])
                except (ValueError, TypeError):
                    pass

            # Fallback to volume records
            cursor.execute("""
                SELECT close_price
                FROM volume_daily_records
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT 2
            """, (ticker,))

            rows = cursor.fetchall()
            if len(rows) >= 2:
                current = rows[0]['close_price']
                previous = rows[1]['close_price']
                if current and previous:
                    return ((current - previous) / previous) * 100

            return None

        except Exception as e:
            logger.warning(f"Error getting price change for {ticker}: {e}")
            return None
        finally:
            conn.close()

    def detect_volume_anomaly(self, ticker: str, threshold: float = 2.0) -> Optional[Dict]:
        """
        Detect if volume is significantly above average.

        Args:
            ticker: Stock ticker symbol
            threshold: Multiplier threshold for anomaly detection

        Returns:
            Dict with anomaly detection results
        """
        metrics = self.calculate_volume_metrics(ticker)
        if not metrics:
            return None

        volume_ratio = metrics.get('volume_ratio', 0) or 0
        is_anomaly = volume_ratio >= threshold

        return {
            'ticker': ticker,
            'is_anomaly': is_anomaly,
            'volume_ratio': volume_ratio,
            'threshold': threshold,
            'severity': self._get_anomaly_severity(volume_ratio),
            'metrics': metrics
        }

    def _get_anomaly_severity(self, volume_ratio: float) -> str:
        """Get severity level for volume anomaly."""
        if volume_ratio >= 5.0:
            return 'EXTREME'
        elif volume_ratio >= 3.0:
            return 'HIGH'
        elif volume_ratio >= 2.0:
            return 'MODERATE'
        elif volume_ratio >= 1.5:
            return 'MILD'
        else:
            return 'NONE'

    def classify_volume_signal(
        self,
        ticker: str,
        price_change: Optional[float] = None
    ) -> Tuple[str, int]:
        """
        Classify volume pattern as ACCUMULATION, DISTRIBUTION, or NORMAL.

        Args:
            ticker: Stock ticker symbol
            price_change: Optional price change percentage

        Returns:
            Tuple of (signal, confidence)
        """
        metrics = self.calculate_volume_metrics(ticker)
        if not metrics:
            return 'NORMAL', 0

        volume_ratio = metrics.get('volume_ratio', 0) or 0

        # Use provided price change or get from metrics
        if price_change is None:
            price_change = metrics.get('price_change', 0) or 0

        return self._classify_volume_signal(volume_ratio, price_change, metrics.get('is_strong_spike', False))

    def _classify_volume_signal(
        self,
        volume_ratio: float,
        price_change: float,
        is_strong_spike: bool
    ) -> Tuple[str, int]:
        """
        Internal classification logic.

        Returns:
            Tuple of (signal, confidence)
        """
        # Strong accumulation: Volume spike + Price up
        if volume_ratio >= self.VOLUME_STRONG_SPIKE_THRESHOLD and price_change > 0:
            return 'ACCUMULATION', 90 if is_strong_spike else 75

        # Moderate accumulation: Volume spike + Price up (but smaller spike)
        if volume_ratio >= self.VOLUME_SPIKE_THRESHOLD and price_change > 0:
            return 'ACCUMULATION', 70

        # Distribution: Volume spike + Price down
        if volume_ratio >= self.VOLUME_SPIKE_THRESHOLD and price_change < 0:
            return 'DISTRIBUTION', 85 if is_strong_spike else 70

        # Light accumulation: Moderate volume increase + Price up
        if volume_ratio >= 1.5 and price_change > 2:
            return 'ACCUMULATION', 55

        # Normal volume patterns
        return 'NORMAL', 50

    def _get_signal_description(self, signal: str, volume_ratio: float) -> str:
        """Get human-readable description for signal."""
        descriptions = {
            'ACCUMULATION': f'Volume {volume_ratio:.1f}x avg with positive price action - potential accumulation',
            'DISTRIBUTION': f'Volume {volume_ratio:.1f}x avg with negative price action - potential distribution',
            'NORMAL': f'Normal volume activity ({volume_ratio:.1f}x avg)'
        }
        return descriptions.get(signal, 'Unknown signal')

    def get_volume_score(self, ticker: str) -> int:
        """
        Get scoring points for volume pattern.

        Used in bandarmology deep analysis scoring.

        Returns:
            Score contribution (0-10 for accumulation, -5 to 0 for distribution)
        """
        metrics = self.calculate_volume_metrics(ticker)
        if not metrics:
            return 0

        signal = metrics.get('signal', 'NORMAL')
        volume_ratio = metrics.get('volume_ratio', 0) or 0

        if signal == 'ACCUMULATION':
            if volume_ratio >= 3.0:
                return 10  # Strong accumulation
            elif volume_ratio >= 2.0:
                return 7   # Moderate accumulation
            else:
                return 5   # Light accumulation

        elif signal == 'DISTRIBUTION':
            if volume_ratio >= 3.0:
                return -5  # Strong distribution warning
            else:
                return -3  # Moderate distribution warning

        return 0  # Normal volume

    def update_volume_daily_record(self, ticker: str) -> bool:
        """
        Update volume_daily_records with latest metrics.

        Args:
            ticker: Stock ticker symbol

        Returns:
            True if successful
        """
        metrics = self.calculate_volume_metrics(ticker)
        if not metrics:
            return False

        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')

            cursor.execute("""
                UPDATE volume_daily_records
                SET avg_volume_10d = ?,
                    avg_volume_3m = ?,
                    volume_ratio = ?,
                    volume_signal = ?,
                    fetched_at = ?
                WHERE ticker = ? AND trade_date = ?
            """, (
                metrics.get('avg_volume_10d'),
                metrics.get('avg_volume_3m'),
                metrics.get('volume_ratio'),
                metrics.get('signal'),
                datetime.now().isoformat(),
                ticker,
                today
            ))

            # If no rows updated, insert new record
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO volume_daily_records
                    (ticker, trade_date, volume, avg_volume_10d, avg_volume_3m, volume_ratio, volume_signal, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    today,
                    metrics.get('current_volume'),
                    metrics.get('avg_volume_10d'),
                    metrics.get('avg_volume_3m'),
                    metrics.get('volume_ratio'),
                    metrics.get('signal'),
                    datetime.now().isoformat()
                ))

            conn.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating volume record for {ticker}: {e}")
            return False
        finally:
            conn.close()

    def batch_update_volume_metrics(self, tickers: List[str]) -> Dict[str, bool]:
        """
        Update volume metrics for multiple tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to success status
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.update_volume_daily_record(ticker)
        return results


# Singleton instance
_volume_analyzer: Optional[VolumeAnalyzer] = None


def get_volume_analyzer(db_path: Optional[str] = None) -> VolumeAnalyzer:
    """Get or create singleton instance of VolumeAnalyzer."""
    global _volume_analyzer
    if _volume_analyzer is None:
        _volume_analyzer = VolumeAnalyzer(db_path)
    return _volume_analyzer
