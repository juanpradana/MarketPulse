"""
Bandarmology Analyzer Module

Analyzes stocks using multi-method confluence from NeoBDM market summary data
(Market Maker, Non-Retail, Foreign Flow) combined with broker summary data
to produce a bandarmology screening score and swing/intraday classification.
"""
import json
import os
import re
import logging
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import numpy as np

import config

logger = logging.getLogger(__name__)


def _parse_numeric(val) -> float:
    """Parse a numeric value from various string formats."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ('', 'nan', 'none', '-', 'x'):
        return 0.0
    # Remove commas, pipes, tooltip parts
    s = s.split('|')[0].strip()
    s = s.replace(',', '')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _safe_float(val) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _is_flag_set(val) -> bool:
    """Check if a flag column (pinky, crossing, unusual, likuid) is set."""
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ('v', 'true', '1', 'yes', '✓', '✔')


def _load_broker_classifications() -> Dict[str, Dict]:
    """Load broker classifications from brokers_idx.json."""
    json_path = os.path.join(config.DATA_DIR, "brokers_idx.json")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        brokers = {}
        for b in data.get('brokers', []):
            brokers[b['code']] = {
                'name': b.get('name', ''),
                'categories': b.get('category', [])
            }
        return brokers
    except Exception as e:
        logger.warning(f"Could not load broker classifications: {e}")
        return {}


class BandarmologyAnalyzer:
    """
    Bandarmology screening engine.

    Combines market summary data across all 3 methods (MM, NR, Foreign)
    with broker summary data to score and classify stocks.
    """

    # Sector mapping for stocks (can be populated from external source)
    # Format: { 'TICKER': 'SECTOR_NAME' }
    _sector_mapping: Dict[str, str] = {}

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")
        self.broker_classes = _load_broker_classifications()
        self._market_averages_cache: Optional[Dict] = None
        self._sector_averages_cache: Optional[Dict] = None

    @classmethod
    def load_sector_mapping(cls, mapping: Dict[str, str]):
        """Load sector mapping from external source."""
        cls._sector_mapping.update(mapping)
        logger.info(f"Loaded sector mapping for {len(mapping)} stocks")

    @classmethod
    def clear_sector_mapping(cls):
        """Clear all sector mappings."""
        cls._sector_mapping.clear()
        logger.info("Cleared sector mapping")

    def clear_caches(self):
        """Clear internal caches (call when data changes)."""
        self._market_averages_cache = None
        self._sector_averages_cache = None

    def _get_conn(self):
        import sqlite3
        return sqlite3.connect(self.db_path)

    def analyze(self, target_date: Optional[str] = None) -> List[Dict]:
        """
        Run full bandarmology analysis.

        Args:
            target_date: Specific date to analyze (YYYY-MM-DD). None = latest.

        Returns:
            List of scored stock dicts, sorted by score descending.
        """
        # Clear caches for fresh analysis
        self.clear_caches()

        # 1. Get market summary data for all methods
        daily_data = self._get_market_summary_data('d', target_date)
        cumulative_data = self._get_market_summary_data('c', target_date)

        if not daily_data and not cumulative_data:
            return []

        # 2. Build per-symbol consolidated view
        symbols = set()
        for method_data in daily_data.values():
            symbols.update(method_data.keys())
        for method_data in cumulative_data.values():
            symbols.update(method_data.keys())

        # 3. Get broker summary stats for the date
        actual_date = self._resolve_date(target_date)
        broker_stats = self._get_broker_summary_stats(actual_date)

        # 4. Score each symbol
        results = []
        for symbol in sorted(symbols):
            if not symbol or len(symbol) > 6:
                continue
            try:
                score_result = self._score_symbol(
                    symbol, daily_data, cumulative_data, broker_stats
                )
                if score_result:
                    results.append(score_result)
            except Exception as e:
                logger.warning(f"Error scoring {symbol}: {e}")

        # 5. Sort by total score descending
        results.sort(key=lambda x: x['total_score'], reverse=True)

        return results

    def _resolve_date(self, target_date: Optional[str] = None) -> Optional[str]:
        """Resolve the actual date from the database."""
        conn = self._get_conn()
        try:
            if target_date:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT scraped_at FROM neobdm_records WHERE scraped_at LIKE ? ORDER BY scraped_at DESC LIMIT 1",
                    (f"{target_date}%",)
                )
                row = cursor.fetchone()
                return row[0][:10] if row else target_date
            else:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT scraped_at FROM neobdm_records ORDER BY scraped_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                return row[0][:10] if row else None
        finally:
            conn.close()

    def _get_market_summary_data(
        self, period: str, target_date: Optional[str] = None
    ) -> Dict[str, Dict[str, Dict]]:
        """
        Get market summary data grouped by method and symbol.
        
        Returns:
            {
                'm': {'BBRI': {row_dict}, 'TLKM': {row_dict}, ...},
                'nr': {'BBRI': {row_dict}, ...},
                'f': {'BBRI': {row_dict}, ...}
            }
        """
        conn = self._get_conn()
        try:
            result = {}
            for method in ['m', 'nr', 'f']:
                if target_date:
                    query = """
                    SELECT * FROM neobdm_records
                    WHERE method = ? AND period = ? AND scraped_at LIKE ?
                    ORDER BY scraped_at DESC
                    """
                    cursor = conn.cursor()
                    cursor.execute(query, (method, period, f"{target_date}%"))
                else:
                    # Get latest scraped_at for this method+period
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT MAX(scraped_at) FROM neobdm_records WHERE method = ? AND period = ?",
                        (method, period)
                    )
                    latest = cursor.fetchone()
                    if not latest or not latest[0]:
                        result[method] = {}
                        continue
                    latest_date = latest[0]

                    query = """
                    SELECT * FROM neobdm_records
                    WHERE method = ? AND period = ? AND scraped_at = ?
                    """
                    cursor = conn.cursor()
                    cursor.execute(query, (method, period, latest_date))

                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                method_data = {}
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    symbol = (row_dict.get('symbol') or '').strip()
                    # Clean symbol
                    symbol = re.sub(r'\|?Add\s+.*?to\s+Watchlist', '', symbol, flags=re.IGNORECASE)
                    symbol = re.sub(r'\|?Remove\s+from\s+Watchlist', '', symbol, flags=re.IGNORECASE)
                    symbol = symbol.replace('★', '').replace('⭐', '').strip('| ').strip()
                    if symbol:
                        method_data[symbol] = row_dict

                result[method] = method_data

            return result
        finally:
            conn.close()

    def _get_broker_summary_stats(self, trade_date: Optional[str]) -> Dict[str, Dict]:
        """
        Get aggregated broker summary statistics per ticker for the given date.
        
        Returns:
            {
                'BBRI': {
                    'institutional_net_lot': 1500,
                    'institutional_net_val': 125.5,
                    'foreign_net_lot': 800,
                    'foreign_net_val': 60.2,
                    'retail_net_lot': -2300,
                    'top_buyer': 'YP',
                    'top_buyer_lot': 500,
                    'top_seller': 'RH',
                    'top_seller_lot': -300,
                    'total_brokers_buying': 5,
                    'total_brokers_selling': 8
                },
                ...
            }
        """
        if not trade_date:
            return {}

        conn = self._get_conn()
        try:
            query = """
            SELECT ticker, side, broker, nlot, nval, avg_price
            FROM neobdm_broker_summaries
            WHERE trade_date = ?
            ORDER BY ticker, side, nval DESC
            """
            cursor = conn.cursor()
            cursor.execute(query, (trade_date,))
            rows = cursor.fetchall()

            stats = {}
            for row in rows:
                ticker, side, broker, nlot, nval, avg_price = row
                ticker = (ticker or '').upper().strip()
                broker = (broker or '').upper().strip()
                if not ticker:
                    continue

                if ticker not in stats:
                    stats[ticker] = {
                        'institutional_net_lot': 0,
                        'institutional_net_val': 0,
                        'foreign_net_lot': 0,
                        'foreign_net_val': 0,
                        'retail_net_lot': 0,
                        'retail_net_val': 0,
                        'top_buyer': None,
                        'top_buyer_lot': 0,
                        'top_seller': None,
                        'top_seller_lot': 0,
                        'total_brokers_buying': 0,
                        'total_brokers_selling': 0,
                    }

                nlot = nlot or 0
                nval = nval or 0

                # Classify broker
                broker_info = self.broker_classes.get(broker, {})
                categories = broker_info.get('categories', [])

                if side == 'BUY':
                    stats[ticker]['total_brokers_buying'] += 1
                    if not stats[ticker]['top_buyer'] or nlot > stats[ticker]['top_buyer_lot']:
                        stats[ticker]['top_buyer'] = broker
                        stats[ticker]['top_buyer_lot'] = nlot

                    if 'foreign' in categories:
                        stats[ticker]['foreign_net_lot'] += nlot
                        stats[ticker]['foreign_net_val'] += nval
                    elif 'institutional' in categories:
                        stats[ticker]['institutional_net_lot'] += nlot
                        stats[ticker]['institutional_net_val'] += nval
                    else:
                        stats[ticker]['retail_net_lot'] += nlot
                        stats[ticker]['retail_net_val'] += nval

                elif side == 'SELL':
                    stats[ticker]['total_brokers_selling'] += 1
                    if not stats[ticker]['top_seller'] or nlot > stats[ticker]['top_seller_lot']:
                        stats[ticker]['top_seller'] = broker
                        stats[ticker]['top_seller_lot'] = nlot

                    if 'foreign' in categories:
                        stats[ticker]['foreign_net_lot'] -= nlot
                        stats[ticker]['foreign_net_val'] -= nval
                    elif 'institutional' in categories:
                        stats[ticker]['institutional_net_lot'] -= nlot
                        stats[ticker]['institutional_net_val'] -= nval
                    else:
                        stats[ticker]['retail_net_lot'] -= nlot
                        stats[ticker]['retail_net_val'] -= nval

            return stats
        finally:
            conn.close()

    # ==================== MARKET/SECTOR CONTEXT COMPARISON ====================

    def _get_stock_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a stock. Returns None if not mapped."""
        return self._sector_mapping.get(symbol.upper())

    def _calculate_market_averages(
        self, daily_data: Dict[str, Dict[str, Dict]], cumulative_data: Dict[str, Dict[str, Dict]]
    ) -> Dict:
        """
        Calculate market-wide average flows for context comparison.

        Returns:
            Dict with average flows per method:
            {
                'mm': {'avg_cum': X, 'avg_daily': Y, 'median_cum': Z},
                'nr': {...},
                'f': {...}
            }
        """
        if self._market_averages_cache:
            return self._market_averages_cache

        averages = {'mm': {}, 'nr': {}, 'f': {}}

        for method in ['m', 'nr', 'f']:
            method_key = 'mm' if method == 'm' else method
            cum_values = []
            daily_values = []

            # Get cumulative values
            method_cum = cumulative_data.get(method, {})
            for symbol, data in method_cum.items():
                d_0 = _parse_numeric(data.get('d_0'))
                c_5 = _parse_numeric(data.get('c_5'))
                if c_5 != 0:
                    cum_values.append(c_5)
                if d_0 != 0:
                    daily_values.append(d_0)

            if cum_values:
                averages[method_key]['avg_cum'] = np.mean(cum_values)
                averages[method_key]['median_cum'] = np.median(cum_values)
                averages[method_key]['std_cum'] = np.std(cum_values)
                averages[method_key]['count'] = len(cum_values)
            else:
                averages[method_key] = {
                    'avg_cum': 0, 'median_cum': 0, 'std_cum': 0, 'count': 0
                }

            if daily_values:
                averages[method_key]['avg_daily'] = np.mean(daily_values)
                averages[method_key]['median_daily'] = np.median(daily_values)

        self._market_averages_cache = averages
        return averages

    def _calculate_sector_averages(
        self, daily_data: Dict[str, Dict[str, Dict]], cumulative_data: Dict[str, Dict[str, Dict]]
    ) -> Dict:
        """
        Calculate sector-average flows for stocks with sector mapping.

        Returns:
            Dict keyed by sector name with average flows.
        """
        if self._sector_averages_cache:
            return self._sector_averages_cache

        # Group stocks by sector
        sector_data: Dict[str, Dict[str, List[float]]] = {}

        for method in ['m', 'nr', 'f']:
            method_key = 'mm' if method == 'm' else method

            method_cum = cumulative_data.get(method, {})
            for symbol, data in method_cum.items():
                sector = self._get_stock_sector(symbol)
                if not sector:
                    continue

                if sector not in sector_data:
                    sector_data[sector] = {'mm': [], 'nr': [], 'f': []}

                c_5 = _parse_numeric(data.get('c_5'))
                if c_5 != 0:
                    sector_data[sector][method_key].append(c_5)

        # Calculate averages per sector
        sector_averages = {}
        for sector, method_data in sector_data.items():
            sector_averages[sector] = {}
            for method_key, values in method_data.items():
                if values:
                    sector_averages[sector][method_key] = {
                        'avg_cum': np.mean(values),
                        'median_cum': np.median(values),
                        'count': len(values)
                    }
                else:
                    sector_averages[sector][method_key] = {
                        'avg_cum': 0, 'median_cum': 0, 'count': 0
                    }

        self._sector_averages_cache = sector_averages
        return sector_averages

    def _calculate_relative_flow_score(
        self,
        symbol: str,
        daily_data: Dict[str, Dict[str, Dict]],
        cumulative_data: Dict[str, Dict[str, Dict]]
    ) -> Tuple[float, Dict]:
        """
        Calculate relative flow score comparing stock to market and sector averages.

        Returns:
            Tuple of (multiplier, context_info)
            - multiplier: 0.8 to 1.2 adjustment factor
            - context_info: dict with comparison details
        """
        context_info = {
            'market_context': {},
            'sector_context': {},
            'relative_score': 1.0
        }

        # Get market averages
        market_avg = self._calculate_market_averages(daily_data, cumulative_data)

        # Get stock's MM cumulative flow
        mm_cum = cumulative_data.get('m', {}).get(symbol, {})
        stock_mm_flow = _parse_numeric(mm_cum.get('c_5', 0))

        if stock_mm_flow == 0:
            return 1.0, context_info

        # Market comparison
        market_mm = market_avg.get('mm', {})
        market_avg_cum = market_mm.get('avg_cum', 0)
        market_std = market_mm.get('std_cum', 1)  # Avoid division by zero

        market_z_score = 0
        if market_std > 0:
            market_z_score = (stock_mm_flow - market_avg_cum) / market_std

        context_info['market_context'] = {
            'stock_flow': round(stock_mm_flow, 2),
            'market_avg': round(market_avg_cum, 2),
            'market_std': round(market_std, 2),
            'z_score': round(market_z_score, 2),
            'percentile': self._z_score_to_percentile(market_z_score)
        }

        # Sector comparison (if sector data available)
        sector = self._get_stock_sector(symbol)
        sector_z_score = 0

        if sector:
            sector_avg = self._calculate_sector_averages(daily_data, cumulative_data)
            sector_mm = sector_avg.get(sector, {}).get('mm', {})
            sector_avg_cum = sector_mm.get('avg_cum', 0)
            sector_count = sector_mm.get('count', 0)

            if sector_count >= 3 and sector_avg_cum != 0:  # Need at least 3 stocks for meaningful average
                # Simple comparison (sector std not available with small sample)
                sector_diff_pct = (stock_mm_flow - sector_avg_cum) / abs(sector_avg_cum) if sector_avg_cum != 0 else 0
                sector_z_score = sector_diff_pct * 2  # Approximate z-score

                context_info['sector_context'] = {
                    'sector': sector,
                    'stock_flow': round(stock_mm_flow, 2),
                    'sector_avg': round(sector_avg_cum, 2),
                    'sector_count': sector_count,
                    'diff_pct': round(sector_diff_pct * 100, 1)
                }

        # Calculate relative score multiplier
        # Use the better of market or sector comparison
        best_z_score = max(abs(market_z_score), abs(sector_z_score)) if sector else abs(market_z_score)
        best_z_sign = np.sign(market_z_score if abs(market_z_score) >= abs(sector_z_score) else sector_z_score)

        # Convert z-score to multiplier
        # z > 1.0 (top 16%): 1.2 multiplier (20% bonus)
        # z > 0.5 (top 31%): 1.1 multiplier (10% bonus)
        # z > -0.5: 1.0 multiplier (neutral)
        # z > -1.0: 0.9 multiplier (10% penalty)
        # z < -1.0: 0.8 multiplier (20% penalty)

        if best_z_score >= 1.0 and best_z_sign > 0:
            multiplier = 1.2
        elif best_z_score >= 0.5 and best_z_sign > 0:
            multiplier = 1.1
        elif best_z_score >= 0.5 or (best_z_score >= 0 and best_z_sign >= 0):
            multiplier = 1.0
        elif best_z_score >= 1.0 and best_z_sign < 0:
            multiplier = 0.8
        else:
            multiplier = 0.9

        context_info['relative_score'] = multiplier
        context_info['z_score_used'] = round(best_z_score, 2) if sector else round(market_z_score, 2)

        return multiplier, context_info

    @staticmethod
    @staticmethod
    def _z_score_to_percentile(z_score: float) -> float:
        """Convert z-score to approximate percentile (0-100)."""
        # Approximation using error function
        try:
            percentile = 50 * (1 + math.erf(z_score / math.sqrt(2)))
            return round(percentile, 1)
        except Exception:
            return 50.0

    def _resolve_data_source_conflicts(
        self, scores_by_source: Dict[str, float]
    ) -> Tuple[float, Dict]:
        """
        Detect and resolve conflicts between data sources.

        When data sources disagree (e.g., inventory shows distribution while
        transaction chart shows accumulation), reduce confidence in the score.

        Args:
            scores_by_source: Dict mapping source name to score
                e.g., {'inventory': 15, 'transaction_chart': 25, 'broker_summary': 20}

        Returns:
            Tuple of (multiplier, signals)
            - multiplier: 0.8 to 1.0 penalty factor
            - signals: dict with conflict information
        """
        signals = {}

        if len(scores_by_source) < 2:
            return 1.0, signals

        # Calculate statistics across sources
        scores = list(scores_by_source.values())
        mean_score = np.mean(scores)
        std_score = np.std(scores)

        # Calculate coefficient of variation (CV) - normalized measure of dispersion
        cv = std_score / abs(mean_score) if mean_score != 0 else 0

        # Detect directional conflict (positive vs negative signals)
        positive_sources = [k for k, v in scores_by_source.items() if v > 5]
        negative_sources = [k for k, v in scores_by_source.items() if v < 0]

        has_directional_conflict = len(positive_sources) > 0 and len(negative_sources) > 0

        # Calculate multiplier based on conflict severity
        multiplier = 1.0

        if has_directional_conflict:
            # Severe conflict: some sources say buy, others say sell
            multiplier = 0.8
            signals['data_conflict_severe'] = (
                f"Directional conflict: {', '.join(positive_sources)} positive vs "
                f"{', '.join(negative_sources)} negative"
            )
        elif cv > 0.5:
            # High variance in scores (>50% of mean)
            multiplier = 0.85
            signals['data_conflict_warning'] = (
                f"High variance between sources (CV={cv:.2f}): "
                f"scores range from {min(scores):.0f} to {max(scores):.0f}"
            )
        elif cv > 0.3:
            # Moderate variance
            multiplier = 0.9
            signals['data_conflict_moderate'] = (
                f"Moderate variance between sources (CV={cv:.2f})"
            )

        # Add diagnostic info
        signals['_conflict_stats'] = {
            'mean': round(mean_score, 2),
            'std': round(std_score, 2),
            'cv': round(cv, 2),
            'sources': scores_by_source,
            'multiplier': multiplier
        }

        return multiplier, signals

    def _score_symbol(
        self,
        symbol: str,
        daily_data: Dict[str, Dict[str, Dict]],
        cumulative_data: Dict[str, Dict[str, Dict]],
        broker_stats: Dict[str, Dict]
    ) -> Optional[Dict]:
        """
        Score a single symbol based on bandarmology criteria.
        
        Returns a dict with all scoring details, or None if insufficient data.
        """
        # Get data from each method (daily)
        mm_daily = daily_data.get('m', {}).get(symbol)
        nr_daily = daily_data.get('nr', {}).get(symbol)
        ff_daily = daily_data.get('f', {}).get(symbol)

        # Get data from each method (cumulative)
        mm_cum = cumulative_data.get('m', {}).get(symbol)
        nr_cum = cumulative_data.get('nr', {}).get(symbol)
        ff_cum = cumulative_data.get('f', {}).get(symbol)

        # Use MM daily as primary source (most common), fallback to NR or FF
        primary = mm_daily or nr_daily or ff_daily
        primary_cum = mm_cum or nr_cum or ff_cum

        if not primary and not primary_cum:
            return None

        ref = primary or primary_cum

        # --- Extract base values ---
        pinky = _is_flag_set(ref.get('pinky'))
        crossing = _is_flag_set(ref.get('crossing'))
        unusual = _is_flag_set(ref.get('unusual'))
        likuid = _is_flag_set(ref.get('likuid'))
        price = _parse_numeric(ref.get('price'))
        pct_1d = _parse_numeric(ref.get('pct_1d'))

        # MA values
        ma5 = _parse_numeric(ref.get('ma5'))
        ma10 = _parse_numeric(ref.get('ma10'))
        ma20 = _parse_numeric(ref.get('ma20'))
        ma50 = _parse_numeric(ref.get('ma50'))
        ma100 = _parse_numeric(ref.get('ma100'))

        # Daily flow values (d-0 is today's flow)
        d_0_mm = _parse_numeric((mm_daily or {}).get('d_0'))
        d_0_nr = _parse_numeric((nr_daily or {}).get('d_0'))
        d_0_ff = _parse_numeric((ff_daily or {}).get('d_0'))

        # Weekly accumulation values from daily data
        w_1 = _parse_numeric((primary or {}).get('w_1'))
        w_2 = _parse_numeric((primary or {}).get('w_2'))
        w_3 = _parse_numeric((primary or {}).get('w_3'))
        w_4 = _parse_numeric((primary or {}).get('w_4'))

        # Daily accumulation
        d_2 = _parse_numeric((primary or {}).get('d_2'))
        d_3 = _parse_numeric((primary or {}).get('d_3'))
        d_4 = _parse_numeric((primary or {}).get('d_4'))

        # Cumulative values
        c_3 = _parse_numeric((primary_cum or {}).get('c_3'))
        c_5 = _parse_numeric((primary_cum or {}).get('c_5'))
        c_10 = _parse_numeric((primary_cum or {}).get('c_10'))
        c_20 = _parse_numeric((primary_cum or {}).get('c_20'))

        # --- SCORING ---
        scores = {}
        total_score = 0

        # 1. Pinky Score (15 pts)
        pinky_score = 15 if pinky else 0
        scores['pinky'] = pinky_score
        total_score += pinky_score

        # 2. Crossing Score (10 pts)
        crossing_score = 10 if crossing else 0
        scores['crossing'] = crossing_score
        total_score += crossing_score

        # 3. Unusual Volume Score (10 pts)
        unusual_score = 10 if unusual else 0
        scores['unusual'] = unusual_score
        total_score += unusual_score

        # 4. Liquidity Score (5 pts)
        likuid_score = 5 if likuid else 0
        scores['likuid'] = likuid_score
        total_score += likuid_score

        # 5. Multi-Method Confluence (20 pts)
        # Check if d_0 is positive across methods
        positive_methods = []
        if d_0_mm > 0:
            positive_methods.append('MM')
        if d_0_nr > 0:
            positive_methods.append('NR')
        if d_0_ff > 0:
            positive_methods.append('FF')

        if len(positive_methods) >= 3:
            confluence_score = 20
            confluence_status = "TRIPLE"
        elif len(positive_methods) == 2:
            confluence_score = 12
            confluence_status = "DOUBLE"
        elif len(positive_methods) == 1:
            confluence_score = 5
            confluence_status = "SINGLE"
        else:
            confluence_score = 0
            confluence_status = "NONE"

        scores['confluence'] = confluence_score
        total_score += confluence_score

        # 6. Accumulation Trend (15 pts)
        # Check weekly trend (w_4 → w_3 → w_2 → w_1 → d_0)
        weekly_values = [w_4, w_3, w_2, w_1]
        positive_weeks = sum(1 for v in weekly_values if v > 0)
        recent_positive = sum(1 for v in [d_0_mm, d_2, d_3] if v > 0)

        acc_score = 0
        if positive_weeks >= 3 and d_0_mm > 0:
            acc_score = 15  # Strong consistent accumulation
        elif positive_weeks >= 2 and d_0_mm > 0:
            acc_score = 10
        elif positive_weeks >= 1 and recent_positive >= 2:
            acc_score = 6
        elif d_0_mm > 0:
            acc_score = 3

        scores['accumulation'] = acc_score
        total_score += acc_score

        # 7. Price Position vs MAs (10 pts)
        ma_score = 0
        ma_above_count = 0
        if price > 0:
            if ma5 > 0 and price >= ma5:
                ma_above_count += 1
            if ma10 > 0 and price >= ma10:
                ma_above_count += 1
            if ma20 > 0 and price >= ma20:
                ma_above_count += 1
            if ma50 > 0 and price >= ma50:
                ma_above_count += 1
            if ma100 > 0 and price >= ma100:
                ma_above_count += 1

        if ma_above_count >= 5:
            ma_score = 10
        elif ma_above_count >= 4:
            ma_score = 8
        elif ma_above_count >= 3:
            ma_score = 5
        elif ma_above_count >= 2:
            ma_score = 3

        scores['ma_position'] = ma_score
        total_score += ma_score

        # 8. Short-term Momentum (10 pts)
        momentum_score = 0
        if d_0_mm > 0 and pct_1d > 0:
            momentum_score = 10
        elif d_0_mm > 0 or pct_1d > 0:
            momentum_score = 5
        elif d_0_mm > 0 and pct_1d < -3:
            momentum_score = 2  # Inflow despite price drop = potential reversal

        scores['momentum'] = momentum_score
        total_score += momentum_score

        # 9. Institutional/Foreign Broker Activity (5 pts)
        broker_info = broker_stats.get(symbol, {})
        inst_score = 0
        inst_net = broker_info.get('institutional_net_lot', 0)
        foreign_net = broker_info.get('foreign_net_lot', 0)
        if inst_net > 0 and foreign_net > 0:
            inst_score = 5
        elif inst_net > 0 or foreign_net > 0:
            inst_score = 3

        scores['institutional'] = inst_score
        total_score += inst_score

        # 10. Relative Market/Sector Context (±20% adjustment)
        rel_multiplier, rel_context = self._calculate_relative_flow_score(
            symbol, daily_data, cumulative_data
        )
        # Apply multiplier to total score
        adjusted_total_score = int(total_score * rel_multiplier)

        # Add context info to scores
        scores['relative_context'] = rel_context
        scores['relative_multiplier'] = rel_multiplier

        # Use adjusted score for classification but keep raw for reference
        classification_score = adjusted_total_score

        # --- CLASSIFICATION ---
        trade_type = self._classify_trade_type(
            classification_score, scores, pinky, crossing, unusual, likuid,
            positive_weeks, d_0_mm, pct_1d, ma_above_count,
            w_1, w_2, c_3, c_5
        )

        # --- Build result ---
        return {
            'symbol': symbol,
            'total_score': adjusted_total_score,
            'total_score_raw': total_score,
            'max_score': 100,
            'trade_type': trade_type,
            'pinky': pinky,
            'crossing': crossing,
            'unusual': unusual,
            'likuid': likuid,
            'confluence_status': confluence_status,
            'positive_methods': positive_methods,
            'price': price,
            'pct_1d': pct_1d,
            'ma_above_count': ma_above_count,

            # Accumulation values
            'w_4': w_4,
            'w_3': w_3,
            'w_2': w_2,
            'w_1': w_1,
            'd_4': d_4,
            'd_3': d_3,
            'd_2': d_2,
            'd_0_mm': d_0_mm,
            'd_0_nr': d_0_nr,
            'd_0_ff': d_0_ff,

            # Cumulative
            'c_3': c_3,
            'c_5': c_5,
            'c_10': c_10,
            'c_20': c_20,

            # Broker info
            'inst_net_lot': broker_info.get('institutional_net_lot', 0),
            'foreign_net_lot': broker_info.get('foreign_net_lot', 0),
            'retail_net_lot': broker_info.get('retail_net_lot', 0),
            'top_buyer': broker_info.get('top_buyer'),
            'top_seller': broker_info.get('top_seller'),
            'brokers_buying': broker_info.get('total_brokers_buying', 0),
            'brokers_selling': broker_info.get('total_brokers_selling', 0),

            # Relative market/sector context
            'relative_multiplier': rel_multiplier,
            'market_context': rel_context.get('market_context', {}),
            'sector_context': rel_context.get('sector_context', {}),

            # Score breakdown
            'scores': scores,
        }

    def _classify_trade_type(
        self, total_score, scores, pinky, crossing, unusual, likuid,
        positive_weeks, d_0_mm, pct_1d, ma_above_count,
        w_1, w_2, c_3, c_5
    ) -> str:
        """Classify whether a stock is suitable for swing, intraday, or both."""
        is_swing = False
        is_intraday = False

        # SWING criteria: multi-week accumulation + institutional backing + above MAs
        if (total_score >= 55 and positive_weeks >= 2 and ma_above_count >= 3):
            is_swing = True
        elif (total_score >= 45 and positive_weeks >= 3):
            is_swing = True
        elif (pinky and positive_weeks >= 2 and (w_1 > 0 or w_2 > 0)):
            is_swing = True
        elif (c_5 > 0 and c_3 > 0 and ma_above_count >= 3):
            is_swing = True

        # INTRADAY criteria: short-term signals (unusual volume, crossing, momentum)
        if (unusual or crossing) and d_0_mm > 0:
            is_intraday = True
        elif total_score >= 50 and d_0_mm > 0 and pct_1d > 0:
            is_intraday = True
        elif unusual and pct_1d > 0:
            is_intraday = True
        elif crossing and d_0_mm > 0:
            is_intraday = True

        if is_swing and is_intraday:
            return "BOTH"
        elif is_swing:
            return "SWING"
        elif is_intraday:
            return "INTRADAY"
        elif total_score >= 30:
            return "WATCH"
        else:
            return "—"

    def get_available_dates(self) -> List[str]:
        """Get available analysis dates from neobdm_records."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT SUBSTR(scraped_at, 1, 10) as date
                FROM neobdm_records
                ORDER BY date DESC
                LIMIT 60
            """)
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== DATA VALIDATION ====================

    def _validate_data_consistency(
        self,
        target_date: str,
        inventory_data: Optional[List[Dict]] = None,
        txn_chart_data: Optional[Dict] = None,
        broker_summary_data: Optional[Dict] = None,
        inventory_meta: Optional[Dict] = None,
        broker_summary_meta: Optional[Dict] = None
    ) -> Tuple[bool, List[str], Dict[str, str]]:
        """
        Validate that all data sources are within acceptable date range of each other.

        Args:
            target_date: Expected analysis date (YYYY-MM-DD)
            inventory_data: Inventory data (list of brokers)
            txn_chart_data: Transaction chart with date metadata
            broker_summary_data: Broker summary dict with 'buy'/'sell' lists
            inventory_meta: Optional dict with inventory metadata (firstDate, lastDate)
            broker_summary_meta: Optional dict with broker summary metadata (trade_date)

        Returns:
            Tuple of (is_valid, warnings, date_info)
            - is_valid: True if all dates align within tolerance
            - warnings: List of warning messages for mismatched dates
            - date_info: Dict mapping source names to their actual dates
        """
        warnings = []
        date_info = {'target': target_date}

        if not target_date:
            return False, ["No target date provided"], date_info

        try:
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            return False, [f"Invalid target date format: {target_date}"], date_info

        # Extract dates from each data source
        source_dates = {}

        # Inventory data: check metadata first, then try to extract from data
        if inventory_data or inventory_meta:
            inv_date = None
            # First check metadata if provided
            if inventory_meta and isinstance(inventory_meta, dict):
                inv_date = inventory_meta.get('lastDate') or inventory_meta.get('date_end')
            # Check if inventory_data is a dict with metadata (full API response)
            if not inv_date and isinstance(inventory_data, dict):
                inv_date = inventory_data.get('lastDate') or inventory_data.get('date_end')
            # Check individual broker records for date_end
            if not inv_date and isinstance(inventory_data, list) and len(inventory_data) > 0:
                # Most recent broker record date
                dates = []
                for b in inventory_data:
                    if isinstance(b, dict):
                        d = b.get('date_end') or b.get('scraped_at')
                        if d:
                            dates.append(d)
                if dates:
                    # Use most recent date
                    inv_date = max(dates)
            source_dates['inventory'] = inv_date

        # Transaction chart data
        if txn_chart_data:
            txn_date = txn_chart_data.get('lastDate') or txn_chart_data.get('date_end')
            source_dates['transaction_chart'] = txn_date

        # Broker summary data
        if broker_summary_data or broker_summary_meta:
            broksum_date = None
            # First check metadata if provided
            if broker_summary_meta and isinstance(broker_summary_meta, dict):
                broksum_date = broker_summary_meta.get('trade_date') or broker_summary_meta.get('date')
            # Check broker_summary_data dict
            if not broksum_date and isinstance(broker_summary_data, dict):
                broksum_date = broker_summary_data.get('trade_date') or broker_summary_data.get('date')
                # Try to infer from first buy/sell entry
                if not broksum_date:
                    buy_list = broker_summary_data.get('buy', [])
                    if buy_list and isinstance(buy_list[0], dict):
                        broksum_date = buy_list[0].get('trade_date')
            source_dates['broker_summary'] = broksum_date

        date_info.update(source_dates)

        # Check each source against target date (allow 1 trading day tolerance)
        max_date_diff_days = 3  # Allow weekend + 1 day buffer

        for source_name, source_date in source_dates.items():
            if not source_date:
                warnings.append(f"{source_name}: No date information available")
                continue

            try:
                # Handle different date formats
                if isinstance(source_date, str):
                    if 'T' in source_date:
                        source_dt = datetime.strptime(source_date.split('T')[0], '%Y-%m-%d')
                    else:
                        source_dt = datetime.strptime(source_date, '%Y-%m-%d')
                else:
                    continue

                date_diff = abs((source_dt - target_dt).days)

                if date_diff > max_date_diff_days:
                    warnings.append(
                        f"{source_name}: Date mismatch - expected {target_date}, "
                        f"got {source_date} ({date_diff} days difference)"
                    )
            except ValueError as e:
                warnings.append(f"{source_name}: Could not parse date '{source_date}': {e}")

        # Check cross-source consistency (if multiple sources provided)
        available_dates = {k: v for k, v in source_dates.items() if v}
        if len(available_dates) >= 2:
            try:
                dates = []
                for d in available_dates.values():
                    if isinstance(d, str):
                        if 'T' in d:
                            dates.append(datetime.strptime(d.split('T')[0], '%Y-%m-%d'))
                        else:
                            dates.append(datetime.strptime(d, '%Y-%m-%d'))

                if dates:
                    date_range = max(dates) - min(dates)
                    if date_range.days > max_date_diff_days:
                        warnings.append(
                            f"Cross-source date range: {date_range.days} days between "
                            f"earliest and latest data sources"
                        )
            except ValueError:
                pass

        is_valid = len(warnings) == 0
        return is_valid, warnings, date_info

    def _apply_freshness_decay(self, deep_cache_date: str, analysis_date: str) -> float:
        """
        Calculate confidence multiplier based on data age.

        Args:
            deep_cache_date: Date of cached deep analysis (YYYY-MM-DD)
            analysis_date: Current analysis date (YYYY-MM-DD)

        Returns:
            Float multiplier (0.0-1.0) for confidence decay
        """
        try:
            cache_dt = datetime.strptime(deep_cache_date, '%Y-%m-%d')
            current_dt = datetime.strptime(analysis_date, '%Y-%m-%d')
            days_old = (current_dt - cache_dt).days

            if days_old < 0:
                return 1.0  # Future data, assume full confidence
            elif days_old == 0:
                return 1.0  # Same day, full confidence
            elif days_old <= 1:
                return 0.95  # 1 day old
            elif days_old <= 3:
                return 0.90  # 2-3 days old
            elif days_old <= 7:
                return 0.80  # Week old
            elif days_old <= 14:
                return 0.65  # Two weeks old
            else:
                return 0.50  # > 50% decay for older data
        except ValueError:
            return 1.0  # Assume full confidence if dates unparseable

    # ==================== DEEP ANALYSIS (Inventory + Txn Chart) ====================

    def analyze_deep(
        self,
        ticker: str,
        inventory_data: Optional[List[Dict]] = None,
        txn_chart_data: Optional[Dict] = None,
        broker_summary_data: Optional[Dict] = None,
        broksum_multiday_data: Optional[List[Dict]] = None,
        price_series: Optional[List[Dict]] = None,
        base_result: Optional[Dict] = None,
        previous_deep: Optional[Dict] = None,
        important_dates_data: Optional[List[Dict]] = None,
        inventory_meta: Optional[Dict] = None,
        broker_summary_meta: Optional[Dict] = None
    ) -> Dict:
        """
        Perform deep analysis on a single ticker using inventory + transaction chart + broker summary data.

        Enhances the base screening score with:
        - Controlling broker detection & accumulation phase analysis
        - Inventory accumulation patterns (broker-level)
        - Transaction chart flow analysis (multi-method)
        - Cross-index scoring
        - Broker summary analysis (avg price, lot, entry/target)
        - Enhanced trade type classification

        Args:
            ticker: Stock ticker
            inventory_data: List of broker inventory records (from DB or scraper)
            txn_chart_data: Transaction chart record (from DB or scraper)
            broker_summary_data: Broker summary dict with 'buy' and 'sell' lists
            broksum_multiday_data: Multi-day broker summary for consistency analysis
            price_series: List of price OHLC dicts from inventory chart
            base_result: Existing bandarmology result dict to enhance
            previous_deep: Previous deep analysis for historical comparison
            important_dates_data: Broker summary data for important dates
            inventory_meta: Metadata for inventory (firstDate, lastDate)
            broker_summary_meta: Metadata for broker summary (trade_date)

        Returns:
            Enhanced result dict with deep_* fields added
        """
        deep = {
            'deep_score': 0,
            'deep_signals': {},
            'deep_trade_type': None,
            # Inventory metrics
            'inv_accum_brokers': 0,
            'inv_distrib_brokers': 0,
            'inv_clean_brokers': 0,
            'inv_tektok_brokers': 0,
            'inv_total_accum_lot': 0,
            'inv_total_distrib_lot': 0,
            'inv_top_accum_broker': None,
            'inv_top_accum_lot': 0,
            'inv_brokers_detail': [],
            # Transaction chart metrics
            'txn_mm_cum': 0,
            'txn_foreign_cum': 0,
            'txn_institution_cum': 0,
            'txn_retail_cum': 0,
            'txn_cross_index': 0,
            'txn_foreign_participation': 0,
            'txn_institution_participation': 0,
            'txn_mm_trend': 'NEUTRAL',
            'txn_foreign_trend': 'NEUTRAL',
            # Broker summary metrics
            'broksum_total_buy_lot': 0,
            'broksum_total_sell_lot': 0,
            'broksum_total_buy_val': 0,
            'broksum_total_sell_val': 0,
            'broksum_avg_buy_price': 0,
            'broksum_avg_sell_price': 0,
            'broksum_floor_price': 0,
            'broksum_target_price': 0,
            'broksum_top_buyers': [],
            'broksum_top_sellers': [],
            'broksum_net_institutional': 0,
            'broksum_net_foreign': 0,
            # Entry/target analysis
            'entry_price': 0,
            'target_price': 0,
            'stop_loss': 0,
            'risk_reward_ratio': 0,
            # Controlling broker analysis
            'controlling_brokers': [],
            'accum_start_date': None,
            'accum_phase': 'UNKNOWN',
            'bandar_avg_cost': 0,
            # Conflict resolution
            'data_source_conflict': False,
            'conflict_multiplier': 1.0,
            'source_scores': {},
            'bandar_total_lot': 0,
            'coordination_score': 0,
            'phase_confidence': 'LOW',
            'breakout_signal': 'NONE',
            'bandar_peak_lot': 0,
            'bandar_distribution_pct': 0.0,
            'distribution_alert': 'NONE',
            # Cross-reference: broker summary ↔ inventory
            'bandar_buy_today_count': 0,
            'bandar_sell_today_count': 0,
            'bandar_buy_today_lot': 0,
            'bandar_sell_today_lot': 0,
            'bandar_confirmation': 'NONE',
            # Multi-day broker summary consistency
            'broksum_days_analyzed': 0,
            'broksum_consistency_score': 0,
            'broksum_consistent_buyers': [],
            'broksum_consistent_sellers': [],
            # Breakout probability
            'breakout_probability': 0,
            'breakout_factors': {},
            # Accumulation duration
            'accum_duration_days': 0,
            # Concentration risk
            'concentration_broker': None,
            'concentration_pct': 0.0,
            'concentration_risk': 'NONE',
            # Smart money vs retail divergence
            'txn_smart_money_cum': 0,
            'txn_retail_cum_deep': 0,
            'smart_retail_divergence': 0,
            'smart_retail_divergence_ratio': 0.0,
            # Volume context
            'volume_score': 0,
            'volume_signal': 'NONE',
            'volume_confirmation_multiplier': 1.0,
            'volume_lot_total': 0,
            'volume_proxy_participation': 0,
            # MA cross
            'ma_cross_signal': 'NONE',
            'ma_cross_score': 0,
            # Historical comparison
            'prev_deep_score': 0,
            'prev_phase': '',
            'phase_transition': 'NONE',
            'score_trend': 'NONE',
            # Flow velocity/acceleration
            'flow_velocity_mm': 0,
            'flow_velocity_foreign': 0,
            'flow_velocity_institution': 0,
            'flow_acceleration_mm': 0,
            'flow_acceleration_signal': 'NONE',
            'flow_velocity_score': 0,
            # Important dates broker summary
            'important_dates': [],
            'important_dates_score': 0,
            'important_dates_signal': 'NONE',
            # Pump tomorrow prediction
            'pump_tomorrow_score': 0,
            'pump_tomorrow_signal': 'NONE',
            'pump_tomorrow_factors': {},
        }

        signals = {}
        deep_score = 0

        # ---- DATA SOURCE VALIDATION ----
        # Get analysis date from base_result or use today
        analysis_date = None
        if base_result:
            analysis_date = base_result.get('date') or base_result.get('analysis_date')
        if not analysis_date:
            analysis_date = datetime.now().strftime('%Y-%m-%d')

        # Validate data source date consistency
        is_valid, validation_warnings, date_info = self._validate_data_consistency(
            target_date=analysis_date,
            inventory_data=inventory_data,
            txn_chart_data=txn_chart_data,
            broker_summary_data=broker_summary_data,
            inventory_meta=inventory_meta,
            broker_summary_meta=broker_summary_meta
        )

        # Add validation info to deep results
        deep['data_validation'] = {
            'is_valid': is_valid,
            'warnings': validation_warnings,
            'source_dates': date_info,
            'analysis_date': analysis_date
        }

        # Log warnings if data is inconsistent
        if not is_valid:
            for warning in validation_warnings:
                logger.warning(f"[{ticker}] Data validation: {warning}")
            # Add warning signals
            if validation_warnings:
                signals['data_date_mismatch'] = f"Date mismatch: {'; '.join(validation_warnings[:2])}"

        # ---- INVENTORY METRICS (populated for display, scored separately below) ----
        if inventory_data:
            # Populate inventory metrics for display
            accum = [b for b in inventory_data if b.get('is_accumulating') or b.get('isAccumulating')]
            distrib = [b for b in inventory_data if not (b.get('is_accumulating') or b.get('isAccumulating'))]
            clean = [b for b in inventory_data if b.get('is_clean') or b.get('isClean')]
            tektok = [b for b in inventory_data if b.get('is_tektok') or b.get('isTektok')]

            deep['inv_accum_brokers'] = len(accum)
            deep['inv_distrib_brokers'] = len(distrib)
            deep['inv_clean_brokers'] = len(clean)
            deep['inv_tektok_brokers'] = len(tektok)

            accum_lots = sum(
                abs(b.get('final_net_lot') or b.get('finalNetLot') or 0)
                for b in accum
            )
            distrib_lots = sum(
                abs(b.get('final_net_lot') or b.get('finalNetLot') or 0)
                for b in distrib
            )
            deep['inv_total_accum_lot'] = accum_lots
            deep['inv_total_distrib_lot'] = distrib_lots

            if accum:
                top = max(accum, key=lambda b: abs(b.get('final_net_lot') or b.get('finalNetLot') or 0))
                deep['inv_top_accum_broker'] = top.get('broker_code') or top.get('code')
                deep['inv_top_accum_lot'] = abs(top.get('final_net_lot') or top.get('finalNetLot') or 0)

            # Build detail list (top 5 accum + top 3 distrib)
            accum_sorted = sorted(accum, key=lambda b: abs(b.get('final_net_lot') or b.get('finalNetLot') or 0), reverse=True)
            distrib_sorted = sorted(distrib, key=lambda b: abs(b.get('final_net_lot') or b.get('finalNetLot') or 0), reverse=True)
            deep['inv_brokers_detail'] = [
                {
                    'code': b.get('broker_code') or b.get('code'),
                    'net_lot': b.get('final_net_lot') or b.get('finalNetLot') or 0,
                    'is_clean': bool(b.get('is_clean') or b.get('isClean')),
                    'is_tektok': bool(b.get('is_tektok') or b.get('isTektok')),
                    'side': 'ACCUM'
                }
                for b in accum_sorted[:5]
            ] + [
                {
                    'code': b.get('broker_code') or b.get('code'),
                    'net_lot': b.get('final_net_lot') or b.get('finalNetLot') or 0,
                    'is_clean': bool(b.get('is_clean') or b.get('isClean')),
                    'is_tektok': bool(b.get('is_tektok') or b.get('isTektok')),
                    'side': 'DISTRIB'
                }
                for b in distrib_sorted[:3]
            ]

            # ---- INVENTORY SCORING (max 30 pts) ----
            inv_score, inv_signals = self._score_inventory(inventory_data)
            deep_score += inv_score
            signals.update(inv_signals)

        # ---- TRANSACTION CHART ANALYSIS (max 30 pts) ----
        if txn_chart_data:
            txn_score, txn_signals = self._score_transaction_chart(txn_chart_data)

            # ---- VOLUME CONFIRMATION MULTIPLIER ----
            vol_mult, vol_conf_signals = self._score_volume_confirmed_flow(
                txn_chart_data, broker_summary_data
            )
            deep['volume_confirmation_multiplier'] = round(vol_mult, 2)

            # Apply volume multiplier to transaction score
            adjusted_txn_score = round(txn_score * vol_mult, 1)
            deep['txn_score_raw'] = round(txn_score, 1)
            deep['txn_score_adjusted'] = adjusted_txn_score

            deep_score += adjusted_txn_score
            signals.update(txn_signals)
            signals.update(vol_conf_signals)

            # Populate volume metrics from signals
            if 'volume_lot_total' in vol_conf_signals:
                deep['volume_lot_total'] = vol_conf_signals.get('volume_lot_total', 0)
            if 'volume_proxy_participation' in vol_conf_signals:
                deep['volume_proxy_participation'] = vol_conf_signals.get('volume_proxy_participation', 0)

            # Populate txn metrics
            deep['txn_mm_cum'] = round(_safe_float(txn_chart_data.get('cum_mm')), 2)
            deep['txn_foreign_cum'] = round(_safe_float(txn_chart_data.get('cum_foreign')), 2)
            deep['txn_institution_cum'] = round(_safe_float(txn_chart_data.get('cum_institution')), 2)
            deep['txn_retail_cum'] = round(_safe_float(txn_chart_data.get('cum_retail')), 2)
            deep['txn_cross_index'] = round(_safe_float(txn_chart_data.get('cross_index')), 2)
            deep['txn_foreign_participation'] = round(_safe_float(txn_chart_data.get('part_foreign')), 2)
            deep['txn_institution_participation'] = round(_safe_float(txn_chart_data.get('part_institution')), 2)
            deep['txn_mm_trend'] = txn_chart_data.get('mm_trend') or 'NEUTRAL'
            deep['txn_foreign_trend'] = txn_chart_data.get('foreign_trend') or 'NEUTRAL'

        # ---- DATA SOURCE CONFLICT RESOLUTION ----
        # Track scores by source for conflict detection
        scores_by_source = {}
        if inventory_data:
            scores_by_source['inventory'] = inv_score
        if txn_chart_data:
            scores_by_source['transaction_chart'] = txn_score

        # Store source scores for reference
        deep['source_scores'] = scores_by_source.copy()

        # Add broker summary score when available
        if broker_summary_data:
            broksum_score = deep.get('broksum_consistency_score', 0)
            scores_by_source['broker_summary'] = broksum_score

        # Filter out None values and zero scores (sources not providing meaningful data)
        available_scores = {k: v for k, v in scores_by_source.items() if v is not None and v != 0}

        if len(available_scores) >= 2:
            conflict_mult, conflict_signals = self._resolve_data_source_conflicts(available_scores)
            if conflict_mult != 1.0:
                # Apply conflict penalty to deep score
                deep_score = round(deep_score * conflict_mult, 1)
                signals.update(conflict_signals)
                deep['conflict_multiplier'] = round(conflict_mult, 2)
                deep['data_source_conflict'] = True
                # Remove internal diagnostic data from signals (not JSON serializable for frontend)
                deep['conflict_stats'] = signals.pop('_conflict_stats', None)

        # ---- FLOW VELOCITY/ACCELERATION (max 15 pts) ----
        if txn_chart_data:
            vel_score, vel_signals, vel_data = self._score_flow_velocity(txn_chart_data)
            deep_score += vel_score
            signals.update(vel_signals)
            deep['flow_velocity_mm'] = vel_data.get('velocity_mm', 0)
            deep['flow_velocity_foreign'] = vel_data.get('velocity_foreign', 0)
            deep['flow_velocity_institution'] = vel_data.get('velocity_institution', 0)
            deep['flow_acceleration_mm'] = vel_data.get('acceleration_mm', 0)
            deep['flow_acceleration_signal'] = vel_data.get('acceleration_signal', 'NONE')
            deep['flow_velocity_score'] = vel_score

        # ---- SMART MONEY vs RETAIL DIVERGENCE (max 5 pts) ----
        if txn_chart_data:
            sr_score, sr_signals = self._score_smart_retail_divergence(txn_chart_data)
            deep_score += sr_score
            deep['txn_smart_money_cum'] = _safe_float(txn_chart_data.get('cum_smart'))
            deep['txn_retail_cum_deep'] = _safe_float(txn_chart_data.get('cum_retail'))
            deep['smart_retail_divergence'] = sr_signals.pop('_sr_divergence', 0)
            deep['smart_retail_divergence_ratio'] = sr_signals.pop('_sr_divergence_ratio', 0.0)
            signals.update(sr_signals)

        # ---- BROKER SUMMARY ANALYSIS (max 20 pts) ----
        if broker_summary_data:
            broksum_score, broksum_signals = self._score_broker_summary(
                broker_summary_data, base_result
            )
            deep_score += broksum_score
            signals.update(broksum_signals)

            # Populate broker summary metrics
            buy_list = broker_summary_data.get('buy', [])
            sell_list = broker_summary_data.get('sell', [])

            total_buy_lot = sum(self._parse_broksum_num(b.get('nlot', 0)) for b in buy_list)
            total_sell_lot = sum(self._parse_broksum_num(s.get('nlot', 0)) for s in sell_list)
            total_buy_val = sum(self._parse_broksum_num(b.get('nval', 0)) for b in buy_list)
            total_sell_val = sum(self._parse_broksum_num(s.get('nval', 0)) for s in sell_list)

            deep['broksum_total_buy_lot'] = total_buy_lot
            deep['broksum_total_sell_lot'] = total_sell_lot
            deep['broksum_total_buy_val'] = total_buy_val
            deep['broksum_total_sell_val'] = total_sell_val

            # Calculate weighted avg buy/sell prices
            if total_buy_lot > 0:
                deep['broksum_avg_buy_price'] = round(
                    (total_buy_val * 1e9) / (total_buy_lot * 100), 0
                ) if total_buy_val > 0 else 0
            if total_sell_lot > 0:
                deep['broksum_avg_sell_price'] = round(
                    (total_sell_val * 1e9) / (total_sell_lot * 100), 0
                ) if total_sell_val > 0 else 0

            # Top 5 buyers and sellers
            deep['broksum_top_buyers'] = [
                {'broker': b.get('broker', ''), 'nlot': self._parse_broksum_num(b.get('nlot', 0)),
                 'avg_price': self._parse_broksum_num(b.get('bavg', 0))}
                for b in buy_list[:5]
            ]
            deep['broksum_top_sellers'] = [
                {'broker': s.get('broker', ''), 'nlot': self._parse_broksum_num(s.get('nlot', 0)),
                 'avg_price': self._parse_broksum_num(s.get('savg', 0))}
                for s in sell_list[:5]
            ]

            # Institutional/foreign net from broker classification
            inst_net = 0
            foreign_net = 0
            for b in buy_list:
                code = b.get('broker', '')
                info = self.broker_classes.get(code, {})
                cats = info.get('categories', [])
                nlot = self._parse_broksum_num(b.get('nlot', 0))
                if 'institutional' in cats:
                    inst_net += nlot
                if 'foreign' in cats:
                    foreign_net += nlot
            for s in sell_list:
                code = s.get('broker', '')
                info = self.broker_classes.get(code, {})
                cats = info.get('categories', [])
                nlot = self._parse_broksum_num(s.get('nlot', 0))
                if 'institutional' in cats:
                    inst_net -= nlot
                if 'foreign' in cats:
                    foreign_net -= nlot
            deep['broksum_net_institutional'] = inst_net
            deep['broksum_net_foreign'] = foreign_net

            # Floor price (institutional weighted avg buy price)
            inst_buy_lot = 0
            inst_buy_val = 0
            for b in buy_list:
                code = b.get('broker', '')
                info = self.broker_classes.get(code, {})
                cats = info.get('categories', [])
                if 'institutional' in cats or 'foreign' in cats:
                    inst_buy_lot += self._parse_broksum_num(b.get('nlot', 0))
                    inst_buy_val += self._parse_broksum_num(b.get('nval', 0))
            if inst_buy_lot > 0 and inst_buy_val > 0:
                deep['broksum_floor_price'] = round(
                    (inst_buy_val * 1e9) / (inst_buy_lot * 100), 0
                )

            # Target price (institutional weighted avg sell price)
            inst_sell_lot = 0
            inst_sell_val = 0
            for s in sell_list:
                code = s.get('broker', '')
                info = self.broker_classes.get(code, {})
                cats = info.get('categories', [])
                if 'institutional' in cats or 'foreign' in cats:
                    inst_sell_lot += self._parse_broksum_num(s.get('nlot', 0))
                    inst_sell_val += self._parse_broksum_num(s.get('nval', 0))
            if inst_sell_lot > 0 and inst_sell_val > 0:
                deep['broksum_target_price'] = round(
                    (inst_sell_val * 1e9) / (inst_sell_lot * 100), 0
                )

        # ---- CONTROLLING BROKER DETECTION & SCORING (max 30 pts) ----
        ctrl_result = {}
        if inventory_data:
            ctrl_result = self.detect_controlling_brokers(
                inventory_data, price_series=price_series, min_brokers=3
            )
            # Populate controlling broker fields
            deep['controlling_brokers'] = ctrl_result.get('controlling_brokers', [])
            deep['accum_start_date'] = ctrl_result.get('accum_start_date')
            deep['accum_phase'] = ctrl_result.get('accum_phase', 'UNKNOWN')
            deep['bandar_avg_cost'] = ctrl_result.get('bandar_avg_cost', 0)
            deep['bandar_total_lot'] = ctrl_result.get('bandar_total_lot', 0)
            deep['coordination_score'] = ctrl_result.get('coordination_score', 0)
            deep['phase_confidence'] = ctrl_result.get('phase_confidence', 'LOW')
            deep['breakout_signal'] = ctrl_result.get('breakout_signal', 'NONE')
            deep['bandar_peak_lot'] = ctrl_result.get('bandar_peak_lot', 0)
            deep['bandar_distribution_pct'] = ctrl_result.get('bandar_distribution_pct', 0.0)
            deep['distribution_alert'] = ctrl_result.get('distribution_alert', 'NONE')

            # Score the controlling broker analysis
            ctrl_score, ctrl_signals = self._score_controlling_brokers(ctrl_result, base_result)
            deep_score += ctrl_score
            signals.update(ctrl_signals)

        # ---- ACCUMULATION DURATION (stored for display, scored in _score_controlling_brokers) ----
        if deep.get('accum_start_date'):
            try:
                start_dt = datetime.strptime(deep['accum_start_date'], '%Y-%m-%d')
                deep['accum_duration_days'] = (datetime.now() - start_dt).days
            except (ValueError, TypeError):
                deep['accum_duration_days'] = 0

        # ---- CONCENTRATION RISK ----
        if ctrl_result and ctrl_result.get('controlling_brokers'):
            conc_score, conc_signals = self._score_concentration_risk(ctrl_result)
            deep_score += conc_score  # This is a penalty (negative or zero)
            signals.update(conc_signals)
            deep['concentration_broker'] = conc_signals.get('_conc_broker')
            deep['concentration_pct'] = conc_signals.get('_conc_pct', 0.0)
            deep['concentration_risk'] = conc_signals.get('_conc_risk', 'NONE')
            # Remove internal keys
            conc_signals.pop('_conc_broker', None)
            conc_signals.pop('_conc_pct', None)
            conc_signals.pop('_conc_risk', None)

        # ---- VOLUME CONTEXT (max 5 pts) ----
        if price_series and len(price_series) >= 10:
            vol_score, vol_signals = self._score_volume_context(
                price_series, deep
            )
            deep_score += vol_score
            signals.update(vol_signals)
            deep['volume_score'] = vol_score
            deep['volume_signal'] = vol_signals.get('_vol_signal', 'NONE')
            vol_signals.pop('_vol_signal', None)

        # ---- MA GOLDEN/DEATH CROSS (max 5 pts, min -3 pts) ----
        if price_series and len(price_series) >= 50:
            ma_score, ma_signals = self._score_ma_cross(price_series)
            deep_score += ma_score
            deep['ma_cross_score'] = ma_score
            deep['ma_cross_signal'] = ma_signals.get('_ma_cross_signal', 'NONE')
            ma_signals.pop('_ma_cross_signal', None)
            signals.update(ma_signals)

        # ---- ENTRY/TARGET PRICE CALCULATION ----
        # Priority: bandar_avg_cost > broksum_floor_price > broksum_avg_buy_price > fallback
        current_price = base_result.get('price', 0) if base_result else 0
        if current_price > 0:
            bandar_cost = deep.get('bandar_avg_cost', 0)
            floor = deep.get('broksum_floor_price', 0)
            target_inst = deep.get('broksum_target_price', 0)
            avg_buy = deep.get('broksum_avg_buy_price', 0)

            # Entry price: use bandar avg cost (most accurate), then institutional floor, then avg buy
            if bandar_cost > 0:
                deep['entry_price'] = bandar_cost
            elif floor > 0:
                deep['entry_price'] = floor
            elif avg_buy > 0:
                deep['entry_price'] = avg_buy
            else:
                deep['entry_price'] = round(current_price * 0.97, 0)

            # Target price: institutional sell avg, or bandar cost + 10-20% markup
            if target_inst > 0 and target_inst > deep['entry_price']:
                deep['target_price'] = target_inst
            elif bandar_cost > 0:
                # Markup depends on accumulation phase
                phase = deep.get('accum_phase', 'UNKNOWN')
                if phase == 'ACCUMULATION':
                    markup = 1.15  # 15% target when still loading
                elif phase == 'HOLDING':
                    markup = 1.10  # 10% when ready
                else:
                    markup = 1.05  # 5% conservative
                deep['target_price'] = round(bandar_cost * markup, 0)
            elif deep['entry_price'] > 0:
                deep['target_price'] = round(deep['entry_price'] * 1.05, 0)

            # Stop loss = entry * 0.95 (5% risk) or lowest controlling broker cost * 0.97
            if deep['entry_price'] > 0:
                cbs = deep.get('controlling_brokers', [])
                cb_costs = [cb['avg_buy_price'] for cb in cbs if cb.get('avg_buy_price', 0) > 0]
                if cb_costs:
                    min_cb_cost = min(cb_costs)
                    deep['stop_loss'] = round(min_cb_cost * 0.95, 0)
                else:
                    deep['stop_loss'] = round(deep['entry_price'] * 0.95, 0)

            # Risk/reward ratio
            if deep['entry_price'] > 0 and deep['stop_loss'] > 0 and deep['target_price'] > 0:
                risk = deep['entry_price'] - deep['stop_loss']
                reward = deep['target_price'] - deep['entry_price']
                if risk > 0:
                    deep['risk_reward_ratio'] = round(reward / risk, 2)

        # ---- CROSS-REFERENCE: Broker Summary ↔ Controlling Brokers (max 10 pts) ----
        if broker_summary_data and ctrl_result.get('controlling_brokers'):
            xref_score, xref_signals, xref_data = self._score_cross_reference(
                ctrl_result, broker_summary_data
            )
            deep_score += xref_score
            signals.update(xref_signals)
            deep['bandar_buy_today_count'] = xref_data.get('buy_count', 0)
            deep['bandar_sell_today_count'] = xref_data.get('sell_count', 0)
            deep['bandar_buy_today_lot'] = xref_data.get('buy_lot', 0)
            deep['bandar_sell_today_lot'] = xref_data.get('sell_lot', 0)
            deep['bandar_confirmation'] = xref_data.get('confirmation', 'NONE')

        # ---- IMPORTANT DATES BROKER SUMMARY ANALYSIS (max 10 pts) ----
        if important_dates_data and ctrl_result.get('controlling_brokers'):
            impdate_score, impdate_signals, impdate_analyzed = self._score_important_dates_broksum(
                important_dates_data,
                ctrl_result.get('controlling_brokers', [])
            )
            deep_score += impdate_score
            signals.update(impdate_signals)
            deep['important_dates'] = impdate_analyzed
            deep['important_dates_score'] = impdate_score
            # Determine signal
            if impdate_score >= 7:
                deep['important_dates_signal'] = 'STRONG_ACCUMULATION'
            elif impdate_score >= 4:
                deep['important_dates_signal'] = 'ACCUMULATION'
            elif impdate_score >= 1:
                deep['important_dates_signal'] = 'MILD_ACCUMULATION'
            elif impdate_score < 0:
                deep['important_dates_signal'] = 'DISTRIBUTION'
            else:
                deep['important_dates_signal'] = 'NEUTRAL'

        # ---- MULTI-DAY BROKER SUMMARY CONSISTENCY ----
        if broksum_multiday_data and len(broksum_multiday_data) >= 2:
            consistency_data = self._analyze_broker_consistency(
                broksum_multiday_data,
                ctrl_result.get('controlling_brokers', []) if ctrl_result else []
            )
            deep['broksum_days_analyzed'] = consistency_data.get('days_analyzed', 0)
            deep['broksum_consistency_score'] = consistency_data.get('consistency_score', 0)
            deep['broksum_consistent_buyers'] = consistency_data.get('consistent_buyers', [])
            deep['broksum_consistent_sellers'] = consistency_data.get('consistent_sellers', [])
            # Add consistency signals
            if consistency_data.get('signals'):
                signals.update(consistency_data['signals'])

        # ---- COMBINED SCORING ----
        # Synergy bonus: inventory confirms txn chart (max 10 pts)
        if inventory_data and txn_chart_data:
            synergy_score, synergy_signals = self._score_synergy(deep)
            deep_score += synergy_score
            signals.update(synergy_signals)

        deep['deep_score'] = round(deep_score, 1)
        deep['deep_signals'] = signals

        # ---- BREAKOUT PROBABILITY SCORE ----
        bp, bp_factors = self._calculate_breakout_probability(deep, base_result)
        deep['breakout_probability'] = bp
        deep['breakout_factors'] = bp_factors

        # ---- PUMP TOMORROW PREDICTION SCORE ----
        pt_score, pt_signal, pt_factors = self._calculate_pump_tomorrow_score(
            deep, base_result, broker_summary_data
        )
        deep['pump_tomorrow_score'] = pt_score
        deep['pump_tomorrow_signal'] = pt_signal
        deep['pump_tomorrow_factors'] = pt_factors

        # Enhanced classification
        deep['deep_trade_type'] = self._classify_deep_trade_type(
            deep, base_result
        )

        # ---- HISTORICAL COMPARISON ----
        if previous_deep:
            comparison = self._compare_with_previous(deep, previous_deep)
            deep.update(comparison)

            # Apply freshness decay to historical comparison scores
            prev_date = previous_deep.get('analysis_date')
            if prev_date and analysis_date:
                freshness = self._apply_freshness_decay(prev_date, analysis_date)
                deep['historical_freshness'] = freshness
                if freshness < 1.0:
                    deep['historical_warning'] = f"Previous analysis is {freshness:.0%} fresh ({prev_date})"

        return deep

    @staticmethod
    def _parse_broksum_num(value) -> float:
        """Parse broker summary numeric value (handles string formats like '1,234' or '1.5B')."""
        if value is None or value == '':
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            val_str = str(value).replace(',', '').strip()
            multiplier = 1.0
            if val_str.endswith('B'):
                val_str = val_str[:-1]
                multiplier = 1.0
            elif val_str.endswith('M'):
                val_str = val_str[:-1]
                multiplier = 0.001
            elif val_str.endswith('K'):
                val_str = val_str[:-1]
                multiplier = 0.000001
            return float(val_str) * multiplier if val_str else 0.0
        except (ValueError, AttributeError):
            return 0.0

    def _score_broker_summary(self, broksum: Dict, base_result: Optional[Dict] = None) -> Tuple[int, Dict]:
        """Score broker summary data. Max 20 points."""
        score = 0
        signals = {}

        buy_list = broksum.get('buy', [])
        sell_list = broksum.get('sell', [])
        if not buy_list and not sell_list:
            return 0, signals

        total_buy_lot = sum(self._parse_broksum_num(b.get('nlot', 0)) for b in buy_list)
        total_sell_lot = sum(self._parse_broksum_num(s.get('nlot', 0)) for s in sell_list)

        # 1. Buy/Sell lot imbalance (max 6 pts)
        total_lot = total_buy_lot + total_sell_lot
        if total_lot > 0:
            buy_ratio = total_buy_lot / total_lot
            if buy_ratio >= 0.6:
                score += 6
                signals['broksum_buy_dominant'] = f"Buy dominant ({buy_ratio:.0%} of total)"
            elif buy_ratio >= 0.52:
                score += 3
                signals['broksum_slight_buy'] = f"Slight buy pressure ({buy_ratio:.0%})"
            elif buy_ratio < 0.4:
                signals['broksum_sell_dominant'] = f"Sell dominant ({1-buy_ratio:.0%})"

        # 2. Institutional/foreign net buying (max 8 pts)
        inst_buy = 0
        foreign_buy = 0
        inst_sell = 0
        foreign_sell = 0
        for b in buy_list:
            code = b.get('broker', '')
            info = self.broker_classes.get(code, {})
            cats = info.get('categories', [])
            nlot = self._parse_broksum_num(b.get('nlot', 0))
            if 'institutional' in cats:
                inst_buy += nlot
            if 'foreign' in cats:
                foreign_buy += nlot
        for s in sell_list:
            code = s.get('broker', '')
            info = self.broker_classes.get(code, {})
            cats = info.get('categories', [])
            nlot = self._parse_broksum_num(s.get('nlot', 0))
            if 'institutional' in cats:
                inst_sell += nlot
            if 'foreign' in cats:
                foreign_sell += nlot

        inst_net = inst_buy - inst_sell
        foreign_net = foreign_buy - foreign_sell

        if inst_net > 0 and foreign_net > 0:
            score += 8
            signals['broksum_inst_foreign_buy'] = f"Institutional (+{inst_net:.0f}) & Foreign (+{foreign_net:.0f}) net buying"
        elif inst_net > 0:
            score += 5
            signals['broksum_inst_buy'] = f"Institutional net buying (+{inst_net:.0f} lot)"
        elif foreign_net > 0:
            score += 5
            signals['broksum_foreign_buy'] = f"Foreign net buying (+{foreign_net:.0f} lot)"
        elif inst_net < 0 and foreign_net < 0:
            signals['broksum_inst_foreign_sell'] = "Institutional & Foreign net selling"

        # 3. Price positioning vs floor (max 6 pts)
        current_price = base_result.get('price', 0) if base_result else 0
        if current_price > 0 and total_buy_lot > 0:
            # Calculate avg buy price
            total_buy_val = sum(self._parse_broksum_num(b.get('nval', 0)) for b in buy_list)
            if total_buy_val > 0:
                avg_buy_price = (total_buy_val * 1e9) / (total_buy_lot * 100)
                price_vs_avg = (current_price - avg_buy_price) / avg_buy_price if avg_buy_price > 0 else 0

                if -0.03 <= price_vs_avg <= 0.02:
                    score += 6
                    signals['broksum_near_floor'] = f"Price near avg buy ({avg_buy_price:.0f}), good entry"
                elif price_vs_avg < -0.03:
                    score += 4
                    signals['broksum_below_floor'] = f"Price below avg buy ({avg_buy_price:.0f}), potential discount"
                elif price_vs_avg > 0.05:
                    signals['broksum_above_floor'] = f"Price {price_vs_avg:.0%} above avg buy ({avg_buy_price:.0f})"

        return min(score, 20), signals

    def _score_inventory(self, inventory_data: List[Dict]) -> Tuple[int, Dict]:
        """Score inventory data. Max 30 points."""
        score = 0
        signals = {}

        accum = [b for b in inventory_data if b.get('is_accumulating') or b.get('isAccumulating')]
        distrib = [b for b in inventory_data if not (b.get('is_accumulating') or b.get('isAccumulating'))]
        clean = [b for b in inventory_data if b.get('is_clean') or b.get('isClean')]
        tektok = [b for b in inventory_data if b.get('is_tektok') or b.get('isTektok')]

        # 1. Net accumulation ratio (max 10 pts)
        total_accum_lot = sum(abs(b.get('final_net_lot') or b.get('finalNetLot') or 0) for b in accum)
        total_distrib_lot = sum(abs(b.get('final_net_lot') or b.get('finalNetLot') or 0) for b in distrib)
        total_lot = total_accum_lot + total_distrib_lot

        if total_lot > 0:
            accum_ratio = total_accum_lot / total_lot
            if accum_ratio >= 0.7:
                score += 10
                signals['inv_heavy_accum'] = f"Strong accumulation ({accum_ratio:.0%})"
            elif accum_ratio >= 0.55:
                score += 7
                signals['inv_moderate_accum'] = f"Moderate accumulation ({accum_ratio:.0%})"
            elif accum_ratio >= 0.4:
                score += 3
                signals['inv_weak_accum'] = f"Weak accumulation ({accum_ratio:.0%})"

        # 2. Clean vs tektok quality (max 8 pts)
        if len(clean) > 0 and len(tektok) == 0:
            score += 8
            signals['inv_all_clean'] = f"{len(clean)} clean broker(s), no tektokan"
        elif len(clean) > len(tektok):
            score += 5
            signals['inv_mostly_clean'] = f"{len(clean)} clean vs {len(tektok)} tektok"
        elif len(clean) > 0:
            score += 2
            signals['inv_some_clean'] = f"{len(clean)} clean, {len(tektok)} tektok"
        elif len(tektok) > 0:
            signals['inv_warning_tektok'] = f"{len(tektok)} tektokan detected"

        # 3. Accumulating broker count (max 6 pts)
        if len(accum) >= 5:
            score += 6
            signals['inv_many_accum'] = f"{len(accum)} brokers accumulating"
        elif len(accum) >= 3:
            score += 4
            signals['inv_some_accum'] = f"{len(accum)} brokers accumulating"
        elif len(accum) >= 1:
            score += 2

        # 4. Institutional broker check (max 6 pts)
        inst_accum = 0
        for b in accum:
            code = b.get('broker_code') or b.get('code', '')
            broker_info = self.broker_classes.get(code, {})
            cats = broker_info.get('categories', [])
            if 'institutional' in cats or 'foreign' in cats:
                inst_accum += 1

        if inst_accum >= 3:
            score += 6
            signals['inv_inst_accum'] = f"{inst_accum} institutional/foreign brokers accumulating"
        elif inst_accum >= 2:
            score += 4
            signals['inv_inst_accum'] = f"{inst_accum} institutional/foreign brokers accumulating"
        elif inst_accum >= 1:
            score += 2
            signals['inv_inst_accum'] = f"{inst_accum} institutional/foreign broker accumulating"

        return min(score, 30), signals

    def _score_transaction_chart(self, txn: Dict) -> Tuple[int, Dict]:
        """Score transaction chart data. Max 30 points."""
        score = 0
        signals = {}

        cum_mm = _safe_float(txn.get('cum_mm'))
        cum_foreign = _safe_float(txn.get('cum_foreign'))
        cum_inst = _safe_float(txn.get('cum_institution'))
        cum_retail = _safe_float(txn.get('cum_retail'))
        daily_mm = _safe_float(txn.get('daily_mm'))
        daily_foreign = _safe_float(txn.get('daily_foreign'))
        daily_inst = _safe_float(txn.get('daily_institution'))
        cross_idx = _safe_float(txn.get('cross_index'))
        part_foreign = _safe_float(txn.get('part_foreign'))
        part_inst = _safe_float(txn.get('part_institution'))
        mm_trend = txn.get('mm_trend') or 'NEUTRAL'
        foreign_trend = txn.get('foreign_trend') or 'NEUTRAL'

        # 1. Market Maker cumulative trend (max 8 pts)
        if mm_trend == 'STRONG_UP':
            score += 8
            signals['txn_mm_strong_up'] = f"MM cumulative strongly rising ({cum_mm:.1f}B)"
        elif mm_trend == 'UP':
            score += 5
            signals['txn_mm_up'] = f"MM cumulative rising ({cum_mm:.1f}B)"
        elif cum_mm > 0 and daily_mm > 0:
            score += 3
            signals['txn_mm_positive'] = f"MM cumulative positive ({cum_mm:.1f}B)"
        elif mm_trend in ('STRONG_DOWN', 'DOWN') and cum_mm < 0:
            signals['txn_mm_warning'] = f"MM cumulative declining ({cum_mm:.1f}B)"

        # 2. Foreign flow (max 7 pts)
        if foreign_trend == 'STRONG_UP' and cum_foreign > 0:
            score += 7
            signals['txn_foreign_strong'] = f"Strong foreign inflow ({cum_foreign:.1f}B)"
        elif cum_foreign > 0 and daily_foreign > 0:
            score += 5
            signals['txn_foreign_positive'] = f"Foreign net inflow ({cum_foreign:.1f}B)"
        elif cum_foreign > 0:
            score += 2
        elif cum_foreign < 0 and daily_foreign < 0:
            signals['txn_foreign_outflow'] = f"Foreign outflow ({cum_foreign:.1f}B)"

        # 3. Institution flow (max 5 pts)
        if cum_inst > 0 and daily_inst > 0:
            score += 5
            signals['txn_inst_inflow'] = f"Institution inflow ({cum_inst:.1f}B)"
        elif cum_inst > 0:
            score += 3

        # 4. Cross index quality (max 5 pts) — lower is better (less crossing/manipulation)
        if cross_idx < 0.3:
            score += 5
            signals['txn_low_cross'] = f"Low cross index ({cross_idx:.2f}) = clean market"
        elif cross_idx < 0.5:
            score += 3
            signals['txn_moderate_cross'] = f"Moderate cross index ({cross_idx:.2f})"
        elif cross_idx > 0.7:
            signals['txn_high_cross'] = f"High cross index ({cross_idx:.2f}) = heavy crossing"

        # 5. Participation quality (max 5 pts)
        if part_foreign > 0.5:
            score += 5
            signals['txn_foreign_dominated'] = f"Foreign dominates ({part_foreign:.0%})"
        elif part_inst > 0.3:
            score += 4
            signals['txn_inst_active'] = f"Institution active ({part_inst:.0%})"
        elif part_foreign > 0.3:
            score += 3

        return min(score, 30), signals

    def _score_volume_confirmed_flow(
        self, txn: Dict, broker_summary_data: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate volume confirmation multiplier for flow scores.

        Strong flows on high volume = higher confidence (multiplier > 1.0)
        Strong flows on low volume = lower confidence (multiplier < 1.0)

        Uses broker summary lot data as volume proxy, or participation ratios
        as fallback if broker summary not available.

        Returns: (multiplier, signals)
        - multiplier: 0.5 to 1.5 range
        - signals: dict with volume confirmation info
        """
        signals = {}
        multiplier = 1.0  # Default: no adjustment

        # Calculate volume proxy from broker summary
        total_lot = 0
        if broker_summary_data:
            buy_list = broker_summary_data.get('buy', [])
            sell_list = broker_summary_data.get('sell', [])
            total_buy_lot = sum(
                self._parse_broksum_num(b.get('nlot', 0)) for b in buy_list
            )
            total_sell_lot = sum(
                self._parse_broksum_num(s.get('nlot', 0)) for s in sell_list
            )
            total_lot = total_buy_lot + total_sell_lot

        # Get flow direction
        daily_mm = _safe_float(txn.get('daily_mm'))
        cum_mm = _safe_float(txn.get('cum_mm'))
        flow_positive = daily_mm > 0 or cum_mm > 0

        if not flow_positive:
            # For negative flows, volume confirmation is less relevant
            return 1.0, signals

        # Volume-based scoring thresholds (in lot units)
        if total_lot > 0:
            # High volume threshold: > 1000 lots
            # Low volume threshold: < 100 lots
            if total_lot >= 1000:
                multiplier = 1.3
                signals['vol_confirmed_strong'] = f"Strong flow confirmed by high volume ({total_lot:,.0f} lots)"
            elif total_lot >= 500:
                multiplier = 1.15
                signals['vol_confirmed_good'] = f"Good volume confirmation ({total_lot:,.0f} lots)"
            elif total_lot >= 200:
                multiplier = 1.0
                # Neutral - normal volume
            elif total_lot >= 100:
                multiplier = 0.85
                signals['vol_weak'] = f"Weak volume ({total_lot:,.0f} lots), flow less reliable"
            else:
                multiplier = 0.7
                signals['vol_very_weak'] = f"Very low volume ({total_lot:,.0f} lots), flow may be misleading"

            signals['volume_lot_total'] = total_lot

        else:
            # Fallback: use participation ratios as volume proxy
            part_foreign = _safe_float(txn.get('part_foreign'))
            part_inst = _safe_float(txn.get('part_institution'))
            total_participation = part_foreign + part_inst

            if total_participation >= 0.6:
                multiplier = 1.2
                signals['vol_proxy_strong'] = f"High institutional participation ({total_participation:.0%})"
            elif total_participation >= 0.4:
                multiplier = 1.1
                signals['vol_proxy_moderate'] = f"Moderate institutional participation ({total_participation:.0%})"
            elif total_participation <= 0.2:
                multiplier = 0.8
                signals['vol_proxy_weak'] = f"Low institutional participation ({total_participation:.0%})"

            signals['volume_proxy_participation'] = total_participation

        return multiplier, signals

    def _score_flow_velocity(self, txn: Dict) -> Tuple[int, Dict, Dict]:
        """
        Score flow velocity (rate of change) and acceleration for transaction chart.
        
        Velocity = (latest - week_ago) / 5 trading days
        Acceleration = velocity_5d - velocity_20d (positive = accelerating)
        
        A stock where MM flow went from +5B to +15B in 5 days is much more
        interesting than one sitting at +15B for a month.
        
        Returns: (score, signals, velocity_data)
        Max 15 points.
        """
        score = 0
        signals = {}
        velocity_data = {
            'velocity_mm': 0.0,
            'velocity_foreign': 0.0,
            'velocity_institution': 0.0,
            'acceleration_mm': 0.0,
            'acceleration_signal': 'NONE',
        }

        # Extract current and historical values
        cum_mm = _safe_float(txn.get('cum_mm'))
        cum_foreign = _safe_float(txn.get('cum_foreign'))
        cum_inst = _safe_float(txn.get('cum_institution'))

        mm_week = _safe_float(txn.get('cum_mm_week_ago'))
        foreign_week = _safe_float(txn.get('cum_foreign_week_ago'))
        inst_week = _safe_float(txn.get('cum_institution_week_ago'))

        mm_month = _safe_float(txn.get('cum_mm_month_ago'))
        foreign_month = _safe_float(txn.get('cum_foreign_month_ago'))
        inst_month = _safe_float(txn.get('cum_institution_month_ago'))

        # Skip if no historical data available
        if mm_week == 0 and mm_month == 0 and foreign_week == 0:
            return 0, signals, velocity_data

        # ---- Calculate velocities (change per trading day) ----
        # 5-day velocity (short-term momentum)
        vel_mm_5d = (cum_mm - mm_week) / 5.0 if mm_week != 0 or cum_mm != 0 else 0
        vel_foreign_5d = (cum_foreign - foreign_week) / 5.0
        vel_inst_5d = (cum_inst - inst_week) / 5.0

        # 20-day velocity (medium-term trend)
        vel_mm_20d = (cum_mm - mm_month) / 20.0 if mm_month != 0 or cum_mm != 0 else 0
        vel_foreign_20d = (cum_foreign - foreign_month) / 20.0
        vel_inst_20d = (cum_inst - inst_month) / 20.0

        # ---- Calculate acceleration (change in velocity) ----
        accel_mm = vel_mm_5d - vel_mm_20d
        accel_foreign = vel_foreign_5d - vel_foreign_20d
        accel_inst = vel_inst_5d - vel_inst_20d

        velocity_data['velocity_mm'] = round(vel_mm_5d, 2)
        velocity_data['velocity_foreign'] = round(vel_foreign_5d, 2)
        velocity_data['velocity_institution'] = round(vel_inst_5d, 2)
        velocity_data['acceleration_mm'] = round(accel_mm, 2)

        # ---- Scoring ----

        # 1. MM Flow Velocity (max 6 pts)
        if vel_mm_5d > 0 and accel_mm > 0:
            # Accelerating positive MM flow = strongest signal
            if vel_mm_5d > 1.0:  # >1B/day inflow
                score += 6
                signals['flow_mm_surge'] = (
                    f"MM flow AKSELERASI KUAT: +{vel_mm_5d:.1f}B/hari "
                    f"(percepatan +{accel_mm:.1f}B/hari)"
                )
            elif vel_mm_5d > 0.3:
                score += 4
                signals['flow_mm_accelerating'] = (
                    f"MM flow akselerasi: +{vel_mm_5d:.1f}B/hari "
                    f"(percepatan +{accel_mm:.1f}B/hari)"
                )
            else:
                score += 2
                signals['flow_mm_mild_accel'] = (
                    f"MM flow naik perlahan: +{vel_mm_5d:.1f}B/hari"
                )
        elif vel_mm_5d > 0 and accel_mm <= 0:
            # Positive but decelerating
            score += 1
            signals['flow_mm_decelerating'] = (
                f"MM flow positif tapi melambat: +{vel_mm_5d:.1f}B/hari "
                f"(perlambatan {accel_mm:.1f}B/hari)"
            )
        elif vel_mm_5d < -0.5 and accel_mm < 0:
            # Accelerating outflow = danger
            score -= 2
            signals['flow_mm_outflow_accel'] = (
                f"WARNING: MM flow keluar akselerasi: {vel_mm_5d:.1f}B/hari"
            )

        # 2. Foreign Flow Velocity (max 5 pts)
        if vel_foreign_5d > 0 and accel_foreign > 0:
            if vel_foreign_5d > 0.5:
                score += 5
                signals['flow_foreign_surge'] = (
                    f"Foreign inflow akselerasi: +{vel_foreign_5d:.1f}B/hari"
                )
            else:
                score += 3
                signals['flow_foreign_accel'] = (
                    f"Foreign inflow naik: +{vel_foreign_5d:.1f}B/hari"
                )
        elif vel_foreign_5d > 0:
            score += 1

        # 3. Institution Flow Velocity (max 4 pts)
        if vel_inst_5d > 0 and accel_inst > 0:
            score += 4
            signals['flow_inst_accel'] = (
                f"Institution inflow akselerasi: +{vel_inst_5d:.1f}B/hari"
            )
        elif vel_inst_5d > 0:
            score += 2

        # ---- Determine acceleration signal ----
        positive_accel = sum(1 for a in [accel_mm, accel_foreign, accel_inst] if a > 0)
        negative_accel = sum(1 for a in [accel_mm, accel_foreign, accel_inst] if a < 0)

        if positive_accel >= 3 and accel_mm > 0:
            velocity_data['acceleration_signal'] = 'STRONG_ACCELERATING'
            signals['flow_triple_accel'] = (
                "SINYAL KUAT: MM + Foreign + Institution semua akselerasi"
            )
        elif positive_accel >= 2 and accel_mm > 0:
            velocity_data['acceleration_signal'] = 'ACCELERATING'
        elif accel_mm > 0:
            velocity_data['acceleration_signal'] = 'MILD_ACCELERATING'
        elif negative_accel >= 2 and accel_mm < 0:
            velocity_data['acceleration_signal'] = 'DECELERATING'
        elif accel_mm < 0:
            velocity_data['acceleration_signal'] = 'MILD_DECELERATING'
        else:
            velocity_data['acceleration_signal'] = 'STABLE'

        return max(-2, min(score, 15)), signals, velocity_data

    def _score_important_dates_broksum(
        self,
        important_dates_data: List[Dict],
        controlling_brokers: List[Dict]
    ) -> Tuple[int, Dict, List[Dict]]:
        """
        Score broker summary analysis from important dates (turn_dates, peak_dates).
        
        Compares who was buying at accumulation start vs who is buying now.
        If the same controlling brokers are STILL buying = strong continuation signal.
        If controlling brokers switched to selling = distribution warning.
        
        Args:
            important_dates_data: List of {date, buy, sell, date_type} dicts
            controlling_brokers: List of controlling broker dicts from inventory
            
        Returns: (score, signals, analyzed_dates_summary)
        Max 10 points.
        """
        score = 0
        signals = {}
        analyzed_dates = []

        if not important_dates_data or not controlling_brokers:
            return 0, signals, analyzed_dates

        cb_codes = set(b.get('code', '') for b in controlling_brokers)
        if not cb_codes:
            return 0, signals, analyzed_dates

        # Analyze each important date
        bandar_buy_dates = 0
        bandar_sell_dates = 0
        total_dates = 0
        bandar_total_buy_lot = 0
        bandar_total_sell_lot = 0

        for day_data in important_dates_data:
            date_str = day_data.get('date', '')
            date_type = day_data.get('date_type', 'unknown')
            buy_list = day_data.get('buy', [])
            sell_list = day_data.get('sell', [])

            if not buy_list and not sell_list:
                continue

            total_dates += 1

            # Check controlling brokers in this date's buy/sell
            day_bandar_buy = 0
            day_bandar_sell = 0
            day_bandar_buy_lot = 0
            day_bandar_sell_lot = 0

            for b in buy_list:
                code = (b.get('broker') or '').upper()
                if code in cb_codes:
                    nlot = self._parse_broksum_num(b.get('nlot', 0))
                    day_bandar_buy += 1
                    day_bandar_buy_lot += nlot

            for s in sell_list:
                code = (s.get('broker') or '').upper()
                if code in cb_codes:
                    nlot = self._parse_broksum_num(s.get('nlot', 0))
                    day_bandar_sell += 1
                    day_bandar_sell_lot += nlot

            net_bandar = day_bandar_buy_lot - day_bandar_sell_lot
            if net_bandar > 0:
                bandar_buy_dates += 1
            elif net_bandar < 0:
                bandar_sell_dates += 1

            bandar_total_buy_lot += day_bandar_buy_lot
            bandar_total_sell_lot += day_bandar_sell_lot

            analyzed_dates.append({
                'date': date_str,
                'date_type': date_type,
                'bandar_buy_count': day_bandar_buy,
                'bandar_sell_count': day_bandar_sell,
                'bandar_net_lot': round(net_bandar),
            })

        if total_dates == 0:
            return 0, signals, analyzed_dates

        # ---- Scoring ----
        net_total = bandar_total_buy_lot - bandar_total_sell_lot

        # 1. Bandar consistency across important dates (max 5 pts)
        buy_ratio = bandar_buy_dates / total_dates if total_dates > 0 else 0
        if buy_ratio >= 0.8 and net_total > 0:
            score += 5
            signals['impdate_bandar_consistent_buy'] = (
                f"Bandar konsisten BELI di {bandar_buy_dates}/{total_dates} tanggal penting "
                f"(+{bandar_total_buy_lot:,.0f} lot)"
            )
        elif buy_ratio >= 0.6 and net_total > 0:
            score += 3
            signals['impdate_bandar_mostly_buy'] = (
                f"Bandar mayoritas beli di {bandar_buy_dates}/{total_dates} tanggal penting"
            )
        elif buy_ratio >= 0.4:
            score += 1
        elif bandar_sell_dates > bandar_buy_dates and net_total < 0:
            score -= 3
            signals['impdate_bandar_selling'] = (
                f"WARNING: Bandar lebih banyak JUAL di tanggal penting "
                f"({bandar_sell_dates}/{total_dates} hari, -{bandar_total_sell_lot:,.0f} lot)"
            )

        # 2. Volume of bandar activity at important dates (max 5 pts)
        if net_total > 0:
            if bandar_total_buy_lot > 1000:
                score += 5
                signals['impdate_heavy_accum'] = (
                    f"Akumulasi besar di tanggal penting: +{net_total:,.0f} lot net"
                )
            elif bandar_total_buy_lot > 500:
                score += 3
                signals['impdate_moderate_accum'] = (
                    f"Akumulasi sedang di tanggal penting: +{net_total:,.0f} lot net"
                )
            elif bandar_total_buy_lot > 100:
                score += 1

        # Determine overall signal
        if score >= 7:
            imp_signal = 'STRONG_ACCUMULATION'
        elif score >= 4:
            imp_signal = 'ACCUMULATION'
        elif score >= 1:
            imp_signal = 'MILD_ACCUMULATION'
        elif score < 0:
            imp_signal = 'DISTRIBUTION'
        else:
            imp_signal = 'NEUTRAL'

        return max(-3, min(score, 10)), signals, analyzed_dates

    def _score_synergy(self, deep: Dict) -> Tuple[int, Dict]:
        """Score synergy between inventory and transaction chart. Max 10 points."""
        score = 0
        signals = {}

        inv_heavy = deep.get('inv_accum_brokers', 0) >= 3
        inv_clean = deep.get('inv_clean_brokers', 0) > 0 and deep.get('inv_tektok_brokers', 0) == 0
        txn_mm_up = deep.get('txn_mm_trend') in ('UP', 'STRONG_UP')
        txn_foreign_positive = deep.get('txn_foreign_cum', 0) > 0
        txn_inst_positive = deep.get('txn_institution_cum', 0) > 0

        # Inventory accumulation confirmed by MM trend
        if inv_heavy and txn_mm_up:
            score += 5
            signals['synergy_inv_mm'] = "Inventory accumulation confirmed by MM uptrend"

        # Clean inventory + foreign/institution inflow
        if inv_clean and (txn_foreign_positive or txn_inst_positive):
            score += 3
            signals['synergy_clean_flow'] = "Clean accumulation + institutional inflow"

        # Heavy accumulation + low crossing
        if inv_heavy and deep.get('txn_cross_index', 1) < 0.4:
            score += 2
            signals['synergy_clean_accum'] = "Heavy accumulation with low crossing"

        return min(score, 10), signals

    def _score_cross_reference(
        self, ctrl_result: Dict, broker_summary_data: Dict
    ) -> Tuple[int, Dict, Dict]:
        """
        Cross-reference controlling brokers (from inventory) with today's broker summary.
        
        If a controlling broker is buying TODAY → strong confirmation.
        If a controlling broker is selling TODAY → early distribution warning.
        
        Returns: (score, signals, xref_data)
        Max 10 points.
        """
        score = 0
        signals = {}
        xref_data = {
            'buy_count': 0, 'sell_count': 0,
            'buy_lot': 0, 'sell_lot': 0,
            'confirmation': 'NONE'
        }

        cbs = ctrl_result.get('controlling_brokers', [])
        if not cbs:
            return 0, signals, xref_data

        cb_codes = set(b['code'] for b in cbs)

        buy_list = broker_summary_data.get('buy', [])
        sell_list = broker_summary_data.get('sell', [])

        # Check which controlling brokers appear in today's buyers
        bandar_buying = []
        bandar_buy_lot = 0
        for b in buy_list:
            code = b.get('broker', '')
            if code in cb_codes:
                nlot = self._parse_broksum_num(b.get('nlot', 0))
                bandar_buying.append(code)
                bandar_buy_lot += nlot

        # Check which controlling brokers appear in today's sellers
        bandar_selling = []
        bandar_sell_lot = 0
        for s in sell_list:
            code = s.get('broker', '')
            if code in cb_codes:
                nlot = self._parse_broksum_num(s.get('nlot', 0))
                bandar_selling.append(code)
                bandar_sell_lot += nlot

        xref_data['buy_count'] = len(bandar_buying)
        xref_data['sell_count'] = len(bandar_selling)
        xref_data['buy_lot'] = round(bandar_buy_lot)
        xref_data['sell_lot'] = round(bandar_sell_lot)

        # Scoring logic
        net_bandar_lot = bandar_buy_lot - bandar_sell_lot

        if len(bandar_buying) >= 3 and net_bandar_lot > 0:
            score += 10
            confirmation = 'STRONG_BUY'
            codes_str = ', '.join(bandar_buying[:5])
            signals['xref_bandar_strong_buy'] = (
                f"Bandar AKTIF BELI hari ini: {codes_str} "
                f"(+{bandar_buy_lot:,.0f} lot net)"
            )
        elif len(bandar_buying) >= 2 and net_bandar_lot > 0:
            score += 7
            confirmation = 'BUY'
            codes_str = ', '.join(bandar_buying[:5])
            signals['xref_bandar_buying'] = (
                f"Bandar beli hari ini: {codes_str} (+{bandar_buy_lot:,.0f} lot)"
            )
        elif len(bandar_buying) >= 1 and net_bandar_lot > 0:
            score += 4
            confirmation = 'MILD_BUY'
            signals['xref_bandar_mild_buy'] = (
                f"Bandar {bandar_buying[0]} beli hari ini (+{bandar_buy_lot:,.0f} lot)"
            )
        elif len(bandar_selling) >= 3 and net_bandar_lot < 0:
            score -= 5
            confirmation = 'STRONG_SELL'
            codes_str = ', '.join(bandar_selling[:5])
            signals['xref_bandar_strong_sell'] = (
                f"WARNING: Bandar JUAL hari ini: {codes_str} "
                f"(-{bandar_sell_lot:,.0f} lot)"
            )
        elif len(bandar_selling) >= 2 and net_bandar_lot < 0:
            score -= 3
            confirmation = 'SELL'
            codes_str = ', '.join(bandar_selling[:5])
            signals['xref_bandar_selling'] = (
                f"Hati-hati: Bandar jual hari ini: {codes_str} (-{bandar_sell_lot:,.0f} lot)"
            )
        elif len(bandar_selling) >= 1 and net_bandar_lot < 0:
            score -= 1
            confirmation = 'MILD_SELL'
            signals['xref_bandar_mild_sell'] = (
                f"Bandar {bandar_selling[0]} jual hari ini (-{bandar_sell_lot:,.0f} lot)"
            )
        else:
            confirmation = 'NEUTRAL'

        xref_data['confirmation'] = confirmation
        return max(min(score, 10), -5), signals, xref_data

    def _analyze_broker_consistency(
        self, multiday_data: List[Dict], controlling_brokers: List[Dict]
    ) -> Dict:
        """
        Analyze multi-day broker summary to detect consistent buying/selling patterns.
        
        Args:
            multiday_data: List of {date, buy, sell} dicts (most recent first)
            controlling_brokers: List of controlling broker dicts from inventory
            
        Returns:
            Dict with consistency_score, consistent_buyers, consistent_sellers, signals
        """
        result = {
            'days_analyzed': len(multiday_data),
            'consistency_score': 0,
            'consistent_buyers': [],
            'consistent_sellers': [],
            'signals': {}
        }

        if len(multiday_data) < 2:
            return result

        cb_codes = set(b['code'] for b in controlling_brokers) if controlling_brokers else set()
        total_days = len(multiday_data)

        # Count how many days each broker appears as buyer or seller
        broker_buy_days = {}   # code -> count of days appearing as buyer
        broker_sell_days = {}  # code -> count of days appearing as seller
        broker_buy_lots = {}   # code -> total lots bought across days
        broker_sell_lots = {}  # code -> total lots sold across days

        for day_data in multiday_data:
            for b in day_data.get('buy', []):
                code = b.get('broker', '')
                if not code:
                    continue
                nlot = self._parse_broksum_num(b.get('nlot', 0))
                broker_buy_days[code] = broker_buy_days.get(code, 0) + 1
                broker_buy_lots[code] = broker_buy_lots.get(code, 0) + nlot

            for s in day_data.get('sell', []):
                code = s.get('broker', '')
                if not code:
                    continue
                nlot = self._parse_broksum_num(s.get('nlot', 0))
                broker_sell_days[code] = broker_sell_days.get(code, 0) + 1
                broker_sell_lots[code] = broker_sell_lots.get(code, 0) + nlot

        # Identify consistent buyers (appear as buyer >= 60% of days)
        min_days_for_consistent = max(2, int(total_days * 0.6))
        consistent_buyers = []
        for code, days in broker_buy_days.items():
            if days >= min_days_for_consistent:
                consistent_buyers.append({
                    'code': code,
                    'buy_days': days,
                    'total_days': total_days,
                    'total_lot': round(broker_buy_lots.get(code, 0)),
                    'is_bandar': code in cb_codes
                })
        consistent_buyers.sort(key=lambda x: x['total_lot'], reverse=True)

        # Identify consistent sellers
        consistent_sellers = []
        for code, days in broker_sell_days.items():
            if days >= min_days_for_consistent:
                consistent_sellers.append({
                    'code': code,
                    'sell_days': days,
                    'total_days': total_days,
                    'total_lot': round(broker_sell_lots.get(code, 0)),
                    'is_bandar': code in cb_codes
                })
        consistent_sellers.sort(key=lambda x: x['total_lot'], reverse=True)

        result['consistent_buyers'] = consistent_buyers[:8]
        result['consistent_sellers'] = consistent_sellers[:8]

        # Calculate consistency score (0-100)
        # Higher if controlling brokers are consistently buying
        bandar_consistent_buy = sum(1 for b in consistent_buyers if b['is_bandar'])
        bandar_consistent_sell = sum(1 for s in consistent_sellers if s['is_bandar'])
        total_consistent_buy = len(consistent_buyers)

        consistency = 0
        if total_consistent_buy >= 5:
            consistency += 30
        elif total_consistent_buy >= 3:
            consistency += 20
        elif total_consistent_buy >= 1:
            consistency += 10

        if bandar_consistent_buy >= 3:
            consistency += 40
        elif bandar_consistent_buy >= 2:
            consistency += 30
        elif bandar_consistent_buy >= 1:
            consistency += 15

        # Penalize if bandars are consistently selling
        if bandar_consistent_sell >= 2:
            consistency -= 30
        elif bandar_consistent_sell >= 1:
            consistency -= 15

        # Bonus for high day coverage
        if total_days >= 5:
            consistency += 10
        elif total_days >= 3:
            consistency += 5

        # Bonus if more consistent buyers than sellers
        if total_consistent_buy > len(consistent_sellers):
            consistency += 20
        elif total_consistent_buy < len(consistent_sellers):
            consistency -= 20

        result['consistency_score'] = max(0, min(100, consistency))

        # Generate signals
        signals = {}
        if bandar_consistent_buy >= 2:
            codes = ', '.join(b['code'] for b in consistent_buyers if b['is_bandar'])
            signals['consistency_bandar_buy'] = (
                f"Bandar konsisten beli {total_days} hari: {codes}"
            )
        elif bandar_consistent_buy >= 1:
            b = next(x for x in consistent_buyers if x['is_bandar'])
            signals['consistency_bandar_buy'] = (
                f"Bandar {b['code']} konsisten beli {b['buy_days']}/{total_days} hari"
            )

        if bandar_consistent_sell >= 2:
            codes = ', '.join(s['code'] for s in consistent_sellers if s['is_bandar'])
            signals['consistency_bandar_sell'] = (
                f"WARNING: Bandar konsisten jual {total_days} hari: {codes}"
            )

        if result['consistency_score'] >= 70:
            signals['consistency_high'] = (
                f"Pola beli sangat konsisten (score {result['consistency_score']})"
            )
        elif result['consistency_score'] >= 40:
            signals['consistency_moderate'] = (
                f"Pola beli cukup konsisten (score {result['consistency_score']})"
            )

        result['signals'] = signals
        return result

    def _calculate_breakout_probability(
        self, deep: Dict, base_result: Optional[Dict] = None
    ) -> Tuple[int, Dict]:
        """
        Calculate composite breakout probability (0-100) from multiple factors.
        
        Factors (each 0-100, weighted):
        1. Accumulation duration (optimal 2-8 weeks)
        2. Price vs bandar cost (near cost = high probability)
        3. Coordination score
        4. No distribution
        5. Controlling broker count & quality
        6. Institutional backing
        7. Cross-reference confirmation (bandar buying today)
        8. Multi-day consistency
        
        Returns: (probability, factors_dict)
        """
        factors = {}
        weights = {}

        # 1. Accumulation duration (weight 15%)
        accum_start = deep.get('accum_start_date')
        duration_score = 0
        if accum_start:
            try:
                start_dt = datetime.strptime(accum_start, '%Y-%m-%d')
                days_accum = (datetime.now() - start_dt).days
                if 14 <= days_accum <= 56:      # 2-8 weeks = optimal
                    duration_score = 100
                elif 7 <= days_accum < 14:       # 1-2 weeks = early
                    duration_score = 60
                elif 56 < days_accum <= 90:      # 8-13 weeks = getting long
                    duration_score = 70
                elif days_accum > 90:            # >3 months = stale
                    duration_score = 30
                else:                            # <1 week = too early
                    duration_score = 20
            except (ValueError, TypeError):
                duration_score = 0
        factors['accum_duration'] = duration_score
        weights['accum_duration'] = 0.15

        # 2. Price vs bandar cost (weight 20%)
        price_score = 0
        current_price = base_result.get('price', 0) if base_result else 0
        bandar_cost = deep.get('bandar_avg_cost', 0)
        if current_price > 0 and bandar_cost > 0:
            pct_diff = (current_price - bandar_cost) / bandar_cost
            if -0.03 <= pct_diff <= 0.05:
                price_score = 100   # Near cost = best entry
            elif -0.10 <= pct_diff < -0.03:
                price_score = 90    # Below cost = discount
            elif 0.05 < pct_diff <= 0.10:
                price_score = 70    # Slightly above
            elif 0.10 < pct_diff <= 0.20:
                price_score = 40    # Above cost
            elif pct_diff > 0.20:
                price_score = 10    # Far above = risky
            elif pct_diff < -0.10:
                price_score = 50    # Deep discount = might be weak
        factors['price_vs_cost'] = price_score
        weights['price_vs_cost'] = 0.20

        # 3. Coordination (weight 15%)
        coord = deep.get('coordination_score', 0)
        factors['coordination'] = coord  # Already 0-100
        weights['coordination'] = 0.15

        # 4. No distribution (weight 15%)
        dist_alert = deep.get('distribution_alert', 'NONE')
        dist_score = {
            'NONE': 100, 'EARLY': 50, 'MODERATE': 20, 'HEAVY': 0, 'FULL_EXIT': 0
        }.get(dist_alert, 50)
        factors['no_distribution'] = dist_score
        weights['no_distribution'] = 0.15

        # 5. Controlling broker count & quality (weight 10%)
        cbs = deep.get('controlling_brokers', [])
        cb_score = 0
        if len(cbs) >= 5:
            cb_score = 80
        elif len(cbs) >= 3:
            cb_score = 60
        elif len(cbs) >= 1:
            cb_score = 30
        clean_count = sum(1 for b in cbs if b.get('is_clean'))
        if clean_count >= 2:
            cb_score = min(100, cb_score + 20)
        factors['broker_quality'] = cb_score
        weights['broker_quality'] = 0.10

        # 6. Institutional backing (weight 10%)
        inst_score = 0
        inst_net = deep.get('broksum_net_institutional', 0)
        foreign_net = deep.get('broksum_net_foreign', 0)
        if inst_net > 0 and foreign_net > 0:
            inst_score = 100
        elif inst_net > 0:
            inst_score = 70
        elif foreign_net > 0:
            inst_score = 60
        elif inst_net < 0 and foreign_net < 0:
            inst_score = 10
        else:
            inst_score = 30
        factors['institutional'] = inst_score
        weights['institutional'] = 0.10

        # 7. Cross-reference confirmation (weight 10%)
        confirmation = deep.get('bandar_confirmation', 'NONE')
        xref_score = {
            'STRONG_BUY': 100, 'BUY': 80, 'MILD_BUY': 60,
            'NEUTRAL': 40, 'NONE': 30,
            'MILD_SELL': 15, 'SELL': 5, 'STRONG_SELL': 0
        }.get(confirmation, 30)
        factors['today_confirmation'] = xref_score
        weights['today_confirmation'] = 0.10

        # 8. Multi-day consistency (weight 5%)
        consistency = deep.get('broksum_consistency_score', 0)
        factors['multiday_consistency'] = consistency  # Already 0-100
        weights['multiday_consistency'] = 0.05

        # 9. Smart money vs retail divergence (weight 5%)
        sr_div = deep.get('smart_retail_divergence', 0)
        # Convert -100..+100 to 0..100 scale
        sr_factor = max(0, min(100, (sr_div + 100) // 2))
        factors['smart_retail'] = sr_factor
        weights['smart_retail'] = 0.05

        # 10. Volume context (weight 5%)
        vol_score = deep.get('volume_score', 0)
        factors['volume_context'] = min(100, vol_score * 20)  # 0-5 pts → 0-100 scale
        weights['volume_context'] = 0.05

        # 11. MA cross signal (weight 5%)
        ma_cross = deep.get('ma_cross_signal', 'NONE')
        ma_factor = {
            'GOLDEN_CROSS': 100, 'PERFECT_BULLISH': 90, 'BULLISH_ALIGNMENT': 80,
            'CONVERGING': 50, 'NEUTRAL': 40, 'NONE': 40,
            'BEARISH_ALIGNMENT': 10, 'DEATH_CROSS': 0
        }.get(ma_cross, 40)
        factors['ma_cross'] = ma_factor
        weights['ma_cross'] = 0.05

        # 12. Flow velocity/acceleration (weight 10%)
        accel_signal = deep.get('flow_acceleration_signal', 'NONE')
        vel_factor = {
            'STRONG_ACCELERATING': 100, 'ACCELERATING': 80,
            'MILD_ACCELERATING': 60, 'STABLE': 40,
            'MILD_DECELERATING': 20, 'DECELERATING': 5, 'NONE': 30
        }.get(accel_signal, 30)
        factors['flow_velocity'] = vel_factor
        weights['flow_velocity'] = 0.10

        # Calculate weighted average
        total_weight = sum(weights.values())
        if total_weight > 0:
            probability = sum(
                factors[k] * weights[k] for k in factors
            ) / total_weight
        else:
            probability = 0

        return round(probability), factors

    def _calculate_pump_tomorrow_score(
        self, deep: Dict, base_result: Optional[Dict] = None,
        broker_summary_data: Optional[Dict] = None
    ) -> Tuple[int, str, Dict]:
        """
        Calculate "Pump Tomorrow" prediction score (0-100).
        
        Answers: "Apakah saham ini akan pump BESOK?"
        
        7 weighted factors:
        1. Bandar beli hari ini (25%) — bandar_confirmation from cross-reference
        2. Flow acceleration (20%) — MM/Foreign rising sharply last 3 days
        3. Price di zona siap (15%) — near bandar cost, breakout_signal = READY
        4. Volume compression breaking (10%) — price range narrowing then expanding
        5. MA convergence/golden cross (10%) — timing tepat
        6. Institutional fresh entry (10%) — new institutional/foreign in broker summary
        7. Retail capitulation (10%) — retail selling, smart money buying
        
        Returns: (score, signal, factors_dict)
        """
        factors = {}
        weights = {}

        # 1. Bandar beli hari ini (weight 25%)
        confirmation = deep.get('bandar_confirmation', 'NONE')
        bandar_today = {
            'STRONG_BUY': 100, 'BUY': 80, 'MILD_BUY': 55,
            'NEUTRAL': 20, 'NONE': 10,
            'MILD_SELL': 5, 'SELL': 0, 'STRONG_SELL': 0
        }.get(confirmation, 10)
        factors['bandar_beli_hari_ini'] = bandar_today
        weights['bandar_beli_hari_ini'] = 0.25

        # 2. Flow acceleration (weight 20%)
        accel_signal = deep.get('flow_acceleration_signal', 'NONE')
        flow_accel = {
            'STRONG_ACCELERATING': 100, 'ACCELERATING': 80,
            'MILD_ACCELERATING': 55, 'STABLE': 25,
            'MILD_DECELERATING': 10, 'DECELERATING': 0, 'NONE': 15
        }.get(accel_signal, 15)
        # Bonus: check if MM velocity is strongly positive
        vel_mm = deep.get('flow_velocity_mm', 0)
        if vel_mm > 1.0 and flow_accel >= 55:
            flow_accel = min(100, flow_accel + 15)
        factors['flow_acceleration'] = flow_accel
        weights['flow_acceleration'] = 0.20

        # 3. Price di zona siap (weight 15%)
        breakout = deep.get('breakout_signal', 'NONE')
        price_ready = {
            'READY': 100, 'LOADING': 50, 'LAUNCHED': 30,
            'DISTRIBUTING': 0, 'NONE': 20
        }.get(breakout, 20)
        # Refine with price vs bandar cost
        current_price = base_result.get('price', 0) if base_result else 0
        bandar_cost = deep.get('bandar_avg_cost', 0)
        if current_price > 0 and bandar_cost > 0:
            pct_diff = (current_price - bandar_cost) / bandar_cost
            if -0.03 <= pct_diff <= 0.05:
                price_ready = max(price_ready, 95)  # Near cost = best
            elif -0.08 <= pct_diff < -0.03:
                price_ready = max(price_ready, 80)  # Below cost = discount
            elif 0.05 < pct_diff <= 0.12:
                price_ready = max(price_ready, 60)  # Slightly above
        factors['price_zona_siap'] = price_ready
        weights['price_zona_siap'] = 0.15

        # 4. Volume compression breaking (weight 10%)
        vol_signal = deep.get('volume_signal', 'NONE')
        vol_compress = {
            'ACTIVE_BREAKOUT': 100,   # Range expanding + accumulation
            'STEALTH_ACCUM': 85,      # Tight range + heavy accumulation
            'QUIET_ACCUM': 60,        # Relatively quiet + accumulation
            'NEUTRAL': 25,
            'DEAD': 5,
            'DIST_COMPLETE': 10,
            'NONE': 15
        }.get(vol_signal, 15)
        factors['volume_compression'] = vol_compress
        weights['volume_compression'] = 0.10

        # 5. MA convergence/golden cross (weight 10%)
        ma_cross = deep.get('ma_cross_signal', 'NONE')
        ma_timing = {
            'GOLDEN_CROSS': 100, 'PERFECT_BULLISH': 90,
            'BULLISH_ALIGNMENT': 70, 'CONVERGING': 65,
            'NEUTRAL': 25, 'NONE': 20,
            'BEARISH_ALIGNMENT': 5, 'DEATH_CROSS': 0
        }.get(ma_cross, 20)
        factors['ma_timing'] = ma_timing
        weights['ma_timing'] = 0.10

        # 6. Institutional fresh entry (weight 10%)
        inst_fresh = 0
        inst_net = deep.get('broksum_net_institutional', 0)
        foreign_net = deep.get('broksum_net_foreign', 0)
        # Check if institutional/foreign brokers are buying but NOT already controlling brokers
        # (fresh entry = new money coming in)
        cb_codes = set(
            b.get('code', '') for b in deep.get('controlling_brokers', [])
        )
        if broker_summary_data:
            buy_list = broker_summary_data.get('buy', [])
            fresh_inst_count = 0
            fresh_inst_lot = 0
            for b in buy_list:
                code = b.get('broker', '')
                info = self.broker_classes.get(code, {})
                cats = info.get('categories', [])
                if ('institutional' in cats or 'foreign' in cats) and code not in cb_codes:
                    fresh_inst_count += 1
                    fresh_inst_lot += self._parse_broksum_num(b.get('nlot', 0))
            if fresh_inst_count >= 3:
                inst_fresh = 100
            elif fresh_inst_count >= 2:
                inst_fresh = 75
            elif fresh_inst_count >= 1:
                inst_fresh = 50
            elif inst_net > 0 and foreign_net > 0:
                inst_fresh = 40
            elif inst_net > 0 or foreign_net > 0:
                inst_fresh = 25
        else:
            # Fallback to aggregate net values
            if inst_net > 0 and foreign_net > 0:
                inst_fresh = 60
            elif inst_net > 0 or foreign_net > 0:
                inst_fresh = 35
        factors['institutional_fresh_entry'] = inst_fresh
        weights['institutional_fresh_entry'] = 0.10

        # 7. Retail capitulation (weight 10%)
        sr_div = deep.get('smart_retail_divergence', 0)
        # smart_retail_divergence ranges from -100 (bearish) to +100 (bullish)
        # +100 = smart money buying, retail selling (classic pump setup)
        retail_cap = max(0, min(100, (sr_div + 100) // 2))
        # Bonus if daily smart money buying and retail selling
        cum_smart = deep.get('txn_smart_money_cum', 0)
        cum_retail = deep.get('txn_retail_cum_deep', 0)
        if cum_smart > 0 and cum_retail < 0:
            retail_cap = max(retail_cap, 80)
        factors['retail_capitulation'] = retail_cap
        weights['retail_capitulation'] = 0.10

        # Calculate weighted average
        total_weight = sum(weights.values())
        if total_weight > 0:
            score = sum(
                factors[k] * weights[k] for k in factors
            ) / total_weight
        else:
            score = 0

        score = round(score)

        # Determine signal
        if score >= 75:
            signal = 'STRONG_PUMP'
        elif score >= 55:
            signal = 'LIKELY_PUMP'
        elif score >= 40:
            signal = 'POSSIBLE_PUMP'
        elif score >= 25:
            signal = 'LOW_CHANCE'
        else:
            signal = 'UNLIKELY'

        return score, signal, factors

    def _classify_deep_trade_type(
        self, deep: Dict, base_result: Optional[Dict] = None
    ) -> str:
        """Enhanced trade type classification using deep analysis data."""
        deep_score = deep.get('deep_score', 0)
        signals = deep.get('deep_signals', {})
        base_score = base_result.get('total_score', 0) if base_result else 0
        combined_score = base_score + deep_score

        is_swing = False
        is_intraday = False

        # SWING: Strong accumulation + institutional backing + MM uptrend
        inv_strong = deep.get('inv_accum_brokers', 0) >= 3
        inv_clean = deep.get('inv_clean_brokers', 0) > 0
        mm_up = deep.get('txn_mm_trend') in ('UP', 'STRONG_UP')
        foreign_in = deep.get('txn_foreign_cum', 0) > 0
        inst_in = deep.get('txn_institution_cum', 0) > 0

        if combined_score >= 70 and inv_strong and mm_up:
            is_swing = True
        elif combined_score >= 60 and (foreign_in or inst_in) and inv_clean:
            is_swing = True
        elif deep_score >= 40 and inv_strong:
            is_swing = True
        elif 'synergy_inv_mm' in signals:
            is_swing = True

        # INTRADAY: Recent positive daily flows + volume
        daily_mm_pos = _safe_float(deep.get('txn_mm_cum', 0)) > 0
        base_intraday = base_result.get('trade_type', '') in ('INTRADAY', 'BOTH') if base_result else False

        if base_intraday and deep_score >= 15:
            is_intraday = True
        elif daily_mm_pos and deep.get('inv_accum_brokers', 0) >= 1:
            is_intraday = True
        elif combined_score >= 60 and daily_mm_pos:
            is_intraday = True

        # Distribution override: if bandars are heavily distributing, downgrade
        dist_alert = deep.get('distribution_alert', 'NONE')
        if dist_alert in ('HEAVY', 'FULL_EXIT'):
            return "SELL"
        elif dist_alert == 'MODERATE':
            # Moderate distribution: downgrade swing to watch
            if is_swing and not is_intraday:
                return "WATCH"

        if is_swing and is_intraday:
            return "BOTH"
        elif is_swing:
            return "SWING"
        elif is_intraday:
            return "INTRADAY"
        elif combined_score >= 40:
            return "WATCH"
        else:
            return "—"

    # ==================== CONTROLLING BROKER & ACCUMULATION DETECTION ====================

    def detect_controlling_brokers(
        self,
        inventory_data: List[Dict],
        price_series: Optional[List[Dict]] = None,
        min_brokers: int = 3
    ) -> Dict:
        """
        Detect controlling brokers (bandars) from inventory data + price series.
        
        Algorithm:
        1. Rank brokers by absolute cumulative net lot
        2. Select top N (>= min_brokers) with significant positions (> 10% of largest)
        3. For each controlling broker, calculate estimated avg buy price using timeseries + price
        4. Detect coordinated accumulation (multiple brokers turning within 5 trading days)
        5. Classify current phase: ACCUMULATION / HOLDING / MARKUP / DISTRIBUTION
        
        Returns dict with controlling_brokers, accum_start_date, accum_phase, bandar_avg_cost, etc.
        """
        result = {
            'controlling_brokers': [],
            'accum_start_date': None,
            'accum_phase': 'UNKNOWN',
            'bandar_avg_cost': 0,
            'bandar_total_lot': 0,
            'coordination_score': 0,      # 0-100: how coordinated the accumulation is
            'phase_confidence': 'LOW',
            'breakout_signal': 'NONE',     # NONE / LOADING / READY / LAUNCHED / DISTRIBUTING
        }

        if not inventory_data:
            return result

        # Build price lookup dict {date_str: close_price}
        price_map = {}
        if price_series:
            for p in price_series:
                d = p.get('date', '')
                c = p.get('close', 0)
                if d and c:
                    price_map[d] = c

        # ---- Step 1: Rank brokers by absolute net lot ----
        brokers_with_ts = []
        for b in inventory_data:
            code = b.get('broker_code') or b.get('code', '')
            final_lot = b.get('final_net_lot') or b.get('finalNetLot') or 0
            is_accum = b.get('is_accumulating') or b.get('isAccumulating') or False
            is_clean = b.get('is_clean') or b.get('isClean') or False
            is_tektok = b.get('is_tektok') or b.get('isTektok') or False
            ts = b.get('timeSeries') or b.get('time_series') or []

            brokers_with_ts.append({
                'code': code,
                'final_lot': final_lot,
                'abs_lot': abs(final_lot),
                'is_accum': is_accum if isinstance(is_accum, bool) else final_lot > 0,
                'is_clean': bool(is_clean),
                'is_tektok': bool(is_tektok),
                'ts': ts,
            })

        # Sort by absolute lot descending
        brokers_with_ts.sort(key=lambda x: x['abs_lot'], reverse=True)

        if not brokers_with_ts:
            return result

        # ---- Step 2: Select controlling brokers (top N with significant positions) ----
        largest_lot = brokers_with_ts[0]['abs_lot']
        threshold = largest_lot * 0.10  # Must be at least 10% of the largest

        controlling = []
        for b in brokers_with_ts:
            if b['abs_lot'] >= threshold and b['is_accum']:
                controlling.append(b)
            if len(controlling) >= 8:  # cap at 8
                break

        # If we don't have enough accumulators, relax and take top N by abs lot
        if len(controlling) < min_brokers:
            accum_only = [b for b in brokers_with_ts if b['is_accum']]
            controlling = accum_only[:max(min_brokers, len(accum_only))]

        if not controlling:
            return result

        # ---- Step 3: For each controlling broker, calculate cost basis and turning point ----
        turn_dates = []
        total_weighted_cost = 0
        total_buy_lots = 0

        for cb in controlling:
            ts = cb['ts']
            if not ts or len(ts) < 2:
                cb['avg_buy_price'] = 0
                cb['turn_date'] = None
                cb['accum_lots'] = cb['abs_lot']
                cb['avg_daily_last10'] = 0
                cb['peak_lot'] = cb['abs_lot']
                cb['peak_date'] = None
                cb['distribution_pct'] = 0.0
                continue

            # Extract timeseries values
            values = []
            dates = []
            for point in ts:
                v = point.get('cumNetLot') or point.get('cum_net_lot') or 0
                d = point.get('date', '')
                values.append(v)
                dates.append(d)

            # Find turning point (minimum value for accumulating broker)
            min_val = values[0]
            min_idx = 0
            for j in range(len(values)):
                if values[j] < min_val:
                    min_val = values[j]
                    min_idx = j

            cb['turn_date'] = dates[min_idx] if min_idx < len(dates) else None
            if cb['turn_date']:
                turn_dates.append(cb['turn_date'])

            # Calculate estimated avg buy price from timeseries + price
            broker_cost = 0
            broker_buy_lots = 0
            broker_sell_lots = 0
            for j in range(1, len(values)):
                lot_change = values[j] - values[j - 1]
                price = price_map.get(dates[j], 0)
                if price == 0 and j > 0:
                    price = price_map.get(dates[j - 1], 0)

                if lot_change > 0 and price > 0:
                    broker_cost += lot_change * price
                    broker_buy_lots += lot_change
                elif lot_change < 0:
                    broker_sell_lots += abs(lot_change)

            avg_buy = round(broker_cost / broker_buy_lots) if broker_buy_lots > 0 else 0
            cb['avg_buy_price'] = avg_buy
            cb['total_buy_lots'] = round(broker_buy_lots)
            cb['total_sell_lots'] = round(broker_sell_lots)
            cb['accum_lots'] = round(broker_buy_lots - broker_sell_lots)

            # Weighted contribution to overall bandar cost
            if avg_buy > 0 and broker_buy_lots > 0:
                total_weighted_cost += broker_cost
                total_buy_lots += broker_buy_lots

            # Peak lot detection: find the maximum cumulative net lot (peak ownership)
            peak_val = max(values)
            peak_idx = values.index(peak_val)
            cb['peak_lot'] = round(peak_val)
            cb['peak_date'] = dates[peak_idx] if peak_idx < len(dates) else None

            # Distribution percentage: how much has been sold from peak
            current_val = values[-1] if values else 0
            if peak_val > 0:
                cb['distribution_pct'] = round((peak_val - current_val) / peak_val * 100, 1)
            else:
                cb['distribution_pct'] = 0.0

            # Last 10 days avg daily change (momentum indicator)
            n = len(values)
            last10_changes = []
            for j in range(max(n - 10, 1), n):
                last10_changes.append(values[j] - values[j - 1])
            cb['avg_daily_last10'] = round(sum(last10_changes) / len(last10_changes)) if last10_changes else 0

        # ---- Step 4: Detect coordination (turn dates clustering) ----
        coordination = 0
        if len(turn_dates) >= 2:
            # Sort turn dates and check max spread
            sorted_turns = sorted(turn_dates)
            try:
                date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_turns if d]
                if len(date_objs) >= 2:
                    spread_days = (date_objs[-1] - date_objs[0]).days
                    if spread_days <= 5:
                        coordination = 100
                    elif spread_days <= 10:
                        coordination = 80
                    elif spread_days <= 20:
                        coordination = 60
                    elif spread_days <= 40:
                        coordination = 40
                    else:
                        coordination = 20
            except (ValueError, TypeError):
                coordination = 0

        # ---- Step 5: Classify accumulation phase ----
        # Based on majority of controlling brokers' recent momentum
        phase = 'UNKNOWN'
        phase_confidence = 'LOW'
        breakout_signal = 'NONE'

        active_count = 0
        holding_count = 0
        selling_count = 0
        bandar_avg_cost = round(total_weighted_cost / total_buy_lots) if total_buy_lots > 0 else 0

        for cb in controlling:
            avg_d = cb.get('avg_daily_last10', 0)
            if avg_d > 50:       # actively buying
                active_count += 1
            elif avg_d >= -50:   # flat / holding
                holding_count += 1
            else:                # selling
                selling_count += 1

        total_ctrl = len(controlling)
        if total_ctrl > 0:
            if active_count > total_ctrl * 0.5:
                phase = 'ACCUMULATION'
                phase_confidence = 'HIGH' if active_count > total_ctrl * 0.7 else 'MEDIUM'
                breakout_signal = 'LOADING'
            elif holding_count > total_ctrl * 0.5:
                phase = 'HOLDING'
                phase_confidence = 'HIGH' if holding_count > total_ctrl * 0.7 else 'MEDIUM'
                # Check if price is near bandar cost = READY to break out
                if bandar_avg_cost > 0 and price_map:
                    latest_price = list(price_map.values())[-1] if price_map else 0
                    if latest_price > 0 and bandar_avg_cost > 0:
                        price_vs_cost = (latest_price - bandar_avg_cost) / bandar_avg_cost
                        if -0.05 <= price_vs_cost <= 0.10:
                            breakout_signal = 'READY'
                        elif price_vs_cost > 0.15:
                            breakout_signal = 'LAUNCHED'
                        else:
                            breakout_signal = 'LOADING'
            elif selling_count > total_ctrl * 0.5:
                phase = 'DISTRIBUTION'
                phase_confidence = 'HIGH' if selling_count > total_ctrl * 0.7 else 'MEDIUM'
                breakout_signal = 'DISTRIBUTING'
            else:
                phase = 'MIXED'
                phase_confidence = 'LOW'

        # ---- Step 6: Distribution detection (peak vs current lot analysis) ----
        # Aggregate peak lot across all controlling brokers
        bandar_peak_lot = sum(cb.get('peak_lot', 0) for cb in controlling)
        bandar_current_lot = sum(max(cb.get('final_lot', 0), 0) for cb in controlling)

        if bandar_peak_lot > 0:
            bandar_distribution_pct = round(
                (bandar_peak_lot - bandar_current_lot) / bandar_peak_lot * 100, 1
            )
        else:
            bandar_distribution_pct = 0.0

        # Count brokers by distribution severity
        heavy_dist_count = sum(1 for cb in controlling if cb.get('distribution_pct', 0) >= 50)
        moderate_dist_count = sum(1 for cb in controlling if 25 <= cb.get('distribution_pct', 0) < 50)
        early_dist_count = sum(1 for cb in controlling if 10 <= cb.get('distribution_pct', 0) < 25)

        # Determine distribution alert level
        distribution_alert = 'NONE'
        if bandar_distribution_pct >= 80:
            distribution_alert = 'FULL_EXIT'     # bandar almost fully exited
        elif bandar_distribution_pct >= 50 or heavy_dist_count >= 2:
            distribution_alert = 'HEAVY'         # >50% sold from peak - BUANG BARANG
        elif bandar_distribution_pct >= 25 or (heavy_dist_count >= 1 and moderate_dist_count >= 1):
            distribution_alert = 'MODERATE'      # significant selling
        elif bandar_distribution_pct >= 10 or moderate_dist_count >= 1:
            distribution_alert = 'EARLY'         # early signs of distribution
        # else: NONE

        # Override phase/breakout_signal when heavy distribution detected
        if distribution_alert in ('HEAVY', 'FULL_EXIT'):
            phase = 'DISTRIBUTION'
            phase_confidence = 'HIGH'
            breakout_signal = 'DISTRIBUTING'
        elif distribution_alert == 'MODERATE' and phase != 'ACCUMULATION':
            if phase != 'DISTRIBUTION':
                phase = 'DISTRIBUTION'
                phase_confidence = 'MEDIUM'
            breakout_signal = 'DISTRIBUTING'

        # Earliest accumulation start date
        accum_start = min(turn_dates) if turn_dates else None

        # ---- Build result ----
        result['controlling_brokers'] = [
            {
                'code': cb['code'],
                'net_lot': round(cb['final_lot']),
                'avg_buy_price': cb.get('avg_buy_price', 0),
                'total_buy_lots': cb.get('total_buy_lots', 0),
                'total_sell_lots': cb.get('total_sell_lots', 0),
                'is_clean': cb['is_clean'],
                'is_tektok': cb['is_tektok'],
                'turn_date': cb.get('turn_date'),
                'avg_daily_last10': cb.get('avg_daily_last10', 0),
                'broker_class': self.broker_classes.get(cb['code'], {}).get('name', ''),
                'peak_lot': cb.get('peak_lot', 0),
                'peak_date': cb.get('peak_date'),
                'distribution_pct': cb.get('distribution_pct', 0.0),
            }
            for cb in controlling
        ]
        result['accum_start_date'] = accum_start
        result['accum_phase'] = phase
        result['bandar_avg_cost'] = bandar_avg_cost
        result['bandar_total_lot'] = round(total_buy_lots)
        result['coordination_score'] = coordination
        result['phase_confidence'] = phase_confidence
        result['breakout_signal'] = breakout_signal
        result['bandar_peak_lot'] = round(bandar_peak_lot)
        result['bandar_distribution_pct'] = bandar_distribution_pct
        result['distribution_alert'] = distribution_alert

        return result

    def _score_controlling_brokers(self, ctrl_result: Dict, base_result: Optional[Dict] = None) -> Tuple[int, Dict]:
        """
        Score the controlling broker analysis. Max 30 points (replaces old inventory scoring).
        
        Scoring breakdown:
        - Controlling broker count & quality: max 8 pts
        - Coordination score: max 6 pts
        - Phase & breakout signal: max 8 pts
        - Cost basis vs current price: max 8 pts
        """
        score = 0
        signals = {}

        cbs = ctrl_result.get('controlling_brokers', [])
        phase = ctrl_result.get('accum_phase', 'UNKNOWN')
        breakout = ctrl_result.get('breakout_signal', 'NONE')
        coordination = ctrl_result.get('coordination_score', 0)
        bandar_cost = ctrl_result.get('bandar_avg_cost', 0)
        accum_start = ctrl_result.get('accum_start_date')

        if not cbs:
            return 0, signals

        # 1. Controlling broker count & quality (max 8 pts)
        clean_count = sum(1 for b in cbs if b.get('is_clean'))
        tektok_count = sum(1 for b in cbs if b.get('is_tektok'))

        if len(cbs) >= 5:
            score += 5
        elif len(cbs) >= 3:
            score += 3
        elif len(cbs) >= 1:
            score += 1

        if clean_count >= 2 and tektok_count == 0:
            score += 3
            signals['ctrl_clean'] = f"{clean_count} clean controlling brokers"
        elif clean_count >= 1:
            score += 1

        signals['ctrl_count'] = f"{len(cbs)} controlling brokers identified"

        # 2. Coordination score (max 6 pts)
        if coordination >= 80:
            score += 6
            signals['ctrl_coordinated'] = f"Highly coordinated accumulation (score {coordination})"
        elif coordination >= 60:
            score += 4
            signals['ctrl_moderate_coord'] = f"Moderate coordination (score {coordination})"
        elif coordination >= 40:
            score += 2

        # 3. Phase & breakout signal (max 8 pts)
        if phase == 'ACCUMULATION':
            score += 4
            signals['ctrl_accumulating'] = "Bandars actively accumulating"
        elif phase == 'HOLDING':
            score += 3
            signals['ctrl_holding'] = "Bandars holding positions (waiting)"

        if breakout == 'READY':
            score += 4
            signals['ctrl_ready'] = "Price near bandar cost basis - breakout potential HIGH"
        elif breakout == 'LOADING':
            score += 2
            signals['ctrl_loading'] = "Accumulation in progress"
        elif breakout == 'LAUNCHED':
            score += 2
            signals['ctrl_launched'] = "Price above bandar cost - already running"
        elif breakout == 'DISTRIBUTING':
            signals['ctrl_distributing'] = "WARNING: Bandars distributing (selling)"

        # 4. Cost basis vs current price (max 8 pts)
        current_price = base_result.get('price', 0) if base_result else 0
        if current_price > 0 and bandar_cost > 0:
            price_vs_cost = (current_price - bandar_cost) / bandar_cost

            if -0.03 <= price_vs_cost <= 0.05:
                score += 8
                signals['ctrl_near_cost'] = f"Price near bandar avg cost ({bandar_cost:,.0f}) - excellent entry"
            elif -0.10 <= price_vs_cost < -0.03:
                score += 6
                signals['ctrl_below_cost'] = f"Price BELOW bandar cost ({bandar_cost:,.0f}) - discount zone"
            elif 0.05 < price_vs_cost <= 0.15:
                score += 4
                signals['ctrl_above_cost'] = f"Price slightly above bandar cost ({bandar_cost:,.0f})"
            elif price_vs_cost > 0.15:
                score += 1
                signals['ctrl_far_above'] = f"Price {price_vs_cost:.0%} above bandar cost ({bandar_cost:,.0f})"

        # 5. Distribution penalty (NEGATIVE scoring)
        dist_alert = ctrl_result.get('distribution_alert', 'NONE')
        dist_pct = ctrl_result.get('bandar_distribution_pct', 0)
        peak_lot = ctrl_result.get('bandar_peak_lot', 0)

        if dist_alert == 'FULL_EXIT':
            score -= 20
            signals['ctrl_full_exit'] = f"JUAL! Bandar sudah keluar {dist_pct:.0f}% dari puncak ({peak_lot:,} lot)"
        elif dist_alert == 'HEAVY':
            score -= 15
            signals['ctrl_heavy_dist'] = f"BUANG BARANG! Bandar distribusi {dist_pct:.0f}% dari puncak ({peak_lot:,} lot)"
        elif dist_alert == 'MODERATE':
            score -= 8
            signals['ctrl_moderate_dist'] = f"Hati-hati: Bandar mulai distribusi {dist_pct:.0f}% dari puncak"
        elif dist_alert == 'EARLY':
            score -= 3
            signals['ctrl_early_dist'] = f"Perhatikan: Early distribution {dist_pct:.0f}% dari puncak"

        # Per-broker distribution details
        heavy_brokers = [
            b for b in cbs if b.get('distribution_pct', 0) >= 50
        ]
        if heavy_brokers:
            codes = ', '.join(b['code'] for b in heavy_brokers)
            signals['ctrl_brokers_selling'] = f"Broker sudah jual >50% dari peak: {codes}"

        # Accumulation start date signal
        if accum_start:
            signals['ctrl_accum_start'] = f"Accumulation started: {accum_start}"

        # 6. Accumulation Duration Scoring (max 5 pts)
        if accum_start:
            try:
                start_dt = datetime.strptime(accum_start, '%Y-%m-%d')
                days_accum = (datetime.now() - start_dt).days
                if 14 <= days_accum <= 56:       # 2-8 weeks = optimal
                    score += 5
                    signals['accum_duration_optimal'] = f"Akumulasi {days_accum} hari (2-8 minggu, optimal)"
                elif 7 <= days_accum < 14:        # 1-2 weeks = early
                    score += 2
                    signals['accum_duration_early'] = f"Akumulasi baru {days_accum} hari (terlalu dini)"
                elif 56 < days_accum <= 90:       # 8-13 weeks = getting long
                    score += 3
                    signals['accum_duration_long'] = f"Akumulasi {days_accum} hari (mulai lama)"
                elif days_accum > 90:             # >3 months = stale
                    score += 0
                    signals['accum_duration_stale'] = (
                        f"Akumulasi sudah {days_accum} hari (>3 bulan, mungkin sudah distribusi diam-diam)"
                    )
                else:                             # <1 week
                    score += 1
                    signals['accum_duration_very_early'] = f"Akumulasi baru {days_accum} hari"
            except (ValueError, TypeError):
                pass

        return min(max(score, -10), 35), signals  # Allow negative but cap at -10, max 35

    def _score_concentration_risk(self, ctrl_result: Dict) -> Tuple[int, Dict]:
        """
        Detect concentration risk: if 1 broker holds >50% of total controlling lots.
        
        Returns penalty score (0 or negative) and signals dict.
        Internal keys _conc_broker, _conc_pct, _conc_risk are used to pass data back.
        """
        score = 0
        signals = {}

        cbs = ctrl_result.get('controlling_brokers', [])
        if not cbs or len(cbs) < 2:
            signals['_conc_broker'] = None
            signals['_conc_pct'] = 0.0
            signals['_conc_risk'] = 'NONE'
            return 0, signals

        total_lot = sum(abs(cb.get('net_lot', 0)) for cb in cbs)
        if total_lot <= 0:
            signals['_conc_broker'] = None
            signals['_conc_pct'] = 0.0
            signals['_conc_risk'] = 'NONE'
            return 0, signals

        # Find broker with highest share
        max_broker = max(cbs, key=lambda cb: abs(cb.get('net_lot', 0)))
        max_lot = abs(max_broker.get('net_lot', 0))
        max_pct = (max_lot / total_lot) * 100

        signals['_conc_broker'] = max_broker.get('code', '')
        signals['_conc_pct'] = round(max_pct, 1)

        if max_pct >= 60:
            score = -5
            signals['_conc_risk'] = 'HIGH'
            signals['conc_high_risk'] = (
                f"RISIKO TINGGI: {max_broker['code']} menguasai {max_pct:.0f}% lot bandar "
                f"(single-entity risk)"
            )
        elif max_pct >= 50:
            score = -3
            signals['_conc_risk'] = 'HIGH'
            signals['conc_high_risk'] = (
                f"Konsentrasi tinggi: {max_broker['code']} menguasai {max_pct:.0f}% lot bandar"
            )
        elif max_pct >= 40:
            score = -1
            signals['_conc_risk'] = 'MEDIUM'
            signals['conc_medium_risk'] = (
                f"Konsentrasi sedang: {max_broker['code']} menguasai {max_pct:.0f}% lot bandar"
            )
        else:
            signals['_conc_risk'] = 'LOW'

        return score, signals

    def _score_smart_retail_divergence(self, txn: Dict) -> Tuple[int, Dict]:
        """
        Score Smart Money vs Retail divergence from transaction chart.

        Enhanced scoring based on:
        1. Classic divergence patterns (direction)
        2. Magnitude ratio (how extreme is the divergence)
        3. Historical context (compare to week-ago baseline)

        Classic signals:
        - Smart money accumulating + retail selling = strong bullish (max 5 pts)
        - Smart money selling + retail buying = bearish trap warning

        Returns: (score, signals)
        Max 5 points.
        """
        score = 0
        signals = {}

        cum_smart = _safe_float(txn.get('cum_smart'))
        cum_retail = _safe_float(txn.get('cum_retail'))
        daily_smart = _safe_float(txn.get('daily_smart'))
        daily_retail = _safe_float(txn.get('daily_retail'))

        # Historical data for context
        smart_week_ago = _safe_float(txn.get('cum_smart_week_ago'))
        retail_week_ago = _safe_float(txn.get('cum_retail_week_ago'))

        # Skip if no meaningful data
        if cum_smart == 0 and cum_retail == 0:
            return 0, signals

        # ---- MAGNITUDE-BASED DIVERGENCE SCORING ----
        divergence_ratio = 0
        if abs(cum_retail) > 0:
            divergence_ratio = abs(cum_smart / cum_retail)

        # Classic divergence: smart money accumulating, retail selling
        if cum_smart > 0 and cum_retail < 0:
            # Base score + magnitude bonus
            base_score = 3
            # Strong divergence when smart > 2x retail magnitude
            if divergence_ratio >= 2.0:
                base_score = 5
                signals['sr_strong_divergence'] = (
                    f"Smart money ({cum_smart:+.1f}B) > 2x retail magnitude ({abs(cum_retail):.1f}B) "
                    f"= divergensi sangat kuat"
                )
            elif divergence_ratio >= 1.5:
                base_score = 4
                signals['sr_moderate_divergence'] = (
                    f"Smart money ({cum_smart:+.1f}B) vs retail ({cum_retail:+.1f}B) "
                    f"= divergensi moderat ({divergence_ratio:.1f}x)"
                )
            else:
                signals['sr_classic_bullish'] = (
                    f"Smart money akumulasi ({cum_smart:+.1f}B) vs retail distribusi ({cum_retail:+.1f}B)"
                )
            score += base_score

        # Both accumulating (broad buying)
        elif cum_smart > 0 and cum_retail > 0:
            score += 2
            signals['sr_broad_buying'] = (
                f"Smart money ({cum_smart:+.1f}B) & retail ({cum_retail:+.1f}B) sama-sama beli"
            )

        # Bearish divergence: smart money selling, retail buying (retail trap)
        elif cum_smart < 0 and cum_retail > 0:
            score -= 2
            if divergence_ratio >= 2.0:
                signals['sr_strong_retail_trap'] = (
                    f"WARNING: Retail buying ({cum_retail:+.1f}B) > 2x smart selling ({abs(cum_smart):.1f}B) "
                    f"= jebakan retail sangat kuat"
                )
            else:
                signals['sr_retail_trap'] = (
                    f"WARNING: Smart money jual ({cum_smart:+.1f}B) tapi retail beli ({cum_retail:+.1f}B) "
                    f"= potensi jebakan retail"
                )

        # Both selling
        elif cum_smart < 0 and cum_retail < 0:
            signals['sr_broad_selling'] = (
                f"Smart money ({cum_smart:+.1f}B) & retail ({cum_retail:+.1f}B) sama-sama jual"
            )

        # ---- HISTORICAL CONTEXT ----
        if smart_week_ago != 0 or retail_week_ago != 0:
            # Calculate historical divergence
            hist_divergence = 0
            if abs(retail_week_ago) > 0:
                hist_divergence = abs(smart_week_ago / retail_week_ago)

            current_divergence = divergence_ratio if divergence_ratio > 0 else 0

            # Compare current vs historical
            if current_divergence > hist_divergence * 1.5 and cum_smart > 0 and cum_retail < 0:
                # Divergence is strengthening significantly
                if score < 5:
                    score = min(score + 1, 5)
                signals['sr_divergence_strengthening'] = (
                    f"Divergensi memperkuat dari minggu lalu ({hist_divergence:.1f}x → {current_divergence:.1f}x)"
                )
            elif current_divergence < hist_divergence * 0.5 and cum_smart > 0 and cum_retail < 0:
                # Divergence is weakening
                signals['sr_divergence_weakening'] = (
                    f"Divergensi melemah dari minggu lalu ({hist_divergence:.1f}x → {current_divergence:.1f}x)"
                )

        # Daily momentum bonus (only if cumulative already shows divergence)
        if daily_smart > 0 and daily_retail < 0 and cum_smart > 0:
            if score < 5:
                score = min(score + 1, 5)
            signals['sr_daily_divergence'] = (
                f"Hari ini: smart money beli ({daily_smart:+.1f}B), retail jual ({daily_retail:+.1f}B)"
            )

        # ---- DIVERGENCE METRICS ----
        if cum_smart != 0 or cum_retail != 0:
            # Standardized divergence score (-100 to +100)
            # Positive = smart buying & retail selling (bullish)
            # Negative = smart selling & retail buying (bearish)
            total_abs = abs(cum_smart) + abs(cum_retail)
            if total_abs > 0:
                divergence = int(((cum_smart - cum_retail) / total_abs) * 100)
                signals['_sr_divergence'] = max(-100, min(100, divergence))
                signals['_sr_divergence_ratio'] = round(divergence_ratio, 2)
            else:
                signals['_sr_divergence'] = 0
                signals['_sr_divergence_ratio'] = 0
        else:
            signals['_sr_divergence'] = 0
            signals['_sr_divergence_ratio'] = 0

        return max(-2, min(score, 5)), signals

    def _score_volume_context(
        self, price_series: List[Dict], deep: Dict
    ) -> Tuple[int, Dict]:
        """
        Score volume context using price series data.
        
        Detects:
        - Price compression + heavy accumulation = stealth accumulation (bullish)
        - Price expansion + accumulation = active breakout
        - Price flat + no accumulation = dead stock
        
        Uses price range analysis since raw volume isn't in price_series.
        
        Returns: (score, signals)
        Max 5 points.
        """
        score = 0
        signals = {}

        if not price_series or len(price_series) < 10:
            signals['_vol_signal'] = 'NONE'
            return 0, signals

        # Calculate recent vs historical price range (volatility proxy)
        n = len(price_series)
        recent_n = min(10, n // 3)  # Last ~10 days or 1/3 of data
        hist_n = n - recent_n

        # Recent price range
        recent = price_series[-recent_n:]
        recent_highs = [p.get('high', 0) or p.get('close', 0) for p in recent]
        recent_lows = [p.get('low', 0) or p.get('close', 0) for p in recent]
        recent_closes = [p.get('close', 0) for p in recent]

        # Historical price range
        hist = price_series[:hist_n]
        hist_highs = [p.get('high', 0) or p.get('close', 0) for p in hist]
        hist_lows = [p.get('low', 0) or p.get('close', 0) for p in hist]

        if not recent_closes or not hist_highs:
            signals['_vol_signal'] = 'NONE'
            return 0, signals

        # Average daily range (high-low) as % of close
        avg_recent_range = 0
        avg_hist_range = 0

        for i, p in enumerate(recent):
            h = recent_highs[i]
            l = recent_lows[i]
            c = recent_closes[i]
            if c > 0 and h > 0 and l > 0:
                avg_recent_range += (h - l) / c

        for i, p in enumerate(hist):
            h = hist_highs[i]
            l = hist_lows[i]
            c = p.get('close', 0)
            if c > 0 and h > 0 and l > 0:
                avg_hist_range += (h - l) / c

        avg_recent_range = avg_recent_range / len(recent) if recent else 0
        avg_hist_range = avg_hist_range / len(hist) if hist else 0

        # Get accumulation context
        accum_brokers = deep.get('inv_accum_brokers', 0)
        accum_lot = deep.get('inv_total_accum_lot', 0)
        is_accumulating = accum_brokers >= 3 and accum_lot > 0

        # Price compression ratio (< 1 means recent range is tighter)
        compression_ratio = avg_recent_range / avg_hist_range if avg_hist_range > 0 else 1.0

        if compression_ratio < 0.6 and is_accumulating:
            # Tight range + heavy accumulation = stealth accumulation
            score += 5
            signals['vol_stealth_accum'] = (
                f"Harga menyempit ({compression_ratio:.1%}x range normal) "
                f"+ {accum_brokers} broker akumulasi = stealth accumulation"
            )
            signals['_vol_signal'] = 'STEALTH_ACCUM'
        elif compression_ratio < 0.8 and is_accumulating:
            score += 3
            signals['vol_quiet_accum'] = (
                f"Harga relatif tenang ({compression_ratio:.1%}x range normal) "
                f"+ akumulasi aktif"
            )
            signals['_vol_signal'] = 'QUIET_ACCUM'
        elif compression_ratio > 1.5 and is_accumulating:
            score += 2
            signals['vol_active_breakout'] = (
                f"Range harga melebar ({compression_ratio:.1%}x normal) "
                f"+ akumulasi = potensi breakout aktif"
            )
            signals['_vol_signal'] = 'ACTIVE_BREAKOUT'
        elif compression_ratio < 0.5 and not is_accumulating:
            signals['vol_dead_stock'] = (
                f"Harga sangat sempit ({compression_ratio:.1%}x normal) "
                f"tanpa akumulasi = saham mati"
            )
            signals['_vol_signal'] = 'DEAD'
        elif compression_ratio > 2.0 and not is_accumulating:
            signals['vol_distribution_complete'] = (
                f"Volatilitas tinggi ({compression_ratio:.1%}x normal) "
                f"tanpa akumulasi = distribusi mungkin selesai"
            )
            signals['_vol_signal'] = 'DIST_COMPLETE'
        else:
            signals['_vol_signal'] = 'NEUTRAL'

        return min(score, 5), signals

    def _score_ma_cross(
        self, price_series: List[Dict]
    ) -> Tuple[int, Dict]:
        """
        Detect Golden Cross / Death Cross from price series.
        
        Calculates MA5, MA20, MA50 from close prices and detects:
        - Golden Cross: MA5 crosses above MA20 (bullish)
        - Death Cross: MA5 crosses below MA20 (bearish)
        - Bullish Alignment: MA5 > MA20 > MA50 (strong uptrend)
        - Bearish Alignment: MA5 < MA20 < MA50 (strong downtrend)
        
        Returns: (score, signals)
        Max 5 points, min -3 points.
        """
        score = 0
        signals = {}

        if not price_series or len(price_series) < 50:
            signals['_ma_cross_signal'] = 'NONE'
            return 0, signals

        closes = [p.get('close', 0) for p in price_series if p.get('close', 0) > 0]
        if len(closes) < 50:
            signals['_ma_cross_signal'] = 'NONE'
            return 0, signals

        def calc_sma(data: list, period: int) -> list:
            """Calculate Simple Moving Average."""
            result = []
            for i in range(len(data)):
                if i < period - 1:
                    result.append(None)
                else:
                    result.append(sum(data[i - period + 1:i + 1]) / period)
            return result

        ma5 = calc_sma(closes, 5)
        ma20 = calc_sma(closes, 20)
        ma50 = calc_sma(closes, 50)

        # Get current and previous values (last 2 valid points)
        curr_ma5 = ma5[-1]
        curr_ma20 = ma20[-1]
        curr_ma50 = ma50[-1]
        prev_ma5 = ma5[-2] if len(ma5) >= 2 else None
        prev_ma20 = ma20[-2] if len(ma20) >= 2 else None

        if curr_ma5 is None or curr_ma20 is None or curr_ma50 is None:
            signals['_ma_cross_signal'] = 'NONE'
            return 0, signals

        current_price = closes[-1]

        # Detect crossover (MA5 vs MA20)
        golden_cross = False
        death_cross = False
        if prev_ma5 is not None and prev_ma20 is not None:
            # Golden Cross: MA5 was below MA20, now above
            if prev_ma5 <= prev_ma20 and curr_ma5 > curr_ma20:
                golden_cross = True
            # Death Cross: MA5 was above MA20, now below
            elif prev_ma5 >= prev_ma20 and curr_ma5 < curr_ma20:
                death_cross = True

        # Check alignment
        bullish_alignment = curr_ma5 > curr_ma20 > curr_ma50
        bearish_alignment = curr_ma5 < curr_ma20 < curr_ma50

        # Check price position relative to MAs
        price_above_all = current_price > curr_ma5 > curr_ma20 > curr_ma50

        if golden_cross:
            score += 5
            signals['ma_golden_cross'] = (
                f"GOLDEN CROSS: MA5 ({curr_ma5:,.0f}) menembus MA20 ({curr_ma20:,.0f}) ke atas"
            )
            signals['_ma_cross_signal'] = 'GOLDEN_CROSS'
        elif death_cross:
            score -= 3
            signals['ma_death_cross'] = (
                f"DEATH CROSS: MA5 ({curr_ma5:,.0f}) menembus MA20 ({curr_ma20:,.0f}) ke bawah"
            )
            signals['_ma_cross_signal'] = 'DEATH_CROSS'
        elif price_above_all:
            score += 4
            signals['ma_perfect_alignment'] = (
                f"Perfect alignment: Price ({current_price:,.0f}) > MA5 > MA20 > MA50"
            )
            signals['_ma_cross_signal'] = 'PERFECT_BULLISH'
        elif bullish_alignment:
            score += 3
            signals['ma_bullish_alignment'] = (
                f"Bullish alignment: MA5 ({curr_ma5:,.0f}) > MA20 ({curr_ma20:,.0f}) > MA50 ({curr_ma50:,.0f})"
            )
            signals['_ma_cross_signal'] = 'BULLISH_ALIGNMENT'
        elif bearish_alignment:
            score -= 2
            signals['ma_bearish_alignment'] = (
                f"Bearish alignment: MA5 ({curr_ma5:,.0f}) < MA20 ({curr_ma20:,.0f}) < MA50 ({curr_ma50:,.0f})"
            )
            signals['_ma_cross_signal'] = 'BEARISH_ALIGNMENT'
        else:
            signals['_ma_cross_signal'] = 'NEUTRAL'

        # MA distance analysis (how far apart the MAs are)
        if curr_ma20 > 0:
            ma5_20_gap = (curr_ma5 - curr_ma20) / curr_ma20 * 100
            if abs(ma5_20_gap) < 1.0 and not golden_cross and not death_cross:
                signals['ma_converging'] = (
                    f"MA5 dan MA20 konvergen (gap {ma5_20_gap:+.1f}%) - potensi crossover"
                )
                if signals.get('_ma_cross_signal') == 'NEUTRAL':
                    signals['_ma_cross_signal'] = 'CONVERGING'

        return max(-3, min(score, 5)), signals

    def _compare_with_previous(
        self, current_deep: Dict, previous_deep: Optional[Dict]
    ) -> Dict:
        """
        Compare current deep analysis with previous to detect phase transitions.
        
        Detects:
        - Phase transitions (ACCUMULATION→HOLDING, HOLDING→DISTRIBUTION, etc.)
        - Score trend (IMPROVING, DECLINING, STABLE)
        - Key metric changes
        
        Returns dict with comparison data to be merged into deep result.
        """
        result = {
            'prev_deep_score': 0,
            'prev_phase': '',
            'phase_transition': 'NONE',
            'score_trend': 'NONE',
        }

        if not previous_deep:
            return result

        prev_score = previous_deep.get('deep_score', 0)
        curr_score = current_deep.get('deep_score', 0)
        prev_phase = previous_deep.get('accum_phase', 'UNKNOWN')
        curr_phase = current_deep.get('accum_phase', 'UNKNOWN')

        result['prev_deep_score'] = prev_score
        result['prev_phase'] = prev_phase

        # Detect phase transition
        if prev_phase and curr_phase and prev_phase != curr_phase:
            transition = f"{prev_phase}_TO_{curr_phase}"
            result['phase_transition'] = transition

            # Generate signals based on transition type
            signals = current_deep.get('deep_signals', {})

            if prev_phase == 'ACCUMULATION' and curr_phase == 'HOLDING':
                signals['phase_accum_to_hold'] = (
                    f"Fase berubah: AKUMULASI → HOLDING (bandar selesai beli, siap markup)"
                )
            elif prev_phase == 'ACCUMULATION' and curr_phase == 'DISTRIBUTION':
                signals['phase_accum_to_dist'] = (
                    f"WARNING: Fase berubah: AKUMULASI → DISTRIBUSI (bandar mulai jual!)"
                )
            elif prev_phase == 'HOLDING' and curr_phase == 'DISTRIBUTION':
                signals['phase_hold_to_dist'] = (
                    f"WARNING: Fase berubah: HOLDING → DISTRIBUSI (bandar mulai buang barang)"
                )
            elif prev_phase == 'HOLDING' and curr_phase == 'ACCUMULATION':
                signals['phase_hold_to_accum'] = (
                    f"Fase berubah: HOLDING → AKUMULASI (bandar beli lagi, positif)"
                )
            elif prev_phase == 'DISTRIBUTION' and curr_phase == 'ACCUMULATION':
                signals['phase_dist_to_accum'] = (
                    f"Fase berubah: DISTRIBUSI → AKUMULASI (re-accumulation, potensi reversal)"
                )
            elif prev_phase == 'DISTRIBUTION' and curr_phase == 'HOLDING':
                signals['phase_dist_to_hold'] = (
                    f"Fase berubah: DISTRIBUSI → HOLDING (distribusi berhenti)"
                )
            elif prev_phase != 'UNKNOWN' and curr_phase != 'UNKNOWN':
                signals[f'phase_{prev_phase.lower()}_to_{curr_phase.lower()}'] = (
                    f"Fase berubah: {prev_phase} → {curr_phase}"
                )

            current_deep['deep_signals'] = signals

        # Score trend
        if prev_score > 0:
            score_diff = curr_score - prev_score
            if score_diff >= 10:
                result['score_trend'] = 'STRONG_IMPROVING'
            elif score_diff >= 3:
                result['score_trend'] = 'IMPROVING'
            elif score_diff <= -10:
                result['score_trend'] = 'STRONG_DECLINING'
            elif score_diff <= -3:
                result['score_trend'] = 'DECLINING'
            else:
                result['score_trend'] = 'STABLE'

        return result

    def enrich_results_with_deep(
        self,
        results: List[Dict],
        deep_cache: Dict[str, Dict]
    ) -> List[Dict]:
        """
        Merge deep analysis data into base screening results.
        
        Args:
            results: Base screening results from analyze()
            deep_cache: Dict of ticker -> deep analysis cache data
        
        Returns:
            Enriched results list with deep_* fields added
        """
        for r in results:
            symbol = r.get('symbol', '')
            deep = deep_cache.get(symbol)
            if deep:
                r['deep_score'] = round(deep.get('deep_score', 0), 1)
                r['deep_trade_type'] = deep.get('deep_trade_type', '')
                r['combined_score'] = round(r.get('total_score', 0) + deep.get('deep_score', 0), 1)
                r['max_combined_score'] = 250  # 100 base + 150 deep

                # Inventory summary
                r['inv_accum_brokers'] = deep.get('inv_accum_brokers', 0)
                r['inv_distrib_brokers'] = deep.get('inv_distrib_brokers', 0)
                r['inv_clean_brokers'] = deep.get('inv_clean_brokers', 0)
                r['inv_tektok_brokers'] = deep.get('inv_tektok_brokers', 0)
                r['inv_total_accum_lot'] = deep.get('inv_total_accum_lot', 0)
                r['inv_top_accum_broker'] = deep.get('inv_top_accum_broker', '')
                r['inv_brokers_detail'] = deep.get('inv_brokers_detail', [])

                # Transaction chart summary
                r['txn_mm_cum'] = deep.get('txn_mm_cum', 0)
                r['txn_foreign_cum'] = deep.get('txn_foreign_cum', 0)
                r['txn_institution_cum'] = deep.get('txn_institution_cum', 0)
                r['txn_cross_index'] = deep.get('txn_cross_index', 0)
                r['txn_mm_trend'] = deep.get('txn_mm_trend', '')
                r['txn_foreign_trend'] = deep.get('txn_foreign_trend', '')

                # Broker summary
                r['broksum_avg_buy_price'] = deep.get('broksum_avg_buy_price', 0)
                r['broksum_avg_sell_price'] = deep.get('broksum_avg_sell_price', 0)
                r['broksum_floor_price'] = deep.get('broksum_floor_price', 0)
                r['broksum_total_buy_lot'] = deep.get('broksum_total_buy_lot', 0)
                r['broksum_total_sell_lot'] = deep.get('broksum_total_sell_lot', 0)
                r['broksum_net_institutional'] = deep.get('broksum_net_institutional', 0)
                r['broksum_net_foreign'] = deep.get('broksum_net_foreign', 0)
                r['broksum_top_buyers'] = deep.get('broksum_top_buyers', [])
                r['broksum_top_sellers'] = deep.get('broksum_top_sellers', [])

                # Entry/target prices
                r['entry_price'] = deep.get('entry_price', 0)
                r['target_price'] = deep.get('target_price', 0)
                r['stop_loss'] = deep.get('stop_loss', 0)
                r['risk_reward_ratio'] = deep.get('risk_reward_ratio', 0)

                # Controlling broker analysis
                r['controlling_brokers'] = deep.get('controlling_brokers', [])
                r['accum_start_date'] = deep.get('accum_start_date')
                r['accum_phase'] = deep.get('accum_phase', 'UNKNOWN')
                r['bandar_avg_cost'] = deep.get('bandar_avg_cost', 0)
                r['bandar_total_lot'] = deep.get('bandar_total_lot', 0)
                r['coordination_score'] = deep.get('coordination_score', 0)
                r['phase_confidence'] = deep.get('phase_confidence', 'LOW')
                r['breakout_signal'] = deep.get('breakout_signal', 'NONE')
                r['bandar_peak_lot'] = deep.get('bandar_peak_lot', 0)
                r['bandar_distribution_pct'] = deep.get('bandar_distribution_pct', 0.0)
                r['distribution_alert'] = deep.get('distribution_alert', 'NONE')

                # Cross-reference: broker summary ↔ inventory
                r['bandar_buy_today_count'] = deep.get('bandar_buy_today_count', 0)
                r['bandar_sell_today_count'] = deep.get('bandar_sell_today_count', 0)
                r['bandar_buy_today_lot'] = deep.get('bandar_buy_today_lot', 0)
                r['bandar_sell_today_lot'] = deep.get('bandar_sell_today_lot', 0)
                r['bandar_confirmation'] = deep.get('bandar_confirmation', 'NONE')

                # Multi-day consistency
                r['broksum_days_analyzed'] = deep.get('broksum_days_analyzed', 0)
                r['broksum_consistency_score'] = deep.get('broksum_consistency_score', 0)
                r['broksum_consistent_buyers'] = deep.get('broksum_consistent_buyers', [])
                r['broksum_consistent_sellers'] = deep.get('broksum_consistent_sellers', [])

                # Breakout probability
                r['breakout_probability'] = deep.get('breakout_probability', 0)
                r['breakout_factors'] = deep.get('breakout_factors', {})

                # Accumulation duration
                r['accum_duration_days'] = deep.get('accum_duration_days', 0)

                # Concentration risk
                r['concentration_broker'] = deep.get('concentration_broker')
                r['concentration_pct'] = deep.get('concentration_pct', 0.0)
                r['concentration_risk'] = deep.get('concentration_risk', 'NONE')

                # Smart money vs retail divergence
                r['txn_smart_money_cum'] = deep.get('txn_smart_money_cum', 0)
                r['txn_retail_cum_deep'] = deep.get('txn_retail_cum_deep', 0)
                r['smart_retail_divergence'] = deep.get('smart_retail_divergence', 0)

                # Volume context
                r['volume_score'] = deep.get('volume_score', 0)
                r['volume_signal'] = deep.get('volume_signal', 'NONE')

                # MA cross
                r['ma_cross_signal'] = deep.get('ma_cross_signal', 'NONE')
                r['ma_cross_score'] = deep.get('ma_cross_score', 0)

                # Historical comparison
                r['prev_deep_score'] = deep.get('prev_deep_score', 0)
                r['prev_phase'] = deep.get('prev_phase', '')
                r['phase_transition'] = deep.get('phase_transition', 'NONE')
                r['score_trend'] = deep.get('score_trend', 'NONE')

                # Flow velocity/acceleration
                r['flow_velocity_mm'] = deep.get('flow_velocity_mm', 0)
                r['flow_velocity_foreign'] = deep.get('flow_velocity_foreign', 0)
                r['flow_velocity_institution'] = deep.get('flow_velocity_institution', 0)
                r['flow_acceleration_mm'] = deep.get('flow_acceleration_mm', 0)
                r['flow_acceleration_signal'] = deep.get('flow_acceleration_signal', 'NONE')
                r['flow_velocity_score'] = deep.get('flow_velocity_score', 0)

                # Important dates broker summary
                r['important_dates'] = deep.get('important_dates', [])
                r['important_dates_score'] = deep.get('important_dates_score', 0)
                r['important_dates_signal'] = deep.get('important_dates_signal', 'NONE')

                # Pump tomorrow prediction
                r['pump_tomorrow_score'] = deep.get('pump_tomorrow_score', 0)
                r['pump_tomorrow_signal'] = deep.get('pump_tomorrow_signal', 'NONE')
                r['pump_tomorrow_factors'] = deep.get('pump_tomorrow_factors', {})

                # Deep signals
                r['deep_signals'] = deep.get('deep_signals', {})

                # Override trade_type with deep version if available
                if deep.get('deep_trade_type') and deep['deep_trade_type'] != '—':
                    r['trade_type'] = deep['deep_trade_type']
            else:
                r['deep_score'] = 0
                r['combined_score'] = r.get('total_score', 0)
                r['max_combined_score'] = 250
                r['has_deep'] = False

        # Re-sort by combined score
        results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        return results
