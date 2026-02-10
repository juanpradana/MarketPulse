"""Repository for Bandarmology deep analysis data (inventory, transaction chart, cache)."""
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime
from .connection import BaseRepository

logger = logging.getLogger(__name__)


class BandarmologyRepository(BaseRepository):
    """Repository for bandarmology inventory, transaction chart, and deep analysis cache."""

    # ==================== INVENTORY ====================

    def save_inventory_batch(self, ticker: str, brokers: List[Dict], date_start: str, date_end: str):
        """Save inventory broker data for a ticker."""
        conn = self._get_conn()
        try:
            scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Delete existing data for this ticker+date_end
            conn.execute(
                "DELETE FROM bandarmology_inventory WHERE UPPER(ticker) = UPPER(?) AND date_end = ?",
                (ticker, date_end)
            )

            query = """
            INSERT INTO bandarmology_inventory (
                ticker, broker_code, is_clean, is_tektok, is_accumulating,
                final_net_lot, start_net_lot, data_points,
                time_series_json, date_start, date_end, scraped_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            rows = []
            for b in brokers:
                # Only store last 10 points of time series to save space
                ts = b.get('timeSeries', [])
                ts_compact = ts[-10:] if len(ts) > 10 else ts

                rows.append((
                    ticker.upper(),
                    b.get('code', ''),
                    1 if b.get('isClean') else 0,
                    1 if b.get('isTektok') else 0,
                    1 if b.get('isAccumulating') else 0,
                    b.get('finalNetLot', 0),
                    b.get('startNetLot', 0),
                    b.get('dataPoints', 0),
                    json.dumps(ts_compact),
                    date_start,
                    date_end,
                    scraped_at
                ))

            if rows:
                conn.executemany(query, rows)
                conn.commit()
                logger.info(f"Saved {len(rows)} inventory records for {ticker}")
        except Exception as e:
            logger.error(f"Error saving inventory for {ticker}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_inventory(self, ticker: str, date_end: Optional[str] = None) -> List[Dict]:
        """Get inventory data for a ticker."""
        conn = self._get_conn()
        try:
            if date_end:
                query = """
                SELECT * FROM bandarmology_inventory
                WHERE UPPER(ticker) = UPPER(?) AND date_end = ?
                ORDER BY final_net_lot DESC
                """
                cursor = conn.cursor()
                cursor.execute(query, (ticker, date_end))
            else:
                # Get latest
                query = """
                SELECT * FROM bandarmology_inventory
                WHERE UPPER(ticker) = UPPER(?)
                ORDER BY date_end DESC, final_net_lot DESC
                """
                cursor = conn.cursor()
                cursor.execute(query, (ticker,))

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                return []

            # Group by date_end (return only latest set)
            target_date = rows[0][columns.index('date_end')]
            result = []
            for row in rows:
                d = dict(zip(columns, row))
                if d['date_end'] != target_date:
                    break
                d['time_series'] = json.loads(d.get('time_series_json') or '[]')
                result.append(d)

            return result
        finally:
            conn.close()

    # ==================== TRANSACTION CHART ====================

    def save_transaction_chart(self, ticker: str, data: Dict):
        """Save transaction chart data for a ticker."""
        conn = self._get_conn()
        try:
            scraped_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            period = data.get('period', '6m')
            date_end = data.get('lastDate', '')
            date_start = data.get('firstDate', '')
            data_points = data.get('dataPoints', 0)

            cum = data.get('cumulative', {})
            daily = data.get('daily', {})
            part = data.get('participation', {})
            ci = data.get('cross_index', {})

            # Compute trends
            def compute_trend(method_data):
                if not method_data:
                    return 'NEUTRAL'
                latest = method_data.get('latest', 0)
                week_ago = method_data.get('week_ago', 0)
                month_ago = method_data.get('month_ago', 0)
                if latest > week_ago > month_ago and latest > 0:
                    return 'STRONG_UP'
                elif latest > week_ago and latest > 0:
                    return 'UP'
                elif latest < week_ago < month_ago and latest < 0:
                    return 'STRONG_DOWN'
                elif latest < week_ago:
                    return 'DOWN'
                return 'NEUTRAL'

            mm_trend = compute_trend(cum.get('market_maker'))
            foreign_trend = compute_trend(cum.get('foreign'))
            institution_trend = compute_trend(cum.get('institution'))

            # Delete existing
            conn.execute(
                "DELETE FROM bandarmology_txn_chart WHERE UPPER(ticker) = UPPER(?) AND period = ? AND date_end = ?",
                (ticker, period, date_end)
            )

            # Store compact time series (dates + cumulative values only)
            ts_json = json.dumps({
                'dates': data.get('dates', [])[-30:],  # last 30 dates
                'cumulative': {k: {'latest': v.get('latest', 0)} for k, v in cum.items()},
                'daily': {k: {'latest': v.get('latest', 0)} for k, v in daily.items()}
            })

            conn.execute("""
                INSERT INTO bandarmology_txn_chart (
                    ticker, period,
                    cum_mm, cum_nr, cum_smart, cum_retail, cum_foreign, cum_institution, cum_zombie,
                    daily_mm, daily_nr, daily_smart, daily_retail, daily_foreign, daily_institution, daily_zombie,
                    part_foreign, part_retail, part_institution, part_zombie,
                    cross_index,
                    mm_trend, foreign_trend, institution_trend,
                    time_series_json, date_start, date_end, data_points, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker.upper(), period,
                cum.get('market_maker', {}).get('latest', 0),
                cum.get('non_retail', {}).get('latest', 0),
                cum.get('smart_money', {}).get('latest', 0),
                cum.get('retail', {}).get('latest', 0),
                cum.get('foreign', {}).get('latest', 0),
                cum.get('institution', {}).get('latest', 0),
                cum.get('zombie', {}).get('latest', 0),
                daily.get('market_maker', {}).get('latest', 0),
                daily.get('non_retail', {}).get('latest', 0),
                daily.get('smart_money', {}).get('latest', 0),
                daily.get('retail', {}).get('latest', 0),
                daily.get('foreign', {}).get('latest', 0),
                daily.get('institution', {}).get('latest', 0),
                daily.get('zombie', {}).get('latest', 0),
                part.get('foreign', {}).get('latest', 0),
                part.get('retail', {}).get('latest', 0),
                part.get('institution', {}).get('latest', 0),
                part.get('zombie', {}).get('latest', 0),
                ci.get('latest', 0) if ci else 0,
                mm_trend, foreign_trend, institution_trend,
                ts_json, date_start, date_end, data_points, scraped_at
            ))
            conn.commit()
            logger.info(f"Saved transaction chart for {ticker}")
        except Exception as e:
            logger.error(f"Error saving transaction chart for {ticker}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_transaction_chart(self, ticker: str, period: str = '6m') -> Optional[Dict]:
        """Get transaction chart data for a ticker."""
        conn = self._get_conn()
        try:
            query = """
            SELECT * FROM bandarmology_txn_chart
            WHERE UPPER(ticker) = UPPER(?) AND period = ?
            ORDER BY date_end DESC LIMIT 1
            """
            cursor = conn.cursor()
            cursor.execute(query, (ticker, period))
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if not row:
                return None
            return dict(zip(columns, row))
        finally:
            conn.close()

    # ==================== DEEP ANALYSIS CACHE ====================

    def save_deep_cache(self, ticker: str, analysis_date: str, data: Dict):
        """Save deep analysis cache for a ticker."""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM bandarmology_deep_cache WHERE UPPER(ticker) = UPPER(?) AND analysis_date = ?",
                (ticker, analysis_date)
            )

            conn.execute("""
                INSERT INTO bandarmology_deep_cache (
                    ticker, analysis_date,
                    inv_accum_brokers, inv_distrib_brokers, inv_clean_brokers, inv_tektok_brokers,
                    inv_total_accum_lot, inv_total_distrib_lot, inv_top_accum_broker, inv_top_accum_lot,
                    txn_mm_cum, txn_foreign_cum, txn_institution_cum, txn_retail_cum,
                    txn_cross_index, txn_foreign_participation, txn_institution_participation,
                    txn_mm_trend, txn_foreign_trend,
                    broksum_total_buy_lot, broksum_total_sell_lot,
                    broksum_total_buy_val, broksum_total_sell_val,
                    broksum_avg_buy_price, broksum_avg_sell_price,
                    broksum_floor_price, broksum_target_price,
                    broksum_top_buyers_json, broksum_top_sellers_json,
                    broksum_net_institutional, broksum_net_foreign,
                    entry_price, target_price, stop_loss, risk_reward_ratio,
                    deep_score, deep_trade_type, deep_signals_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker.upper(), analysis_date,
                data.get('inv_accum_brokers', 0),
                data.get('inv_distrib_brokers', 0),
                data.get('inv_clean_brokers', 0),
                data.get('inv_tektok_brokers', 0),
                data.get('inv_total_accum_lot', 0),
                data.get('inv_total_distrib_lot', 0),
                data.get('inv_top_accum_broker', ''),
                data.get('inv_top_accum_lot', 0),
                data.get('txn_mm_cum', 0),
                data.get('txn_foreign_cum', 0),
                data.get('txn_institution_cum', 0),
                data.get('txn_retail_cum', 0),
                data.get('txn_cross_index', 0),
                data.get('txn_foreign_participation', 0),
                data.get('txn_institution_participation', 0),
                data.get('txn_mm_trend', ''),
                data.get('txn_foreign_trend', ''),
                data.get('broksum_total_buy_lot', 0),
                data.get('broksum_total_sell_lot', 0),
                data.get('broksum_total_buy_val', 0),
                data.get('broksum_total_sell_val', 0),
                data.get('broksum_avg_buy_price', 0),
                data.get('broksum_avg_sell_price', 0),
                data.get('broksum_floor_price', 0),
                data.get('broksum_target_price', 0),
                json.dumps(data.get('broksum_top_buyers', [])),
                json.dumps(data.get('broksum_top_sellers', [])),
                data.get('broksum_net_institutional', 0),
                data.get('broksum_net_foreign', 0),
                data.get('entry_price', 0),
                data.get('target_price', 0),
                data.get('stop_loss', 0),
                data.get('risk_reward_ratio', 0),
                data.get('deep_score', 0),
                data.get('deep_trade_type', ''),
                json.dumps(data.get('deep_signals', {}))
            ))
            conn.commit()
            logger.info(f"Saved deep cache for {ticker} on {analysis_date}")
        except Exception as e:
            logger.error(f"Error saving deep cache for {ticker}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def get_deep_cache(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        """Get deep analysis cache for a ticker."""
        conn = self._get_conn()
        try:
            if analysis_date:
                query = """
                SELECT * FROM bandarmology_deep_cache
                WHERE UPPER(ticker) = UPPER(?) AND analysis_date = ?
                """
                cursor = conn.cursor()
                cursor.execute(query, (ticker, analysis_date))
            else:
                query = """
                SELECT * FROM bandarmology_deep_cache
                WHERE UPPER(ticker) = UPPER(?)
                ORDER BY analysis_date DESC LIMIT 1
                """
                cursor = conn.cursor()
                cursor.execute(query, (ticker,))

            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(zip(columns, row))
            d['deep_signals'] = json.loads(d.get('deep_signals_json') or '{}')
            d['broksum_top_buyers'] = json.loads(d.get('broksum_top_buyers_json') or '[]')
            d['broksum_top_sellers'] = json.loads(d.get('broksum_top_sellers_json') or '[]')
            return d
        finally:
            conn.close()

    def get_deep_cache_batch(self, analysis_date: str) -> Dict[str, Dict]:
        """Get all deep analysis caches for a given date."""
        conn = self._get_conn()
        try:
            query = """
            SELECT * FROM bandarmology_deep_cache
            WHERE analysis_date = ?
            """
            cursor = conn.cursor()
            cursor.execute(query, (analysis_date,))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            result = {}
            for row in rows:
                d = dict(zip(columns, row))
                d['deep_signals'] = json.loads(d.get('deep_signals_json') or '{}')
                d['broksum_top_buyers'] = json.loads(d.get('broksum_top_buyers_json') or '[]')
                d['broksum_top_sellers'] = json.loads(d.get('broksum_top_sellers_json') or '[]')
                result[d['ticker']] = d
            return result
        finally:
            conn.close()
