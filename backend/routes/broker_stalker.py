"""Broker Stalker API routes."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from modules.broker_stalker_analyzer import BrokerStalkerAnalyzer
from db import BrokerStalkerRepository

router = APIRouter(prefix="/api/broker-stalker", tags=["Broker Stalker"])

analyzer = BrokerStalkerAnalyzer()
repo = BrokerStalkerRepository()


class AddBrokerRequest(BaseModel):
    broker_code: str
    broker_name: Optional[str] = None
    description: Optional[str] = None


class SyncRequest(BaseModel):
    ticker: Optional[str] = None
    days: int = 7


@router.get("/watchlist")
async def get_watchlist():
    """
    Get all brokers in the watchlist.
    
    Returns:
        List of brokers with their power levels
    """
    try:
        watchlist = repo.get_watchlist()
        return {
            "status": "success",
            "count": len(watchlist),
            "brokers": watchlist
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist")
async def add_broker_to_watchlist(request: AddBrokerRequest):
    """
    Add a broker to the watchlist.
    
    Args:
        request: Broker details
    
    Returns:
        Success status
    """
    try:
        success = repo.add_broker_to_watchlist(
            request.broker_code,
            request.broker_name,
            request.description
        )
        
        if success:
            power_level = analyzer.calculate_power_level(request.broker_code)
            
            return {
                "status": "success",
                "message": f"Broker {request.broker_code} added to watchlist",
                "broker_code": request.broker_code,
                "power_level": power_level
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to add broker")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{broker_code}")
async def remove_broker_from_watchlist(broker_code: str):
    """
    Remove a broker from the watchlist.
    
    Args:
        broker_code: Broker code to remove
    
    Returns:
        Success status
    """
    try:
        success = repo.remove_broker_from_watchlist(broker_code)
        
        if success:
            return {
                "status": "success",
                "message": f"Broker {broker_code} removed from watchlist"
            }
        else:
            raise HTTPException(status_code=404, detail="Broker not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/{broker_code}")
async def get_broker_portfolio(
    broker_code: str,
    min_net_value: float = Query(default=0, description="Minimum net value filter")
):
    """
    Get broker's current portfolio (active positions).
    
    Args:
        broker_code: Broker code
        min_net_value: Minimum net value to include
    
    Returns:
        Portfolio positions
    """
    try:
        portfolio = repo.get_broker_portfolio(broker_code, min_net_value)
        
        total_net = sum(p['total_net_value'] for p in portfolio)
        
        return {
            "status": "success",
            "broker_code": broker_code,
            "total_positions": len(portfolio),
            "total_net_value": total_net,
            "portfolio": portfolio
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{broker_code}/{ticker}")
async def get_broker_analysis(
    broker_code: str,
    ticker: str,
    lookback_days: int = Query(default=30, ge=1, le=90, description="Days to analyze")
):
    """
    Get detailed analysis of broker activity on a ticker.
    
    Args:
        broker_code: Broker code
        ticker: Stock symbol
        lookback_days: Number of days to analyze
    
    Returns:
        Detailed analysis with volumes, streak, and status
    """
    try:
        analysis = analyzer.analyze_broker_activity(broker_code, ticker, lookback_days)
        
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis["error"])
        
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chart/{broker_code}/{ticker}")
async def get_broker_chart_data(
    broker_code: str,
    ticker: str,
    days: int = Query(default=7, ge=1, le=30, description="Days of chart data")
):
    """
    Get chart data for broker activity visualization.
    
    Args:
        broker_code: Broker code
        ticker: Stock symbol
        days: Number of days
    
    Returns:
        Time series data for charting
    """
    try:
        chart_data = analyzer.get_daily_chart_data(broker_code, ticker, days)
        
        return {
            "status": "success",
            "broker_code": broker_code,
            "ticker": ticker,
            "days": days,
            "data": chart_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/{broker_code}/{ticker}")
async def get_execution_ledger(
    broker_code: str,
    ticker: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of records")
):
    """
    Get execution history ledger.
    
    Args:
        broker_code: Broker code
        ticker: Stock symbol
        limit: Maximum records
    
    Returns:
        Recent execution history
    """
    try:
        ledger = analyzer.get_execution_ledger(broker_code, ticker, limit)
        
        return {
            "status": "success",
            "broker_code": broker_code,
            "ticker": ticker,
            "ledger": ledger
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/{broker_code}")
async def sync_broker_data(broker_code: str, request: SyncRequest):
    """
    Sync broker data from done_detail records to tracking table.
    
    Args:
        broker_code: Broker code to sync
        request: Sync parameters
    
    Returns:
        Sync result summary
    """
    try:
        result = analyzer.sync_broker_data(
            broker_code,
            request.ticker,
            request.days
        )
        
        return {
            "status": "success",
            "sync_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{ticker}/activity")
async def get_ticker_broker_activity(
    ticker: str,
    days: int = Query(default=7, ge=1, le=30, description="Days to look back")
):
    """
    Get all broker activity for a specific ticker.
    
    Args:
        ticker: Stock symbol
        days: Number of days
    
    Returns:
        All broker activities on the ticker
    """
    try:
        activity = repo.get_ticker_broker_activity(ticker, days)
        
        return {
            "status": "success",
            "ticker": ticker,
            "days": days,
            "activity_count": len(activity),
            "activity": activity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/power-level/{broker_code}")
async def calculate_power_level(
    broker_code: str,
    lookback_days: int = Query(default=30, ge=7, le=90, description="Days to analyze")
):
    """
    Calculate and update broker power level.
    
    Args:
        broker_code: Broker code
        lookback_days: Days to analyze
    
    Returns:
        Power level score
    """
    try:
        power_level = analyzer.calculate_power_level(broker_code, lookback_days)
        
        return {
            "status": "success",
            "broker_code": broker_code,
            "power_level": power_level,
            "lookback_days": lookback_days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
