"""
MarketPulse Background Task Scheduler

Manages automated scraping and maintenance tasks using APScheduler.
Manual triggers still work via frontend buttons.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the background scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            timezone='Asia/Jakarta',  # WIB timezone
            job_defaults={
                'coalesce': True,  # Run once if multiple executions missed
                'max_instances': 1,  # Prevent overlapping runs
                'misfire_grace_time': 3600  # 1 hour grace period
            }
        )
    return _scheduler


def job_listener(event):
    """Listen for job execution events and log them."""
    if event.exception:
        logger.error(f'Job {event.job_id} crashed: {event.exception}')
    else:
        logger.info(f'Job {event.job_id} executed successfully at {datetime.now()}')


# =============================================================================
# SCHEDULED TASKS
# =============================================================================

def scrape_all_news():
    """
    Scrape news from all configured sources.
    Runs every 1 hour.
    """
    logger.info("[Scheduler] Starting news scraping...")
    sources = [
        ("CNBC Indonesia", "modules.scraper_cnbc"),
        ("EmitenNews", "modules.scraper_emiten"),
        ("Bisnis.com", "modules.scraper_bisnis"),
        ("Investor.id", "modules.scraper_investor"),
        ("Bloomberg Technoz", "modules.scraper_bloomberg"),
    ]

    results = []
    for source_name, module_path in sources:
        try:
            logger.info(f"[Scheduler] Scraping {source_name}...")
            module = __import__(module_path, fromlist=['run_scraper'])
            if hasattr(module, 'run_scraper'):
                result = module.run_scraper()
                results.append({"source": source_name, "status": "success", "result": result})
                logger.info(f"[Scheduler] {source_name} scraped successfully")
            else:
                logger.warning(f"[Scheduler] {source_name} has no run_scraper function")
        except Exception as e:
            logger.error(f"[Scheduler] Failed to scrape {source_name}: {e}")
            results.append({"source": source_name, "status": "failed", "error": str(e)})

    logger.info(f"[Scheduler] News scraping completed. {len([r for r in results if r['status'] == 'success'])} sources succeeded")
    return results


def run_neobdm_batch_scrape():
    """
    Scrape NeoBDM data for all tickers.
    Runs daily at 19:00 WIB.
    """
    logger.info("[Scheduler] Starting NeoBDM batch scrape...")
    try:
        import subprocess
        import os

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        script_path = os.path.join(backend_dir, "scripts", "batch_scrape_neobdm.py")

        if not os.path.exists(script_path):
            logger.error(f"[Scheduler] Batch scrape script not found: {script_path}")
            return {"status": "failed", "error": "Script not found"}

        # Run as subprocess to avoid blocking
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=7200  # 2 hour timeout
        )

        if result.returncode == 0:
            logger.info("[Scheduler] NeoBDM batch scrape completed successfully")
            return {"status": "success", "output": result.stdout}
        else:
            logger.error(f"[Scheduler] NeoBDM batch scrape failed: {result.stderr}")
            return {"status": "failed", "error": result.stderr}

    except Exception as e:
        logger.error(f"[Scheduler] NeoBDM batch scrape error: {e}")
        return {"status": "failed", "error": str(e)}


def generate_market_summary():
    """
    Generate daily market summary report.
    Runs daily at 19:00 WIB after NeoBDM data is collected.
    """
    logger.info("[Scheduler] Generating market summary...")
    try:
        from db import NewsRepository, NeoBDMRepository

        news_repo = NewsRepository()
        neobdm_repo = NeoBDMRepository()

        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "top_positive_news": [],
            "top_negative_news": [],
            "unusual_volume_tickers": [],
            "strong_accumulation": [],
            "generated_at": datetime.now().isoformat()
        }

        # Get top news by sentiment
        # This is a placeholder - implement actual logic based on your news schema
        logger.info("[Scheduler] Market summary generated")
        return summary

    except Exception as e:
        logger.error(f"[Scheduler] Market summary generation failed: {e}")
        return {"status": "failed", "error": str(e)}


def cleanup_old_data():
    """
    Clean up old data files and raw records.
    Runs weekly on Sunday at 00:00.
    """
    logger.info("[Scheduler] Starting data cleanup...")
    try:
        from db import DoneDetailRepository
        import os
        import glob
        import time

        results = {
            "deleted_records": 0,
            "deleted_pdfs": 0,
            "deleted_logs": 0,
            "space_freed_mb": 0
        }

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        current_time = time.time()

        # 1. Delete old Done Detail raw data (>7 days)
        try:
            done_detail_repo = DoneDetailRepository()
            deleted = done_detail_repo.delete_old_raw_data(days=7)
            results["deleted_records"] = deleted
            logger.info(f"[Scheduler] Deleted {deleted} old Done Detail records")
        except Exception as e:
            logger.warning(f"[Scheduler] Done Detail cleanup skipped: {e}")

        # 2. Clean up old PDF files in downloads/ folder (>30 days)
        try:
            downloads_dir = os.path.join(backend_dir, "downloads")
            if os.path.exists(downloads_dir):
                pdf_files = glob.glob(os.path.join(downloads_dir, "*.pdf"))
                deleted_count = 0
                space_freed = 0

                for pdf_path in pdf_files:
                    try:
                        # Check file modification time
                        file_mtime = os.path.getmtime(pdf_path)
                        file_age_days = (current_time - file_mtime) / (24 * 3600)

                        if file_age_days > 30:
                            file_size = os.path.getsize(pdf_path)
                            os.remove(pdf_path)
                            deleted_count += 1
                            space_freed += file_size
                            logger.debug(f"[Scheduler] Deleted old PDF: {os.path.basename(pdf_path)} ({file_age_days:.1f} days old)")
                    except Exception as e:
                        logger.warning(f"[Scheduler] Failed to delete PDF {pdf_path}: {e}")

                results["deleted_pdfs"] = deleted_count
                results["space_freed_mb"] += space_freed / (1024 * 1024)
                logger.info(f"[Scheduler] Deleted {deleted_count} old PDFs, freed {space_freed / (1024 * 1024):.2f} MB")
        except Exception as e:
            logger.warning(f"[Scheduler] PDF cleanup skipped: {e}")

        # 3. Clean up old log files (>30 days)
        try:
            logs_dir = os.path.join(backend_dir, "logs")
            if os.path.exists(logs_dir):
                log_files = glob.glob(os.path.join(logs_dir, "*.log"))
                deleted_count = 0
                space_freed = 0

                for log_path in log_files:
                    try:
                        file_mtime = os.path.getmtime(log_path)
                        file_age_days = (current_time - file_mtime) / (24 * 3600)

                        if file_age_days > 30:
                            file_size = os.path.getsize(log_path)
                            os.remove(log_path)
                            deleted_count += 1
                            space_freed += file_size
                    except Exception as e:
                        logger.warning(f"[Scheduler] Failed to delete log {log_path}: {e}")

                results["deleted_logs"] = deleted_count
                results["space_freed_mb"] += space_freed / (1024 * 1024)
                logger.info(f"[Scheduler] Deleted {deleted_count} old log files, freed {space_freed / (1024 * 1024):.2f} MB")
        except Exception as e:
            logger.warning(f"[Scheduler] Log cleanup skipped: {e}")

        total_freed = results["space_freed_mb"]
        logger.info(f"[Scheduler] Data cleanup completed. Total space freed: {total_freed:.2f} MB")
        return results

    except Exception as e:
        logger.error(f"[Scheduler] Data cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}


# =============================================================================
# SCHEDULER SETUP
# =============================================================================

def setup_jobs():
    """Configure all scheduled jobs."""
    scheduler = get_scheduler()

    # Remove existing jobs to avoid duplicates
    scheduler.remove_all_jobs()

    # 1. News Scraping - Every 1 hour during market hours (09:00-20:00 WIB)
    scheduler.add_job(
        scrape_all_news,
        trigger=IntervalTrigger(hours=1),
        id='news_scraper',
        name='News Scraping (Hourly)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: News scraping every 1 hour")

    # 2. NeoBDM Batch Scrape - Daily at 19:00 WIB
    scheduler.add_job(
        run_neobdm_batch_scrape,
        trigger=CronTrigger(hour=19, minute=0),
        id='neobdm_daily',
        name='NeoBDM Daily Scrape (19:00 WIB)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: NeoBDM daily scrape at 19:00 WIB")

    # 3. Market Summary - Daily at 19:00 WIB (after NeoBDM)
    scheduler.add_job(
        generate_market_summary,
        trigger=CronTrigger(hour=19, minute=30),  # 30 min after NeoBDM
        id='market_summary',
        name='Market Summary Generation (19:30 WIB)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Market summary at 19:30 WIB")

    # 4. Data Cleanup - Weekly on Sunday at 00:00
    scheduler.add_job(
        cleanup_old_data,
        trigger=CronTrigger(day_of_week='sun', hour=0, minute=0),
        id='weekly_cleanup',
        name='Weekly Data Cleanup (Sunday 00:00)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Weekly cleanup on Sunday 00:00")

    # Add event listener for logging
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_scheduler()

    if not scheduler.running:
        setup_jobs()
        scheduler.start()
        logger.info("[Scheduler] Background scheduler started successfully")

        # Log scheduled jobs
        jobs = scheduler.get_jobs()
        logger.info(f"[Scheduler] Active jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")
    else:
        logger.info("[Scheduler] Already running")


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("[Scheduler] Background scheduler stopped")


def get_job_status():
    """Get status of all scheduled jobs."""
    scheduler = get_scheduler()
    jobs = []

    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return {
        "running": scheduler.running,
        "job_count": len(jobs),
        "jobs": jobs
    }


def run_job_manually(job_id: str):
    """Manually trigger a scheduled job by ID."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)

    if not job:
        return {"status": "error", "message": f"Job {job_id} not found"}

    try:
        job.func()
        return {"status": "success", "message": f"Job {job_id} executed manually"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
