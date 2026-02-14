"""Bandarmology routes for stock screening and analysis."""
from fastapi import APIRouter, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging
import asyncio
import numpy as np

router = APIRouter(prefix="/api", tags=["bandarmology"])

logger = logging.getLogger(__name__)

# Track active deep analysis tasks
_deep_analysis_status = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_ticker": "",
    "completed_tickers": [],
    "errors": []
}


def sanitize_data(data):
    """Recursively sanitize data to replace NaN/Inf values with None for JSON compliance."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, float):
        if np.isnan(data) or np.isinf(data):
            return None
        return data
    return data


def _create_minimal_result_from_deep(ticker: str, deep_data: dict, analysis_date: str) -> dict:
    """
    Create a minimal base result entry for a ticker that has deep cache data
    but isn't in the base screening results (e.g., manually deep-analyzed ticker).
    """
    # Get price from deep data if available
    entry_price = deep_data.get('entry_price', 0)
    target_price = deep_data.get('target_price', 0)
    stop_loss = deep_data.get('stop_loss', 0)

    # Use average buy price as current price proxy if entry price not available
    price = entry_price or deep_data.get('broksum_avg_buy_price', 0)

    # Calculate base score from deep data components (simplified)
    # Deep score already has the comprehensive analysis
    deep_score = deep_data.get('deep_score', 0)

    # Base score is derived from available deep metrics
    base_score = min(30, deep_score // 3)  # Conservative estimate

    # Determine confluence status from deep data
    txn_mm_cum = deep_data.get('txn_mm_cum', 0)
    txn_foreign_cum = deep_data.get('txn_foreign_cum', 0)
    txn_institution_cum = deep_data.get('txn_institution_cum', 0)

    # Build positive methods list for confluence display
    positive_methods = []
    if txn_mm_cum > 0:
        positive_methods.append('MM')
    if txn_foreign_cum > 0:
        positive_methods.append('FF')
    if txn_institution_cum > 0:
        positive_methods.append('INST')

    # Determine confluence status
    if len(positive_methods) >= 3:
        confluence_status = 'TRIPLE'
    elif len(positive_methods) == 2:
        confluence_status = 'DOUBLE'
    elif len(positive_methods) == 1:
        confluence_status = 'SINGLE'
    else:
        confluence_status = 'NONE'

    # Get top buyer/seller from deep data if available
    top_buyers = deep_data.get('broksum_top_buyers', [])
    top_sellers = deep_data.get('broksum_top_sellers', [])
    top_buyer = top_buyers[0].get('code', '') if top_buyers else ''
    top_seller = top_sellers[0].get('code', '') if top_sellers else ''

    # Build minimal result structure matching the expected format
    result = {
        'symbol': ticker.upper(),
        'name': ticker.upper(),  # Will display ticker as name
        'price': price,
        'pct_1d': 0,  # Not available for non-screened tickers
        'total_score': base_score,
        'max_score': 100,
        'trade_type': deep_data.get('deep_trade_type', 'WATCH'),
        'ma_above_count': 0,
        'scores': {
            'price_position': 0,
            'flow_alignment': 0,
            'confluence': 0,
            'broker_activity': 0,
            'momentum': 0,
        },
        'confluence_status': confluence_status,
        'positive_methods': positive_methods,  # Required for confluence tooltip
        'pinky': False,
        'crossing': False,
        'unusual': False,
        'likuid': False,
        'flags_detail': {},
        # Weekly/daily flows - not available from base screening
        'w_4': 0, 'w_3': 0, 'w_2': 0, 'w_1': 0,
        'd_0_mm': 0, 'd_0_nr': 0, 'd_0_ff': 0,

        # Broker summary fields (for table display)
        'inst_net_lot': deep_data.get('broksum_net_institutional', 0),
        'foreign_net_lot': deep_data.get('broksum_net_foreign', 0),
        'top_buyer': top_buyer,
        'top_seller': top_seller,

        # Deep analysis fields
        'has_deep': True,
        'deep_score': deep_score,
        'combined_score': base_score + deep_score,
        'max_combined_score': 250,
        'deep_trade_type': deep_data.get('deep_trade_type', '—'),
        'deep_signals': deep_data.get('deep_signals', {}),

        # Inventory
        'inv_accum_brokers': deep_data.get('inv_accum_brokers', 0),
        'inv_distrib_brokers': deep_data.get('inv_distrib_brokers', 0),
        'inv_clean_brokers': deep_data.get('inv_clean_brokers', 0),
        'inv_tektok_brokers': deep_data.get('inv_tektok_brokers', 0),
        'inv_total_accum_lot': deep_data.get('inv_total_accum_lot', 0),
        'inv_top_accum_broker': deep_data.get('inv_top_accum_broker', ''),

        # Transaction chart
        'txn_mm_cum': txn_mm_cum,
        'txn_foreign_cum': txn_foreign_cum,
        'txn_institution_cum': txn_institution_cum,
        'txn_cross_index': deep_data.get('txn_cross_index', 0),
        'txn_mm_trend': deep_data.get('txn_mm_trend', ''),
        'txn_foreign_trend': deep_data.get('txn_foreign_trend', ''),

        # Broker summary
        'broksum_avg_buy_price': deep_data.get('broksum_avg_buy_price', 0),
        'broksum_avg_sell_price': deep_data.get('broksum_avg_sell_price', 0),
        'broksum_floor_price': deep_data.get('broksum_floor_price', 0),
        'broksum_total_buy_lot': deep_data.get('broksum_total_buy_lot', 0),
        'broksum_total_sell_lot': deep_data.get('broksum_total_sell_lot', 0),
        'broksum_net_institutional': deep_data.get('broksum_net_institutional', 0),
        'broksum_net_foreign': deep_data.get('broksum_net_foreign', 0),
        'broksum_top_buyers': top_buyers,
        'broksum_top_sellers': top_sellers,

        # Entry/target
        'entry_price': entry_price,
        'target_price': target_price,
        'stop_loss': stop_loss,
        'risk_reward_ratio': deep_data.get('risk_reward_ratio', 0),

        # Controlling broker
        'controlling_brokers': deep_data.get('controlling_brokers', []),
        'accum_phase': deep_data.get('accum_phase', 'UNKNOWN'),
        'bandar_avg_cost': deep_data.get('bandar_avg_cost', 0),
        'coordination_score': deep_data.get('coordination_score', 0),
        'phase_confidence': deep_data.get('phase_confidence', 'LOW'),
        'breakout_signal': deep_data.get('breakout_signal', 'NONE'),
        'breakout_probability': deep_data.get('breakout_probability', 0),

        # Other deep fields
        'accum_duration_days': deep_data.get('accum_duration_days', 0),
        'concentration_broker': deep_data.get('concentration_broker'),
        'concentration_pct': deep_data.get('concentration_pct', 0),
        'concentration_risk': deep_data.get('concentration_risk', 'NONE'),
        'bandar_confirmation': deep_data.get('bandar_confirmation', 'NONE'),
        'broksum_consistency_score': deep_data.get('broksum_consistency_score', 0),
        'ma_cross_signal': deep_data.get('ma_cross_signal', 'NONE'),
        'phase_transition': deep_data.get('phase_transition', 'NONE'),
        'score_trend': deep_data.get('score_trend', 'NONE'),
        'pump_tomorrow_score': deep_data.get('pump_tomorrow_score', 0),
        'pump_tomorrow_signal': deep_data.get('pump_tomorrow_signal', 'NONE'),

        # Volume confirmation (Improvement 2)
        'volume_confirmation_multiplier': deep_data.get('volume_confirmation_multiplier', 0),

        # Data freshness (Improvement 7)
        'data_freshness': deep_data.get('data_freshness', 1.0),
        'data_source_date': deep_data.get('data_source_date', ''),
        'original_deep_score': deep_data.get('original_deep_score', 0),

        # Target/stop method (Improvement 6)
        'target_method': deep_data.get('target_method', ''),
        'stop_method': deep_data.get('stop_method', ''),
    }

    return result


@router.get("/bandarmology")
async def get_bandarmology_screening(
    date: Optional[str] = Query(None, description="Analysis date (YYYY-MM-DD). None = latest."),
    min_score: int = Query(0, ge=0, le=100, description="Minimum score filter"),
    trade_type: Optional[str] = Query(None, description="Filter by trade type: SWING, INTRADAY, BOTH, WATCH"),
    include_deep: bool = Query(True, description="Include deep analysis data if available")
):
    """
    Get bandarmology screening results with optional deep analysis enrichment.
    """
    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer
        from db.bandarmology_repository import BandarmologyRepository

        analyzer = BandarmologyAnalyzer()
        results = analyzer.analyze(target_date=date)

        # Resolve date for response
        actual_date = analyzer._resolve_date(date)

        # Enrich with deep analysis data if available
        deep_cache = {}
        if include_deep and actual_date:
            try:
                band_repo = BandarmologyRepository()
                deep_cache = band_repo.get_deep_cache_batch(actual_date)
                if deep_cache:
                    # First enrich existing results
                    results = analyzer.enrich_results_with_deep(results, deep_cache)

                    # Add tickers that have deep cache but aren't in base results
                    # (e.g., manually deep-analyzed tickers)
                    base_symbols = {r['symbol'] for r in results}
                    for ticker, deep_data in deep_cache.items():
                        if ticker not in base_symbols:
                            # Create minimal base result for this ticker
                            minimal_result = _create_minimal_result_from_deep(ticker, deep_data, actual_date)
                            results.append(minimal_result)

                    # Re-sort to include new entries
                    results.sort(key=lambda x: x.get('combined_score', x.get('total_score', 0)), reverse=True)
            except Exception as e:
                logger.warning(f"Failed to load deep cache: {e}")

        # Apply filters
        if min_score > 0:
            score_key = 'combined_score' if include_deep else 'total_score'
            results = [r for r in results if r.get(score_key, r.get('total_score', 0)) >= min_score]

        if trade_type:
            trade_type_upper = trade_type.upper()
            if trade_type_upper == "BOTH":
                results = [r for r in results if r['trade_type'] == "BOTH"]
            elif trade_type_upper == "SWING":
                results = [r for r in results if r['trade_type'] in ("SWING", "BOTH")]
            elif trade_type_upper == "INTRADAY":
                results = [r for r in results if r['trade_type'] in ("INTRADAY", "BOTH")]
            elif trade_type_upper == "WATCH":
                results = [r for r in results if r['trade_type'] == "WATCH"]

        return sanitize_data({
            "date": actual_date,
            "total_stocks": len(results),
            "has_deep_data": any(r.get('deep_score', 0) > 0 for r in results),
            "deep_analysis_running": _deep_analysis_status["running"],
            "data": results
        })

    except Exception as e:
        logger.error(f"Bandarmology screening error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/bandarmology/dates")
async def get_bandarmology_dates():
    """Get available dates for bandarmology analysis."""
    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer

        analyzer = BandarmologyAnalyzer()
        dates = analyzer.get_available_dates()

        return {"dates": dates}

    except Exception as e:
        logger.error(f"Bandarmology dates error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/bandarmology/deep-analyze")
async def trigger_deep_analysis(
    background_tasks: BackgroundTasks,
    date: Optional[str] = Query(None, description="Analysis date"),
    top_n: int = Query(30, ge=5, le=100, description="Number of top stocks to deep analyze"),
    min_base_score: int = Query(20, ge=0, description="Minimum base score to qualify for deep analysis")
):
    """
    Trigger deep analysis (inventory + transaction chart scraping) for top N stocks.
    
    This runs as a background task. Poll /bandarmology/deep-status for progress.
    """
    global _deep_analysis_status

    if _deep_analysis_status["running"]:
        return JSONResponse(
            status_code=409,
            content={
                "error": "Deep analysis already running",
                "status": _deep_analysis_status
            }
        )

    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer

        analyzer = BandarmologyAnalyzer()
        results = analyzer.analyze(target_date=date)
        actual_date = analyzer._resolve_date(date)

        # Get top N candidates
        candidates = [r for r in results if r['total_score'] >= min_base_score]
        tickers = [r['symbol'] for r in candidates[:top_n]]

        if not tickers:
            return {"message": "No stocks qualify for deep analysis", "tickers": []}

        # Reset status
        _deep_analysis_status = {
            "running": True,
            "progress": 0,
            "total": len(tickers),
            "current_ticker": "",
            "completed_tickers": [],
            "errors": [],
            "date": actual_date
        }

        # Launch background task
        background_tasks.add_task(
            _run_deep_analysis,
            tickers, actual_date, results
        )

        return {
            "message": f"Deep analysis started for {len(tickers)} stocks",
            "tickers": tickers,
            "date": actual_date
        }

    except Exception as e:
        logger.error(f"Failed to start deep analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/bandarmology/deep-analyze-tickers")
async def trigger_deep_analysis_tickers(
    background_tasks: BackgroundTasks,
    tickers: str = Query(..., description="Comma-separated ticker symbols to deep analyze"),
    date: Optional[str] = Query(None, description="Analysis date"),
):
    """
    Trigger deep analysis for specific tickers (manual input).
    Accepts comma-separated ticker symbols, e.g. ?tickers=BBCA,BMRI,TLKM
    """
    global _deep_analysis_status

    if _deep_analysis_status["running"]:
        return JSONResponse(
            status_code=409,
            content={
                "error": "Deep analysis already running",
                "status": _deep_analysis_status
            }
        )

    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer

        analyzer = BandarmologyAnalyzer()
        actual_date = analyzer._resolve_date(date)
        results = analyzer.analyze(target_date=actual_date)

        # Parse tickers
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if not ticker_list:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid tickers provided"}
            )

        # Reset status
        _deep_analysis_status = {
            "running": True,
            "progress": 0,
            "total": len(ticker_list),
            "current_ticker": "",
            "completed_tickers": [],
            "errors": [],
            "date": actual_date
        }

        background_tasks.add_task(
            _run_deep_analysis,
            ticker_list, actual_date, results
        )

        return {
            "message": f"Deep analysis started for {len(ticker_list)} ticker(s)",
            "tickers": ticker_list,
            "date": actual_date
        }

    except Exception as e:
        logger.error(f"Failed to start manual deep analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/bandarmology/deep-status")
async def get_deep_analysis_status():
    """Get the status of the running deep analysis task."""
    return _deep_analysis_status


async def _run_deep_analysis(tickers: list, analysis_date: str, base_results: list):
    """Background task: scrape inventory + txn chart and run deep scoring."""
    global _deep_analysis_status

    from modules.neobdm_api_client import NeoBDMApiClient
    from modules.bandarmology_analyzer import BandarmologyAnalyzer
    from db.bandarmology_repository import BandarmologyRepository

    band_repo = BandarmologyRepository()
    analyzer = BandarmologyAnalyzer()

    # Build lookup for base results
    base_lookup = {r['symbol']: r for r in base_results}

    api_client = NeoBDMApiClient()
    try:
        login_ok = await api_client.login()
        if not login_ok:
            _deep_analysis_status["running"] = False
            _deep_analysis_status["errors"].append("Login failed")
            return

        from db.neobdm_repository import NeoBDMRepository
        neobdm_repo = NeoBDMRepository()

        for i, ticker in enumerate(tickers):
            _deep_analysis_status["current_ticker"] = ticker
            _deep_analysis_status["progress"] = i

            try:
                # 1. Fetch Inventory via API
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
                    logger.warning(f"Inventory API failed for {ticker}: {e}")
                    _deep_analysis_status["errors"].append(f"{ticker} inv: {str(e)[:80]}")

                await asyncio.sleep(0.5)

                # 2. Fetch Transaction Chart via API
                txn_data = None
                try:
                    raw_txn = await api_client.get_transaction_chart(ticker)
                    if raw_txn:
                        band_repo.save_transaction_chart(ticker, raw_txn)
                        txn_data = band_repo.get_transaction_chart(ticker)
                except Exception as e:
                    logger.warning(f"Txn chart API failed for {ticker}: {e}")
                    _deep_analysis_status["errors"].append(f"{ticker} txn: {str(e)[:80]}")

                await asyncio.sleep(0.5)

                # 3. Fetch Broker Summary via API (analysis_date + recent days)
                broksum_data = None
                try:
                    raw_broksum = await api_client.get_broker_summary(ticker, analysis_date)
                    if raw_broksum:
                        neobdm_repo.save_broker_summary_batch(
                            ticker, analysis_date,
                            raw_broksum.get('buy', []),
                            raw_broksum.get('sell', [])
                        )
                        broksum_data = raw_broksum
                        print(f"   [BROKSUM] Extracted {len(raw_broksum.get('buy',[]))} buy + {len(raw_broksum.get('sell',[]))} sell for {ticker}")
                except Exception as e:
                    logger.warning(f"Broker summary API failed for {ticker}: {e}")
                    _deep_analysis_status["errors"].append(f"{ticker} broksum: {str(e)[:80]}")

                await asyncio.sleep(0.5)

                # 3b. Fetch broker summary for recent trading days (last 4 days before analysis_date)
                recent_dates_fetched = []
                try:
                    from datetime import datetime as dt, timedelta
                    analysis_dt = dt.strptime(analysis_date, '%Y-%m-%d')
                    for day_offset in range(1, 6):
                        check_date = analysis_dt - timedelta(days=day_offset)
                        # Skip weekends
                        if check_date.weekday() >= 5:
                            continue
                        date_str = check_date.strftime('%Y-%m-%d')
                        # Check if we already have this date in DB
                        existing = neobdm_repo.get_broker_summary(ticker, date_str)
                        if existing and (existing.get('buy') or existing.get('sell')):
                            recent_dates_fetched.append(date_str)
                            continue
                        # Fetch from API
                        try:
                            raw_bs = await api_client.get_broker_summary(ticker, date_str)
                            if raw_bs and (raw_bs.get('buy') or raw_bs.get('sell')):
                                neobdm_repo.save_broker_summary_batch(
                                    ticker, date_str,
                                    raw_bs.get('buy', []),
                                    raw_bs.get('sell', [])
                                )
                                recent_dates_fetched.append(date_str)
                            await asyncio.sleep(0.3)
                        except Exception as e2:
                            logger.debug(f"Broksum fetch for {ticker} on {date_str}: {e2}")
                        if len(recent_dates_fetched) >= 4:
                            break
                except Exception as e:
                    logger.warning(f"Recent days broksum fetch failed for {ticker}: {e}")

                # 3c. Extract important dates from inventory (turn_dates, peak_dates)
                important_dates_data = []
                try:
                    if inv_data:
                        # Run controlling broker detection early to get turn/peak dates
                        ctrl_preview = analyzer.detect_controlling_brokers(
                            inv_data, price_series=price_series, min_brokers=3
                        )
                        important_date_set = set()
                        for cb in ctrl_preview.get('controlling_brokers', []):
                            td = cb.get('turn_date')
                            pd = cb.get('peak_date')
                            if td and td != analysis_date:
                                important_date_set.add(td)
                            if pd and pd != analysis_date and pd != td:
                                important_date_set.add(pd)

                        # Fetch broker summary for each important date
                        for imp_date in sorted(important_date_set):
                            existing = neobdm_repo.get_broker_summary(ticker, imp_date)
                            if existing and (existing.get('buy') or existing.get('sell')):
                                important_dates_data.append({
                                    'date': imp_date,
                                    'date_type': 'turn_or_peak',
                                    'buy': existing.get('buy', []),
                                    'sell': existing.get('sell', []),
                                })
                                continue
                            # Fetch from API
                            try:
                                raw_bs = await api_client.get_broker_summary(ticker, imp_date)
                                if raw_bs and (raw_bs.get('buy') or raw_bs.get('sell')):
                                    neobdm_repo.save_broker_summary_batch(
                                        ticker, imp_date,
                                        raw_bs.get('buy', []),
                                        raw_bs.get('sell', [])
                                    )
                                    important_dates_data.append({
                                        'date': imp_date,
                                        'date_type': 'turn_or_peak',
                                        'buy': raw_bs.get('buy', []),
                                        'sell': raw_bs.get('sell', []),
                                    })
                                await asyncio.sleep(0.3)
                            except Exception as e2:
                                logger.debug(f"Important date broksum for {ticker} on {imp_date}: {e2}")

                        if important_dates_data:
                            print(f"   [IMPDATE] Fetched broksum for {len(important_dates_data)} important dates for {ticker}")
                except Exception as e:
                    logger.warning(f"Important dates broksum failed for {ticker}: {e}")

                # 3d. Fetch multi-day broker summary from DB (now enriched with recent fetches)
                broksum_multiday = None
                try:
                    broksum_multiday = neobdm_repo.get_broker_summary_multiday(
                        ticker, analysis_date, days=5
                    )
                except Exception as e:
                    logger.warning(f"Multi-day broksum fetch failed for {ticker}: {e}")

                # 3e. Fetch previous deep cache for historical comparison
                previous_deep = None
                try:
                    previous_deep = band_repo.get_previous_deep_cache(ticker, analysis_date)
                except Exception as e:
                    logger.warning(f"Previous deep cache fetch failed for {ticker}: {e}")

                # 4. Run deep analysis
                base_result = base_lookup.get(ticker)

                # Prepare metadata for data validation
                inventory_meta = None
                if raw_inv:
                    inventory_meta = {
                        'firstDate': raw_inv.get('firstDate'),
                        'lastDate': raw_inv.get('lastDate')
                    }

                broker_summary_meta = {'trade_date': analysis_date} if analysis_date else None

                deep_result = analyzer.analyze_deep(
                    ticker,
                    inventory_data=inv_data,
                    txn_chart_data=txn_data,
                    broker_summary_data=broksum_data,
                    broksum_multiday_data=broksum_multiday,
                    price_series=price_series,
                    base_result=base_result,
                    previous_deep=previous_deep,
                    important_dates_data=important_dates_data if important_dates_data else None,
                    inventory_meta=inventory_meta,
                    broker_summary_meta=broker_summary_meta
                )

                # 5. Save to cache
                band_repo.save_deep_cache(ticker, analysis_date, deep_result)

                _deep_analysis_status["completed_tickers"].append(ticker)

            except Exception as e:
                logger.error(f"Deep analysis failed for {ticker}: {e}")
                _deep_analysis_status["errors"].append(f"{ticker}: {str(e)[:80]}")

            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Critical deep analysis error: {e}")
        _deep_analysis_status["errors"].append(f"Critical: {str(e)[:120]}")
    finally:
        await api_client.close()
        _deep_analysis_status["running"] = False
        _deep_analysis_status["progress"] = len(tickers)
        _deep_analysis_status["current_ticker"] = ""
        logger.info(f"Deep analysis completed: {len(_deep_analysis_status['completed_tickers'])}/{len(tickers)} tickers")


@router.get("/bandarmology/watchlist-alerts")
async def get_watchlist_alerts(
    date: Optional[str] = Query(None, description="Analysis date (YYYY-MM-DD). None = latest.")
):
    """
    Auto-watchlist alerts: flag stocks with notable phase transitions or conditions.
    
    Detects:
    - ACCUMULATION → HOLDING with price near bandar cost (ready for breakout)
    - HOLDING → DISTRIBUTION (exit warning)
    - Score strongly improving (>10 pts gain)
    - Golden cross detected
    """
    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer
        from db.bandarmology_repository import BandarmologyRepository

        analyzer = BandarmologyAnalyzer()
        band_repo = BandarmologyRepository()

        actual_date = analyzer._resolve_date(date)
        if not actual_date:
            return {"date": None, "alerts": []}

        # Get all deep caches for this date
        deep_cache = band_repo.get_deep_cache_batch(actual_date)
        if not deep_cache:
            return {"date": actual_date, "alerts": []}

        # Get base results for price info
        results = analyzer.analyze(target_date=actual_date)
        base_lookup = {r['symbol']: r for r in results}

        alerts = []
        for ticker, deep in deep_cache.items():
            base = base_lookup.get(ticker, {})
            price = base.get('price', 0)
            bandar_cost = deep.get('bandar_avg_cost', 0)
            phase = deep.get('accum_phase', 'UNKNOWN')
            phase_transition = deep.get('phase_transition', 'NONE')
            score_trend = deep.get('score_trend', 'NONE')
            ma_cross = deep.get('ma_cross_signal', 'NONE')
            deep_score = deep.get('deep_score', 0)
            prev_phase = deep.get('prev_phase', '')

            # Calculate price vs cost
            price_vs_cost_pct = 0
            if price > 0 and bandar_cost > 0:
                price_vs_cost_pct = round((price - bandar_cost) / bandar_cost * 100, 1)

            # Alert 1: ACCUMULATION → HOLDING with price near cost (READY)
            if phase_transition == 'ACCUMULATION_TO_HOLDING' and bandar_cost > 0:
                near_cost = -5 <= price_vs_cost_pct <= 10
                alerts.append({
                    "ticker": ticker,
                    "alert_type": "PHASE_READY",
                    "priority": "HIGH" if near_cost else "MEDIUM",
                    "description": f"Fase berubah AKUMULASI → HOLDING, harga {price_vs_cost_pct:+.1f}% dari cost bandar ({bandar_cost:,.0f})",
                    "phase": phase,
                    "prev_phase": prev_phase,
                    "price": price,
                    "bandar_cost": bandar_cost,
                    "price_vs_cost_pct": price_vs_cost_pct,
                    "deep_score": deep_score,
                })

            # Alert 2: HOLDING with price near cost and high deep score (watchlist candidate)
            elif phase == 'HOLDING' and bandar_cost > 0 and -5 <= price_vs_cost_pct <= 10 and deep_score >= 30:
                alerts.append({
                    "ticker": ticker,
                    "alert_type": "HOLDING_NEAR_COST",
                    "priority": "HIGH",
                    "description": f"HOLDING + harga dekat cost bandar ({price_vs_cost_pct:+.1f}%), deep score {deep_score}",
                    "phase": phase,
                    "prev_phase": prev_phase,
                    "price": price,
                    "bandar_cost": bandar_cost,
                    "price_vs_cost_pct": price_vs_cost_pct,
                    "deep_score": deep_score,
                })

            # Alert 3: HOLDING/ACCUMULATION → DISTRIBUTION (exit warning)
            elif phase_transition in ('HOLDING_TO_DISTRIBUTION', 'ACCUMULATION_TO_DISTRIBUTION'):
                alerts.append({
                    "ticker": ticker,
                    "alert_type": "PHASE_EXIT",
                    "priority": "HIGH",
                    "description": f"WARNING: Fase berubah {prev_phase} → DISTRIBUSI, bandar mulai jual!",
                    "phase": phase,
                    "prev_phase": prev_phase,
                    "price": price,
                    "bandar_cost": bandar_cost,
                    "price_vs_cost_pct": price_vs_cost_pct,
                    "deep_score": deep_score,
                })

            # Alert 4: Golden cross detected
            elif ma_cross == 'GOLDEN_CROSS' and deep_score >= 20:
                alerts.append({
                    "ticker": ticker,
                    "alert_type": "GOLDEN_CROSS",
                    "priority": "MEDIUM",
                    "description": f"GOLDEN CROSS terdeteksi, deep score {deep_score}",
                    "phase": phase,
                    "prev_phase": prev_phase,
                    "price": price,
                    "bandar_cost": bandar_cost,
                    "price_vs_cost_pct": price_vs_cost_pct,
                    "deep_score": deep_score,
                })

            # Alert 5: Score strongly improving
            elif score_trend == 'STRONG_IMPROVING' and deep_score >= 25:
                alerts.append({
                    "ticker": ticker,
                    "alert_type": "SCORE_SURGE",
                    "priority": "MEDIUM",
                    "description": f"Deep score naik signifikan (sekarang {deep_score}, sebelumnya {deep.get('prev_deep_score', 0)})",
                    "phase": phase,
                    "prev_phase": prev_phase,
                    "price": price,
                    "bandar_cost": bandar_cost,
                    "price_vs_cost_pct": price_vs_cost_pct,
                    "deep_score": deep_score,
                })

        # Sort by priority (HIGH first) then by deep_score
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        alerts.sort(key=lambda a: (priority_order.get(a['priority'], 2), -a['deep_score']))

        return sanitize_data({
            "date": actual_date,
            "total_alerts": len(alerts),
            "alerts": alerts
        })

    except Exception as e:
        logger.error(f"Watchlist alerts error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/bandarmology/{ticker}/detail")
async def get_stock_detail(
    ticker: str,
    date: Optional[str] = Query(None, description="Analysis date")
):
    """
    Get detailed deep analysis for a single stock.
    
    Returns comprehensive data including:
    - Base screening scores
    - Inventory broker breakdown (accumulation/distribution)
    - Transaction chart flows (MM, Foreign, Institution)
    - Broker summary (top buyers/sellers, avg prices)
    - Entry/target price analysis
    - Swing vs Intraday classification with reasoning
    """
    try:
        from modules.bandarmology_analyzer import BandarmologyAnalyzer
        from db.bandarmology_repository import BandarmologyRepository
        from db.neobdm_repository import NeoBDMRepository

        analyzer = BandarmologyAnalyzer()
        band_repo = BandarmologyRepository()
        neobdm_repo = NeoBDMRepository()

        actual_date = analyzer._resolve_date(date)
        ticker_upper = ticker.upper()

        # 1. Get base screening result
        results = analyzer.analyze(target_date=actual_date)
        base_result = next((r for r in results if r['symbol'] == ticker_upper), None)

        # 2. Get deep cache (check early to handle tickers not in screening)
        deep_cache = band_repo.get_deep_cache(ticker_upper, actual_date)

        # If not in screening results but has deep cache, create minimal base result
        if not base_result and deep_cache:
            logger.info(f"Ticker {ticker_upper} not in screening but has deep cache, using deep data only")
            base_result = _create_minimal_result_from_deep(ticker_upper, deep_cache, actual_date)

        if not base_result:
            return JSONResponse(
                status_code=404,
                content={"error": f"Stock {ticker_upper} not found in screening results or deep analysis cache"}
            )

        # 3. Get inventory brokers from DB
        inventory_brokers = band_repo.get_inventory(ticker_upper)

        # 4. Get transaction chart from DB
        txn_chart = band_repo.get_transaction_chart(ticker_upper)

        # 5. Get broker summary from DB
        broker_summary = neobdm_repo.get_broker_summary(ticker_upper, actual_date)

        # 6. Get floor price analysis (historical)
        floor_analysis = neobdm_repo.get_floor_price_analysis(ticker_upper, days=30)

        # 7. Get top holders
        top_holders = neobdm_repo.get_top_holders_by_net_lot(ticker_upper, limit=5)

        # Build response
        detail = {
            "ticker": ticker_upper,
            "date": actual_date,
            "has_deep": deep_cache is not None and deep_cache.get('deep_score', 0) > 0,

            # Base screening
            "base_score": base_result.get('total_score', 0),
            "max_base_score": base_result.get('max_score', 100),
            "trade_type": base_result.get('trade_type', '—'),
            "price": base_result.get('price', 0),
            "pct_1d": base_result.get('pct_1d', 0),
            "ma_above_count": base_result.get('ma_above_count', 0),
            "pinky": base_result.get('pinky', False),
            "crossing": base_result.get('crossing', False),
            "unusual": base_result.get('unusual', False),
            "likuid": base_result.get('likuid', False),
            "confluence_status": base_result.get('confluence_status', 'NONE'),
            "scores": base_result.get('scores', {}),

            # Weekly/daily flows
            "w_4": base_result.get('w_4', 0),
            "w_3": base_result.get('w_3', 0),
            "w_2": base_result.get('w_2', 0),
            "w_1": base_result.get('w_1', 0),
            "d_0_mm": base_result.get('d_0_mm', 0),
            "d_0_nr": base_result.get('d_0_nr', 0),
            "d_0_ff": base_result.get('d_0_ff', 0),
        }

        # Deep analysis data
        if deep_cache:
            detail.update({
                "deep_score": deep_cache.get('deep_score', 0),
                "combined_score": base_result.get('total_score', 0) + deep_cache.get('deep_score', 0),
                "max_combined_score": 250,
                "deep_trade_type": deep_cache.get('deep_trade_type', '—'),
                "deep_signals": deep_cache.get('deep_signals', {}),

                # Inventory
                "inv_accum_brokers": deep_cache.get('inv_accum_brokers', 0),
                "inv_distrib_brokers": deep_cache.get('inv_distrib_brokers', 0),
                "inv_clean_brokers": deep_cache.get('inv_clean_brokers', 0),
                "inv_tektok_brokers": deep_cache.get('inv_tektok_brokers', 0),
                "inv_total_accum_lot": deep_cache.get('inv_total_accum_lot', 0),
                "inv_total_distrib_lot": deep_cache.get('inv_total_distrib_lot', 0),
                "inv_top_accum_broker": deep_cache.get('inv_top_accum_broker', ''),

                # Transaction chart
                "txn_mm_cum": deep_cache.get('txn_mm_cum', 0),
                "txn_foreign_cum": deep_cache.get('txn_foreign_cum', 0),
                "txn_institution_cum": deep_cache.get('txn_institution_cum', 0),
                "txn_retail_cum": deep_cache.get('txn_retail_cum', 0),
                "txn_cross_index": deep_cache.get('txn_cross_index', 0),
                "txn_mm_trend": deep_cache.get('txn_mm_trend', ''),
                "txn_foreign_trend": deep_cache.get('txn_foreign_trend', ''),

                # Broker summary
                "broksum_total_buy_lot": deep_cache.get('broksum_total_buy_lot', 0),
                "broksum_total_sell_lot": deep_cache.get('broksum_total_sell_lot', 0),
                "broksum_avg_buy_price": deep_cache.get('broksum_avg_buy_price', 0),
                "broksum_avg_sell_price": deep_cache.get('broksum_avg_sell_price', 0),
                "broksum_floor_price": deep_cache.get('broksum_floor_price', 0),
                "broksum_net_institutional": deep_cache.get('broksum_net_institutional', 0),
                "broksum_net_foreign": deep_cache.get('broksum_net_foreign', 0),
                "broksum_top_buyers": deep_cache.get('broksum_top_buyers', []),
                "broksum_top_sellers": deep_cache.get('broksum_top_sellers', []),

                # Entry/target
                "entry_price": deep_cache.get('entry_price', 0),
                "target_price": deep_cache.get('target_price', 0),
                "stop_loss": deep_cache.get('stop_loss', 0),
                "risk_reward_ratio": deep_cache.get('risk_reward_ratio', 0),
                "target_method": deep_cache.get('target_method', ''),
                "stop_method": deep_cache.get('stop_method', ''),

                # Controlling broker analysis
                "controlling_brokers": deep_cache.get('controlling_brokers', []),
                "accum_start_date": deep_cache.get('accum_start_date'),
                "accum_phase": deep_cache.get('accum_phase', 'UNKNOWN'),
                "bandar_avg_cost": deep_cache.get('bandar_avg_cost', 0),
                "bandar_total_lot": deep_cache.get('bandar_total_lot', 0),
                "coordination_score": deep_cache.get('coordination_score', 0),
                "phase_confidence": deep_cache.get('phase_confidence', 'LOW'),
                "breakout_signal": deep_cache.get('breakout_signal', 'NONE'),
                "bandar_peak_lot": deep_cache.get('bandar_peak_lot', 0),
                "bandar_distribution_pct": deep_cache.get('bandar_distribution_pct', 0.0),
                "distribution_alert": deep_cache.get('distribution_alert', 'NONE'),

                # Cross-reference: broker summary <-> inventory
                "bandar_buy_today_count": deep_cache.get('bandar_buy_today_count', 0),
                "bandar_sell_today_count": deep_cache.get('bandar_sell_today_count', 0),
                "bandar_buy_today_lot": deep_cache.get('bandar_buy_today_lot', 0),
                "bandar_sell_today_lot": deep_cache.get('bandar_sell_today_lot', 0),
                "bandar_confirmation": deep_cache.get('bandar_confirmation', 'NONE'),

                # Multi-day consistency
                "broksum_days_analyzed": deep_cache.get('broksum_days_analyzed', 0),
                "broksum_consistency_score": deep_cache.get('broksum_consistency_score', 0),
                "broksum_consistent_buyers": deep_cache.get('broksum_consistent_buyers', []),
                "broksum_consistent_sellers": deep_cache.get('broksum_consistent_sellers', []),

                # Breakout probability
                "breakout_probability": deep_cache.get('breakout_probability', 0),
                "breakout_factors": deep_cache.get('breakout_factors', {}),

                # Accumulation duration
                "accum_duration_days": deep_cache.get('accum_duration_days', 0),

                # Concentration risk
                "concentration_broker": deep_cache.get('concentration_broker'),
                "concentration_pct": deep_cache.get('concentration_pct', 0.0),
                "concentration_risk": deep_cache.get('concentration_risk', 'NONE'),

                # Smart money vs retail divergence
                "txn_smart_money_cum": deep_cache.get('txn_smart_money_cum', 0),
                "txn_retail_cum_deep": deep_cache.get('txn_retail_cum_deep', 0),
                "smart_retail_divergence": deep_cache.get('smart_retail_divergence', 0),

                # Volume context
                "volume_score": deep_cache.get('volume_score', 0),
                "volume_signal": deep_cache.get('volume_signal', 'NONE'),
                "volume_confirmation_multiplier": deep_cache.get('volume_confirmation_multiplier', 0),

                # MA cross
                "ma_cross_signal": deep_cache.get('ma_cross_signal', 'NONE'),
                "ma_cross_score": deep_cache.get('ma_cross_score', 0),

                # Historical comparison
                "prev_deep_score": deep_cache.get('prev_deep_score', 0),
                "prev_phase": deep_cache.get('prev_phase', ''),
                "phase_transition": deep_cache.get('phase_transition', 'NONE'),
                "score_trend": deep_cache.get('score_trend', 'NONE'),

                # Flow velocity/acceleration
                "flow_velocity_mm": deep_cache.get('flow_velocity_mm', 0),
                "flow_velocity_foreign": deep_cache.get('flow_velocity_foreign', 0),
                "flow_velocity_institution": deep_cache.get('flow_velocity_institution', 0),
                "flow_acceleration_mm": deep_cache.get('flow_acceleration_mm', 0),
                "flow_acceleration_signal": deep_cache.get('flow_acceleration_signal', 'NONE'),
                "flow_velocity_score": deep_cache.get('flow_velocity_score', 0),

                # Important dates broker summary
                "important_dates": deep_cache.get('important_dates', []),
                "important_dates_score": deep_cache.get('important_dates_score', 0),
                "important_dates_signal": deep_cache.get('important_dates_signal', 'NONE'),

                # Pump tomorrow prediction
                "pump_tomorrow_score": deep_cache.get('pump_tomorrow_score', 0),
                "pump_tomorrow_signal": deep_cache.get('pump_tomorrow_signal', 'NONE'),
                "pump_tomorrow_factors": deep_cache.get('pump_tomorrow_factors', {}),

                # Data freshness (Improvement 7)
                "data_freshness": deep_cache.get('data_freshness', 1.0),
                "data_source_date": deep_cache.get('data_source_date', ''),
                "original_deep_score": deep_cache.get('original_deep_score', 0),
            })
        else:
            detail.update({
                "deep_score": 0,
                "combined_score": base_result.get('total_score', 0),
                "max_combined_score": 250,
                "ma_cross_signal": 'NONE',
                "ma_cross_score": 0,
                "prev_deep_score": 0,
                "prev_phase": '',
                "phase_transition": 'NONE',
                "score_trend": 'NONE',
            })

        # Inventory broker detail list
        if inventory_brokers:
            detail["inventory_brokers"] = inventory_brokers
        else:
            detail["inventory_brokers"] = []

        # Transaction chart raw data
        if txn_chart:
            detail["txn_chart"] = txn_chart
        else:
            detail["txn_chart"] = None

        # Broker summary detail
        detail["broker_summary"] = broker_summary if broker_summary else {"buy": [], "sell": []}

        # Floor price analysis
        detail["floor_analysis"] = floor_analysis if floor_analysis else {}

        # Top holders
        detail["top_holders"] = top_holders if top_holders else []

        return sanitize_data(detail)

    except Exception as e:
        logger.error(f"Stock detail error for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
