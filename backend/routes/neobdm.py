"""NeoBDM routes for market maker/non-retail/foreign flow analysis."""
from fastapi import APIRouter, Query, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import logging
import asyncio
import json
import os
import numpy as np

router = APIRouter(prefix="/api", tags=["neobdm"])


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


class BrokerSummaryBatchTask(BaseModel):
    ticker: str
    dates: List[str]


@router.get("/neobdm-summary")
async def get_neobdm_summary(
    method: str = "m",
    period: str = "c",
    scrape: bool = Query(False),
    scrape_date: Optional[str] = None
):
    """
    Get NeoBDM market summary data.
    
    Args:
        method: Analysis method ('m'=Market Maker, 'nr'=Non-Retail, 'f'=Foreign Flow)
        period: Time period ('d'=Daily, 'c'=Cumulative)
        scrape: If True, scrape fresh data from NeoBDM website
        scrape_date: Specific date to fetch from database (YYYY-MM-DD)
    
    Returns:
        Scraped_at timestamp and data array
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()

    if scrape:
        try:
            from modules.neobdm_api_client import NeoBDMApiClient
            api_client = NeoBDMApiClient()
            try:
                df, reference_date = await api_client.get_market_summary(method=method, period=period)
            finally:
                await api_client.close()
            
            if df is not None and not df.empty:
                data_list = df.to_dict(orient="records")
                scraped_at = reference_date if reference_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                db_manager.save_neobdm_record_batch(method, period, data_list, scraped_at=scraped_at)
                return {
                    "scraped_at": scraped_at,
                    "data": sanitize_data(data_list)
                }
            return {"scraped_at": None, "data": []}
        except Exception as e:
            logging.error(f"NeoBDM Summary API error: {e}")
            return {"error": str(e), "data": []}
    else:
        # Fetch from DB
        df = db_manager.get_neobdm_summaries(
            method=method, 
            period=period, 
            start_date=scrape_date, 
            end_date=scrape_date
        )
        if df.empty:
            return {"scraped_at": None, "data": []}
        
        # Handle legacy format with data_json
        if 'data_json' in df.columns:
            latest = df.iloc[0]
            try:
                data_list = json.loads(latest['data_json'])
                scraped_at = latest['scraped_at']
                return {
                    "scraped_at": scraped_at,
                    "data": sanitize_data(data_list)
                }
            except Exception:
                return {"scraped_at": None, "data": []}
        
        # New structure returns individual rows
        scraped_at = df.iloc[0]['scraped_at'] if 'scraped_at' in df.columns else None
        
        return {
            "scraped_at": scraped_at,
            "data": sanitize_data(df.to_dict(orient="records"))
        }


@router.get("/neobdm-broker-summary")
async def get_neobdm_broker_summary(
    ticker: str,
    trade_date: str,
    scrape: bool = Query(False)
):
    """
    Get or scrape broker summary for a specific ticker and date.
    
    Args:
        ticker: Stock ticker
        trade_date: Trade date (YYYY-MM-DD)
        scrape: Whether to force scrape fresh data
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()

    if scrape:
        try:
            from modules.neobdm_api_client import NeoBDMApiClient
            api_client = NeoBDMApiClient()
            try:
                data = await api_client.get_broker_summary(ticker.upper(), trade_date)
            finally:
                await api_client.close()
            
            if data and (data.get('buy') or data.get('sell')):
                db_manager.save_broker_summary_batch(
                    ticker.upper(), 
                    trade_date, 
                    data.get('buy', []), 
                    data.get('sell', [])
                )
                normalized = db_manager.get_broker_summary(ticker.upper(), trade_date)
                return {
                    "ticker": ticker.upper(),
                    "trade_date": trade_date,
                    "buy": normalized.get('buy', []),
                    "sell": normalized.get('sell', []),
                    "source": "api"
                }
            return {
                "ticker": ticker.upper(),
                "trade_date": trade_date,
                "buy": [],
                "sell": [],
                "source": "api"
            }
            
        except Exception as e:
            logging.error(f"Broker Summary API error: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})
    else:
        # Fetch from DB
        data = db_manager.get_broker_summary(ticker.upper(), trade_date)
        return {
            "ticker": ticker.upper(),
            "trade_date": trade_date,
            "buy": data.get('buy', []),
            "sell": data.get('sell', []),
            "source": "database"
        }


@router.get("/neobdm-broker-summary/available-dates/{ticker}")
async def get_broker_summary_available_dates(ticker: str):
    """
    Get list of available dates where broker summary data exists for a ticker.
    
    Args:
        ticker: Stock ticker
    
    Returns:
        List of dates with data available
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    
    try:
        dates = db_manager.get_available_dates_for_ticker(ticker.upper())
        return {
            "ticker": ticker.upper(),
            "available_dates": dates,
            "total_count": len(dates)
        }
    except Exception as e:
        logging.error(f"Error fetching available dates for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


class BrokerJourneyRequest(BaseModel):
    ticker: str
    brokers: List[str]
    start_date: str
    end_date: str


@router.post("/neobdm-broker-summary/journey")
async def get_broker_journey_data(request: BrokerJourneyRequest):
    """
    Get broker journey data showing accumulation/distribution over time.
    
    Request Body:
        {
            "ticker": "ANTM",
            "brokers": ["YP", "RH", "OP"],
            "start_date": "2026-01-01",
            "end_date": "2026-01-13"
        }
    
    Returns:
        Broker journey data with daily breakdown and cumulative tracking
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    
    try:
        if not request.brokers:
            return JSONResponse(
                status_code=400,
                content={"error": "At least one broker must be specified"}
            )
        
        journey_data = db_manager.get_broker_journey(
            request.ticker.upper(),
            request.brokers,
            request.start_date,
            request.end_date
        )
        
        return journey_data
        
    except Exception as e:
        logging.error(f"Error fetching broker journey: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/neobdm-broker-summary/top-holders/{ticker}")
async def get_top_holders(
    ticker: str,
    limit: int = Query(3, ge=1, le=10)
):
    """
    Get top N holders for a ticker based on cumulative net lot.
    
    Args:
        ticker: Stock ticker symbol
        limit: Number of top holders to return (default 3, max 10)
    
    Returns:
        {
            "ticker": "ANTM",
            "top_holders": [
                {
                    "broker_code": "YP",
                    "total_net_lot": 150000,
                    "total_net_value": 1250.5,
                    "trade_count": 15,
                    "first_date": "2026-01-01",
                    "last_date": "2026-01-13"
                },
                ...
            ]
        }
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    
    try:
        top_holders = db_manager.get_top_holders_by_net_lot(ticker.upper(), limit)
        return {
            "ticker": ticker.upper(),
            "top_holders": top_holders
        }
    except Exception as e:
        logging.error(f"Error fetching top holders for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/neobdm-broker-summary/floor-price/{ticker}")
async def get_floor_price_analysis(
    ticker: str,
    days: int = Query(30, ge=0, le=365, description="Number of days (0 = all data)")
):
    """
    Get floor price analysis based on institutional broker buy prices.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to analyze (default 30, range 7-90)
    
    Returns:
        {
            "ticker": "ANTM",
            "floor_price": 1450,
            "confidence": "HIGH" | "MEDIUM" | "LOW" | "NO_DATA",
            "institutional_buy_value": 125.5,
            "institutional_buy_lot": 15000,
            "institutional_brokers": [...],
            "foreign_brokers": [...],
            "days_analyzed": 15
        }
    """
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    
    try:
        analysis = db_manager.get_floor_price_analysis(ticker.upper(), days)
        return analysis
    except Exception as e:
        logging.error(f"Error fetching floor price for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/neobdm-dates")
def get_neobdm_dates():
    """Get list of available scrape dates in database."""
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    dates = db_manager.get_available_neobdm_dates()
    return {"dates": dates}


@router.post("/neobdm-batch-scrape")
async def run_neobdm_batch_scrape(background_tasks: BackgroundTasks):
    """
    Full synchronization of all NeoBDM data (Background Task).
    """
    background_tasks.add_task(perform_full_sync)
    return {
        "status": "processing",
        "message": "Full synchronization started in the background. This will take a few minutes."
    }


async def perform_full_sync():
    """Core logic for background sync using a SEPARATE SUBPROCESS.

    Spawns batch_scrape_neobdm.py as a standalone process to avoid Windows
    event loop conflicts (Playwright async API can't create subprocesses
    inside uvicorn's ProactorEventLoop on Windows).
    
    The subprocess uses Playwright to capture ALL columns including flags
    (pinky, crossing, unusual, likuid, suspend, special_notice) and MA values.
    """
    import subprocess
    import sys
    
    try:
        start_time = datetime.now()
        print(f"[*] Starting background Full Sync at {start_time}")
        print(f"[*] Using SUBPROCESS approach (separate Python process for Playwright)")
        
        # Resolve paths
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(backend_dir, "scripts", "batch_scrape_neobdm.py")
        
        # Run the batch scrape script as a separate process
        # This avoids the Windows asyncio subprocess limitation
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [sys.executable, script_path],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
        )
        
        # Print subprocess output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                print(f"  {line}")
        
        if result.returncode != 0:
            print(f"[!] Batch scrape subprocess exited with code {result.returncode}")
            if result.stderr:
                print(f"[!] Stderr: {result.stderr[-500:]}")
        else:
            print(f"[*] Batch scrape subprocess completed successfully.")
            
        duration = datetime.now() - start_time
        print(f"\n[*] Background Full Sync completed in {duration.total_seconds():.2f}s.")

    except subprocess.TimeoutExpired:
        print(f"[!] Batch scrape subprocess timed out after 600s")
    except Exception as e:
        print(f"[!] Critical error in background sync: {e}")
        logging.error(f"Critical error in background sync: {e}")


@router.get("/neobdm-history")
@router.get("/neobdm/history") # Al ias to fix potential 404s from slash/dash mismatch
def get_neobdm_history(
    symbol: str = None,
    ticker: str = None,
    method: str = "m",
    period: str = "c",
    limit: int = 30
):
    """
    Get historical money flow data for a ticker.
    
    Args:
        symbol: Stock symbol (primary)
        ticker: Alternative name for symbol (compatibility)
        method: Analysis method
        period: Time period
        limit: Number of days to return
    """
    from modules.database import DatabaseManager
    from data_provider import data_provider
    
    # Use symbol or fallback to ticker
    stock_symbol = symbol or ticker
    
    if not stock_symbol:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required parameter: symbol or ticker"}
        )
    
    try:
        db_manager = DatabaseManager()
        history_data = db_manager.get_neobdm_history(stock_symbol.upper(), method, period, limit)
        
        # NEW: Enrich dengan market cap dan flow impact
        market_cap = data_provider.get_market_cap(stock_symbol)
        
        if market_cap:
            for record in history_data:
                # Add market cap to each record
                record['market_cap'] = market_cap
                
                # Calculate flow impact if we have flow data
                flow_d0 = record.get('flow_d0', 0)
                if flow_d0 != 0:
                    flow_impact = data_provider.calculate_flow_impact(flow_d0, market_cap)
                    record['flow_impact_pct'] = flow_impact['impact_pct']
                    record['impact_label'] = flow_impact['impact_label']
                    record['normalized_flow'] = flow_impact['flow_idr']
                else:
                    record['flow_impact_pct'] = 0.0
                    record['impact_label'] = 'MINIMAL'
                    record['normalized_flow'] = 0.0
        
        # Return with backward-compatible structure (sanitize to prevent NaN/Inf JSON errors)
        return {
            "symbol": stock_symbol.upper(),
            "history": sanitize_data(history_data)
        }
    
    except Exception as e:
        logging.error(f"Error fetching NeoBDM history: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/neobdm-tickers")
async def get_neobdm_tickers():
    """Get list of all tickers available in NeoBDM data."""
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    try:
        tickers = db_manager.get_neobdm_tickers()
        return {"tickers": tickers}
    except Exception as e:
        logging.error(f"NeoBDM Tickers error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/neobdm-hot")
async def get_neobdm_hot():
    """Get hot signals - stocks with interesting flow patterns."""
    from modules.database import DatabaseManager
    db_manager = DatabaseManager()
    try:
        hot_list = db_manager.get_latest_hot_signals()
        return {"signals": hot_list}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/broker-summary")
async def get_broker_summary_api(
    ticker: str,
    trade_date: str,
    scrape: bool = Query(False)
):
    """
    Get broker summary data (Net Buy & Net Sell).
    If data is not in DB or scrape=True, trigger the scraper.
    """
    from modules.database import DatabaseManager
    from modules.neobdm_api_client import NeoBDMApiClient
    
    db_manager = DatabaseManager()
    
    # 1. Try to fetch from DB first (unless forced scrape)
    if not scrape:
        data = db_manager.get_broker_summary(ticker.upper(), trade_date)
        if data['buy'] or data['sell']:
            print(f"[*] Found broker summary for {ticker} on {trade_date} in DB.")
            return {
                "ticker": ticker.upper(),
                "trade_date": trade_date,
                "buy": data['buy'],
                "sell": data['sell'],
                "source": "database"
            }
            
    # 2. Fetch via API if needed
    print(f"[*] Fetching broker summary for {ticker} on {trade_date} via API...")
    api_client = NeoBDMApiClient()
    try:
        scraped_data = await api_client.get_broker_summary(ticker.upper(), trade_date)
        
        if scraped_data and (scraped_data.get('buy') or scraped_data.get('sell')):
            # Save to DB, then return normalized DB output
            db_manager.save_broker_summary_batch(
                ticker=ticker,
                trade_date=trade_date,
                buy_data=scraped_data['buy'],
                sell_data=scraped_data['sell']
            )

            data = db_manager.get_broker_summary(ticker.upper(), trade_date)
            return {
                "ticker": ticker.upper(),
                "trade_date": trade_date,
                "buy": data['buy'],
                "sell": data['sell'],
                "source": "api"
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"No data found for {ticker} on {trade_date}"}
            )
            
    except Exception as e:
        logging.error(f"Broker Summary API error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    finally:
        await api_client.close()


@router.post("/neobdm-broker-summary-batch")
async def run_neobdm_broker_summary_batch(
    background_tasks: BackgroundTasks,
    tasks: List[BrokerSummaryBatchTask] = Body(...)
):
    """
    Trigger a batch scraping job for multiple tickers and dates.
    Format: [{"ticker": "ANTM", "dates": ["2026-01-12", "2026-01-11"]}, ...]
    """
    if not tasks:
        return JSONResponse(status_code=400, content={"error": "No batch tasks provided"})

    tasks_payload = [task.dict() for task in tasks]
    background_tasks.add_task(perform_broker_summary_batch_sync, tasks_payload)
    return {
        "status": "processing",
        "message": f"Scrape job started for {len(tasks)} tickers. Data will be available in the database shortly."
    }


async def perform_broker_summary_batch_sync(tasks: list):
    """Background task for batch broker summary sync via API."""
    from modules.neobdm_api_client import NeoBDMApiClient
    from modules.database import DatabaseManager
    import logging
    
    db_manager = DatabaseManager()
    api_client = NeoBDMApiClient()
    
    try:
        results = await api_client.get_broker_summary_batch(tasks)
        success_count = 0
        error_count = 0
        for res in results:
            if "error" not in res:
                db_manager.save_broker_summary_batch(
                    ticker=res['ticker'],
                    trade_date=res['trade_date'],
                    buy_data=res['buy'],
                    sell_data=res['sell']
                )
                success_count += 1
            else:
                error_count += 1
                logging.warning(f"[!] Batch Broker Summary error for {res.get('ticker')} on {res.get('trade_date')}: {res.get('error')}")
        
        print(f"[*] Batch Broker Summary Sync completed. {success_count} saved, {error_count} errors.")
        
    except Exception as e:
        logging.error(f"Error in background batch broker summary sync: {e}")
    finally:
        await api_client.close()


@router.get("/volume-daily")
async def get_volume_daily(ticker: str):
    """
    Get daily volume data for a ticker with smart incremental fetching.
    
    Args:
        ticker: Stock ticker (e.g., 'BBCA')
    
    Returns:
        {
            "ticker": "BBCA",
            "data": [
                {
                    "trade_date": "2025-12-22",
                    "volume": 12500000,
                    "close_price": 8750,
                    ...
                }
            ],
            "source": "database" | "fetched_full" | "fetched_incremental",
            "records_added": 10
        }
    """
    from db.neobdm_repository import NeoBDMRepository
    
    try:
        neobdm_repo = NeoBDMRepository()
        result = neobdm_repo.get_or_fetch_volume(ticker.upper())
        
        return result
        
    except Exception as e:
        logging.error(f"Error fetching volume data for {ticker}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
