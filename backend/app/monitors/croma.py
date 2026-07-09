import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.croma")

class CromaMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("croma", "Croma")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            # Parse custom headers for pincode
            pincode = None
            if custom_headers:
                import json
                try:
                    parsed = json.loads(custom_headers)
                    pincode = parsed.get("pincode")
                except Exception as ex:
                    logger.warning(f"Failed to parse custom_headers for Croma: {ex}")

            # Default to Mumbai pincode if none set
            if not pincode:
                pincode = "400049"

            # Geocode the pincode to mock browser geolocation API
            lat, lon = 18.9400, 72.8350 # Default Mumbai coordinates fallback
            coords = await self.geocode_pincode(pincode)
            if coords:
                lat, lon = coords

            geolocation = {
                "longitude": lon,
                "latitude": lat
            }

            # Set location cookies as fallback
            cookies = {
                "pincode": str(pincode),
                "mylocation": str(pincode),
                "location": str(pincode)
            }
            logger.info(f"Croma checking with pincode {pincode} (lat={lat:.4f}, lon={lon:.4f})")

            # Fetch HTML using Firefox Playwright and mock geolocation
            html = await self.fetch_html_playwright(url, cookies=cookies, geolocation=geolocation)
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for bot / captcha blocks
            is_blocked = "cloudflare" in html.lower() or "captcha" in html.lower() or "robot check" in html.lower() or "access denied" in html.lower() or "checking your browser" in html.lower()
            
            title_el = soup.find("h1") or soup.find(class_="pd-title")
            if not title_el or is_blocked:
                raise Exception("Blocked by Croma anti-bot / CAPTCHA detection")
                
            product_name = title_el.get_text(strip=True)
            
            price_el = soup.find(id="pdp-info-price") or soup.find(class_="amount")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))

            # Clean BeautifulSoup tree for OOS text checking
            clean_soup = BeautifulSoup(html, "html.parser")
            for s in clean_soup(["script", "style", "noscript", "iframe", "svg"]):
                s.decompose()
            page_text = clean_soup.get_text().lower()

            # Target exact phrases signifying out of stock / not available
            oos_phrases = ["not available for your pincode", "out of stock", "temporarily unavailable", "sold out", "temporarily out of stock", "not available"]
            has_oos_phrase = any(phrase in page_text for phrase in oos_phrases)

            # Find Buy Now or Add to Cart buttons
            buy_now = soup.find(class_="buyNowBtn") or soup.find(class_="pdp-add-to-cart")
            
            is_disabled = False
            if buy_now:
                is_disabled = (
                    buy_now.has_attr("disabled")
                    or "disabled" in buy_now.get("class", [])
                    or "disabled" in "".join(buy_now.get("class", [])).lower()
                )

            is_available = False
            logger.info(f"Croma Parsing - Title: '{product_name}', Price: {price}, Buy Now Found: {buy_now is not None}, Disabled: {is_disabled}, OOS Phrase Found: {has_oos_phrase}")
            
            if buy_now and not is_disabled and not has_oos_phrase:
                is_available = True
                
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Croma check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Croma)",
                "error_message": str(e)
            }
