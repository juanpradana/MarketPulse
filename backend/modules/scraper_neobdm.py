import os
import asyncio
import pandas as pd
import logging
from playwright.async_api import async_playwright
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

class NeoBDMScraper:
    def __init__(self):
        self.email = os.getenv("NEOBDM_EMAIL")
        self.password = os.getenv("NEOBDM_PASSWORD")
        self.base_url = "https://neobdm.tech"
        self.browser = None
        self.context = None
        self.page = None

    async def init_browser(self, headless=True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login(self):
        print(f"Attempting login for {self.email}...")
        await self.page.goto(f"{self.base_url}/accounts/login/")
        
        # Fill login form based on actual IDs found
        await self.page.fill('#id_login', self.email)
        await self.page.fill('#id_password', self.password)
        
        # Submit using the primary action button class
        await self.page.click('.primaryAction.btn.btn-primary')
        
        # Wait for navigation/dashboard indicator
        try:
            # Check if we are redirected to home
            await self.page.wait_for_url(f"{self.base_url}/home/", timeout=15000)
            print("Login successful!")
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            # Check for error messages
            error_msg = await self.page.query_selector('.alert-danger')
            if error_msg:
                print(f"Error detail: {await error_msg.inner_text()}")
            return False

    async def get_market_summary(self, method='m', period='d'):
        """
        Scrapes the Market Summary table.
        method: 'm' (Market Maker), 'nr' (Non-Retail), 'f' (Foreign Flow)
        period: 'd' (Daily), 'c' (Cumulative)
        """
        if not self.page:
            return None, None
            
        try:
            target_url = f"{self.base_url}/market_summary/"
            
            # CRITICAL FIX: Hard reload to clear ALL Dash state (especially after long daily scraping)
            print(f"   [SYNC] Performing hard refresh to clear state...", flush=True)
            await self.page.goto(target_url, wait_until='networkidle', timeout=60000)
            
            # Additional: Reload again to ensure no cached Dash callbacks
            await self.page.reload(wait_until='networkidle', timeout=60000)
            
            current_url = self.page.url
            current_title = await self.page.title()
            logger.debug(f"Navigation successful - URL: {current_url}, Title: {current_title}")

            # Wait for main controls (Chart might be slow, but controls should appear)
            await self.page.wait_for_selector('#summary-mode', state='visible', timeout=20000)
            
            # Clear any existing table state by scrolling to top
            await self.page.evaluate("window.scrollTo(0, 0);")
            await asyncio.sleep(2)
            
            # Trigger change events manually to ensure Dash sees the update
            await self.page.evaluate("""
                (args) => {
                    const methodSelect = document.querySelector('#method');
                    const periodSelect = document.querySelector('#summary-mode');
                    if (methodSelect) {
                        methodSelect.value = args.m;
                        methodSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    if (periodSelect) {
                        periodSelect.value = args.p;
                        periodSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """, {"m": method, "p": period})

            print(f"   [SYNC] Setting analysis parameters...", flush=True)
            # CRITICAL: Extended wait especially for cumulative after daily (Dash needs time to clear old pagination state)
            await asyncio.sleep(12) # Increased from 8 to 12 seconds for full Dash re-render

        except Exception as e:
            print(f"   [SYNC] Error refreshing/setting parameters: {e}")
            # We continue, hoping that the checkboxes/scraping might still work or it will fail later gracefully

        # --- Handle Checkboxes (Normalize OFF, Moving Average ON) ---
        try:
            # 1. Normalize -> Uncheck
            # Using value="normalize" if available, else label text
            norm_cb = self.page.locator('input[value="normalize"]')
            if await norm_cb.count() > 0:
                if await norm_cb.is_checked():
                    await norm_cb.uncheck()
                    print("Unchecked 'Normalize'")
            else:
                print("Warning: 'Normalize' checkbox not found by value.")

            # 2. Moving Average -> Check
            # Try value="ma" first, then label text
            ma_cb = self.page.locator('input[value="ma"]')
            if await ma_cb.count() == 0:
                 # Fallback to label text using robust xpath from debug_toggling
                 ma_label = self.page.locator('label', has_text="Moving Average")
                 if await ma_label.count() > 0:
                     ma_cb = ma_label.locator("xpath=preceding-sibling::input | descendant::input | ..//input").first
            
            if await ma_cb.count() > 0:
                if not await ma_cb.is_checked():
                    await ma_cb.check()
                    print("Checked 'Moving Average'")
            else:
                print("Warning: 'Moving Average' checkbox not found.")
                
            # 3. Compatible Only -> Check
            comp_cb = self.page.locator('input[value="compatible"]')
            if await comp_cb.count() > 0:
                if not await comp_cb.is_checked():
                    await comp_cb.check()
                    print("Checked 'Compatible Only'")
            else:
                # Fallback to label
                comp_label = self.page.locator('label', has_text="Compatible Only")
                if await comp_label.count() > 0:
                    comp_cb = comp_label.locator("xpath=preceding-sibling::input | descendant::input | ..//input").first
                    if await comp_cb.count() > 0 and not await comp_cb.is_checked():
                        await comp_cb.check()
                        print("Checked 'Compatible Only'")

            # Wait a bit for table update after checkboxes
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Error toggling checkboxes: {e}")

        # Wait for the Dash table to load or refresh
        # CRITICAL FIX: Wait for ALL loading indicators to complete
        print("  [LOADING] Waiting for Dash to complete rendering...")
        
        # 1. Wait for primary loading spinner (dash-spreadsheet)
        try:
            await self.page.wait_for_selector('.dash-spreadsheet-inner.dash-loading', timeout=2000)
            print("  [LOADING] Primary spinner detected, waiting for it to hide...")
            await self.page.wait_for_selector('.dash-spreadsheet-inner.dash-loading', state='hidden', timeout=30000)
        except:
            pass
        
        # 2. Wait for global Dash loading overlay (sometimes appears for heavy calculations)
        try:
            await self.page.wait_for_selector('._dash-loading-callback', timeout=2000)
            print("  [LOADING] Global Dash callback spinner detected, waiting...")
            await self.page.wait_for_selector('._dash-loading-callback', state='hidden', timeout=30000)
        except:
            pass
        
        # 3. Additional hard wait to let pagination info update (CRITICAL for cumulative)
        print("  [LOADING] Waiting additional time for pagination to update...")
        await asyncio.sleep(8)  # Give Dash extra time to update pagination counter

        # 4. Wait for the table row content to be present and STABLE
        # Issue: Dash might show old rows for a split second before clearing/updating.
        # Fix: Wait for at least 10 rows if we expect data, or wait for stability
        print("  Waiting for table rows...")
        try:
            # Basic wait for any cell
            await self.page.wait_for_selector('.dash-cell', timeout=20000)
            
            # Additional wait to ensure it's not the old table or empty skeleton
            # We poll the row count until it stabilizes or > 5
            for _ in range(10): # Try for 5 seconds
                row_count = await self.page.locator('.dash-spreadsheet-container tr').count()
                if row_count > 5:
                    break
                await asyncio.sleep(0.5)
            
            # One final hard wait to let Dash render everything
            await asyncio.sleep(2)
            
        except Exception as e:
             print(f"  Warning: waiting for rows timed out: {e}")

        # Extract Reference Date from title (e.g., "Market Maker Analysis Summary [2024-12-19]")
        reference_date = None
        try:
            title_text = await self.page.inner_text('label.mb-0.form-label')
            if '[' in title_text and ']' in title_text:
                reference_date = title_text.split('[')[1].split(']')[0]
                print(f"   [DATA] Extracted Reference Date: {reference_date}")
        except Exception as e:
            print(f"   [DATA] Failed to extract reference date: {e}")

        # Extraction logic for Plotly Dash Table via JS
        all_data = []
        current_page = 1
        total_pages = 1

        # Detect total pages with retry loop - wait for container to be VISIBLE, not just present
        # CRITICAL: After Daily scraping, Cumulative needs MORE time for Dash to reset pagination
        for attempt in range(15):  # Increased from 10 to 15 attempts (up to 75 seconds total)
            try:
                # Wait for pagination container to be VISIBLE (not just present)
                await self.page.wait_for_selector('.previous-next-container', state='visible', timeout=10000)
                
                # Additional check: Ensure the pagination is NOT from the old/previous data
                # by waiting for any loading indicators to finish
                try:
                    await self.page.wait_for_selector('.dash-loading', state='hidden', timeout=2000)
                except:
                    pass  # No loading indicator found, which is fine
                
                total_pages_text = await self.page.inner_text('.page-number .last-page')
                clean_text = total_pages_text.strip().split('/')[-1].strip()
                
                if clean_text and clean_text.isdigit():
                    total_pages = int(clean_text)
                    if total_pages > 0:
                        print(f"   [PAGINATION] Total pages detected: {total_pages} (Attempt {attempt+1})", flush=True)
                        
                        # Additional verification: Check if next button state matches expected pages
                        next_btn = self.page.locator('button.next-page')
                        is_next_enabled = await next_btn.is_enabled() if await next_btn.count() > 0 else False
                        
                        # If total_pages > 1, next button SHOULD be enabled
                        if total_pages > 1 and not is_next_enabled:
                            print(f"   [PAGINATION] WARNING: {total_pages} pages detected but next button disabled. Retrying...", flush=True)
                            await asyncio.sleep(5)
                            continue
                        
                        # Pagination looks good, proceed
                        break
                        
                print(f"   [PAGINATION] Waiting for total pages text... (Attempt {attempt+1})", flush=True)
                await asyncio.sleep(5)  # Increased from 3 to 5 seconds
            except Exception as e:
                # Don't print full error every time, just on last attempt
                if attempt >= 7:
                    print(f"   [PAGINATION] Detection attempt {attempt+1} failed: {e}", flush=True)
                await asyncio.sleep(3)
        else:
            print(f"   [PAGINATION] Could not detect total pages after retries, defaulting to 1", flush=True)

        while current_page <= total_pages:
            print(f"Scraping page {current_page} of {total_pages}...")
            
            # Extract current page data
            page_data = await self.page.evaluate(r"""
                () => {
                    const headers = Array.from(document.querySelectorAll('.dash-header span'))
                        .map(s => s.innerText.trim())
                        .filter(s => s.length > 0);
                        
                    const allTrs = Array.from(document.querySelectorAll('tr')).filter(tr => tr.querySelector('.dash-cell'));
                    
                    const cleanText = (str) => {
                        if (!str) return '';
                        let clean = str.replace(/\|?Add\s+.*?to\s+Watchlist/gi, '').trim();
                        clean = clean.replace(/\|?Remove\s+from\s+Watchlist/gi, '').trim();
                        // Remove leading/trailing pipe symbols
                        clean = clean.replace(/^\|+|\|+$/g, '').trim();
                        return clean;
                    };

                    return allTrs.map(tr => {
                        const allCells = Array.from(tr.querySelectorAll('td, th'));
                        const cells = allCells.slice(-headers.length);
                        
                        let rowData = {};
                        headers.forEach((header, index) => {
                            if (cells[index]) {
                                let rawText = cells[index].textContent.trim();
                                let text = cleanText(rawText);
                                
                                // Enhanced Extraction: Check for title/tooltip
                                // This solves "Value Extraction" by grabbing hidden details in hover states
                                let rawTooltip = cells[index].getAttribute('title');
                                if (!rawTooltip) {
                                    const child = cells[index].querySelector('[title]');
                                    if (child) rawTooltip = child.getAttribute('title');
                                }
                                
                                let tooltip = cleanText(rawTooltip);
                                
                                // Check for SVG/Icon titles (common in Dash conditional formatting)
                                if (!tooltip && (text === '' || text.toLowerCase() === 'v')) {
                                     // Try to find aria-label or other indicators if simple text hidden
                                     const icon = cells[index].querySelector('svg, i');
                                     if (icon) tooltip = "Marker Present"; 
                                }

                                if (tooltip && tooltip !== text) {
                                    // Append tooltip info. stored as "Value|Tooltip"
                                    if (text) text = `${text}|${tooltip}`;
                                    else text = tooltip;
                                }
                                
                                rowData[header] = text;
                            }
                        });
                        return rowData;
                    });
                }
            """)
            
            if page_data:
                all_data.extend(page_data)
                print(f"  Extracted {len(page_data)} rows from page {current_page}.")
            else:
                print(f"  Warning: No data found on page {current_page}.")

            if current_page < total_pages:
                try:
                    # Capture signature of first row to detect change
                    first_row_signature = str(page_data[0]) if page_data else None
                    
                    # Click Next
                    next_btn = self.page.locator('button.next-page')
                    
                    # Retry logic: Wait for button to be enabled (sometimes it lags)
                    btn_enabled = False
                    for _ in range(10): # Wait up to 10s
                        if await next_btn.is_enabled():
                            btn_enabled = True
                            break
                        await asyncio.sleep(1)
                        
                    if btn_enabled:
                        await next_btn.click()
                        
                        # Wait for either spinner OR content change
                        # Wait for up to 5 seconds for change
                        for _ in range(10):
                            await asyncio.sleep(0.5)
                            new_page_data = await self.page.evaluate("""
                                () => {
                                    const firstCell = document.querySelector('.dash-cell');
                                    return firstCell ? firstCell.textContent.trim() : null;
                                }
                            """)
                            # If we had data and now first cell text is different, we definitely moved pages
                            # (Simplification: just checking if table refreshed)
                            if page_data and new_page_data != page_data[0].get(list(page_data[0].keys())[0]):
                                break
                        
                        current_page += 1
                    else:
                        print(f"  Next button disabled. Assuming end of filtered data (Footer mismatch). Stopping.")
                        break
                except Exception as e:
                    print(f"  Error navigating to next page: {e}")
                    break
            else:
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            # Remove duplicates if any (Dash sometimes overlaps during transitions)
            df = df.drop_duplicates().reset_index(drop=True)
            print(f"Successfully extracted total {len(df)} unique rows.")
            return df, reference_date
        else:
            print("No data found across any pages.")
            return None, reference_date

    async def _get_data_fingerprint(self):
        """
        Extract a fingerprint of current broker summary data.
        Returns list of first 3 broker codes from buy side.
        """
        try:
            fingerprint = await self.page.evaluate("""
                () => {
                    const table = document.querySelector('#broker-summary-table');
                    if (!table) return [];
                    const rows = table.querySelectorAll('tbody tr');
                    const brokers = [];
                    for (let i = 0; i < Math.min(3, rows.length); i++) {
                        const span = rows[i].querySelector('.broksum-broker');
                        if (span) brokers.push(span.textContent.trim());
                    }
                    return brokers;
                }
            """)
            return fingerprint if fingerprint else []
        except Exception:
            return []

    async def _select_ticker_robust(self, ticker: str, retry_count: int = 3) -> bool:
        """
        Robustly select ticker from Selectize.js dropdown with retry logic.
        Site uses Selectize.js (not React-Select).
        """
        if not self.page:
            return False
        
        for attempt in range(retry_count):
            try:
                print(f"   [TICKER] Selecting {ticker} (attempt {attempt+1})...")
                
                # Method 1: Selectize.js API via JavaScript (most reliable)
                try:
                    success = await self.page.evaluate("""
                        (ticker) => {
                            const selectEl = document.querySelector('#input-broksum-ticker');
                            if (selectEl && selectEl.selectize) {
                                selectEl.selectize.setValue(ticker, false);
                                return selectEl.selectize.getValue() === ticker;
                            }
                            return false;
                        }
                    """, ticker)
                    
                    if success:
                        print(f"   [TICKER] Successfully selected {ticker} via Selectize API")
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    print(f"   [TICKER] Selectize API method failed: {e}")
                
                # Method 2: Click input, type, select from dropdown
                try:
                    print(f"   [TICKER] Trying input click method...")
                    input_selector = '#input-broksum-ticker-selectized'
                    await self.page.wait_for_selector(input_selector, state='visible', timeout=10000)
                    
                    # Clear existing value first
                    await self.page.evaluate("""
                        () => {
                            const selectEl = document.querySelector('#input-broksum-ticker');
                            if (selectEl && selectEl.selectize) {
                                selectEl.selectize.clear(true);
                            }
                        }
                    """)
                    await asyncio.sleep(0.5)
                    
                    # Click and type
                    await self.page.click(input_selector)
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.type(ticker, delay=100)
                    await asyncio.sleep(2)
                    
                    # Click the matching option
                    option_selector = f'.selectize-dropdown-content .option[data-value="{ticker}"]'
                    try:
                        await self.page.wait_for_selector(option_selector, state='visible', timeout=5000)
                        await self.page.click(option_selector)
                        print(f"   [TICKER] Successfully selected {ticker} from dropdown")
                        await asyncio.sleep(1)
                        return True
                    except Exception:
                        # Try pressing Enter as fallback
                        await self.page.keyboard.press('Enter')
                        await asyncio.sleep(1)
                        print(f"   [TICKER] Used Enter key to confirm selection")
                        return True
                        
                except Exception as e:
                    print(f"   [TICKER] Input click method failed: {e}")
                    
            except Exception as e:
                print(f"   [TICKER] Attempt {attempt+1} failed completely: {e}")
                
            # Wait before retry
            if attempt < retry_count - 1:
                await asyncio.sleep(2)
        
        print(f"   [TICKER] Failed to select {ticker} after {retry_count} attempts")
        return False

    async def _get_broker_summary_date_value(self):
        """Get current start date value from the broker summary page.
        New site uses #broksum-start-date with format 'DD MMM YYYY'."""
        if not self.page:
            return None
        try:
            raw_date = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('#broksum-start-date');
                    return el ? el.value : null;
                }
            """)
            if not raw_date:
                return None
            # Convert 'DD MMM YYYY' to 'YYYY-MM-DD'
            return self._parse_display_date(raw_date)
        except Exception:
            return None

    @staticmethod
    def _parse_display_date(display_date: str) -> str:
        """Convert 'DD MMM YYYY' (e.g. '06 Feb 2026') to 'YYYY-MM-DD'."""
        from datetime import datetime
        try:
            dt = datetime.strptime(display_date.strip(), '%d %b %Y')
            return dt.strftime('%Y-%m-%d')
        except Exception:
            return display_date

    @staticmethod
    def _format_display_date(iso_date: str) -> str:
        """Convert 'YYYY-MM-DD' to 'DD MMM YYYY' (e.g. '06 Feb 2026')."""
        from datetime import datetime
        try:
            dt = datetime.strptime(iso_date.strip(), '%Y-%m-%d')
            return dt.strftime('%d %b %Y')
        except Exception:
            return iso_date

    async def _navigate_to_date_via_arrows(self, target_date: str, max_clicks: int = 30) -> bool:
        """
        Navigate to target date using arrow buttons with JavaScript fallback.
        New site uses #broksum-button-back / #broksum-button-forward.
        Returns True if successfully navigated to target date.
        """
        if not self.page:
            return False
        
        from datetime import datetime, timedelta
        
        try:
            # Get current date from field
            current_date_str = await self._get_broker_summary_date_value()
            if not current_date_str:
                print(f"   [DATE] Cannot get current date value, using JS fallback...")
                return await self._set_date_via_javascript(target_date)
            
            print(f"   [DATE] Current date: {current_date_str}, Target: {target_date}")
            
            # Parse dates
            try:
                current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
                target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
            except Exception as e:
                print(f"   [DATE] Date parsing error: {e}, using JS fallback...")
                return await self._set_date_via_javascript(target_date)
            
            # Calculate difference
            diff_days = (target_date_obj - current_date).days
            print(f"   [DATE] Need to move {diff_days} days")
            
            if diff_days == 0:
                print(f"   [DATE] Already at target date")
                return True
            
            # If difference is too large (>5 days), use JS directly
            if abs(diff_days) > 5:
                print(f"   [DATE] Large date difference ({diff_days} days), using direct JS method...")
                return await self._set_date_via_javascript(target_date)
            
            # Try arrow method for small differences
            print(f"   [DATE] Attempting arrow navigation for {abs(diff_days)} days...")
            
            # Determine direction and button (new IDs)
            if diff_days > 0:
                arrow_selector = '#broksum-button-forward'
                direction = "forward"
            else:
                arrow_selector = '#broksum-button-back'
                direction = "backward"
                diff_days = abs(diff_days)
            
            # Attempt arrow navigation (quick attempt, 3 clicks max)
            last_seen_date = current_date_str
            
            for i in range(min(diff_days, 3)):
                try:
                    arrow_button = self.page.locator(arrow_selector).first
                    if await arrow_button.count() > 0:
                        await arrow_button.click(force=True)
                        await asyncio.sleep(1.0)
                        
                        new_date = await self._get_broker_summary_date_value()
                        print(f"   [DATE] After click {i+1}, date is: {new_date}")
                        
                        if new_date == target_date:
                            print(f"   [DATE] Successfully reached target via arrows")
                            await asyncio.sleep(1.5)
                            return True
                        
                        if new_date == last_seen_date:
                            print(f"   [DATE] Arrow method not working, switching to JS fallback...")
                            break
                        
                        last_seen_date = new_date
                    else:
                        break
                except Exception as e:
                    print(f"   [DATE] Arrow click error: {e}")
                    break
            
            # Fallback to JavaScript method
            print(f"   [DATE] Arrow method failed or incomplete, using JS fallback...")
            return await self._set_date_via_javascript(target_date)
                
        except Exception as e:
            print(f"   [DATE] Navigation failed: {e}, trying JS fallback...")
            return await self._set_date_via_javascript(target_date)

    async def _set_date_via_javascript(self, target_date: str) -> bool:
        """
        Directly set date value using JavaScript.
        New site uses #broksum-start-date and #broksum-end-date with 'DD MMM YYYY' format.
        """
        if not self.page:
            return False
        
        try:
            display_date = self._format_display_date(target_date)
            print(f"   [JS] Setting date to {target_date} (display: {display_date}) via JavaScript...")
            
            # Set both start and end date inputs to the same value
            await self.page.evaluate("""
                (displayDate) => {
                    const startInput = document.querySelector('#broksum-start-date');
                    const endInput = document.querySelector('#broksum-end-date');
                    
                    if (startInput) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeSetter.call(startInput, displayDate);
                        startInput.dispatchEvent(new Event('input', { bubbles: true }));
                        startInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                    if (endInput) {
                        const nativeSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        nativeSetter.call(endInput, displayDate);
                        endInput.dispatchEvent(new Event('input', { bubbles: true }));
                        endInput.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """, display_date)
            
            await asyncio.sleep(1)
            
            # Verify the date was set correctly
            final_date = await self._get_broker_summary_date_value()
            print(f"   [JS] Verification - date is now: {final_date}")
            
            if final_date == target_date:
                print(f"   [JS] Successfully set date to {target_date}")
                return True
            else:
                # Fallback: use Playwright fill method
                print(f"   [JS] Mismatch. Trying Playwright fill method...")
                try:
                    await self.page.fill('#broksum-start-date', display_date)
                    await self.page.fill('#broksum-end-date', display_date)
                    await asyncio.sleep(1)
                    
                    verify_date = await self._get_broker_summary_date_value()
                    if verify_date == target_date:
                        print(f"   [JS] Successfully set date on second attempt")
                        return True
                except Exception:
                    pass
                
                print(f"   [JS] Failed to set date. Current: {final_date}, Expected: {target_date}")
                return False
                
        except Exception as e:
            print(f"   [JS] JavaScript date setting failed: {e}")
            return False

    async def _wait_for_broker_summary_render(self):
        """Wait for broker summary table to finish rendering after loading data."""
        if not self.page:
            return
        # New site uses standard HTML table, wait for it to appear
        try:
            await self.page.wait_for_selector('#broker-summary-table tbody tr', timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(1.5)

    async def get_broker_summary(self, ticker: str, date_str: str):
        """
        Scrapes the Broker Summary table for a specific ticker and date.
        date_str: 'YYYY-MM-DD'
        
        New site (2026+) uses:
        - Selectize.js for ticker dropdown
        - #broksum-start-date / #broksum-end-date (format 'DD MMM YYYY')
        - #broksum-button-load to trigger data fetch
        - #broker-summary-table (standard HTML table, not Dash)
        """
        if not self.page:
            return None

        try:
            target_url = f"{self.base_url}/broker_summary/"
            
            # Navigate if NOT already on the page
            current = self.page.url.rstrip('/')
            target = target_url.rstrip('/')
            if current != target:
                print(f"   [SYNC] Navigating to {target_url}...", flush=True)
                await self.page.goto(target_url, wait_until='networkidle', timeout=60000)
                # Wait for Selectize.js ticker input to be ready
                await self.page.wait_for_selector('#input-broksum-ticker-selectized', state='visible', timeout=20000)
            else:
                print(f"   [SYNC] Already on {target_url}, skipping navigation.", flush=True)

            # 1. Select Ticker
            if not await self._select_ticker_robust(ticker):
                print(f"   [ERROR] Failed to select ticker {ticker}")
                return None

            # 2. Set Date
            print(f"   [SYNC] Setting date to {date_str}...", flush=True)
            if not await self._set_date_via_javascript(date_str):
                # Try arrow navigation as fallback
                if not await self._navigate_to_date_via_arrows(date_str):
                    actual_date = await self._get_broker_summary_date_value()
                    print(f"   [WARNING] Failed to set date {date_str}. Currently at: {actual_date}")
                    return None

            # 3. Click Load button to fetch data
            print(f"   [SYNC] Clicking Load button...", flush=True)
            try:
                load_btn = self.page.locator('#broksum-button-load')
                await load_btn.click()
            except Exception as e:
                print(f"   [WARNING] Could not click Load button: {e}")

            # 4. Wait for table to render
            await self._wait_for_broker_summary_render()
            
            # Extra wait for data to fully load
            await asyncio.sleep(2)

            # 5. Check if data is available (site shows "Data tidak tersedia" when no data)
            no_data = await self.page.evaluate("""
                () => {
                    const container = document.querySelector('#broksum-table-container');
                    if (!container) return true;
                    const text = container.innerText.trim();
                    return text.includes('Data tidak tersedia') || text.includes('tidak tersedia');
                }
            """)
            
            if no_data:
                print(f"   [DATA] No data available for {ticker} on {date_str}")
                return None

            # 6. Extract Data from standard HTML table
            print("   [DATA] Extracting rows from #broker-summary-table...")
            data = await self.page.evaluate(r"""
                () => {
                    const table = document.querySelector('#broker-summary-table');
                    if (!table) return null;
                    
                    const rows = table.querySelectorAll('tbody tr');
                    if (rows.length === 0) return null;
                    
                    const buyData = [];
                    const sellData = [];
                    
                    rows.forEach(tr => {
                        const cells = tr.querySelectorAll('td');
                        if (cells.length < 8) return;
                        
                        // Table structure: BY | nlot | nval | bavg | SL | nlot | nval | savg
                        // Buy side (columns 0-3)
                        const buyBrokerSpan = cells[0].querySelector('.broksum-broker');
                        const buyBroker = buyBrokerSpan ? buyBrokerSpan.textContent.trim() : cells[0].textContent.trim();
                        if (buyBroker) {
                            buyData.push({
                                broker: buyBroker,
                                nlot: cells[1].textContent.trim(),
                                nval: cells[2].textContent.trim(),
                                bavg: cells[3].textContent.trim()
                            });
                        }
                        
                        // Sell side (columns 4-7)
                        const sellBrokerSpan = cells[4].querySelector('.broksum-broker');
                        const sellBroker = sellBrokerSpan ? sellBrokerSpan.textContent.trim() : cells[4].textContent.trim();
                        if (sellBroker) {
                            sellData.push({
                                broker: sellBroker,
                                nlot: cells[5].textContent.trim(),
                                nval: cells[6].textContent.trim(),
                                savg: cells[7].textContent.trim()
                            });
                        }
                    });
                    
                    return {
                        buy: buyData,
                        sell: sellData
                    };
                }
            """)

            if not data or (not data.get('buy') and not data.get('sell')):
                print(f"   [DATA] No broker summary data found for {ticker} on {date_str}")
                return None

            print(f"   [DATA] Extracted {len(data['buy'])} buy rows and {len(data['sell'])} sell rows.")
            return data

        except Exception as e:
            print(f"   [ERROR] Failed to scrape broker summary: {e}")
            return None

    async def get_broker_summary_batch(self, tasks: list):
        """
        Execute multiple broker summary scrapes in a single session.
        tasks format: [{"ticker": "ANTM", "dates": ["2026-01-12", "2026-01-11"]}, ...]
        """
        if not self.page:
            return []

        results = []
        try:
            # Login once
            login_success = await self.login()
            if not login_success:
                return [{"error": "Login failed"}]

            # Navigate once with retry logic
            target_url = f"{self.base_url}/broker_summary/"
            print(f"[*] Navigating to {target_url}...")
            await self.page.goto(target_url, wait_until='networkidle', timeout=60000)
            
            # Wait for page to be ready with retry logic (Selectize.js)
            selector_found = False
            for attempt in range(3):
                try:
                    print(f"[*] Waiting for Selectize ticker input (attempt {attempt+1}/3)...")
                    await self.page.wait_for_selector('#input-broksum-ticker-selectized', state='visible', timeout=20000)
                    selector_found = True
                    print(f"[*] Selectize input found, page is ready")
                    break
                except Exception as e:
                    print(f"[!] Attempt {attempt+1} failed: {e}")
                    if attempt < 2:
                        print(f"[*] Reloading page and retrying...")
                        await self.page.reload(wait_until='networkidle', timeout=30000)
                        await asyncio.sleep(3)
                    else:
                        print(f"[!] Failed to find Selectize input after 3 attempts")
                        return [{"error": "Page failed to load properly - Selectize input not found"}]

            if not selector_found:
                return [{"error": "Page not ready for scraping"}]
            
            for task in tasks:
                ticker = task.get('ticker')
                dates = task.get('dates', [])
                
                for date_str in dates:
                    print(f"[*] Batch Sync: Processing {ticker} for {date_str}...")
                    try:
                        data = await self.get_broker_summary(ticker, date_str)
                    except Exception as e:
                        print(f"[!] Error scraping {ticker} on {date_str}: {e}")
                        data = None
                    
                    if data:
                        results.append({
                            "ticker": ticker,
                            "trade_date": date_str,
                            "buy": data.get('buy', []),
                            "sell": data.get('sell', [])
                        })
                    else:
                        print(f"[!] Batch Sync: No data found for {ticker} on {date_str}")
                        results.append({
                            "ticker": ticker,
                            "trade_date": date_str,
                            "error": "No data found or date mismatch"
                        })
                    
                    # Small cooldown between requests
                    await asyncio.sleep(2)

            return results

        except Exception as e:
            print(f"[!] Critical error in Batch Sync: {e}")
            return results

    # ==================== BANDARMOLOGY: INVENTORY ====================

    async def _select_ticker_react_select(self, ticker: str, container_selector: str = None) -> bool:
        """
        Select ticker from React-Select dropdown (used by inventory & transaction_chart pages).
        Uses JS-based approach for reliability across repeated page loads.
        
        Args:
            container_selector: CSS selector to scope which React-Select to target.
                               e.g. '#ticker-container' or None for first found.
        """
        if not self.page:
            return False
        
        try:
            # Wait for React-Select to be present in DOM
            for _ in range(10):
                ready = await self.page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('.Select-input input, .Select input[role="combobox"]');
                        return inputs.length > 0;
                    }
                """)
                if ready:
                    break
                await asyncio.sleep(1)
            
            # Strategy 1: Use JS to simulate React-Select interaction
            # This is more reliable than clicking DOM elements
            selected = await self.page.evaluate("""
                (ticker) => {
                    // Find the FIRST .Select-control (ticker select, not broker)
                    const controls = document.querySelectorAll('.Select-control');
                    if (controls.length === 0) return 'no_controls';
                    
                    // Click to open
                    controls[0].click();
                    return 'opened';
                }
            """, ticker)
            
            if selected == 'no_controls':
                print(f"   [TICKER] No .Select-control found on page")
                return False
            
            await asyncio.sleep(0.5)
            
            # Type into the input that should now be focused/visible
            input_el = self.page.locator('.Select-input input').first
            if await input_el.count() > 0:
                await input_el.fill('')
                await asyncio.sleep(0.3)
                await input_el.type(ticker, delay=50)
                await asyncio.sleep(2)
                
                # Try clicking the matching option
                option = self.page.locator('.Select-menu .Select-option, .VirtualizedSelectOption').filter(has_text=ticker).first
                if await option.count() > 0:
                    await option.click()
                    await asyncio.sleep(1)
                    print(f"   [TICKER] Selected {ticker} via React-Select option click")
                    return True
                
                # Fallback: try grid-based dropdown
                grid_option = self.page.locator('[role="grid"] [role="row"]').filter(has_text=ticker).first
                if await grid_option.count() > 0:
                    await grid_option.click()
                    await asyncio.sleep(1)
                    print(f"   [TICKER] Selected {ticker} via grid dropdown")
                    return True
                    
                # Fallback: press Enter to select first match
                await input_el.press('Enter')
                await asyncio.sleep(1)
                print(f"   [TICKER] Selected {ticker} via Enter key")
                return True
            
            # Strategy 2: Try clicking placeholder directly then typing
            placeholder = self.page.locator('.Select-placeholder').first
            if await placeholder.count() > 0:
                await placeholder.click()
                await asyncio.sleep(0.5)
                # After clicking placeholder, the input should appear
                input_el2 = self.page.locator('.Select-input input').first
                if await input_el2.count() > 0:
                    await input_el2.type(ticker, delay=50)
                    await asyncio.sleep(2)
                    await input_el2.press('Enter')
                    await asyncio.sleep(1)
                    print(f"   [TICKER] Selected {ticker} via placeholder+Enter")
                    return True
            
            print(f"   [TICKER] React-Select input not found after all strategies")
            return False
            
        except Exception as e:
            print(f"   [TICKER] React-Select selection failed: {e}")
            return False

    async def get_inventory(self, ticker: str, period_months: int = 3) -> dict:
        """
        Scrape inventory chart data for a specific ticker.
        Returns broker accumulation/distribution data from Plotly chart.
        """
        if not self.page:
            return None
        
        try:
            target_url = f"{self.base_url}/inventory/"
            
            # Always navigate fresh to avoid stale DOM issues
            print(f"   [INV] Navigating to {target_url}...")
            await self.page.goto(target_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # CRITICAL: Uncheck "hide tektok" and "hide netdist" to show ALL brokers
            try:
                hide_tektok = self.page.locator('input[type="checkbox"]').nth(0)
                hide_netdist = self.page.locator('input[type="checkbox"]').nth(1)
                
                # Check if "hide tektok" is checked and uncheck it
                is_tektok_checked = await hide_tektok.is_checked()
                if is_tektok_checked:
                    await hide_tektok.click()
                    await asyncio.sleep(0.3)
                    print(f"   [INV] Unchecked 'hide tektok'")
                
                # Check if "hide netdist" is checked and uncheck it
                is_netdist_checked = await hide_netdist.is_checked()
                if is_netdist_checked:
                    await hide_netdist.click()
                    await asyncio.sleep(0.3)
                    print(f"   [INV] Unchecked 'hide netdist'")
            except Exception as e:
                print(f"   [INV] Warning: Could not uncheck hide checkboxes: {e}")
            
            # Select ticker
            if not await self._select_ticker_react_select(ticker):
                print(f"   [INV] Failed to select ticker {ticker}")
                return None
            
            # Click Fetch button
            fetch_btn = self.page.locator('button:has-text("Fetch")')
            if await fetch_btn.count() > 0:
                await fetch_btn.click()
                print(f"   [INV] Clicked Fetch for {ticker}")
            else:
                print(f"   [INV] Fetch button not found")
                return None
            
            # Wait for chart to load (inventory charts can be slow)
            await asyncio.sleep(8)
            
            # Wait for Plotly chart to have broker data (more than just price+volume)
            chart_info = None
            for attempt in range(15):
                chart_info = await self.page.evaluate("""
                    () => {
                        const p = document.querySelector('.js-plotly-plot');
                        if (!p || !p._fullData) return { found: false, traces: 0 };
                        return { found: true, traces: p._fullData.length };
                    }
                """)
                if chart_info.get('found') and chart_info.get('traces', 0) > 2:
                    break
                await asyncio.sleep(1)
            
            trace_count = chart_info.get('traces', 0) if chart_info else 0
            print(f"   [INV] Chart has {trace_count} traces for {ticker}")
            
            if trace_count <= 2:
                print(f"   [INV] Only price/volume traces found, no broker data for {ticker}")
                return None
            
            # Extract inventory data from Plotly
            # NOTE: Plotly _fullData uses typed arrays (Float64Array) for y values,
            # so Array.isArray() returns false. We use t.y && t.y.length instead.
            data = await self.page.evaluate(r"""
                () => {
                    const p = document.querySelector('.js-plotly-plot');
                    if (!p || !p._fullData) return null;
                    const fd = p._fullData;
                    
                    const result = { brokers: [], lastDate: null, firstDate: null, traceCount: fd.length };
                    
                    for (let i = 0; i < fd.length; i++) {
                        const t = fd[i];
                        const name = t.name || '';
                        
                        // Skip price, volume, and marker traces
                        if (t.type === 'candlestick' || name === 'volume' || name === 'price') continue;
                        if (t.mode === 'markers+text') continue;
                        if (t.type !== 'scatter') continue;
                        
                        // Plotly uses typed arrays (Float64Array), not regular Arrays
                        const yLen = (t.y && t.y.length) ? t.y.length : 0;
                        const xLen = (t.x && t.x.length) ? t.x.length : 0;
                        if (yLen === 0) continue;
                        
                        // Convert typed arrays to regular arrays
                        const dates = Array.from(t.x || []);
                        const values = Array.from(t.y);
                        
                        const code = name.replace(/[\u2713\u2717]/g, '').trim();
                        if (!code) continue;
                        
                        const lastVal = values[values.length - 1];
                        const firstVal = values[0];
                        
                        result.brokers.push({
                            code: code,
                            isClean: name.indexOf('\u2713') !== -1,
                            isTektok: name.indexOf('\u2717') !== -1,
                            finalNetLot: lastVal,
                            startNetLot: firstVal,
                            isAccumulating: lastVal > 0,
                            dataPoints: yLen,
                            timeSeries: values.map(function(v, idx) {
                                return { date: dates[idx] || null, cumNetLot: v };
                            })
                        });
                        
                        if (dates.length > 0) {
                            result.lastDate = dates[dates.length - 1];
                            result.firstDate = dates[0];
                        }
                    }
                    
                    return result;
                }
            """)
            
            if data and data.get('brokers') and len(data['brokers']) > 0:
                print(f"   [INV] Extracted {len(data['brokers'])} broker traces for {ticker}")
                data['ticker'] = ticker
                return data
            else:
                print(f"   [INV] No broker data extracted for {ticker} (traces={trace_count})")
                return None
                
        except Exception as e:
            print(f"   [INV] Error scraping inventory for {ticker}: {e}")
            return None

    # ==================== BANDARMOLOGY: TRANSACTION CHART ====================

    async def get_transaction_chart(self, ticker: str, period: str = '6m') -> dict:
        """
        Scrape transaction chart data for a specific ticker.
        Returns flow data for all methods (MM, NR, Smart, Retail, Foreign, Institution, Zombie).
        
        Args:
            ticker: Stock ticker symbol
            period: Time period ('3m', '6m', '9m')
        
        Returns:
            Dict with cumulative flows, daily flows, participation ratios, cross_index
        """
        if not self.page:
            return None
        
        try:
            target_url = f"{self.base_url}/transaction_chart/"
            
            # Always navigate fresh to avoid stale DOM issues
            print(f"   [TXN] Navigating to {target_url}...")
            await self.page.goto(target_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # Select period radio button
            try:
                period_label = self.page.locator(f'label:has-text("{period}"), div:has-text("{period}")').first
                if await period_label.count() > 0:
                    await period_label.click()
                    await asyncio.sleep(0.5)
            except:
                pass
            
            # Select ticker
            if not await self._select_ticker_react_select(ticker):
                print(f"   [TXN] Failed to select ticker {ticker}")
                return None
            
            # Wait for chart to load
            await asyncio.sleep(5)
            
            # Wait for Plotly chart data
            for attempt in range(10):
                has_data = await self.page.evaluate("""
                    () => {
                        const p = document.querySelector('.js-plotly-plot');
                        return p && p._fullData && p._fullData.length > 5;
                    }
                """)
                if has_data:
                    break
                await asyncio.sleep(1)
            
            # Extract transaction chart data
            data = await self.page.evaluate(r"""
                () => {
                    const p = document.querySelector('.js-plotly-plot');
                    if (!p || !p._fullData) return null;
                    const fd = p._fullData;
                    
                    // Map trace names to their meaning
                    const METHOD_MAP = {
                        'm': 'market_maker', 'nr': 'non_retail', 's': 'smart_money',
                        'r': 'retail', 'f': 'foreign', 'i': 'institution', 'z': 'zombie'
                    };
                    
                    const result = {
                        cumulative: {},
                        daily: {},
                        participation: {},
                        cross_index: null,
                        volume: null,
                        dates: [],
                        lastDate: null,
                        firstDate: null,
                        dataPoints: 0
                    };
                    
                    for (let i = 0; i < fd.length; i++) {
                        const t = fd[i];
                        const name = t.name || '';
                        const yLen = t.y ? t.y.length : 0;
                        if (yLen === 0 && t.type !== 'candlestick') continue;
                        
                        const method = METHOD_MAP[name];
                        
                        // Cumulative lines (scatter, yaxis=y, long time series)
                        if (method && t.type === 'scatter' && t.mode === 'lines' && (t.yaxis === 'y' || t.yaxis === 'y2' || !t.yaxis)) {
                            if (yLen > 60) {
                                const values = [];
                                for (let j = 0; j < yLen; j++) values.push(t.y[j]);
                                const dates = [];
                                for (let j = 0; j < t.x.length; j++) dates.push(t.x[j]);
                                
                                result.cumulative[method] = {
                                    latest: values[values.length - 1],
                                    prev: values.length > 1 ? values[values.length - 2] : 0,
                                    week_ago: values.length > 5 ? values[values.length - 6] : 0,
                                    month_ago: values.length > 22 ? values[values.length - 23] : values[0],
                                    start: values[0],
                                    dataPoints: yLen
                                };
                                
                                if (dates.length > 0 && !result.lastDate) {
                                    result.lastDate = dates[dates.length - 1];
                                    result.firstDate = dates[0];
                                    result.dates = dates;
                                    result.dataPoints = yLen;
                                }
                            }
                        }
                        
                        // Daily bars (bar, yaxis=y6)
                        if (method && t.type === 'bar' && t.yaxis === 'y6') {
                            const values = [];
                            for (let j = 0; j < yLen; j++) values.push(t.y[j]);
                            
                            result.daily[method] = {
                                latest: values[values.length - 1],
                                prev: values.length > 1 ? values[values.length - 2] : 0,
                                avg_5d: values.length >= 5 ? 
                                    values.slice(-5).reduce((a, b) => a + b, 0) / 5 : values[values.length - 1],
                                avg_20d: values.length >= 20 ?
                                    values.slice(-20).reduce((a, b) => a + b, 0) / 20 : values[values.length - 1]
                            };
                        }
                        
                        // Participation ratios (bar, yaxis=y10)
                        if (method && t.type === 'bar' && t.yaxis === 'y10') {
                            const values = [];
                            for (let j = 0; j < yLen; j++) values.push(t.y[j]);
                            
                            result.participation[method] = {
                                latest: values[values.length - 1],
                                avg_5d: values.length >= 5 ?
                                    values.slice(-5).reduce((a, b) => a + b, 0) / 5 : values[values.length - 1]
                            };
                        }
                        
                        // Cross index (scatter, yaxis=y9)
                        if (name === 'cross_index' && t.type === 'scatter') {
                            const values = [];
                            for (let j = 0; j < yLen; j++) values.push(t.y[j]);
                            
                            result.cross_index = {
                                latest: values[values.length - 1],
                                prev: values.length > 1 ? values[values.length - 2] : 0,
                                avg_5d: values.length >= 5 ?
                                    values.slice(-5).reduce((a, b) => a + b, 0) / 5 : values[values.length - 1]
                            };
                        }
                        
                        // Volume
                        if (name === 'volume' && t.type === 'bar') {
                            const values = [];
                            for (let j = 0; j < yLen; j++) values.push(t.y[j]);
                            
                            result.volume = {
                                latest: values[values.length - 1],
                                avg_20d: values.length >= 20 ?
                                    values.slice(-20).reduce((a, b) => a + b, 0) / 20 : values[values.length - 1]
                            };
                        }
                    }
                    
                    return result;
                }
            """)
            
            if data and (data.get('cumulative') or data.get('daily')):
                print(f"   [TXN] Extracted transaction chart for {ticker}: " +
                      f"{len(data.get('cumulative', {}))} cumulative, " +
                      f"{len(data.get('daily', {}))} daily methods")
                data['ticker'] = ticker
                data['period'] = period
                return data
            else:
                print(f"   [TXN] No transaction chart data for {ticker}")
                return None
                
        except Exception as e:
            print(f"   [TXN] Error scraping transaction chart for {ticker}: {e}")
            return None

    # ==================== BANDARMOLOGY: BATCH DEEP ANALYSIS ====================

    async def get_bandarmology_deep_batch(self, tickers: list, period: str = '6m') -> list:
        """
        Execute deep analysis scraping for multiple tickers in a single browser session.
        Scrapes both inventory and transaction chart for each ticker.
        
        Args:
            tickers: List of ticker strings to analyze
            period: Transaction chart period ('3m', '6m', '9m')
        
        Returns:
            List of dicts with inventory and transaction chart data per ticker
        """
        if not self.page:
            return []
        
        results = []
        try:
            # Login once
            login_success = await self.login()
            if not login_success:
                return [{"error": "Login failed"}]
            
            for i, ticker in enumerate(tickers):
                print(f"\n[DEEP] Processing {ticker} ({i+1}/{len(tickers)})...")
                result = {"ticker": ticker}
                
                # 1. Scrape Inventory
                try:
                    inv_data = await self.get_inventory(ticker)
                    if inv_data:
                        result["inventory"] = inv_data
                    else:
                        result["inventory"] = None
                        result["inventory_error"] = "No data"
                except Exception as e:
                    print(f"   [DEEP] Inventory error for {ticker}: {e}")
                    result["inventory"] = None
                    result["inventory_error"] = str(e)
                
                await asyncio.sleep(2)
                
                # 2. Scrape Transaction Chart
                try:
                    txn_data = await self.get_transaction_chart(ticker, period)
                    if txn_data:
                        result["transaction_chart"] = txn_data
                    else:
                        result["transaction_chart"] = None
                        result["txn_error"] = "No data"
                except Exception as e:
                    print(f"   [DEEP] Transaction chart error for {ticker}: {e}")
                    result["transaction_chart"] = None
                    result["txn_error"] = str(e)
                
                results.append(result)
                
                # Cooldown between tickers
                await asyncio.sleep(2)
            
            return results
            
        except Exception as e:
            print(f"[!] Critical error in deep batch: {e}")
            return results

    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

async def verify_credentials():
    scraper = NeoBDMScraper()
    try:
        await scraper.init_browser(headless=True)
        success = await scraper.login()
        if success:
            print("Verification RESULT: SUCCESS")
            # Test Cumulative
            df_cum, ref_date_cum = await scraper.get_market_summary(method='m', period='c')
            if df_cum is not None:
                print(f"Cumulative Market Summary Sample (Date: {ref_date_cum}):")
                print(df_cum.head())
            
            # Test Daily
            df_daily, ref_date_daily = await scraper.get_market_summary(method='m', period='d')
            if df_daily is not None:
                print(f"Daily Market Summary Sample (Date: {ref_date_daily}):")
                print(df_daily.head())
        else:
            print("Verification RESULT: FAILED")
    finally:
        await scraper.close()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(verify_credentials())
