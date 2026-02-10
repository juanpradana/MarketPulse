"""Scraper routes for triggering news and disclosure scrapers."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api", tags=["scrapers"])


class ScrapeRequest(BaseModel):
    """Request model for scraper endpoints."""
    source: str
    start_date: str
    end_date: str
    ticker: Optional[str] = None
    scrape_all_history: Optional[bool] = False


@router.post("/scrape")
async def run_scraper(request: ScrapeRequest):
    """
    Execute news/disclosure scrapers based on source.
    
    Supported sources:
    - "EmitenNews": Scrape from emitennews.com
    - "CNBC Indonesia": Scrape from cnbcindonesia.com
    - "Bisnis.com": Scrape from bisnis.com market section
    - "Investor.id": Scrape from investor.id (corporate-action + market)
    - "IDX (Keterbukaan Informasi)": Scrape IDX disclosures
    
    Args:
        request: Scraper configuration including source, date range, and ticker
    
    Returns:
        Status, message, and count of new items scraped
    """
    try:
        from modules.database import DatabaseManager
        from modules.analyzer import get_engine
        from modules.utils import extract_tickers
        
        db_manager = DatabaseManager()
        
        # Parse dates
        start_dt = datetime.fromisoformat(request.start_date)
        end_dt = datetime.fromisoformat(request.end_date)
        
        new_count = 0
        message = ""
        
        if request.source == "EmitenNews":
            from modules.scraper_emiten import EmitenNewsScraper
            scraper = EmitenNewsScraper()
            raw_articles = scraper.run(start_dt, end_dt)
            
            if raw_articles:
                engine = get_engine()
                analyzed_data = engine.process_and_save(raw_articles)
                
                # Enrich with ticker extraction
                for article in analyzed_data:
                    if 'ticker' not in article or not article['ticker']:
                        article['ticker'] = extract_tickers(article.get('title', ''))
                
                db_manager.save_news(analyzed_data)
                new_count = len(analyzed_data)
                message = f"Berhasil mengambil {new_count} berita dari EmitenNews."
            else:
                message = "Tidak ada berita baru ditemukan di EmitenNews."

        elif request.source == "CNBC Indonesia":
            from modules.scraper_cnbc import CNBCScraper
            scraper = CNBCScraper()
            raw_articles = scraper.run(start_date=start_dt, end_date=end_dt)
            
            if raw_articles:
                engine = get_engine()
                analyzed_data = engine.process_and_save(raw_articles)
                db_manager.save_news(analyzed_data)
                new_count = len(analyzed_data)
                message = f"Berhasil mengambil {new_count} berita dari CNBC Indonesia."
            else:
                message = "Tidak ada berita baru ditemukan di CNBC Indonesia."

        elif request.source == "IDX (Keterbukaan Informasi)":
            import logging
            idx_logger = logging.getLogger("scraper_idx_route")
            
            from modules.scraper_idx import fetch_and_save_pipeline
            
            final_start = start_dt.date()
            final_end = end_dt.date()
            
            if request.ticker and request.scrape_all_history:
                final_start = datetime(2010, 1, 1).date()
                final_end = datetime.now().date()
            
            # Step 1: Download pipeline
            pipeline_result = fetch_and_save_pipeline(
                ticker=request.ticker if request.ticker and request.ticker.strip() != "" else None,
                start_date=final_start,
                end_date=final_end,
                download_dir="downloads"
            )
            
            new_count = pipeline_result.get("downloaded", 0)
            fetched = pipeline_result.get("fetched", 0)
            failed_dl = pipeline_result.get("failed", 0)
            
            # Step 2: Auto-run Indexing ONLY for newly downloaded docs
            #         (not the entire backlog - that would take hours)
            process_msg = ""
            downloaded_urls = pipeline_result.get("downloaded_urls", [])
            try:
                from idx_processor import IDXProcessor
                processor = IDXProcessor()
                if downloaded_urls:
                    proc_result = processor.run_processor_for_urls(downloaded_urls)
                else:
                    proc_result = {"processed": 0, "success": 0, "failed": 0}
                
                proc_success = proc_result.get("success", 0)
                proc_failed = proc_result.get("failed", 0)
                process_msg = f" Diproses: {proc_success} berhasil, {proc_failed} gagal."
            except Exception as proc_err:
                idx_logger.error(f"IDX Processor error (non-fatal): {proc_err}")
                process_msg = f" Indexing dilewati: {str(proc_err)[:100]}"
            
            message = (
                f"Pipeline IDX Selesai. "
                f"Ditemukan: {fetched}, Terdownload: {new_count}, Gagal download: {failed_dl}."
                f"{process_msg}"
            )
            
        elif request.source == "Bisnis.com":
            from modules.scraper_bisnis import BisnisScraper
            scraper = BisnisScraper()
            raw_articles = scraper.run(start_date=start_dt, end_date=end_dt)
            
            if raw_articles:
                engine = get_engine()
                analyzed_data = engine.process_and_save(raw_articles)
                db_manager.save_news(analyzed_data)
                new_count = len(analyzed_data)
                message = f"Berhasil mengambil {new_count} berita dari Bisnis.com."
            else:
                message = "Tidak ada berita baru ditemukan di Bisnis.com."

        elif request.source == "Investor.id":
            from modules.scraper_investor import InvestorScraper
            scraper = InvestorScraper()
            raw_articles = scraper.run(start_date=start_dt, end_date=end_dt)
            
            if raw_articles:
                engine = get_engine()
                analyzed_data = engine.process_and_save(raw_articles)
                db_manager.save_news(analyzed_data)
                new_count = len(analyzed_data)
                message = f"Berhasil mengambil {new_count} berita dari Investor.id."
            else:
                message = "Tidak ada berita baru ditemukan di Investor.id."

        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Sumber tidak dikenal: {request.source}"}
            )

        return {
            "status": "success",
            "message": message,
            "new_count": new_count
        }
        
    except Exception as e:
        print(f"Scrape Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
