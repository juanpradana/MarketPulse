import argparse
import os
import sqlite3
import statistics
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modules.bandarmology_analyzer import BandarmologyAnalyzer, _parse_numeric


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _build_price_index(db_path: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, List[str]]]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT symbol, scraped_at, price
            FROM neobdm_records
            WHERE method = 'm' AND period = 'd'
            ORDER BY scraped_at ASC
            """
        )
        price_by_ticker: Dict[str, Dict[str, float]] = {}
        for symbol, scraped_at, price in cursor.fetchall():
            if not symbol:
                continue
            date_str = str(scraped_at)[:10]
            p = _parse_numeric(price)
            if p <= 0:
                continue
            ticker = symbol.strip().upper()
            if ticker not in price_by_ticker:
                price_by_ticker[ticker] = {}
            price_by_ticker[ticker][date_str] = p

        dates_by_ticker: Dict[str, List[str]] = {}
        for ticker, date_map in price_by_ticker.items():
            dates_by_ticker[ticker] = sorted(date_map.keys())

        return price_by_ticker, dates_by_ticker
    finally:
        conn.close()


def _forward_return(
    price_by_ticker: Dict[str, Dict[str, float]],
    dates_by_ticker: Dict[str, List[str]],
    ticker: str,
    date_str: str,
    horizon: int
) -> Optional[float]:
    dates = dates_by_ticker.get(ticker)
    if not dates:
        return None
    try:
        idx = dates.index(date_str)
    except ValueError:
        return None
    target_idx = idx + horizon
    if target_idx >= len(dates):
        return None
    future_date = dates[target_idx]
    p0 = price_by_ticker.get(ticker, {}).get(date_str)
    p1 = price_by_ticker.get(ticker, {}).get(future_date)
    if not p0 or not p1:
        return None
    return (p1 - p0) / p0 * 100.0


def _summarize(returns: List[float]) -> Dict[str, float]:
    if not returns:
        return {
            "count": 0,
            "avg": 0.0,
            "median": 0.0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
        }
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    avg_win = statistics.mean(wins) if wins else 0.0
    avg_loss = statistics.mean(losses) if losses else 0.0
    return {
        "count": len(returns),
        "avg": statistics.mean(returns),
        "median": statistics.median(returns),
        "win_rate": (len(wins) / len(returns)) * 100.0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def _resolve_trade_filter(profile: str, explicit: str) -> List[str]:
    if explicit and explicit != "AUTO":
        if explicit == "ANY":
            return ["SWING", "INTRADAY", "BOTH", "WATCH"]
        return [explicit]
    if profile == "swing":
        return ["SWING", "BOTH"]
    if profile == "daytrade":
        return ["INTRADAY", "BOTH"]
    return ["SWING", "INTRADAY", "BOTH"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bandarmology backtest runner")
    parser.add_argument("--profile", default="balanced", choices=["balanced", "swing", "daytrade"])
    parser.add_argument("--start", help="YYYY-MM-DD")
    parser.add_argument("--end", help="YYYY-MM-DD")
    parser.add_argument("--max-days", type=int, default=60)
    parser.add_argument("--top-n", type=int, default=30)
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--horizons", default="1,3,5,10")
    parser.add_argument("--trade-type", default="AUTO", choices=["AUTO", "SWING", "INTRADAY", "BOTH", "WATCH", "ANY"])
    args = parser.parse_args()

    analyzer = BandarmologyAnalyzer()
    profile = args.profile
    horizons = [int(x) for x in args.horizons.split(",") if x.strip().isdigit()]
    horizons = sorted(set(horizons))
    if not horizons:
        print("No valid horizons provided.")
        return 1

    available_dates = analyzer.get_available_dates()
    if args.start:
        start_dt = _parse_date(args.start)
        available_dates = [d for d in available_dates if _parse_date(d) >= start_dt]
    if args.end:
        end_dt = _parse_date(args.end)
        available_dates = [d for d in available_dates if _parse_date(d) <= end_dt]
    available_dates = sorted(available_dates)
    if args.max_days and len(available_dates) > args.max_days:
        available_dates = available_dates[-args.max_days:]

    price_by_ticker, dates_by_ticker = _build_price_index(analyzer.db_path)
    trade_filter = _resolve_trade_filter(profile, args.trade_type)

    returns_by_horizon: Dict[int, List[float]] = {h: [] for h in horizons}
    total_trades = 0
    trades_by_day: List[int] = []

    for date_str in available_dates:
        results = analyzer.analyze(target_date=date_str, profile=profile)
        filtered = [r for r in results if r.get("total_score", 0) >= args.min_score]
        filtered = [r for r in filtered if r.get("trade_type") in trade_filter]
        filtered.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        if args.top_n:
            filtered = filtered[: args.top_n]

        trades_by_day.append(len(filtered))
        for row in filtered:
            ticker = (row.get("symbol") or "").upper()
            if not ticker:
                continue
            total_trades += 1
            for h in horizons:
                ret = _forward_return(price_by_ticker, dates_by_ticker, ticker, date_str, h)
                if ret is not None:
                    returns_by_horizon[h].append(ret)

    print("")
    print("Bandarmology Backtest")
    print(f"Profile: {profile}")
    print(f"Dates: {available_dates[0] if available_dates else '-'} to {available_dates[-1] if available_dates else '-'}")
    print(f"Trade filter: {', '.join(trade_filter)}")
    print(f"Top N: {args.top_n} | Min score: {args.min_score}")
    print(f"Total trades selected: {total_trades}")
    if trades_by_day:
        print(f"Avg trades/day: {statistics.mean(trades_by_day):.1f}")
    print("")

    for h in horizons:
        stats = _summarize(returns_by_horizon[h])
        print(f"Horizon {h}D")
        print(f"Count: {stats['count']}")
        print(f"Avg return: {stats['avg']:.2f}% | Median: {stats['median']:.2f}%")
        print(f"Win rate: {stats['win_rate']:.1f}% | Avg win: {stats['avg_win']:.2f}% | Avg loss: {stats['avg_loss']:.2f}%")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
