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
from typing import List, Dict, Optional, Tuple
from datetime import datetime

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

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(config.DATA_DIR, "market_sentinel.db")
        self.broker_classes = _load_broker_classifications()

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

        # --- CLASSIFICATION ---
        trade_type = self._classify_trade_type(
            total_score, scores, pinky, crossing, unusual, likuid,
            positive_weeks, d_0_mm, pct_1d, ma_above_count,
            w_1, w_2, c_3, c_5
        )

        # --- Build result ---
        return {
            'symbol': symbol,
            'total_score': total_score,
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

    # ==================== DEEP ANALYSIS (Inventory + Txn Chart) ====================

    def analyze_deep(
        self,
        ticker: str,
        inventory_data: Optional[List[Dict]] = None,
        txn_chart_data: Optional[Dict] = None,
        broker_summary_data: Optional[Dict] = None,
        base_result: Optional[Dict] = None
    ) -> Dict:
        """
        Perform deep analysis on a single ticker using inventory + transaction chart + broker summary data.
        
        Enhances the base screening score with:
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
            base_result: Existing bandarmology result dict to enhance
        
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
        }

        signals = {}
        deep_score = 0

        # ---- INVENTORY ANALYSIS (max 30 pts) ----
        if inventory_data:
            inv_score, inv_signals = self._score_inventory(inventory_data)
            deep_score += inv_score
            signals.update(inv_signals)

            # Populate inventory metrics
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

        # ---- TRANSACTION CHART ANALYSIS (max 30 pts) ----
        if txn_chart_data:
            txn_score, txn_signals = self._score_transaction_chart(txn_chart_data)
            deep_score += txn_score
            signals.update(txn_signals)

            # Populate txn metrics
            deep['txn_mm_cum'] = _safe_float(txn_chart_data.get('cum_mm'))
            deep['txn_foreign_cum'] = _safe_float(txn_chart_data.get('cum_foreign'))
            deep['txn_institution_cum'] = _safe_float(txn_chart_data.get('cum_institution'))
            deep['txn_retail_cum'] = _safe_float(txn_chart_data.get('cum_retail'))
            deep['txn_cross_index'] = _safe_float(txn_chart_data.get('cross_index'))
            deep['txn_foreign_participation'] = _safe_float(txn_chart_data.get('part_foreign'))
            deep['txn_institution_participation'] = _safe_float(txn_chart_data.get('part_institution'))
            deep['txn_mm_trend'] = txn_chart_data.get('mm_trend') or 'NEUTRAL'
            deep['txn_foreign_trend'] = txn_chart_data.get('foreign_trend') or 'NEUTRAL'

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

        # ---- ENTRY/TARGET PRICE CALCULATION ----
        current_price = base_result.get('price', 0) if base_result else 0
        if current_price > 0:
            floor = deep.get('broksum_floor_price', 0)
            target = deep.get('broksum_target_price', 0)
            avg_buy = deep.get('broksum_avg_buy_price', 0)

            # Entry price = floor price if available, else avg buy price, else current price * 0.97
            if floor > 0:
                deep['entry_price'] = floor
            elif avg_buy > 0:
                deep['entry_price'] = avg_buy
            else:
                deep['entry_price'] = round(current_price * 0.97, 0)

            # Target price = institutional sell avg if available, else entry * 1.05 (5% gain)
            if target > 0 and target > deep['entry_price']:
                deep['target_price'] = target
            elif deep['entry_price'] > 0:
                deep['target_price'] = round(deep['entry_price'] * 1.05, 0)

            # Stop loss = entry * 0.97 (3% risk)
            if deep['entry_price'] > 0:
                deep['stop_loss'] = round(deep['entry_price'] * 0.97, 0)

            # Risk/reward ratio
            if deep['entry_price'] > 0 and deep['stop_loss'] > 0 and deep['target_price'] > 0:
                risk = deep['entry_price'] - deep['stop_loss']
                reward = deep['target_price'] - deep['entry_price']
                if risk > 0:
                    deep['risk_reward_ratio'] = round(reward / risk, 2)

        # ---- COMBINED SCORING ----
        # Synergy bonus: inventory confirms txn chart (max 10 pts)
        if inventory_data and txn_chart_data:
            synergy_score, synergy_signals = self._score_synergy(deep)
            deep_score += synergy_score
            signals.update(synergy_signals)

        deep['deep_score'] = deep_score
        deep['deep_signals'] = signals

        # Enhanced classification
        deep['deep_trade_type'] = self._classify_deep_trade_type(
            deep, base_result
        )

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
                r['deep_score'] = deep.get('deep_score', 0)
                r['deep_trade_type'] = deep.get('deep_trade_type', '')
                r['combined_score'] = r.get('total_score', 0) + deep.get('deep_score', 0)
                r['max_combined_score'] = 190  # 100 base + 90 deep

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

                # Deep signals
                r['deep_signals'] = deep.get('deep_signals', {})

                # Override trade_type with deep version if available
                if deep.get('deep_trade_type') and deep['deep_trade_type'] != '—':
                    r['trade_type'] = deep['deep_trade_type']
            else:
                r['deep_score'] = 0
                r['combined_score'] = r.get('total_score', 0)
                r['max_combined_score'] = 190
                r['has_deep'] = False

        # Re-sort by combined score
        results.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        return results
