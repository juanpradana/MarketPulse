import asyncio
import os
import sys
from datetime import datetime

# Add the backend directory to sys.path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.neobdm_api_client import NeoBDMApiClient
from modules.database import DatabaseManager

async def run_batch_scrape():
    methods = [('m', 'Market Maker'), ('nr', 'Non-Retail'), ('f', 'Foreign Flow')]
    periods = [('d', 'Daily'), ('c', 'Cumulative')]
    
    db_manager = DatabaseManager()
    
    start_time = datetime.now()
    today_str = start_time.strftime('%Y-%m-%d')
    
    print(f"=== Starting NeoBDM Batch Fetch (API Client) for {today_str} ===")
    
    api_client = NeoBDMApiClient()
    try:
        for m_code, m_label in methods:
            for p_code, p_label in periods:
                log_prefix = f"[{m_label}/{p_label}]"
                print(f"\n[>] Fetching: {m_label} | {p_label}")
                
                # 1. Cleanup old data
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
                        print(f"    [CLEANUP] Cleared {count_before} existing records.")
                except Exception as e:
                    print(f"    [CLEANUP] Warning: {e}")

                # 2. Fetch via API
                try:
                    df, reference_date = await api_client.get_market_summary(method=m_code, period=p_code)
                    
                    if df is not None and not df.empty:
                        data_list = df.to_dict(orient="records")
                        scraped_at = reference_date if reference_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        db_manager.save_neobdm_record_batch(m_code, p_code, data_list, scraped_at=scraped_at)
                        print(f"    [+] Success: Saved {len(df)} rows.")
                    else:
                        print(f"    [-] Warning: No data found.")
                        
                except Exception as e:
                    print(f"    [!] Error during fetch: {e}")
                
                # Cool-down
                await asyncio.sleep(1)
    finally:
        await api_client.close()

    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n=== Batch Fetch Completed in {duration.total_seconds():.2f}s ===")

if __name__ == "__main__":
    asyncio.run(run_batch_scrape())
