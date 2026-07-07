import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.zepto")

class ZeptoMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("zepto", "Zepto")

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
                                "latitude": f"{lat:.4f}",
                                "longitude": f"{lon:.4f}",
                                "user_pincode": str(pincode),
                                "pincode": str(pincode)
                            }
                            logger.info(f"Zepto checking with location for pincode {pincode}: lat={lat:.4f}, lon={lon:.4f}")
                except Exception as ex:
                    logger.warning(f"Failed to parse custom_headers for Zepto: {ex}")
            
            html = await self.fetch_html(url, cookies=cookies)
            soup = BeautifulSoup(html, "html.parser")
            
            title_el = soup.find("h1") or soup.find(attrs={"data-testid": "product-name"})
            product_name = title_el.get_text(strip=True) if title_el else "Sony PlayStation 5 (Zepto)"
            
            price_el = soup.find(attrs={"data-testid": "product-price"}) or soup.find(class_="price")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))
                
            # If we see add button or not
            add_button = soup.find(attrs={"data-testid": "add-to-cart-btn"}) or soup.find(string=lambda t: t and "add" in t.lower())
            out_of_stock = soup.find(string=lambda t: t and "out of stock" in t.lower())
            
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
            logger.error(f"Zepto check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Zepto)",
                "error_message": str(e)
            }
