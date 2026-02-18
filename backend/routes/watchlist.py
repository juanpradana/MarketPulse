"""
Watchlist API Routes

Endpoints for managing user's personalized ticker watchlist.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import subprocess
import sys
import os

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


class AddTickerRequest(BaseModel):
    """Request to add ticker to watchlist."""
    ticker: str


class RemoveTickerRequest(BaseModel):
    """Request to remove ticker from watchlist."""
    ticker: str


class WatchlistItem(BaseModel):
    """Watchlist item response."""
    ticker: str
    added_at: str
    company_name: Optional[str] = None
    latest_price: Optional[dict] = None


class AlphaHunterAnalysis(BaseModel):
    """Alpha Hunter signal analysis for a ticker."""
    signal_score: Optional[float] = None
    signal_strength: Optional[str] = None
    conviction: Optional[str] = None
    patterns: List[str] = []
    flow: Optional[float] = None
    entry_zone: Optional[str] = None
    momentum_status: Optional[str] = None
    warning_status: Optional[str] = None
    has_signal: bool = False


class BandarmologyAnalysis(BaseModel):
    """Bandarmology analysis for a ticker."""
    total_score: Optional[float] = None
    deep_score: Optional[float] = None
    combined_score: Optional[float] = None
    trade_type: Optional[str] = None
    deep_trade_type: Optional[str] = None
    phase: Optional[str] = None
    bandar_avg_cost: Optional[float] = None
    price_vs_cost_pct: Optional[float] = None
    breakout_signal: Optional[str] = None
    distribution_alert: Optional[str] = None
    pinky: bool = False
    crossing: bool = False
    unusual: bool = False
    has_analysis: bool = False


class WatchlistItemWithAnalysis(BaseModel):
    """Watchlist item with combined analysis."""
    ticker: str
    added_at: str
    company_name: Optional[str] = None
    latest_price: Optional[dict] = None
    alpha_hunter: AlphaHunterAnalysis
    bandarmology: BandarmologyAnalysis
    combined_rating: Optional[str] = None
    recommendation: Optional[str] = None


@router.get("", response_model=List[WatchlistItem])
async def get_watchlist(user_id: str = "default"):
    """
    Get user's watchlist with latest price data.

    Args:
        user_id: User identifier (default for single-user mode)

    Returns:
        List of watchlist items with ticker details
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        watchlist = repo.get_watchlist(user_id)

        return watchlist

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get watchlist: {str(e)}")


@router.post("/add")
async def add_ticker(request: AddTickerRequest, user_id: str = "default"):
    """
    Add a ticker to user's watchlist.

    Args:
        request: Contains ticker symbol to add
        user_id: User identifier

    Returns:
        Success status
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        added = repo.add_ticker(request.ticker, user_id)

        if added:
            return {
                "status": "success",
                "message": f"{request.ticker.upper()} added to watchlist"
            }
        else:
            return {
                "status": "exists",
                "message": f"{request.ticker.upper()} is already in watchlist"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add ticker: {str(e)}")


@router.post("/remove")
async def remove_ticker(request: RemoveTickerRequest, user_id: str = "default"):
    """
    Remove a ticker from user's watchlist.

    Args:
        request: Contains ticker symbol to remove
        user_id: User identifier

    Returns:
        Success status
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        removed = repo.remove_ticker(request.ticker, user_id)

        if removed:
            return {
                "status": "success",
                "message": f"{request.ticker.upper()} removed from watchlist"
            }
        else:
            raise HTTPException(status_code=404, detail=f"{request.ticker.upper()} not found in watchlist")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove ticker: {str(e)}")


@router.get("/tickers")
async def get_watchlist_tickers(user_id: str = "default"):
    """
    Get just the ticker symbols from watchlist.

    Args:
        user_id: User identifier

    Returns:
        List of ticker symbols
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        tickers = repo.get_watchlist_tickers(user_id)

        return {
            "tickers": tickers,
            "count": len(tickers)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tickers: {str(e)}")


@router.get("/check/{ticker}")
async def check_watchlist(ticker: str, user_id: str = "default"):
    """
    Check if a specific ticker is in watchlist.

    Args:
        ticker: Stock ticker symbol
        user_id: User identifier

    Returns:
        Boolean indicating if ticker is in watchlist
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        is_in = repo.is_in_watchlist(ticker, user_id)

        return {
            "ticker": ticker.upper(),
            "in_watchlist": is_in
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check watchlist: {str(e)}")


@router.get("/stats")
async def get_watchlist_stats(user_id: str = "default"):
    """
    Get watchlist statistics.

    Args:
        user_id: User identifier

    Returns:
        Count and other stats
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        count = repo.get_watchlist_count(user_id)
        tickers = repo.get_watchlist_tickers(user_id)

        return {
            "count": count,
            "tickers": tickers,
            "user_id": user_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/toggle")
async def toggle_watchlist(request: AddTickerRequest, user_id: str = "default"):
    """
    Toggle ticker in watchlist (add if not exists, remove if exists).

    Args:
        request: Contains ticker symbol
        user_id: User identifier

    Returns:
        New status of ticker
    """
    try:
        from db.watchlist_repository import WatchlistRepository

        repo = WatchlistRepository()
        is_in = repo.is_in_watchlist(request.ticker, user_id)

        if is_in:
            repo.remove_ticker(request.ticker, user_id)
            return {
                "status": "removed",
                "ticker": request.ticker.upper(),
                "in_watchlist": False
            }
        else:
            repo.add_ticker(request.ticker, user_id)
            return {
                "status": "added",
                "ticker": request.ticker.upper(),
                "in_watchlist": True
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to toggle watchlist: {str(e)}")


@router.get("/with-analysis", response_model=List[WatchlistItemWithAnalysis])
async def get_watchlist_with_analysis(user_id: str = "default"):
    """
    Get user's watchlist with Alpha Hunter and Bandarmology analysis.

    Args:
        user_id: User identifier (default for single-user mode)

    Returns:
        List of watchlist items with combined analysis from both systems
    """
    try:
        from db.watchlist_repository import WatchlistRepository
        from db.neobdm_repository import NeoBDMRepository
        from db.bandarmology_repository import BandarmologyRepository

        repo = WatchlistRepository()
        neobdm_repo = NeoBDMRepository()
        bandar_repo = BandarmologyRepository()

        watchlist = repo.get_watchlist(user_id)
        results = []

        for item in watchlist:
            ticker = item["ticker"]

            # Get Alpha Hunter data (NeoBDM signals)
            alpha_data = neobdm_repo.get_signals_for_ticker(ticker)
            alpha_analysis = AlphaHunterAnalysis(
                signal_score=alpha_data.get("signal_score"),
                signal_strength=alpha_data.get("signal_strength"),
                conviction=alpha_data.get("conviction"),
                patterns=alpha_data.get("patterns", []),
                flow=alpha_data.get("flow"),
                entry_zone=alpha_data.get("entry_zone"),
                momentum_status=alpha_data.get("momentum_status"),
                warning_status=alpha_data.get("warning_status"),
                has_signal=alpha_data.get("signal_score") is not None
            )

            # Get Bandarmology data
            bandar_data = bandar_repo.get_stock_summary(ticker)
            bandar_analysis = BandarmologyAnalysis(
                total_score=bandar_data.get("total_score"),
                deep_score=bandar_data.get("deep_score"),
                combined_score=bandar_data.get("combined_score"),
                trade_type=bandar_data.get("trade_type"),
                deep_trade_type=bandar_data.get("deep_trade_type"),
                phase=bandar_data.get("accum_phase"),
                bandar_avg_cost=bandar_data.get("bandar_avg_cost"),
                price_vs_cost_pct=bandar_data.get("price_vs_cost_pct"),
                breakout_signal=bandar_data.get("breakout_signal"),
                distribution_alert=bandar_data.get("distribution_alert"),
                pinky=bandar_data.get("pinky", False),
                crossing=bandar_data.get("crossing", False),
                unusual=bandar_data.get("unusual", False),
                has_analysis=bandar_data.get("total_score") is not None
            )

            # Calculate combined rating and recommendation
            combined_rating = _calculate_combined_rating(alpha_analysis, bandar_analysis)
            recommendation = _generate_recommendation(alpha_analysis, bandar_analysis)

            results.append(WatchlistItemWithAnalysis(
                ticker=ticker,
                added_at=item["added_at"],
                company_name=item.get("company_name"),
                latest_price=item.get("latest_price"),
                alpha_hunter=alpha_analysis,
                bandarmology=bandar_analysis,
                combined_rating=combined_rating,
                recommendation=recommendation
            ))

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get watchlist with analysis: {str(e)}")


def _calculate_combined_rating(alpha: AlphaHunterAnalysis, bandar: BandarmologyAnalysis) -> Optional[str]:
    """Calculate combined rating from both analysis systems."""
    if not alpha.has_signal and not bandar.has_analysis:
        return None

    # Score from 0-100
    score = 0
    count = 0

    if alpha.has_signal and alpha.signal_score:
        # Normalize alpha score (typically 0-100)
        score += min(100, max(0, alpha.signal_score))
        count += 1

    if bandar.has_analysis:
        if bandar.combined_score:
            score += bandar.combined_score
            count += 1
        elif bandar.total_score:
            score += bandar.total_score
            count += 1

    if count == 0:
        return None

    avg_score = score / count

    if avg_score >= 70:
        return "STRONG_BUY"
    elif avg_score >= 55:
        return "BUY"
    elif avg_score >= 40:
        return "HOLD"
    else:
        return "AVOID"


def _generate_recommendation(alpha: AlphaHunterAnalysis, bandar: BandarmologyAnalysis) -> Optional[str]:
    """Generate recommendation based on both systems."""
    signals = []

    # Alpha Hunter signals
    if alpha.has_signal:
        if alpha.signal_strength in ["VERY_STRONG", "STRONG"]:
            signals.append("alpha_bullish")
        if alpha.conviction in ["VERY_HIGH", "HIGH"]:
            signals.append("alpha_high_conviction")
        if alpha.warning_status and "REPO" in alpha.warning_status:
            signals.append("alpha_repo_risk")

    # Bandarmology signals
    if bandar.has_analysis:
        if bandar.breakout_signal and "BREAKOUT" in bandar.breakout_signal:
            signals.append("bandar_breakout")
        if bandar.distribution_alert:
            signals.append("bandar_distribution")
        if bandar.pinky:
            signals.append("bandar_pinky")
        if bandar.phase in ["ACCUMULATION", "EARLY_ACCUM"]:
            signals.append("bandar_accumulating")

    # Generate recommendation
    bullish = [s for s in signals if "bullish" in s or "breakout" in s or "accumulating" in s]
    bearish = [s for s in signals if "repo" in s or "distribution" in s or "pinky" in s]

    if len(bullish) > len(bearish) and len(bullish) >= 2:
        return "STRONG_ACCUMULATION"
    elif len(bullish) > len(bearish):
        return "ACCUMULATING"
    elif len(bearish) > len(bullish) and len(bearish) >= 2:
        return "DISTRIBUTION_RISK"
    elif len(bearish) > len(bullish):
        return "CAUTION"
    elif len(bullish) > 0:
        return "MIXED_SIGNALS"
    else:
        return "NEUTRAL"


# Global status for deep analysis
_deep_analysis_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_ticker": "",
    "completed_tickers": [],
    "errors": [],
    "stage": ""  # 'neobdm', 'bandarmology'
}


@router.post("/analyze-missing")
async def analyze_missing_tickers(
    background_tasks: BackgroundTasks,
    tickers: str = Query(..., description="Comma-separated ticker symbols to analyze")
):
    """
    Trigger deep analysis for specific watchlist tickers missing data.
    Runs both NeoBDM (Alpha Hunter) and Bandarmology analysis.
    """
    global _deep_analysis_status

    if _deep_analysis_status["running"]:
        return {
            "status": "already_running",
            "message": "Analysis already in progress",
            "current_status": _deep_analysis_status
        }

    # Parse tickers
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No valid tickers provided")

    # Reset status
    _deep_analysis_status = {
        "running": True,
        "progress": 0,
        "total": len(ticker_list) * 2,  # base analysis + deep per ticker
        "current_ticker": "",
        "completed_tickers": [],
        "errors": [],
        "stage": "starting"
    }

    # Launch background task
    background_tasks.add_task(_run_missing_analysis, ticker_list)

    return {
        "status": "started",
        "message": f"Deep analysis started for {len(ticker_list)} ticker(s)",
        "tickers": ticker_list,
        "status_endpoint": "/api/watchlist/analyze-status"
    }


@router.get("/analyze-status")
async def get_analysis_status():
    """Get the status of the running deep analysis."""
    return _deep_analysis_status


async def _run_missing_analysis(tickers: List[str]):
    """Background task: Run NeoBDM and Bandarmology deep analysis for tickers."""
    global _deep_analysis_status

    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer
        from modules.neobdm_api_client import NeoBDMApiClient
        from db.bandarmology_repository import BandarmologyRepository
        from db.neobdm_repository import NeoBDMRepository

        analyzer = BandarmologyAnalyzer()
        actual_date = analyzer._resolve_date(None)

        # Stage 1: Run base analysis to get scores
        _deep_analysis_status["stage"] = "neobdm"
        _deep_analysis_status["current_ticker"] = "Running base analysis..."
        try:
            base_results = analyzer.analyze(target_date=actual_date)
            _deep_analysis_status["completed_tickers"].append("base_analysis")
        except Exception as e:
            base_results = []
            _deep_analysis_status["errors"].append({
                "ticker": "all",
                "stage": "neobdm",
                "error": str(e)
            })

        _deep_analysis_status["progress"] = len(tickers)

        # Stage 2: Bandarmology Deep Analysis via API client
        _deep_analysis_status["stage"] = "bandarmology"
        band_repo = BandarmologyRepository()
        neobdm_repo = NeoBDMRepository()
        base_lookup = {r['symbol']: r for r in base_results}

        api_client = NeoBDMApiClient()
        login_ok = await api_client.login()
        if not login_ok:
            _deep_analysis_status["errors"].append({
                "ticker": "all",
                "stage": "bandarmology",
                "error": "NeoBDM API login failed"
            })
        else:
            for i, ticker in enumerate(tickers):
                _deep_analysis_status["current_ticker"] = ticker

                try:
                    # Fetch Inventory
                    inv_data = None
                    price_series = None
                    try:
                        raw_inv = await api_client.get_inventory(ticker)
                        if raw_inv and raw_inv.get('brokers'):
                            band_repo.save_inventory_batch(
                                ticker,
                                raw_inv['brokers'],
                                raw_inv.get('firstDate', ''),
                                raw_inv.get('lastDate', '')
                            )
                            inv_data = raw_inv['brokers']
                            price_series = raw_inv.get('priceSeries')
                    except Exception as e:
                        _deep_analysis_status["errors"].append({
                            "ticker": ticker, "stage": "inventory", "error": str(e)[:80]
                        })

                    await asyncio.sleep(0.5)

                    # Fetch Transaction Chart
                    txn_data = None
                    try:
                        raw_txn = await api_client.get_transaction_chart(ticker)
                        if raw_txn:
                            band_repo.save_transaction_chart(ticker, raw_txn)
                            txn_data = band_repo.get_transaction_chart(ticker)
                    except Exception as e:
                        _deep_analysis_status["errors"].append({
                            "ticker": ticker, "stage": "txn_chart", "error": str(e)[:80]
                        })

                    await asyncio.sleep(0.5)

                    # Fetch Broker Summary
                    broksum_data = None
                    try:
                        raw_broksum = await api_client.get_broker_summary(ticker, actual_date)
                        if raw_broksum:
                            neobdm_repo.save_broker_summary_batch(
                                ticker, actual_date,
                                raw_broksum.get('buy', []),
                                raw_broksum.get('sell', [])
                            )
                            broksum_data = raw_broksum
                    except Exception as e:
                        _deep_analysis_status["errors"].append({
                            "ticker": ticker, "stage": "broksum", "error": str(e)[:80]
                        })

                    await asyncio.sleep(0.3)

                    # Fetch recent broker summary days
                    try:
                        from datetime import datetime as dt, timedelta
                        analysis_dt = dt.strptime(actual_date, '%Y-%m-%d')
                        for day_offset in range(1, 6):
                            check_date = analysis_dt - timedelta(days=day_offset)
                            if check_date.weekday() >= 5:
                                continue
                            date_str = check_date.strftime('%Y-%m-%d')
                            existing = neobdm_repo.get_broker_summary(ticker, date_str)
                            if existing and (existing.get('buy') or existing.get('sell')):
                                continue
                            try:
                                raw_bs = await api_client.get_broker_summary(ticker, date_str)
                                if raw_bs and (raw_bs.get('buy') or raw_bs.get('sell')):
                                    neobdm_repo.save_broker_summary_batch(
                                        ticker, date_str,
                                        raw_bs.get('buy', []),
                                        raw_bs.get('sell', [])
                                    )
                                await asyncio.sleep(0.2)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # Run deep analysis
                    base_data = base_lookup.get(ticker)
                    if base_data or inv_data or txn_data:
                        if not base_data:
                            base_data = {'symbol': ticker, 'total_score': 0}
                        try:
                            broksum_multiday = neobdm_repo.get_broker_summary_multiday(ticker, actual_date, days=5)
                            deep_result = analyzer.analyze_deep(
                                ticker=ticker,
                                inventory_data=inv_data,
                                txn_chart_data=txn_data,
                                broker_summary_data=broksum_data,
                                base_result=base_data,
                                analysis_date=actual_date,
                                price_series=price_series,
                                broksum_multiday_data=broksum_multiday,
                            )
                            if deep_result:
                                band_repo.save_deep_cache(ticker, actual_date, deep_result)
                                _deep_analysis_status["completed_tickers"].append(f"{ticker}_deep")
                        except Exception as e:
                            _deep_analysis_status["errors"].append({
                                "ticker": ticker, "stage": "deep_analysis", "error": str(e)[:120]
                            })
                    else:
                        _deep_analysis_status["completed_tickers"].append(f"{ticker}_skipped")

                except Exception as e:
                    _deep_analysis_status["errors"].append({
                        "ticker": ticker, "stage": "bandarmology", "error": str(e)[:120]
                    })

                _deep_analysis_status["progress"] = len(tickers) + i + 1

        await api_client.close()

    except Exception as e:
        _deep_analysis_status["errors"].append({
            "ticker": "all", "stage": "init", "error": str(e)
        })
    finally:
        _deep_analysis_status["running"] = False
        _deep_analysis_status["stage"] = "completed"
        _deep_analysis_status["current_ticker"] = ""
