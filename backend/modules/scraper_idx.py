from curl_cffi import requests
import datetime
import os
import json
import time
import logging
from modules.database import DatabaseManager

logger = logging.getLogger(__name__)

# Constants
IDX_API_URL = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement"
REFERER_URL = "https://www.idx.co.id/id/perusahaan-tercatat/keterbukaan-informasi/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def _create_session():
    """Create a reusable curl_cffi session with proper headers."""
    s = requests.Session(impersonate="chrome120")
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Referer": REFERER_URL,
        "Accept": "application/json, text/plain, */*",
    })
    return s

def _format_date(d):
    """Convert date input to YYYYMMDD string format."""
    if not d:
        return datetime.date.today().strftime("%Y%m%d")
    if isinstance(d, (datetime.date, datetime.datetime)):
        return d.strftime("%Y%m%d")
    return str(d).replace("-", "")

def fetch_idx_disclosures(ticker=None, date_from=None, date_to=None, limit=None, save_to_db=False):
    """
    Fetches Corporate Disclosures from IDX API.
    
    Args:
        ticker (str, optional): Stock ticker code.
        date_from (str/datetime): Start date.
        date_to (str/datetime): End date.
        limit (int, optional): Max records.
        save_to_db (bool): If True, saves metadata to SQLite (status: PENDING).

    Returns:
        list: List of dictionaries containing disclosure details.
    """
    date_from = _format_date(date_from)
    date_to = _format_date(date_to)

    session = _create_session()
    
    # Warm up session with cookies
    try:
        session.get(REFERER_URL, timeout=15)
    except Exception:
        logger.warning("IDX warm-up request failed, continuing anyway...")

    db = DatabaseManager() if save_to_db else None

    results = []
    current_index = 0
    page_size = 100 
    max_retries = 3
    
    logger.info(f"Fetching IDX disclosures for ticker={ticker}, range={date_from}-{date_to}...")

    while True:
        if limit and len(results) >= limit:
            break

        current_request_size = page_size
        if limit:
            remaining = limit - len(results)
            if remaining < page_size:
                current_request_size = remaining

        params = {
            "kodeEmiten": ticker if ticker else "",
            "emitenType": "*",
            "indexFrom": current_index,
            "pageSize": current_request_size,
            "dateFrom": date_from,
            "dateTo": date_to,
            "lang": "id",
            "keyword": ""
        }
        
        # Retry logic for transient failures
        response = None
        for attempt in range(max_retries):
            try:
                response = session.get(IDX_API_URL, params=params, timeout=30)
                if response.status_code == 200:
                    break
                logger.warning(f"IDX API returned status {response.status_code}, attempt {attempt+1}/{max_retries}")
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                logger.warning(f"IDX API request failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))
        
        if not response or response.status_code != 200:
            logger.error(f"IDX API failed after {max_retries} retries at index {current_index}")
            break
        
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse IDX API response: {e}")
            break
            
        replies = data.get("Replies", [])
        
        if not replies:
            break
            
        for item in replies:
            pengumuman = item.get("pengumuman", {})
            attachments = item.get("attachments", [])
            
            if not attachments:
                continue
                
            title = pengumuman.get("JudulPengumuman", "No Title")
            pub_date = pengumuman.get("TglPengumuman", "") 
            item_ticker = pengumuman.get("Kode_Emiten", ticker or "")
            
            for att in attachments:
                download_url = att.get("FullSavePath", "")
                original_filename = att.get("OriginalFilename", "")
                
                if not download_url:
                    continue
                    
                file_id = download_url.split("/")[-1]

                record = {
                    "date": pub_date,
                    "ticker": item_ticker.strip() if item_ticker else "",
                    "title": title,
                    "download_url": download_url,
                    "file_id": file_id,
                    "filename": original_filename,
                    "local_path": ""
                }
                
                results.append(record)

                if save_to_db and db:
                    db.insert_disclosure(record)

        logger.info(f"  Fetched items {current_index+1} to {current_index + len(replies)}...")
        current_index += len(replies)
        
        if len(replies) < current_request_size:
            break
            
        time.sleep(0.5)

    logger.info(f"Total disclosures found: {len(results)}")
    return results

def download_pdf(url, save_dir, session=None):
    """
    Downloads a PDF using curl_cffi.
    
    Args:
        url: Download URL
        save_dir: Directory to save the file
        session: Optional reusable session (creates new one if None)
    
    Returns:
        str: Local file path if successful, None otherwise
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    filename = url.split("/")[-1]
    filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_', '-')]).strip()
    
    if not filename:
        filename = f"idx_doc_{int(time.time())}.pdf"
    
    save_path = os.path.join(save_dir, filename)

    # Skip if already downloaded
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        logger.info(f"  Already exists, skipping: {filename}")
        return save_path

    try:
        if session is None:
            session = _create_session()
        
        response = session.get(url, timeout=60)
        
        if response.status_code == 200:
            content = response.content
            # Validate we got actual content (not an error page)
            if len(content) < 100:
                logger.warning(f"  Downloaded file too small ({len(content)} bytes), skipping: {filename}")
                return None
            
            with open(save_path, "wb") as f:
                f.write(content)
            return save_path
        else:
            logger.warning(f"  Failed to download {filename}: Status {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"  Failed to download {filename}: {e}")
        return None

def fetch_and_save_pipeline(ticker=None, days=30, download_dir="downloads", start_date=None, end_date=None):
    """
    Full pipeline: fetch metadata -> download PDFs -> update DB.
    
    Returns:
        dict: Pipeline result with counts and status
    """
    db = DatabaseManager()
    
    # Determine date range
    if start_date and end_date:
        s_date = start_date
        e_date = end_date
    else:
        s_date = datetime.date.today() - datetime.timedelta(days=days)
        e_date = datetime.date.today()
    
    logger.info(f"[*] Starting IDX Scraper Pipeline for ticker: {ticker or 'ALL'}")
    logger.info(f"[*] Date Range: {s_date} to {e_date}")
    
    result = {
        "fetched": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "status": "success"
    }
    
    # 1. Fetch & Save Metadata
    try:
        disclosures = fetch_idx_disclosures(
            ticker=ticker, 
            date_from=s_date, 
            date_to=e_date, 
            save_to_db=True
        )
    except Exception as e:
        logger.error(f"Failed to fetch IDX disclosures: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result
    
    if not disclosures:
        logger.info("[-] No disclosures found.")
        result["status"] = "empty"
        return result
    
    result["fetched"] = len(disclosures)
    
    # 2. Download PDFs with reused session
    download_session = _create_session()
    
    for item in disclosures:
        url = item['download_url']
        fname = item.get('filename', url.split('/')[-1])
        logger.info(f"  Downloading: {fname}")
        
        local_path = download_pdf(url, download_dir, session=download_session)
        
        if local_path:
            # Update DB with local path using proper repository method
            db.disclosure_repo.update_local_path(url, local_path, 'DOWNLOADED')
            result["downloaded"] += 1
        else:
            result["failed"] += 1
    
    logger.info(f"[*] Pipeline complete. Fetched={result['fetched']}, Downloaded={result['downloaded']}, Failed={result['failed']}")
    return result
