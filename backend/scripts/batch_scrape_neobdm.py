"""Batch scrape NeoBDM market summary using Playwright.

This script runs as a STANDALONE PROCESS to avoid Windows event loop
conflicts with uvicorn. It uses Playwright to scrape the full market
summary table including flag columns (pinky, crossing, unusual, likuid,
suspend, special_notice) and MA values that the Dash API doesn't expose.

Usage:
    python scripts/batch_scrape_neobdm.py
"""
import asyncio
import os
import sys
import traceback
from datetime import datetime

# Add the backend directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.scraper_neobdm import NeoBDMScraper
from modules.database import DatabaseManager


async def run_batch_scrape():
    methods = [('m', 'Market Maker'), ('nr', 'Non-Retail'), ('f', 'Foreign Flow')]
    periods = [('d', 'Daily'), ('c', 'Cumulative')]
    
    db_manager = DatabaseManager()
    
    start_time = datetime.now()
    today_str = start_time.strftime('%Y-%m-%d')
    
    print(f"=== Starting NeoBDM Batch Scrape (Playwright) for {today_str} ===", flush=True)
    
    for m_code, m_label in methods:
        for p_code, p_label in periods:
            log_prefix = f"[{m_label}/{p_label}]"
            print(f"\n{log_prefix} Starting isolated scraping session...", flush=True)
            
            scraper = NeoBDMScraper()
            
            try:
                # Initialize browser
                print(f"{log_prefix} Initializing browser...", flush=True)
                await scraper.init_browser(headless=True)
                
                # Login
                print(f"{log_prefix} Logging in...", flush=True)
                login_success = await scraper.login()
                
                if not login_success:
                    print(f"{log_prefix} Login failed, skipping.", flush=True)
                    continue
                
                # Cleanup old data for today
                try:
                    conn = db_manager._get_conn()
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM neobdm_records WHERE method=? AND period=? AND scraped_at LIKE ?",
                        (m_code, p_code, f"{today_str}%")
                    )
                    count_before = cursor.fetchone()[0]
                    
                    conn.execute(
                        "DELETE FROM neobdm_records WHERE method=? AND period=? AND scraped_at LIKE ?", 
                        (m_code, p_code, f"{today_str}%")
                    )
                    conn.commit()
                    conn.close()
                    if count_before > 0:
                        print(f"{log_prefix} Cleared {count_before} existing records.", flush=True)
                except Exception as e:
                    print(f"{log_prefix} Cleanup warning: {e}", flush=True)
                
                # Scrape
                print(f"{log_prefix} Scraping data...", flush=True)
                try:
                    df, reference_date = await scraper.get_market_summary(method=m_code, period=p_code)
                    
                    if df is not None and not df.empty:
                        data_list = df.to_dict(orient="records")
                        scraped_at = reference_date if reference_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        db_manager.save_neobdm_record_batch(m_code, p_code, data_list, scraped_at=scraped_at)
                        print(f"{log_prefix} Success: Saved {len(df)} rows.", flush=True)
                    else:
                        print(f"{log_prefix} No data found.", flush=True)
                except Exception as e:
                    print(f"{log_prefix} Scraping error: {traceback.format_exc()}", flush=True)
                    
            except Exception as e:
                print(f"{log_prefix} Session error: {e}", flush=True)
            finally:
                try:
                    await scraper.close()
                except Exception:
                    pass
                await asyncio.sleep(2)

    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n=== Batch Scrape Completed in {duration.total_seconds():.2f}s ===", flush=True)


if __name__ == "__main__":
    asyncio.run(run_batch_scrape())
