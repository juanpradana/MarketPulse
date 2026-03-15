"""
MarketPulse Background Task Scheduler

Manages automated scraping and maintenance tasks using APScheduler.
Manual triggers still work via frontend buttons.
"""

import logging
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None

# Default limit for Yahoo Finance refresh (top N tickers from bandarmology summary)
DEFAULT_YAHOO_REFRESH_LIMIT = 200


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


def _check_ollama_available():
    """Check if Ollama server is reachable for RAG processing."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_idx_disclosure_fetch(days: int = 1, skip_processing: bool = False):
    """
    Fetch IDX disclosures for recent days.
    Runs every 6 hours (balanced frequency for IDX disclosures).

    Args:
        days: Number of days to look back (default: 1)
        skip_processing: If True, skip RAG indexing (use when AI unavailable)
    """
    logger.info("[Scheduler] Starting IDX disclosure fetch...")

    # Check AI availability upfront
    ollama_available = _check_ollama_available()
    if not ollama_available:
        logger.warning("[Scheduler] Ollama not available - will download PDFs only, skip RAG indexing")
        skip_processing = True

    try:
        from modules.scraper_idx import fetch_and_save_pipeline

        # 1. Fetch and download PDFs (always run, no AI needed)
        result = fetch_and_save_pipeline(days=days)

        if result["status"] == "success":
            logger.info(f"[Scheduler] IDX disclosures: {result['fetched']} fetched, "
                       f"{result['downloaded']} downloaded, {result['skipped']} skipped")

            # 2. RAG indexing - DISABLED (too heavy for current hardware)
            # PDFs are still downloaded but not processed for AI chat
            if result["downloaded"] > 0:
                logger.info(f"[Scheduler] Downloaded {result['downloaded']} PDFs - RAG indexing skipped (disabled)")
                logger.info("[Scheduler] PDFs saved to downloads folder but NOT indexed for AI chat")
        else:
            logger.warning(f"[Scheduler] IDX disclosure fetch: {result['status']}")

        return {
            **result,
            "ollama_available": ollama_available,
            "processing_skipped": skip_processing
        }

    except Exception as e:
        logger.error(f"[Scheduler] IDX disclosure fetch failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "failed", "error": str(e), "ollama_available": ollama_available}


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


def _infer_news_source(url: str) -> str:
    """Infer human-friendly source from URL."""
    try:
        host = urlparse(url or "").netloc.lower()
    except Exception:
        host = ""

    if "cnbcindonesia.com" in host:
        return "CNBC"
    if "emitennews.com" in host:
        return "EmitenNews"
    if "idx.co.id" in host:
        return "IDX"
    if "bisnis.com" in host:
        return "Bisnis.com"
    if "investor.id" in host:
        return "Investor.id"
    if "bloombergtechnoz.com" in host:
        return "Bloomberg Technoz"
    return "Web"


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_market_summary_narrative(summary: dict) -> dict:
    """Build deterministic newsletter/narrative text from summary sections."""
    breadth = summary.get("market_breadth", {})
    bullish = int(breadth.get("bullish_count", 0))
    bearish = int(breadth.get("bearish_count", 0))
    avg_sentiment = _to_float(breadth.get("avg_sentiment_score", 0.0), 0.0)
    hot_count = len(summary.get("strong_accumulation", []))
    unusual_count = len(summary.get("unusual_volume_tickers", []))

    if bullish > bearish and avg_sentiment >= 0:
        tone = "cenderung konstruktif"
    elif bearish > bullish and avg_sentiment < 0:
        tone = "cenderung defensif"
    else:
        tone = "mixed dengan volatilitas selektif"

    top_pos = summary.get("top_positive_news", [])
    top_neg = summary.get("top_negative_news", [])
    top_pos_ticker = top_pos[0].get("ticker", "-") if top_pos else "-"
    top_neg_ticker = top_neg[0].get("ticker", "-") if top_neg else "-"

    bullets = [
        f"Sentimen harian {tone} (bullish: {bullish}, bearish: {bearish}, avg score: {avg_sentiment:.3f}).",
        f"{hot_count} ticker masuk daftar akumulasi kuat dari signal engine terbaru.",
        f"{unusual_count} ticker terdeteksi anomali volume yang perlu dipantau lanjutan.",
        f"Headline positif dominan: {top_pos_ticker}; tekanan negatif utama: {top_neg_ticker}.",
    ]

    headline = f"Market Pulse {summary.get('date', '')}: Sentimen {tone}"
    newsletter = (
        f"{headline}. "
        f"Di sisi berita, rasio bullish vs bearish berada di {bullish}:{bearish} dengan rerata skor {avg_sentiment:.3f}. "
        f"Engine mendeteksi {hot_count} kandidat akumulasi kuat dan {unusual_count} anomali volume signifikan. "
        "Fokus berikutnya: validasi follow-through harga dan disiplin manajemen risiko pada ticker dengan sinyal paling konsisten."
    )

    return {
        "headline": headline,
        "bullets": bullets,
        "newsletter": newsletter,
    }


def generate_market_summary():
    """
    Generate daily market summary report.
    Runs daily at 19:00 WIB after NeoBDM data is collected.
    """
    logger.info("[Scheduler] Generating market summary...")
    try:
        from db import NewsRepository, NeoBDMRepository
        from db.price_volume_repository import price_volume_repo

        news_repo = NewsRepository()
        neobdm_repo = NeoBDMRepository()

        summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "top_positive_news": [],
            "top_negative_news": [],
            "unusual_volume_tickers": [],
            "strong_accumulation": [],
            "market_breadth": {
                "news_count": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "avg_sentiment_score": 0.0,
            },
            "narrative": {
                "headline": "",
                "bullets": [],
                "newsletter": "",
            },
            "generated_at": datetime.now().isoformat()
        }

        end_date = datetime.now().strftime("%Y-%m-%d")

        # 1) News sentiment summary (latest 24h window)
        news_df = news_repo.get_news(start_date=end_date, end_date=end_date, limit=300)
        if not news_df.empty:
            # Deduplicate by title
            news_df = news_df.copy()
            news_df["title_key"] = news_df["title"].astype(str).str.strip().str.lower()
            news_df = news_df.drop_duplicates(subset=["title_key"])  # keep first (latest)

            score_series = news_df["sentiment_score"].apply(_to_float)
            summary["market_breadth"] = {
                "news_count": int(len(news_df)),
                "bullish_count": int((news_df["sentiment_label"] == "Bullish").sum()),
                "bearish_count": int((news_df["sentiment_label"] == "Bearish").sum()),
                "neutral_count": int((news_df["sentiment_label"] == "Netral").sum()),
                "avg_sentiment_score": round(float(score_series.mean()) if len(score_series) > 0 else 0.0, 4),
            }

            top_positive = news_df.sort_values("sentiment_score", ascending=False).head(5)
            top_negative = news_df.sort_values("sentiment_score", ascending=True).head(5)

            summary["top_positive_news"] = [
                {
                    "ticker": str(row.get("ticker") or "-").split(",")[0].strip() or "-",
                    "title": str(row.get("title") or ""),
                    "score": round(_to_float(row.get("sentiment_score"), 0.0), 4),
                    "sentiment_label": row.get("sentiment_label") or "Netral",
                    "source": _infer_news_source(str(row.get("url") or "")),
                    "timestamp": str(row.get("timestamp") or ""),
                    "url": str(row.get("url") or ""),
                }
                for _, row in top_positive.iterrows()
            ]

            summary["top_negative_news"] = [
                {
                    "ticker": str(row.get("ticker") or "-").split(",")[0].strip() or "-",
                    "title": str(row.get("title") or ""),
                    "score": round(_to_float(row.get("sentiment_score"), 0.0), 4),
                    "sentiment_label": row.get("sentiment_label") or "Netral",
                    "source": _infer_news_source(str(row.get("url") or "")),
                    "timestamp": str(row.get("timestamp") or ""),
                    "url": str(row.get("url") or ""),
                }
                for _, row in top_negative.iterrows()
            ]

        # 2) Unusual volume candidates
        try:
            unusual = price_volume_repo.detect_unusual_volumes(scan_days=3, lookback_days=20, min_ratio=2.0)
            summary["unusual_volume_tickers"] = [
                {
                    "ticker": row.get("ticker"),
                    "date": row.get("date"),
                    "ratio": row.get("ratio"),
                    "price_change": row.get("price_change"),
                    "category": row.get("category"),
                }
                for row in unusual[:10]
            ]
        except Exception as vol_err:
            logger.warning(f"[Scheduler] Unusual volume scan skipped: {vol_err}")

        # 3) Strong accumulation from latest signal engine
        try:
            hot_signals = neobdm_repo.get_latest_hot_signals()
            summary["strong_accumulation"] = [
                {
                    "ticker": row.get("symbol"),
                    "signal_score": int(row.get("signal_score", 0)),
                    "signal_strength": row.get("signal_strength"),
                    "flow": row.get("flow"),
                    "change": row.get("change"),
                    "confluence_status": row.get("confluence_status"),
                }
                for row in hot_signals[:10]
            ]
        except Exception as signal_err:
            logger.warning(f"[Scheduler] Hot signal summary skipped: {signal_err}")

        summary["narrative"] = _build_market_summary_narrative(summary)

        has_meaningful_data = any([
            summary["top_positive_news"],
            summary["top_negative_news"],
            summary["unusual_volume_tickers"],
            summary["strong_accumulation"],
        ])

        if not has_meaningful_data:
            logger.warning("[Scheduler] Market summary skipped: placeholder returned empty sections")
            return {
                "status": "skipped",
                "reason": "placeholder_no_data",
                "summary": summary,
            }

        logger.info("[Scheduler] Market summary generated")
        return {
            "status": "success",
            "summary": summary,
        }

    except Exception as e:
        logger.error(f"[Scheduler] Market summary generation failed: {e}")
        return {"status": "failed", "error": str(e)}


def _generate_latest_bandarmology_market_summary():
    """Generate the latest bandarmology market summary snapshot and return rows + date."""
    import sys
    import os

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from modules.bandarmology_analyzer import BandarmologyAnalyzer

    analyzer = BandarmologyAnalyzer()
    results = analyzer.analyze(target_date=None)
    actual_date = analyzer._resolve_date(None)
    return results, actual_date


def run_bandarmology_market_summary():
    """
    Run bandarmology market summary analysis (screening all stocks).
    Runs daily at 19:00 WIB on weekdays (Mon-Fri).
    """
    logger.info("[Scheduler] Starting bandarmology market summary...")
    try:
        results, actual_date = _generate_latest_bandarmology_market_summary()
        logger.info(
            f"[Scheduler] Bandarmology market summary completed: {len(results)} stocks analyzed for {actual_date}"
        )
        return {"status": "success", "total_stocks": len(results), "date": actual_date}

    except Exception as e:
        logger.error(f"[Scheduler] Bandarmology market summary failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


def run_evening_neobdm_bandarmology_pipeline():
    """
    Run the full evening pipeline in strict order:
    1) NeoBDM batch scrape
    2) Bandarmology market summary
    3) Bandarmology deep analyze all

    This avoids time-based race conditions where deep analysis starts
    before NeoBDM data refresh is finished.
    """
    logger.info("[Scheduler] Starting evening NeoBDM -> Bandarmology pipeline...")

    neobdm_result = run_neobdm_batch_scrape()
    if neobdm_result.get("status") != "success":
        logger.warning("[Scheduler] Pipeline stopped: NeoBDM batch scrape did not succeed")
        return {
            "status": "failed",
            "stage": "neobdm_batch",
            "details": neobdm_result,
        }

    summary_result = run_bandarmology_market_summary()
    if summary_result.get("status") != "success":
        logger.warning("[Scheduler] Pipeline stopped: Bandarmology market summary did not succeed")
        return {
            "status": "failed",
            "stage": "bandarmology_market_summary",
            "details": summary_result,
        }

    deep_result = run_deep_analyze_all()
    if deep_result.get("status") != "success":
        logger.warning("[Scheduler] Pipeline finished with deep analysis issue")
        return {
            "status": "failed",
            "stage": "bandarmology_deep_analyze_all",
            "details": deep_result,
        }

    logger.info("[Scheduler] Evening pipeline completed successfully")
    return {
        "status": "success",
        "neobdm": neobdm_result,
        "market_summary": summary_result,
        "deep_analyze": deep_result,
    }


def run_deep_analyze_all():
    """
    Run deep analysis on ALL stocks from the latest bandarmology market summary.
    Runs daily at 19:30 WIB on weekdays (Mon-Fri), after market summary is ready.
    """
    logger.info("[Scheduler] Starting scheduled deep analysis for all market summary stocks...")
    try:
        import asyncio

        # Always refresh summary first to avoid deep analysis using stale market summary data.
        logger.info("[Scheduler] Refreshing bandarmology market summary before deep analyze...")
        results, actual_date = _generate_latest_bandarmology_market_summary()
        logger.info(
            f"[Scheduler] Refreshed market summary for deep analyze: {len(results)} stocks on {actual_date}"
        )

        if not results:
            logger.warning("[Scheduler] No stocks found for deep analysis")
            return {"status": "skipped", "reason": "No stocks in market summary"}

        tickers = [r['symbol'] for r in results if r.get('symbol')]
        scheduler_concurrency = 12
        logger.info(
            f"[Scheduler] Deep analyzing {len(tickers)} stocks for date {actual_date} "
            f"with concurrency={scheduler_concurrency}"
        )

        # Import the async deep analysis function and run it in an event loop
        from routes.bandarmology import _run_deep_analysis

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                _run_deep_analysis(
                    tickers,
                    actual_date,
                    results,
                    concurrency=scheduler_concurrency,
                )
            )
        finally:
            loop.close()

        logger.info(f"[Scheduler] Scheduled deep analysis completed for {len(tickers)} stocks")
        return {"status": "success", "total_stocks": len(tickers), "date": actual_date}

    except Exception as e:
        logger.error(f"[Scheduler] Scheduled deep analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


def run_bandarmology_yahoo_refresh(
    force_refresh: bool = False,
    limit: Optional[int] = None,
    include_float: bool = True,
    include_power: bool = True,
    include_volume: bool = True,
    include_earnings: bool = True,
    days_ahead: int = 30,
    concurrency: int = 4,
):
    """
    Refresh Yahoo Finance-derived caches for Bandarmology columns:
    FLOAT, POWER, VOL, EARN.

    This populates:
    - stock_float_data (float)
    - bandar_power_scores (power)
    - volume_daily_records (volume)
    - earnings_calendar (earnings)

    Uses latest bandarmology summary tickers as the target universe.
    """
    logger.info("[Scheduler] Starting Bandarmology Yahoo Finance cache refresh...")
    try:
        results, actual_date = _generate_latest_bandarmology_market_summary()
        tickers = [r.get('symbol') for r in results if r.get('symbol')]
        effective_limit = DEFAULT_YAHOO_REFRESH_LIMIT if limit is None else limit
        if effective_limit and effective_limit > 0:
            tickers = tickers[:effective_limit]

        if not tickers:
            logger.warning("[Scheduler] No tickers found for Yahoo refresh")
            return {"status": "skipped", "reason": "no_tickers"}

        from modules.yahoo_finance_enhanced import get_yahoo_finance_enhanced
        from modules.volume_analyzer import get_volume_analyzer
        from modules.bandar_power_calculator import get_bandar_power_calculator
        from modules.earnings_tracker import get_earnings_tracker

        yf_enhanced = get_yahoo_finance_enhanced()
        volume_analyzer = get_volume_analyzer()
        power_calc = get_bandar_power_calculator()
        earnings_tracker = get_earnings_tracker()

        totals = {
            "float_ok": 0, "power_ok": 0, "volume_ok": 0, "earnings_ok": 0,
            "float_fail": 0, "power_fail": 0, "volume_fail": 0, "earnings_fail": 0,
        }
        errors = []

        def _process_ticker(ticker: str):
            per = {"ticker": ticker}
            try:
                if include_float:
                    float_data = yf_enhanced.fetch_float_data(ticker, force_refresh=force_refresh)
                    per["float"] = bool(float_data)
                if include_power:
                    power_data = power_calc.calculate_score(ticker, force_refresh=force_refresh)
                    per["power"] = bool(power_data)
                if include_volume:
                    per["volume"] = volume_analyzer.update_volume_daily_record(ticker)
                if include_earnings:
                    earnings = earnings_tracker.fetch_upcoming_earnings(
                        ticker, days_ahead=days_ahead, force_refresh=force_refresh
                    )
                    per["earnings"] = len(earnings) > 0
            except Exception as exc:
                per["error"] = str(exc)
            return per

        # Use limited concurrency to avoid rate limits
        if concurrency and concurrency > 1:
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                for future in as_completed(executor.submit(_process_ticker, t) for t in tickers):
                    per = future.result()
                    if per.get("error"):
                        errors.append(per)
                    else:
                        if include_float:
                            totals["float_ok" if per.get("float") else "float_fail"] += 1
                        if include_power:
                            totals["power_ok" if per.get("power") else "power_fail"] += 1
                        if include_volume:
                            totals["volume_ok" if per.get("volume") else "volume_fail"] += 1
                        if include_earnings:
                            totals["earnings_ok" if per.get("earnings") else "earnings_fail"] += 1
        else:
            for ticker in tickers:
                per = _process_ticker(ticker)
                if per.get("error"):
                    errors.append(per)
                else:
                    if include_float:
                        totals["float_ok" if per.get("float") else "float_fail"] += 1
                    if include_power:
                        totals["power_ok" if per.get("power") else "power_fail"] += 1
                    if include_volume:
                        totals["volume_ok" if per.get("volume") else "volume_fail"] += 1
                    if include_earnings:
                        totals["earnings_ok" if per.get("earnings") else "earnings_fail"] += 1

        logger.info(
            "[Scheduler] Yahoo refresh done: float_ok=%s power_ok=%s volume_ok=%s earnings_ok=%s (errors=%s)",
            totals.get("float_ok"), totals.get("power_ok"), totals.get("volume_ok"),
            totals.get("earnings_ok"), len(errors)
        )

        return {
            "status": "success",
            "date": actual_date,
            "total_tickers": len(tickers),
            "totals": totals,
            "errors": errors[:20],  # truncate to keep payload small
        }

    except Exception as e:
        logger.error(f"[Scheduler] Yahoo refresh failed: {e}")
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

    # 2. Evening Pipeline - Weekdays at 19:00 WIB
    # NeoBDM batch -> Bandarmology summary -> Deep analyze (sequential, no race)
    scheduler.add_job(
        run_evening_neobdm_bandarmology_pipeline,
        trigger=CronTrigger(day_of_week='mon-fri', hour=19, minute=0),
        id='neobdm_evening_pipeline',
        name='NeoBDM + Bandarmology Pipeline (19:00 WIB, Weekdays)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: evening NeoBDM + Bandarmology pipeline at 19:00 WIB (weekdays)")

    # 3. IDX Disclosure Fetch - Every 6 hours
    # 4x per day: captures disclosures throughout the day without excessive API calls
    scheduler.add_job(
        run_idx_disclosure_fetch,
        trigger=IntervalTrigger(hours=6),
        id='idx_disclosure_fetch',
        name='IDX Disclosure Fetch (Every 6 hours)',
        replace_existing=True,
        kwargs={'days': 1}  # Only fetch last 24 hours to minimize overlap
    )
    logger.info("[Scheduler] Job added: IDX disclosure fetch every 6 hours")

    # 5. Market Summary - Every 4 hours at 08:00, 12:00, 16:00, 20:00 WIB (7 days/week)
    scheduler.add_job(
        generate_market_summary,
        trigger=CronTrigger(hour='8,12,16,20', minute=0),
        id='market_summary',
        name='Market Summary Generation (08:00, 12:00, 16:00, 20:00 WIB, Daily)',
        replace_existing=True
    )
    logger.info("[Scheduler] Job added: Market summary at 08:00, 12:00, 16:00, 20:00 WIB (daily)")

    # 6. Bandarmology Yahoo Finance Cache Refresh - Daily at 18:00 WIB
    scheduler.add_job(
        run_bandarmology_yahoo_refresh,
        trigger=CronTrigger(hour=18, minute=0),
        id='bandarmology_yahoo_refresh',
        name='Bandarmology Yahoo Finance Cache Refresh (18:00 WIB, Daily)',
        replace_existing=True,
        kwargs={
            'force_refresh': False,
            'limit': DEFAULT_YAHOO_REFRESH_LIMIT,
            'include_float': True,
            'include_power': True,
            'include_volume': True,
            'include_earnings': True,
            'days_ahead': 30,
            'concurrency': 4,
        }
    )
    logger.info("[Scheduler] Job added: Bandarmology Yahoo Finance cache refresh at 18:00 WIB (daily)")

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
