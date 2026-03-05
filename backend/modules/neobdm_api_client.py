"""
NeoBDM API Client - HTTP-based replacement for Playwright scraping.

Uses direct API calls to neobdm.tech instead of browser automation,
resulting in 10-50x faster data retrieval.

API endpoints discovered:
1. Market Summary: POST /django_plotly_dash/app/ms_app/_dash-update-component
2. Broker Summary: POST /api/broker-summary (form-encoded, needs CSRF)
3. Inventory:      POST /django_plotly_dash/app/ia_app/_dash-update-component
4. Transaction:    POST /django_plotly_dash/app/tc_app/_dash-update-component
"""

import os
import re
import json
import base64
import struct
import asyncio
import logging
import numpy as np
import pandas as pd
import httpx
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

load_dotenv()

# Plotly binary dtype mapping
PLOTLY_DTYPE_MAP = {
    'i1': ('b', 1),   # int8
    'u1': ('B', 1),   # uint8
    'i2': ('<h', 2),  # int16 LE
    'u2': ('<H', 2),  # uint16 LE
    'i4': ('<i', 4),  # int32 LE
    'u4': ('<I', 4),  # uint32 LE
    'f4': ('<f', 4),  # float32 LE
    'f8': ('<d', 8),  # float64 LE
}


def _decode_plotly_bdata(bdata: str, dtype: str) -> list:
    """Decode Plotly binary-encoded array data.
    
    Plotly uses base64-encoded typed arrays for efficient data transfer.
    Format: {"dtype": "i2", "bdata": "<base64>"}
    """
    if not bdata or not dtype:
        return []
    
    try:
        raw = base64.b64decode(bdata)
        fmt_info = PLOTLY_DTYPE_MAP.get(dtype)
        if not fmt_info:
            logger.warning(f"Unknown Plotly dtype: {dtype}")
            return []
        
        fmt_char, byte_size = fmt_info
        count = len(raw) // byte_size
        values = list(struct.unpack(f'<{count}{fmt_char[-1]}', raw))
        return values
    except Exception as e:
        logger.warning(f"Failed to decode bdata (dtype={dtype}): {e}")
        return []


def _extract_plotly_array(data) -> list:
    """Extract array from Plotly data, handling both regular arrays and binary format."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and 'bdata' in data and 'dtype' in data:
        return _decode_plotly_bdata(data['bdata'], data['dtype'])
    return []


class NeoBDMApiClient:
    """HTTP-based client for neobdm.tech APIs. No browser needed."""
    
    def __init__(self):
        self.email = os.getenv("NEOBDM_EMAIL")
        self.password = os.getenv("NEOBDM_PASSWORD")
        self.base_url = "https://neobdm.tech"
        self.client: Optional[httpx.AsyncClient] = None
        self._logged_in = False
        self._csrf_token: Optional[str] = None
    
    async def _ensure_client(self):
        """Create HTTP client if not exists."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=15.0),
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
    
    async def login(self) -> bool:
        """Login to neobdm.tech via HTTP and store session cookies."""
        await self._ensure_client()
        
        try:
            # 1. GET login page to get CSRF token
            login_url = f"{self.base_url}/accounts/login/"
            resp = await self.client.get(login_url)
            
            if resp.status_code != 200:
                logger.error(f"Failed to load login page: {resp.status_code}")
                return False
            
            # Extract CSRF token from the page
            csrf_token = self._extract_csrf_from_html(resp.text)
            if not csrf_token:
                # Try from cookies
                csrf_token = self.client.cookies.get('csrftoken', '')
            
            if not csrf_token:
                logger.error("Could not find CSRF token on login page")
                return False
            
            # 2. POST login credentials
            login_data = {
                'login': self.email,
                'password': self.password,
                'csrfmiddlewaretoken': csrf_token,
            }
            
            resp = await self.client.post(
                login_url,
                data=login_data,
                headers={
                    'Referer': login_url,
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            )
            
            # Check if login succeeded (should redirect to /home/)
            if '/home/' in str(resp.url) or resp.status_code == 200:
                self._logged_in = True
                logger.info(f"API Client: Login successful for {self.email}")
                return True
            
            logger.error(f"API Client: Login failed. URL: {resp.url}, Status: {resp.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"API Client: Login error: {e}")
            return False
    
    def _extract_csrf_from_html(self, html: str) -> Optional[str]:
        """Extract CSRF token from HTML page."""
        # Try hidden input
        match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)', html)
        if match:
            return match.group(1)
        # Try meta tag
        match = re.search(r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)', html)
        if match:
            return match.group(1)
        return None
    
    async def _get_csrf_for_page(self, page_url: str) -> Optional[str]:
        """Get CSRF token by loading a page."""
        await self._ensure_client()
        try:
            resp = await self.client.get(page_url)
            if resp.status_code == 200:
                token = self._extract_csrf_from_html(resp.text)
                if token:
                    self._csrf_token = token
                return token
        except Exception as e:
            logger.warning(f"Failed to get CSRF from {page_url}: {e}")
        return self._csrf_token
    
    # ==================== MARKET SUMMARY ====================
    
    async def get_market_summary(self, method: str = 'm', period: str = 'd') -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Fetch market summary data via Dash API.
        
        Returns same format as NeoBDMScraper.get_market_summary():
            (DataFrame, reference_date_string)
        
        ~50x faster than Playwright (1-2s vs 60-120s).
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return None, None
        
        try:
            # Map method codes to Dash values
            method_map = {
                'm': 'm',
                'nr': 'nr',
                'f': 'f',
            }
            period_map = {
                'd': 'd',
                'c': 'c',
                'w': 'w',
            }
            
            dash_method = method_map.get(method, method)
            dash_period = period_map.get(period, period)
            
            # Build summary options (compatible + ma)
            summary_options = ['compatible', 'ma']
            
            payload = {
                "output": "market-summary.children",
                "outputs": {"id": "market-summary", "property": "children"},
                "inputs": [
                    {"id": "method", "property": "value", "value": dash_method},
                    {"id": "index", "property": "value", "value": "ALL"},
                    {"id": "summary-mode", "property": "value", "value": dash_period},
                    {"id": "summary-options", "property": "value", "value": summary_options},
                    {"id": "user_id", "property": "value", "value": ""}
                ],
                "changedPropIds": ["method.value"]
            }
            
            url = f"{self.base_url}/django_plotly_dash/app/ms_app/_dash-update-component"
            
            resp = await self.client.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if resp.status_code != 200:
                logger.error(f"Market summary API returned {resp.status_code}")
                return None, None
            
            data = resp.json()
            return self._parse_market_summary_response(data)
            
        except Exception as e:
            logger.error(f"Market summary API error: {e}")
            return None, None
    
    def _parse_market_summary_response(self, data: dict) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """Parse the Dash API response for market summary into DataFrame."""
        try:
            response = data.get('response', {})
            market_summary = response.get('market-summary', {})
            children = market_summary.get('children', [])
            
            if not children:
                return None, None
            
            # Extract reference date from first child (Label)
            reference_date = None
            table_data = None
            
            for child in children:
                child_type = child.get('type', '')
                props = child.get('props', {})
                
                # Look for the label with date
                if child_type == 'Label':
                    label_text = props.get('children', '')
                    if '[' in label_text and ']' in label_text:
                        reference_date = label_text.split('[')[1].split(']')[0]
                
                # Look for the Row containing the label
                if child_type == 'Row':
                    row_children = props.get('children', [])
                    if isinstance(row_children, list):
                        for rc in row_children:
                            if isinstance(rc, dict) and rc.get('type') == 'Label':
                                label_text = rc.get('props', {}).get('children', '')
                                if '[' in label_text and ']' in label_text:
                                    reference_date = label_text.split('[')[1].split(']')[0]
                    elif isinstance(row_children, dict) and row_children.get('type') == 'Label':
                        label_text = row_children.get('props', {}).get('children', '')
                        if '[' in label_text and ']' in label_text:
                            reference_date = label_text.split('[')[1].split(']')[0]
                
                # Look for DataTable
                if child_type == 'DataTable':
                    table_data = props.get('data', [])
                
                # DataTable might be nested inside a Row or Div
                if child_type in ('Row', 'Div', 'Col'):
                    table_data = self._find_datatable_data(props)
            
            if not table_data:
                # Try deeper nesting
                table_data = self._find_datatable_data({'children': children})
            
            if not table_data:
                logger.warning("No DataTable data found in market summary response")
                return None, reference_date
            
            # Clean symbol HTML from data
            cleaned_data = []
            for row in table_data:
                cleaned_row = {}
                for key, value in row.items():
                    if key == 'symbol' and isinstance(value, str) and '<a' in value:
                        # Extract ticker from HTML link
                        match = re.search(r'>([A-Z0-9]+)</a>\s*$', value)
                        if match:
                            cleaned_row['symbol'] = match.group(1)
                        else:
                            # Fallback: strip all HTML
                            cleaned_row['symbol'] = re.sub(r'<[^>]+>', '', value).strip()
                    else:
                        cleaned_row[key] = value
                cleaned_data.append(cleaned_row)
            
            if cleaned_data:
                df = pd.DataFrame(cleaned_data)
                logger.info(f"API: Extracted {len(df)} market summary rows (date: {reference_date})")
                return df, reference_date
            
            return None, reference_date
            
        except Exception as e:
            logger.error(f"Error parsing market summary response: {e}")
            return None, None
    
    def _find_datatable_data(self, props: dict) -> Optional[list]:
        """Recursively find DataTable data in nested Dash component tree."""
        children = props.get('children', [])
        if not isinstance(children, list):
            children = [children] if children else []
        
        for child in children:
            if not isinstance(child, dict):
                continue
            
            child_type = child.get('type', '')
            child_props = child.get('props', {})
            
            if child_type == 'DataTable':
                data = child_props.get('data', [])
                if data:
                    return data
            
            # Recurse into children
            result = self._find_datatable_data(child_props)
            if result:
                return result
        
        return None
    
    # ==================== BROKER SUMMARY ====================
    
    async def get_broker_summary(self, ticker: str, date_str: str) -> Optional[Dict]:
        """
        Fetch broker summary via API.
        
        Returns same format as NeoBDMScraper.get_broker_summary():
            {"buy": [...], "sell": [...]}
        
        Args:
            ticker: Stock ticker (e.g. 'BBCA')
            date_str: Date in YYYY-MM-DD format
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return None
        
        try:
            # Get CSRF token from broker summary page
            csrf = await self._get_csrf_for_page(f"{self.base_url}/broker_summary/")
            if not csrf:
                logger.error("Could not get CSRF token for broker summary")
                return None
            
            # Convert date format: YYYY-MM-DD -> DD MMM YYYY
            display_date = self._format_display_date(date_str)
            
            form_data = {
                'tick': ticker.upper(),
                'start_date': display_date,
                'end_date': display_date,
                'event': 'load',
                'foreign_only': 'false',
                'domestic_only': 'false',
                'net': 'net',
                'show_broker_inventory': 'false',
                'csrfmiddlewaretoken': csrf,
            }
            
            resp = await self.client.post(
                f"{self.base_url}/api/broker-summary",
                data=form_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrf,
                    'Referer': f"{self.base_url}/broker_summary/",
                }
            )
            
            if resp.status_code != 200:
                logger.error(f"Broker summary API returned {resp.status_code}")
                return None
            
            result = resp.json()
            
            if not result.get('success', True):
                logger.warning(f"Broker summary API returned success=false for {ticker} on {date_str}")
                return None
            
            # Parse HTML response
            html = result.get('broksum_html', '')
            if not html or 'Data tidak tersedia' in html:
                logger.info(f"No broker summary data for {ticker} on {date_str}")
                return None
            
            return self._parse_broker_summary_html(html)
            
        except Exception as e:
            logger.error(f"Broker summary API error for {ticker}: {e}")
            return None
    
    def _parse_broker_summary_html(self, html: str) -> Optional[Dict]:
        """Parse broker summary HTML table into buy/sell data."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table', id='broker-summary-table')
            if not table:
                # Try finding any table
                table = soup.find('table')
            if not table:
                return None
            
            buy_data = []
            sell_data = []
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 8:
                    continue
                
                # Buy side (columns 0-3): BY | blot | bval | bavg
                buy_broker_span = cells[0].find('span', class_='broksum-broker')
                buy_broker = buy_broker_span.get_text(strip=True) if buy_broker_span else cells[0].get_text(strip=True)
                if buy_broker:
                    buy_data.append({
                        'broker': buy_broker,
                        'nlot': cells[1].get_text(strip=True),
                        'nval': cells[2].get_text(strip=True),
                        'bavg': cells[3].get_text(strip=True),
                    })
                
                # Sell side (columns 4-7): SL | slot | sval | savg
                sell_broker_span = cells[4].find('span', class_='broksum-broker')
                sell_broker = sell_broker_span.get_text(strip=True) if sell_broker_span else cells[4].get_text(strip=True)
                if sell_broker:
                    sell_data.append({
                        'broker': sell_broker,
                        'nlot': cells[5].get_text(strip=True),
                        'nval': cells[6].get_text(strip=True),
                        'savg': cells[7].get_text(strip=True),
                    })
            
            if not buy_data and not sell_data:
                return None
            
            logger.info(f"API: Parsed {len(buy_data)} buy + {len(sell_data)} sell broker summary rows")
            return {'buy': buy_data, 'sell': sell_data}
            
        except Exception as e:
            logger.error(f"Error parsing broker summary HTML: {e}")
            return None
    
    async def get_broker_summary_batch(self, tasks: list) -> list:
        """
        Batch broker summary fetch via API.
        tasks format: [{"ticker": "ANTM", "dates": ["2026-01-12", ...]}, ...]
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return [{"error": "Login failed"}]
        
        results = []
        for task in tasks:
            ticker = task.get('ticker', '')
            dates = task.get('dates', [])
            
            for date_str in dates:
                print(f"[API] Fetching broker summary for {ticker} on {date_str}...")
                try:
                    data = await self.get_broker_summary(ticker, date_str)
                    if data:
                        results.append({
                            "ticker": ticker.upper(),
                            "trade_date": date_str,
                            "buy": data.get('buy', []),
                            "sell": data.get('sell', []),
                        })
                    else:
                        results.append({
                            "ticker": ticker.upper(),
                            "trade_date": date_str,
                            "error": "No data found",
                        })
                except Exception as e:
                    results.append({
                        "ticker": ticker.upper(),
                        "trade_date": date_str,
                        "error": str(e),
                    })
                
                await asyncio.sleep(0.5)
        
        return results
    
    # ==================== INVENTORY ====================
    
    async def get_inventory(self, ticker: str, period_months: int = 3) -> Optional[Dict]:
        """
        Fetch inventory chart data via Dash API.
        
        Returns same format as NeoBDMScraper.get_inventory():
            {brokers: [...], priceSeries: [...], lastDate, firstDate, ticker}
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return None
        
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=period_months * 30)).strftime('%Y-%m-%d')
            
            payload = {
                "output": "inventory-chart.figure",
                "outputs": {"id": "inventory-chart", "property": "figure"},
                "inputs": [
                    {"id": "submit-button", "property": "n_clicks", "value": 1},
                    {"id": "hide-tektok", "property": "value", "value": []},
                    {"id": "hide-net-dist", "property": "value", "value": []},
                    {"id": "darkmode", "property": "value", "value": []}
                ],
                "state": [
                    {"id": "tick", "property": "value", "value": ticker.upper()},
                    {"id": "broker", "property": "value", "value": ["AUTO"]},
                    {"id": "date-picker", "property": "start_date", "value": start_date},
                    {"id": "date-picker", "property": "end_date", "value": end_date}
                ]
            }
            
            url = f"{self.base_url}/django_plotly_dash/app/ia_app/_dash-update-component"
            
            resp = await self.client.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if resp.status_code != 200:
                logger.error(f"Inventory API returned {resp.status_code} for {ticker}")
                return None
            
            data = resp.json()
            return self._parse_inventory_response(data, ticker)
            
        except Exception as e:
            logger.error(f"Inventory API error for {ticker}: {e}")
            return None
    
    def _parse_inventory_response(self, data: dict, ticker: str) -> Optional[Dict]:
        """Parse Plotly figure JSON from inventory Dash API into broker data."""
        try:
            response = data.get('response', {})
            figure = response.get('inventory-chart', {}).get('figure', {})
            traces = figure.get('data', [])
            
            if not traces:
                logger.warning(f"No traces in inventory response for {ticker}")
                return None
            
            result = {
                'brokers': [],
                'priceSeries': [],
                'lastDate': None,
                'firstDate': None,
                'traceCount': len(traces),
            }
            
            for trace in traces:
                name = trace.get('name', '')
                trace_type = trace.get('type', '')
                
                # Extract price (candlestick) data
                if trace_type == 'candlestick':
                    x_data = _extract_plotly_array(trace.get('x', []))
                    close_data = _extract_plotly_array(trace.get('close'))
                    open_data = _extract_plotly_array(trace.get('open'))
                    high_data = _extract_plotly_array(trace.get('high'))
                    low_data = _extract_plotly_array(trace.get('low'))
                    
                    result['priceSeries'] = []
                    for j in range(len(x_data)):
                        result['priceSeries'].append({
                            'date': x_data[j] if j < len(x_data) else None,
                            'close': close_data[j] if j < len(close_data) else None,
                            'open': open_data[j] if j < len(open_data) else None,
                            'high': high_data[j] if j < len(high_data) else None,
                            'low': low_data[j] if j < len(low_data) else None,
                        })
                    continue
                
                # Skip volume and marker traces
                if name in ('volume', 'price'):
                    continue
                mode = trace.get('mode', '')
                if mode == 'markers+text':
                    continue
                if trace_type != 'scatter':
                    continue
                
                # Extract broker data
                y_data = _extract_plotly_array(trace.get('y'))
                x_data = _extract_plotly_array(trace.get('x', []))
                
                if not y_data:
                    continue
                
                # Clean broker code (remove checkmark/cross symbols)
                code = name.replace('\u2713', '').replace('\u2717', '').strip()
                if not code:
                    continue
                
                last_val = y_data[-1] if y_data else 0
                first_val = y_data[0] if y_data else 0
                
                broker_entry = {
                    'code': code,
                    'isClean': '\u2713' in name,
                    'isTektok': '\u2717' in name,
                    'finalNetLot': last_val,
                    'startNetLot': first_val,
                    'isAccumulating': last_val > 0,
                    'dataPoints': len(y_data),
                    'timeSeries': [
                        {
                            'date': x_data[idx] if idx < len(x_data) else None,
                            'cumNetLot': v
                        }
                        for idx, v in enumerate(y_data)
                    ]
                }
                result['brokers'].append(broker_entry)
                
                if x_data:
                    result['lastDate'] = x_data[-1]
                    result['firstDate'] = x_data[0]
            
            if result['brokers']:
                result['ticker'] = ticker
                logger.info(f"API: Extracted {len(result['brokers'])} broker traces for {ticker}")
                return result
            
            logger.warning(f"No broker data in inventory response for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing inventory response for {ticker}: {e}")
            return None
    
    # ==================== TRANSACTION CHART ====================
    
    async def get_transaction_chart(self, ticker: str, period: str = '6m') -> Optional[Dict]:
        """
        Fetch transaction chart data via Dash API.
        
        Returns same format as NeoBDMScraper.get_transaction_chart():
            {cumulative: {...}, daily: {...}, participation: {...}, cross_index, volume, ...}
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return None
        
        try:
            payload = {
                "output": "transaction-chart.figure",
                "outputs": {"id": "transaction-chart", "property": "figure"},
                "inputs": [
                    {"id": "tick", "property": "value", "value": ticker.upper()},
                    {"id": "detail", "property": "value", "value": ["detail"]},
                    {"id": "duration-picker", "property": "value", "value": period},
                    {"id": "darkmode", "property": "value", "value": []}
                ]
            }
            
            url = f"{self.base_url}/django_plotly_dash/app/tc_app/_dash-update-component"
            
            resp = await self.client.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if resp.status_code != 200:
                logger.error(f"Transaction chart API returned {resp.status_code} for {ticker}")
                return None
            
            data = resp.json()
            return self._parse_transaction_chart_response(data, ticker, period)
            
        except Exception as e:
            logger.error(f"Transaction chart API error for {ticker}: {e}")
            return None
    
    def _parse_transaction_chart_response(self, data: dict, ticker: str, period: str) -> Optional[Dict]:
        """Parse Plotly figure JSON from transaction chart Dash API."""
        try:
            response = data.get('response', {})
            figure = response.get('transaction-chart', {}).get('figure', {})
            traces = figure.get('data', [])
            
            if not traces:
                logger.warning(f"No traces in transaction chart response for {ticker}")
                return None
            
            METHOD_MAP = {
                'm': 'market_maker', 'nr': 'non_retail', 's': 'smart_money',
                'r': 'retail', 'f': 'foreign', 'i': 'institution', 'z': 'zombie'
            }
            
            result = {
                'cumulative': {},
                'daily': {},
                'participation': {},
                'cross_index': None,
                'volume': None,
                'dates': [],
                'lastDate': None,
                'firstDate': None,
                'dataPoints': 0,
            }
            
            for trace in traces:
                name = trace.get('name', '')
                trace_type = trace.get('type', '')
                yaxis = trace.get('yaxis', '')
                mode = trace.get('mode', '')
                
                y_data = _extract_plotly_array(trace.get('y'))
                x_data = _extract_plotly_array(trace.get('x', []))
                
                if not y_data and trace_type != 'candlestick':
                    continue
                
                method = METHOD_MAP.get(name)
                
                # Cumulative lines (scatter, long time series)
                # Note: API response may have mode='' instead of mode='lines'
                if method and trace_type == 'scatter' and mode in ('lines', ''):
                    if yaxis in ('y', 'y2', '') and len(y_data) > 60:
                        result['cumulative'][method] = {
                            'latest': y_data[-1],
                            'prev': y_data[-2] if len(y_data) > 1 else 0,
                            'week_ago': y_data[-6] if len(y_data) > 5 else 0,
                            'month_ago': y_data[-23] if len(y_data) > 22 else y_data[0],
                            'start': y_data[0],
                            'dataPoints': len(y_data),
                        }
                        
                        if x_data and not result['lastDate']:
                            result['lastDate'] = x_data[-1]
                            result['firstDate'] = x_data[0]
                            result['dates'] = x_data
                            result['dataPoints'] = len(y_data)
                
                # Daily bars (bar, yaxis=y6)
                if method and trace_type == 'bar' and yaxis == 'y6':
                    result['daily'][method] = {
                        'latest': y_data[-1],
                        'prev': y_data[-2] if len(y_data) > 1 else 0,
                        'avg_5d': sum(y_data[-5:]) / min(5, len(y_data)) if y_data else 0,
                        'avg_20d': sum(y_data[-20:]) / min(20, len(y_data)) if y_data else 0,
                    }
                
                # Participation ratios (bar, yaxis=y10)
                if method and trace_type == 'bar' and yaxis == 'y10':
                    result['participation'][method] = {
                        'latest': y_data[-1],
                        'avg_5d': sum(y_data[-5:]) / min(5, len(y_data)) if y_data else 0,
                    }
                
                # Cross index (scatter, any mode)
                if name == 'cross_index' and trace_type == 'scatter':
                    result['cross_index'] = {
                        'latest': y_data[-1],
                        'prev': y_data[-2] if len(y_data) > 1 else 0,
                        'avg_5d': sum(y_data[-5:]) / min(5, len(y_data)) if y_data else 0,
                    }
                
                # Volume
                if name == 'volume' and trace_type == 'bar':
                    result['volume'] = {
                        'latest': y_data[-1],
                        'avg_20d': sum(y_data[-20:]) / min(20, len(y_data)) if y_data else 0,
                    }
            
            if result['cumulative'] or result['daily']:
                result['ticker'] = ticker
                result['period'] = period
                logger.info(f"API: Extracted txn chart for {ticker}: "
                           f"{len(result['cumulative'])} cumulative, "
                           f"{len(result['daily'])} daily methods")
                return result
            
            logger.warning(f"No transaction chart data for {ticker}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing transaction chart response for {ticker}: {e}")
            return None
    
    # ==================== BATCH DEEP ANALYSIS ====================
    
    async def get_bandarmology_deep_batch(self, tickers: list, period: str = '6m') -> list:
        """
        Batch inventory + transaction chart fetch via API.
        Same interface as NeoBDMScraper.get_bandarmology_deep_batch().
        """
        await self._ensure_client()
        
        if not self._logged_in:
            login_ok = await self.login()
            if not login_ok:
                return [{"error": "Login failed"}]
        
        results = []
        for i, ticker in enumerate(tickers):
            print(f"\n[API-DEEP] Processing {ticker} ({i+1}/{len(tickers)})...")
            result = {"ticker": ticker}
            
            # 1. Fetch Inventory
            try:
                inv_data = await self.get_inventory(ticker)
                result["inventory"] = inv_data
                if not inv_data:
                    result["inventory_error"] = "No data"
            except Exception as e:
                logger.warning(f"API inventory error for {ticker}: {e}")
                result["inventory"] = None
                result["inventory_error"] = str(e)
            
            await asyncio.sleep(0.5)
            
            # 2. Fetch Transaction Chart
            try:
                txn_data = await self.get_transaction_chart(ticker, period)
                result["transaction_chart"] = txn_data
                if not txn_data:
                    result["txn_error"] = "No data"
            except Exception as e:
                logger.warning(f"API txn chart error for {ticker}: {e}")
                result["transaction_chart"] = None
                result["txn_error"] = str(e)
            
            results.append(result)
            await asyncio.sleep(0.5)
        
        return results
    
    # ==================== UTILITIES ====================
    
    @staticmethod
    def _format_display_date(iso_date: str) -> str:
        """Convert 'YYYY-MM-DD' to 'DD MMM YYYY' (e.g. '06 Feb 2026')."""
        try:
            dt = datetime.strptime(iso_date.strip(), '%Y-%m-%d')
            return dt.strftime('%d %b %Y')
        except Exception:
            return iso_date
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._logged_in = False
        self._csrf_token = None
