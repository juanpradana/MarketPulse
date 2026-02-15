"""
Scheduler Control API

Endpoints for monitoring and controlling the background task scheduler.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from modules.scheduler import (
    start_scheduler,
    stop_scheduler,
    get_job_status,
    run_job_manually,
    scrape_all_news,
    run_neobdm_batch_scrape,
    generate_market_summary,
    cleanup_old_data
)

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


@router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Get the current status of the background scheduler.
    Returns list of scheduled jobs and their next run times.
    """
    return get_job_status()


@router.post("/start")
async def start() -> Dict[str, str]:
    """
    Start the background scheduler.
    Idempotent - safe to call multiple times.
    """
    try:
        start_scheduler()
        return {"status": "success", "message": "Scheduler started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop() -> Dict[str, str]:
    """
    Stop the background scheduler.
    All scheduled tasks will be paused.
    """
    try:
        stop_scheduler()
        return {"status": "success", "message": "Scheduler stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{job_id}")
async def run_job(job_id: str) -> Dict[str, Any]:
    """
    Manually trigger a specific scheduled job.

    Available job IDs:
    - news_scraper: Scrape news from all sources
    - neobdm_daily: Run NeoBDM batch scrape
    - market_summary: Generate market summary report
    - weekly_cleanup: Clean up old data
    """
    result = run_job_manually(job_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# =============================================================================
# MANUAL TRIGGER ENDPOINTS (Keep frontend buttons working)
# =============================================================================

@router.post("/manual/news")
async def manual_news_scrape() -> Dict[str, Any]:
    """
    Manually trigger news scraping.
    This is called by the frontend "Refresh Intelligence" button.
    """
    try:
        results = scrape_all_news()
        success_count = len([r for r in results if r["status"] == "success"])
        return {
            "status": "success",
            "message": f"News scraping completed. {success_count} sources succeeded",
            "details": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual/neobdm")
async def manual_neobdm_scrape() -> Dict[str, Any]:
    """
    Manually trigger NeoBDM batch scrape.
    This can be called from frontend or admin panel.
    """
    try:
        result = run_neobdm_batch_scrape()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/manual/cleanup")
async def manual_cleanup() -> Dict[str, Any]:
    """
    Manually trigger data cleanup.
    """
    try:
        result = cleanup_old_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule")
async def get_schedule_config() -> Dict[str, Any]:
    """
    Get the current schedule configuration.
    Shows when each task is scheduled to run.
    """
    return {
        "timezone": "Asia/Jakarta (WIB)",
        "schedules": [
            {
                "job_id": "news_scraper",
                "name": "News Scraping",
                "frequency": "Every 1 hour",
                "description": "Scrapes CNBC, EmitenNews, Bisnis.com, Investor.id, Bloomberg"
            },
            {
                "job_id": "neobdm_daily",
                "name": "NeoBDM Daily Scrape",
                "frequency": "Daily at 19:00 WIB",
                "description": "Scrapes fund flow data for all tickers"
            },
            {
                "job_id": "market_summary",
                "name": "Market Summary",
                "frequency": "Daily at 19:30 WIB",
                "description": "Generates daily market report"
            },
            {
                "job_id": "weekly_cleanup",
                "name": "Weekly Data Cleanup",
                "frequency": "Sunday at 00:00 WIB",
                "description": "Cleans old Done Detail data and log files"
            }
        ]
    }
