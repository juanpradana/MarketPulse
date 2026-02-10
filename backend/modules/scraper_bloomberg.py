"""
Bloomberg Technoz Market News Scraper.

Scrapes news articles from https://www.bloombergtechnoz.com/indeks/market
Following the same architecture as scraper_bisnis.py with hybrid date filtering.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime, timedelta
import pytz
from modules.utils import extract_tickers, clean_text_regex, is_blacklisted, has_whitelist_keywords
from modules.database import DatabaseManager

# --- CONFIG & CONSTANTS ---
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.bloombergtechnoz.com/"
}

# English month mapping (Bloomberg Technoz uses English month names on detail pages)
MONTH_MAP = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
    # Indonesian month names (fallback)
    'januari': '01', 'februari': '02', 'maret': '03',
    'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
    'oktober': '10', 'desember': '12',
    # Short forms
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
    'jun': '06', 'jul': '07', 'aug': '08', 'agu': '08',
    'sep': '09', 'oct': '10', 'okt': '10', 'nov': '11', 'dec': '12', 'des': '12'
}


def parse_bloomberg_date(date_str):
    """
    Parses Bloomberg Technoz date format from article detail page.
    
    Format: "10 February 2026 18:25"
    
    Returns: datetime object (aware, Asia/Jakarta) or None if parsing fails.
    """
    if not date_str:
        return None
    
    try:
        text = date_str.strip().lower()
        
        # Replace month names with numbers
        for month_name, num in MONTH_MAP.items():
            if month_name in text:
                text = text.replace(month_name, num)
                break
        
        # Try pattern: "10 02 2026 18:25"
        match = re.search(r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})\s+(\d{1,2}):(\d{2})', text)
        if match:
            day, month, year, hour, minute = map(int, match.groups())
            dt = datetime(year, month, day, hour, minute, 0)
            return JAKARTA_TZ.localize(dt)
        
        # Try pattern without time: "10 02 2026"
        match = re.search(r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})', text)
        if match:
            day, month, year = map(int, match.groups())
            dt = datetime(year, month, day, 0, 0, 0)
            return JAKARTA_TZ.localize(dt)
            
    except Exception as e:
        print(f"[-] Bloomberg date parse error: {e} | Input: {date_str}")
    
    return None


def parse_relative_time(date_str):
    """
    Parses relative time from Bloomberg Technoz related articles section.
    
    Formats:
    - "Market | 2 jam yang lalu"
    - "Market | 5 menit yang lalu"
    - "10 February 2026 18:25" (absolute)
    
    Returns: datetime object (aware, Asia/Jakarta)
    """
    if not date_str:
        return datetime.now(JAKARTA_TZ)
    
    now = datetime.now(JAKARTA_TZ)
    text = date_str.strip().lower()
    
    try:
        # Pattern 1: "X menit yang lalu"
        minutes_match = re.search(r'(\d+)\s*menit', text)
        if minutes_match:
            mins = int(minutes_match.group(1))
            return now - timedelta(minutes=mins)
        
        # Pattern 2: "X jam yang lalu"
        hours_match = re.search(r'(\d+)\s*jam', text)
        if hours_match:
            hours = int(hours_match.group(1))
            return now - timedelta(hours=hours)
        
        # Pattern 3: "X hari yang lalu"
        days_match = re.search(r'(\d+)\s*hari', text)
        if days_match:
            days = int(days_match.group(1))
            return now - timedelta(days=days)
        
        # Pattern 4: Absolute date
        parsed = parse_bloomberg_date(text)
        if parsed:
            return parsed
        
        return now
        
    except Exception as e:
        print(f"[-] Relative time parse error: {e}")
        return now


class BloombergTechnozScraper:
    """Scraper for Bloomberg Technoz Market news with hybrid date filtering."""
    
    # Index pages to scrape (Market + Finansial categories)
    BASE_URLS = [
        "https://www.bloombergtechnoz.com/indeks/market",
        "https://www.bloombergtechnoz.com/indeks/finansial"
    ]
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.news_data = []
    
    def get_index_page_with_dates(self, base_url, page=1):
        """
        Fetches article links from index page.
        
        Bloomberg Technoz uses infinite scroll, but also supports ?page= parameter.
        
        Returns: List of tuples (url, estimated_date, title)
        """
        url = f"{base_url}?page={page}" if page > 1 else base_url
        
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                print(f"[-] Index page {page} returned status {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            articles = []
            seen_urls = set()
            
            # Find all detail-news links
            for a_tag in soup.find_all('a', href=re.compile(r'/detail-news/\d+')):
                href = a_tag.get('href', '')
                if not href:
                    continue
                
                # Normalize URL
                if href.startswith('/'):
                    href = 'https://www.bloombergtechnoz.com' + href
                
                if href in seen_urls:
                    continue
                seen_urls.add(href)
                
                # Get title from h5 or h6 inside the link
                title_tag = a_tag.find(['h5', 'h6', 'h4', 'h3'])
                title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
                
                # Skip if title is too short (likely navigation links)
                if not title or len(title) < 10:
                    continue
                
                # Try to get date from nearby h6 (related articles show "Market | 2 jam yang lalu")
                date_text = ""
                parent = a_tag.find_parent()
                if parent:
                    h6_tags = parent.find_all('h6')
                    for h6 in h6_tags:
                        h6_text = h6.get_text(strip=True)
                        if any(kw in h6_text.lower() for kw in ['jam', 'menit', 'hari', 'lalu', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                            date_text = h6_text
                            break
                
                estimated_date = parse_relative_time(date_text) if date_text else datetime.now(JAKARTA_TZ)
                articles.append((href, estimated_date, title))
            
            return articles
            
        except Exception as e:
            print(f"[-] Error fetching index page {page}: {e}")
            return []
    
    def get_article_detail(self, url, estimated_date=None):
        """
        Fetches and extracts article details from Bloomberg Technoz detail page.
        
        Returns: Dict with article data or None if failed.
        """
        try:
            time.sleep(random.uniform(0.3, 0.8))  # Polite delay
            
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Title - from <h1> inside <article>
            article_tag = soup.find('article')
            h1 = article_tag.find('h1') if article_tag else soup.find('h1')
            title = h1.get_text(strip=True) if h1 else ""
            
            # 2. Date - from <h5> tag with date pattern "10 February 2026 18:25"
            article_date = None
            
            # Strategy 1: Find h5 tags inside article that contain date
            if article_tag:
                for h5 in article_tag.find_all('h5'):
                    h5_text = h5.get_text(strip=True)
                    # Check if it looks like a date (contains month name or digits with colon)
                    if re.search(r'\d{1,2}\s+\w+\s+\d{4}\s+\d{1,2}:\d{2}', h5_text):
                        article_date = parse_bloomberg_date(h5_text)
                        if article_date:
                            break
            
            # Strategy 2: Try meta tags
            if not article_date:
                meta_date = soup.find('meta', {'property': 'article:published_time'})
                if meta_date and meta_date.get('content'):
                    try:
                        iso_date = meta_date['content']
                        dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
                        article_date = dt.astimezone(JAKARTA_TZ)
                    except:
                        pass
            
            # Strategy 3: Try <time> tags
            if not article_date:
                time_tag = soup.find('time')
                if time_tag:
                    dt_attr = time_tag.get('datetime')
                    if dt_attr:
                        try:
                            dt = datetime.fromisoformat(dt_attr.replace('Z', '+00:00'))
                            article_date = dt.astimezone(JAKARTA_TZ)
                        except:
                            pass
                    if not article_date:
                        article_date = parse_bloomberg_date(time_tag.get_text(strip=True))
            
            # Strategy 4: Fallback to estimated date
            if not article_date:
                article_date = estimated_date or datetime.now(JAKARTA_TZ)
            
            # 3. Content - from <p> tags inside <article>
            content_text = ""
            
            if article_tag:
                # Remove unwanted elements
                for tag in article_tag.find_all(['script', 'style', 'iframe', 'aside', 'nav']):
                    tag.decompose()
                
                # Remove "Baca Juga" section
                for baca_juga in article_tag.find_all('h3', string=re.compile(r'Baca Juga', re.I)):
                    parent = baca_juga.find_parent()
                    if parent:
                        parent.decompose()
                
                paragraphs = article_tag.find_all('p')
                content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Fallback: get all <p> from page
            if not content_text:
                paragraphs = soup.find_all('p')
                content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs[:15] if p.get_text(strip=True)])
            
            content_text = clean_text_regex(content_text)
            
            # 4. Extract Tickers
            tickers = extract_tickers(title)
            if not tickers:
                tickers = extract_tickers(content_text[:1000])
            
            return {
                'title': title,
                'url': url,
                'date': article_date,
                'timestamp': article_date.isoformat(),
                'clean_text': content_text,
                'summary': content_text[:300] + '...' if len(content_text) > 300 else content_text,
                'ticker': ', '.join(tickers) if tickers else '',
                'source': 'Bloomberg Technoz'
            }
            
        except Exception as e:
            print(f"[-] Error fetching article {url}: {e}")
            return None
    
    def run(self, start_date, end_date=None, pages=20):
        """
        Main scraper method with HYBRID approach.
        
        Scrapes from both Market and Finansial categories.
        
        Args:
            start_date: Start date (datetime or date)
            end_date: End date (datetime or date), defaults to now
            pages: Maximum pages per category
            
        Returns:
            List of analyzed article dictionaries
        """
        # Normalize dates
        target_start = start_date.date() if isinstance(start_date, datetime) else start_date
        target_end = end_date.date() if isinstance(end_date, datetime) else (end_date or datetime.now().date())
        
        print("\n" + "="*60)
        print("📊 BLOOMBERG TECHNOZ SCRAPER")
        print("="*60)
        print(f"   Target Range: {target_start} → {target_end}")
        print(f"   Max Pages per Category: {pages}")
        
        # Load existing URLs for incremental scraping
        db = DatabaseManager()
        existing_urls = set(db.get_all_urls())
        print(f"   Existing URLs in DB: {len(existing_urls)}")
        print("-"*60)
        
        self.news_data = []
        processed_urls = set()
        
        # Process each category
        for base_url in self.BASE_URLS:
            category = "market" if "market" in base_url else "finansial"
            print(f"\n{'~'*50}")
            print(f"[{category.upper()}] CATEGORY: {category}")
            print(f"{'~'*50}")
            
            page = 1
            stop_category = False
            old_article_streak = 0
            worthless_streak = 0
            
            while page <= pages and not stop_category:
                print(f"[*] {category} Page {page}...")
                
                articles = self.get_index_page_with_dates(base_url, page)
                if not articles:
                    print("[-] No articles found. Moving to next category.")
                    break
                
                valid_articles = 0
                blacklisted_count = 0
                
                for url, estimated_date, index_title in articles:
                    # 1. Check if already in DB or processed
                    if url in existing_urls or url in processed_urls:
                        worthless_streak += 1
                        if worthless_streak >= 10:
                            print(f"[STOP] 10 consecutive existing/duplicate URLs.")
                            stop_category = True
                            break
                        continue
                    
                    processed_urls.add(url)
                    worthless_streak = 0
                    
                    # 2. Blacklist check on index title
                    is_bad, reason = is_blacklisted(index_title, url)
                    if is_bad:
                        blacklisted_count += 1
                        continue
                    
                    # 3. Fetch article detail for PRECISE date
                    article = self.get_article_detail(url, estimated_date)
                    if not article:
                        continue
                    
                    # 4. PRECISE date check from detail page
                    article_date = article['date'].date()
                    
                    if article_date < target_start:
                        old_article_streak += 1
                        print(f"  [SKIP] Detail date {article_date} < start {target_start} ({old_article_streak}/10)")
                        if old_article_streak >= 10:
                            print(f"[STOP] 10 consecutive articles older than target.")
                            stop_category = True
                            break
                        continue
                    
                    if article_date > target_end:
                        print(f"  [SKIP] Detail date {article_date} > end {target_end}")
                        continue
                    
                    # Reset old article streak
                    old_article_streak = 0
                    
                    # 5. Ticker/Whitelist check
                    if not article['ticker']:
                        if not has_whitelist_keywords(article['title'] + ' ' + article['clean_text'][:500]):
                            print(f"  [SKIP] No ticker/whitelist: {article['title'][:30]}...")
                            continue
                    
                    # Success!
                    self.news_data.append(article)
                    valid_articles += 1
                    print(f"  [OK] [{article_date}] {article['title'][:50]}...")
                
                print(f"  -> Page {page} done. Valid: {valid_articles}" + (f", Blacklisted: {blacklisted_count}" if blacklisted_count else ""))
                page += 1
        
        print(f"\n[*] Scraping complete. Total: {len(self.news_data)} articles")
        
        return self.news_data


if __name__ == "__main__":
    # Quick test - scrape last 3 days
    scraper = BloombergTechnozScraper()
    start = datetime.now() - timedelta(days=3)
    end = datetime.now()
    results = scraper.run(start, end, pages=3)
    print(f"\n=== Results: {len(results)} articles ===")
    for r in results[:5]:
        print(f"  - {r.get('title', 'N/A')[:60]}")
        print(f"    Date: {r.get('timestamp', 'N/A')}")
        print(f"    Tickers: {r.get('ticker', 'N/A')}")
