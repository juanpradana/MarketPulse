"""
Watchlist API Routes

Endpoints for managing user's personalized ticker watchlist.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

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
