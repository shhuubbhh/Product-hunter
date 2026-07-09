import asyncio
import httpx
import logging
from typing import Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger("ps5_hunter.monitor")

class BaseMonitor:
    def __init__(self, name: str, display_name: str):
        self.name = name
        self.display_name = display_name
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    async def fetch_html(self, url: str, headers: Optional[dict] = None, cookies: Optional[dict] = None) -> str:
        """Fetches raw HTML using HTTPX with optional custom headers and cookies."""
        req_headers = {**self.headers}
        if headers:
            req_headers.update(headers)
        async with httpx.AsyncClient(headers=req_headers, cookies=cookies, follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def fetch_html_playwright(self, url: str, cookies: Optional[dict] = None, geolocation: Optional[dict] = None) -> str:
        """Fetches HTML using Playwright to bypass anti-bot systems like Cloudflare."""
        from playwright.async_api import async_playwright
        from urllib.parse import urlparse
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True
            )
            context_args = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1280, "height": 800},
                "extra_http_headers": {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                }
            }
            if geolocation:
                context_args["geolocation"] = geolocation
                context_args["permissions"] = ["geolocation"]

            context = await browser.new_context(**context_args)
            if cookies:
                domain = urlparse(url).netloc
                formatted_cookies = []
                for k, v in cookies.items():
                    formatted_cookies.append({
                        "name": str(k),
                        "value": str(v),
                        "domain": f".{domain}" if not domain.startswith(".") else domain,
                        "path": "/"
                    })
                await context.add_cookies(formatted_cookies)
                
            page = await context.new_page()
            
            # Evasion script to bypass basic webdriver detection
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Dismiss typical location popups if they exist
            try:
                close_btn = page.locator("#close, #triggerClose, .icon-close").first
                if await close_btn.count() > 0 and await close_btn.is_visible():
                    await close_btn.click(force=True)
                else:
                    await page.mouse.click(961, 519)
                await asyncio.sleep(1)
            except Exception:
                pass
            
            # Scroll down to load lazy-loaded elements
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
            await asyncio.sleep(2)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(1)
            
            content = await page.content()
            await browser.close()
            return content

    async def check(self, url: str, custom_headers: Optional[str] = None) -> dict:
        """
        Runs the monitoring check.
        Returns:
            dict containing:
                is_available: bool
                price: Optional[float]
                product_name: str
                error_message: Optional[str]
        """
        raise NotImplementedError("Each store monitor must implement the check method.")

    async def geocode_pincode(self, pincode: str) -> Optional[Tuple[float, float]]:
        """Geocodes an Indian pincode to (latitude, longitude) using OSM Nominatim, with a local fallback."""
        try:
            # Clean pincode to check it is valid 6 digits
            pincode = "".join(c for c in pincode if c.isdigit())
            if len(pincode) != 6:
                return None
                
            headers = {"User-Agent": "ps5_hunter_geocoder/1.0"}
            async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
                url = f"https://nominatim.openstreetmap.org/search?postalcode={pincode}&country=India&format=json"
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        return lat, lon
        except Exception as e:
            logger.warning(f"OSM geocoding failed for pincode {pincode}: {e}")
            
        # Fallback dictionary for common major Indian pincodes if API fails
        fallbacks = {
            "110001": (28.6304, 77.2177), # Delhi
            "400001": (18.9400, 72.8350), # Mumbai
            "560001": (12.9716, 77.5946), # Bangalore
            "600001": (13.0827, 80.2707), # Chennai
            "700001": (22.5726, 88.3639), # Kolkata
            "500001": (17.3850, 78.4867), # Hyderabad
            "380001": (23.0225, 72.5714), # Ahmedabad
            "411001": (18.5204, 73.8567), # Pune
        }
        return fallbacks.get(pincode)

    def parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """Utility to parse standard Indian pricing format (e.g. ₹54,990 or 54,990.00)."""
        if not price_str:
            return None
        try:
            # Remove currency symbols, commas, and whitespace
            cleaned = "".join(c for c in price_str if c.isdigit() or c == ".")
            return float(cleaned) if cleaned else None
        except Exception as e:
            logger.warning(f"Failed to parse price string '{price_str}': {e}")
            return None
