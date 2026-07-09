import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.blinkit")

class BlinkitMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("blinkit", "Blinkit")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            cookies = {}
            if custom_headers:
                import json
                try:
                    parsed = json.loads(custom_headers)
                    pincode = parsed.get("pincode")
                    if pincode:
                        coords = await self.geocode_pincode(pincode)
                        if coords:
                            lat, lon = coords
                            cookies = {
                                "lat": f"{lat:.4f}",
                                "lon": f"{lon:.4f}"
                            }
                            logger.info(f"Blinkit checking with location for pincode {pincode}: lat={lat:.4f}, lon={lon:.4f}")
                except Exception as ex:
                    logger.warning(f"Failed to parse custom_headers for Blinkit: {ex}")
            
            # Perform HTML fetching with location cookies using Playwright to bypass 403 Forbidden
            html = await self.fetch_html_playwright(url, cookies=cookies)
            soup = BeautifulSoup(html, "html.parser")

            # Check for bot / captcha blocks or invalid product link
            is_blocked = "cloudflare" in html.lower() or "captcha" in html.lower() or "robot check" in html.lower() or "access denied" in html.lower() or "checking your browser" in html.lower()
            
            # Simple parser for Blinkit web product page
            title_el = soup.find("h1") or soup.find(class_="ProductBuying__Title")
            
            if not title_el or is_blocked:
                raise Exception("Blocked by Blinkit anti-bot or invalid product URL (title missing)")
                
            product_name = title_el.get_text(strip=True)
            
            price_el = soup.find(class_="ProductBuying__Price") or soup.find(class_="price")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))
                
            # Blinkit shows ADD or Out of stock
            # Check for text "out of stock" or "add" buttons
            out_of_stock = soup.find(string=lambda t: t and "out of stock" in t.lower())
            add_button = soup.find(string=lambda t: t and "add" in t.lower())
            
            is_available = False
            # Ensure the scraped product name contains "playstation 5" or "ps5" and is not an accessory/game to avoid false positives from recommended items
            name_lower = product_name.lower()
            is_ps5_console = ("playstation 5" in name_lower or "ps5" in name_lower) and not any(
                x in name_lower for x in ["controller", "game", "dock", "charger", "headset", "remote", "grip", "stand", "skin", "playstation vr", "pavr"]
            )
            
            if is_ps5_console and add_button and not out_of_stock:
                is_available = True
                
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Blinkit check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Blinkit)",
                "error_message": str(e)
            }
