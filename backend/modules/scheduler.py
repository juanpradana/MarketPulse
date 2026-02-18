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

from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def scrape_single_source(source_name: str, scraper_config: tuple) -> dict:
    """
    Scrape a single news source.
    Helper function for concurrent execution.

    Args:
        source_name: Display name of the source
        scraper_config: (module_path, class_name, run_method) tuple
    """
    import datetime
    start_time = time.time()

    try:
        logger.info(f"[Scheduler] Starting {source_name}...")
        module_path, class_name, run_method = scraper_config

        # Import module and get class
        module = __import__(module_path, fromlist=[class_name])
        scraper_class = getattr(module, class_name)

        # Instantiate scraper
        scraper = scraper_class()

        # Get current date range (last 24 hours)
        end_dt = datetime.datetime.now()
        start_dt = end_dt - datetime.timedelta(days=1)

        # Run scraper
        if run_method == "run":
            result = scraper.run(start_date=start_dt, end_date=end_dt)
        else:
            result = getattr(scraper, run_method)(start_dt, end_dt)

        # Process results if successful
        if result:
            # Analyze sentiment and save to DB
            from modules.analyzer import get_engine
            from modules.database import DatabaseManager
            from modules.utils import extract_tickers

            engine = get_engine()
            analyzed_data = engine.process_and_save(result)

            # Enrich with ticker extraction
            for article in analyzed_data:
                if 'ticker' not in article or not article['ticker']:
                    article['ticker'] = extract_tickers(article.get('title', ''))

            db_manager = DatabaseManager()
            db_manager.save_news(analyzed_data)

            elapsed = time.time() - start_time
            logger.info(f"[Scheduler] {source_name} completed in {elapsed:.1f}s - {len(analyzed_data)} articles")
            return {
                "source": source_name,
                "status": "success",
                "result": analyzed_data,
                "elapsed_seconds": elapsed
            }
        else:
            elapsed = time.time() - start_time
            logger.info(f"[Scheduler] {source_name} completed in {elapsed:.1f}s - No new articles")
            return {
                "source": source_name,
                "status": "success",
                "result": [],
                "elapsed_seconds": elapsed
            }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[Scheduler] Failed to scrape {source_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "source": source_name,
            "status": "failed",
            "error": str(e),
            "elapsed_seconds": elapsed
        }


def scrape_all_news():
    """
    Scrape news from all configured sources CONCURRENTLY.
    Runs every 1 hour.
    Uses ThreadPoolExecutor to parallelize synchronous scrapers.
    """
    logger.info("[Scheduler] Starting CONCURRENT news scraping...")

    # Scraper configurations: (module_path, class_name, run_method)
    sources = [
        ("CNBC Indonesia", ("modules.scraper_cnbc", "CNBCScraper", "run")),
        ("EmitenNews", ("modules.scraper_emiten", "EmitenNewsScraper", "run")),
        ("Bisnis.com", ("modules.scraper_bisnis", "BisnisScraper", "run")),
        ("Investor.id", ("modules.scraper_investor", "InvestorScraper", "run")),
        ("Bloomberg Technoz", ("modules.scraper_bloomberg", "BloombergTechnozScraper", "run")),
    ]

    results = []
    total_start = time.time()

    # Use ThreadPoolExecutor for concurrent scraping
    # max_workers=5 allows all scrapers to run simultaneously
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all scraping tasks
        future_to_source = {
            executor.submit(scrape_single_source, name, config): (name, config)
            for name, config in sources
        }

        # Collect results as they complete
        for future in as_completed(future_to_source):
            source_name, _ = future_to_source[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"[Scheduler] Unexpected error for {source_name}: {e}")
                results.append({
                    "source": source_name,
                    "status": "failed",
                    "error": str(e)
                })

    total_elapsed = time.time() - total_start
    success_count = len([r for r in results if r['status'] == 'success'])

    logger.info(f"[Scheduler] News scraping completed in {total_elapsed:.1f}s")
    logger.info(f"[Scheduler] {success_count}/{len(sources)} sources succeeded")

    # Log individual timings
    for r in results:
        status = "✓" if r['status'] == 'success' else "✗"
        elapsed = r.get('elapsed_seconds', 0)
        logger.info(f"[Scheduler] {status} {r['source']}: {elapsed:.1f}s")

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


def run_bandarmology_market_summary():
    """
    Run bandarmology market summary analysis (screening all stocks).
    Runs daily at 19:00 WIB on weekdays (Mon-Fri).
    """
    logger.info("[Scheduler] Starting bandarmology market summary...")
    try:
        import sys
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        from modules.bandarmology_analyzer import BandarmologyAnalyzer

        analyzer = BandarmologyAnalyzer()
        results = analyzer.analyze(target_date=None)
        logger.info(f"[Scheduler] Bandarmology market summary completed: {len(results)} stocks analyzed")
        return {"status": "success", "total_stocks": len(results)}

    except Exception as e:
        logger.error(f"[Scheduler] Bandarmology market summary failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


def run_deep_analyze_all():
    """
    Run deep analysis on ALL stocks from the latest bandarmology market summary.
    Runs daily at 19:30 WIB on weekdays (Mon-Fri), after market summary is ready.
    """
    logger.info("[Scheduler] Starting scheduled deep analysis for all market summary stocks...")
    try:
        import sys
        import os
        import asyncio

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        from modules.bandarmology_analyzer import BandarmologyAnalyzer

        analyzer = BandarmologyAnalyzer()
        results = analyzer.analyze(target_date=None)
        actual_date = analyzer._resolve_date(None)

        if not results:
            logger.warning("[Scheduler] No stocks found for deep analysis")
            return {"status": "skipped", "reason": "No stocks in market summary"}

        tickers = [r['symbol'] for r in results]
        logger.info(f"[Scheduler] Deep analyzing {len(tickers)} stocks for date {actual_date}")

        # Import the async deep analysis function and run it in an event loop
        from routes.bandarmology import _run_deep_analysis

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_deep_analysis(tickers, actual_date, results))
        finally:
            loop.close()

        logger.info(f"[Scheduler] Scheduled deep analysis completed for {len(tickers)} stocks")
        return {"status": "success", "total_stocks": len(tickers), "date": actual_date}

    except Exception as e:
        logger.error(f"[Scheduler] Scheduled deep analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

    # 2. NeoBDM Batch Scrape - Weekdays at 19:00 WIB
    scheduler.add_job(
        run_neobdm_batch_scrape,
        trigger=CronTrigger(day_of_week='mon-fri', hour=19, minute=0),
        id='neobdm_daily',
        name='NeoBDM Daily Scrape (19:00 WIB, Weekdays)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: NeoBDM daily scrape at 19:00 WIB (weekdays)")

    # 3. Bandarmology Market Summary - Weekdays at 19:00 WIB
    scheduler.add_job(
        run_bandarmology_market_summary,
        trigger=CronTrigger(day_of_week='mon-fri', hour=19, minute=0),
        id='bandarmology_market_summary',
        name='Bandarmology Market Summary (19:00 WIB, Weekdays)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Bandarmology market summary at 19:00 WIB (weekdays)")

    # 4. Deep Analyze All Stocks - Weekdays at 19:30 WIB (after market summary)
    scheduler.add_job(
        run_deep_analyze_all,
        trigger=CronTrigger(day_of_week='mon-fri', hour=19, minute=30),
        id='bandarmology_deep_analyze_all',
        name='Bandarmology Deep Analyze All (19:30 WIB, Weekdays)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Bandarmology deep analyze all at 19:30 WIB (weekdays)")

    # 5. Legacy Market Summary (news-based) - kept for reference
    scheduler.add_job(
        generate_market_summary,
        trigger=CronTrigger(day_of_week='mon-fri', hour=20, minute=0),
        id='market_summary',
        name='Market Summary Generation (20:00 WIB, Weekdays)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Market summary at 20:00 WIB (weekdays)")

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
