"""
Alpha Hunter Health Tracker.
Responsible for monitoring post-spike correction health (Healthy Pullback).
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from modules.database import DatabaseManager

class AlphaHunterHealth:
    def __init__(self):
        self.db = DatabaseManager()

    @staticmethod
    def _auto_detect_spike_date(records: List[Dict], min_ratio: float = 2.0, lookback_days: int = 20) -> Optional[str]:
        """Auto-detect latest spike date from volume history.

        A spike is detected when current volume is >= min_ratio * median(volume of previous lookback_days),
        with non-negative daily price change.
        """
        if not records:
            return None

        df = pd.DataFrame(records)
        required_cols = {'trade_date', 'volume', 'close_price'}
        if not required_cols.issubset(df.columns):
            return None

        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date').reset_index(drop=True)
        if len(df) < 6:
            return None

        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)
        df['close_price'] = pd.to_numeric(df['close_price'], errors='coerce').fillna(0)

        candidates = []
        for idx in range(1, len(df)):
            baseline_start = max(0, idx - lookback_days)
            baseline = df['volume'].iloc[baseline_start:idx]
            if baseline.empty:
                continue

            baseline_median = float(baseline.median())
            if baseline_median <= 0:
                continue

            current_volume = float(df.at[idx, 'volume'])
            ratio = current_volume / baseline_median

            prev_close = float(df.at[idx - 1, 'close_price'])
            current_close = float(df.at[idx, 'close_price'])
            price_chg = ((current_close - prev_close) / prev_close * 100) if prev_close > 0 else 0

            if ratio >= min_ratio and price_chg >= 0:
                candidates.append(df.at[idx, 'trade_date'])

        if not candidates:
            return None
        return max(candidates).strftime('%Y-%m-%d')
        
    def check_pullback_health(self, ticker: str, spike_date: str = None) -> Dict:
        """
        Analyze price/volume correlation after an anomaly spike.
        Target: Price Down + Volume Down = HEALTHY (Accumulation held)
        """
        # Get full daily data first; used for both auto-detect and tracking window
        records = self.db.get_volume_history(ticker)

        if not records:
             return {"error": "No data found"}

        spike_source = "user_input" if spike_date else "none"

        # If spike_date not provided, try watchlist first then auto-detect
        if not spike_date:
            repo = self.db.get_alpha_hunter_repo()
            item = repo.get_watchlist_item(ticker) if repo else None
            if item and item.get('spike_date'):
                spike_date = item['spike_date']
                spike_source = "watchlist"
            else:
                auto_spike_date = self._auto_detect_spike_date(records)
                if auto_spike_date:
                    spike_date = auto_spike_date
                    spike_source = "auto_detected"
                else:
                    spike_source = "fallback_last_14d"
             
        df = pd.DataFrame(records)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df = df.sort_values('trade_date')
        
        if spike_date:
            mask = df['trade_date'] >= pd.to_datetime(spike_date)
            df_tracking = df[mask].copy()
            if df_tracking.empty:
                df_tracking = df.tail(14).copy()
                spike_source = "fallback_last_14d"
                spike_date = None
        else:
            # Default to last 14 days if no spike date
            df_tracking = df.tail(14).copy()
             
        # Analysis
        health_score = 100
        tracking_log = []
        
        # Calculate daily mutations
        df_tracking['prev_price'] = df_tracking['close_price'].shift(1)
        df_tracking['prev_vol'] = df_tracking['volume'].shift(1)
        
        # Skip first row (spike day) for change calc, but include in log
        for idx, row in df_tracking.iterrows():
            if pd.isna(row['prev_price']): 
                continue
                
            price_chg = (row['close_price'] - row['prev_price']) / row['prev_price'] * 100
            vol_chg = (row['volume'] - row['prev_vol']) / row['prev_vol'] * 100 if row['prev_vol'] > 0 else 0
            
            status = "NEUTRAL"
            penalty = 0
            
            # Logic: Healthy Pullback
            if price_chg < 0: # Price Down
                if vol_chg < -20:
                    status = "HEALTHY" # ✅ Vol drying up
                elif vol_chg < 0:
                    status = "OK" # ⚠️ Vol stable/down
                    penalty = 5
                else:
                    status = "DANGER" # 🚨 Price down on rising volume = Distribution
                    penalty = 25
            elif price_chg > 0: # Price Up
                 if vol_chg > 0:
                     status = "STRONG" # ✅ Price up on vol up
                 else:
                     status = "WEAK_BOUNCE" # ⚠️ Price up on vol down
                     penalty = 5
                     
            health_score = max(0, health_score - penalty)
            
            tracking_log.append({
                "date": row['trade_date'].strftime('%Y-%m-%d'),
                "price": row['close_price'],
                "volume": row['volume'],
                "price_chg": round(price_chg, 2),
                "vol_chg": round(vol_chg, 2),
                "status": status
            })
            
        # Determine verdict
        if health_score >= 80: verdict = "HEALTHY PULLBACK"
        elif health_score >= 50: verdict = "WATCHLIST"
        else: verdict = "BROKEN / DISTRIBUTION"
        
        return {
            "ticker": ticker,
            "spike_date": spike_date,
            "spike_source": spike_source,
            "health_score": health_score,
            "verdict": verdict,
            "days_tracked": len(tracking_log),
            "log": tracking_log
        }
