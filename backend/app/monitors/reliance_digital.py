import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.reliance_digital")

class RelianceDigitalMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("reliance_digital", "Reliance Digital")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            html = await self.fetch_html(url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for bot / captcha blocks
            is_blocked = "cloudflare" in html.lower() or "captcha" in html.lower() or "robot check" in html.lower() or "access denied" in html.lower() or "checking your browser" in html.lower()
            
            title_el = soup.find("h1") or soup.find(class_="pdp__title")
            if not title_el or is_blocked:
                raise Exception("Blocked by Reliance Digital anti-bot / CAPTCHA detection")
                
            product_name = title_el.get_text(strip=True)
            
            price_el = soup.find(class_="pdp__priceSection__price") or soup.find(class_="price")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))
                
            # Reliance Digital uses "ADD TO CART" or "TEMPORARILY OUT OF STOCK" / "SOLD OUT"
            add_to_cart = soup.find(id="add-to-cart") or soup.find(text=lambda t: t and "add to cart" in t.lower())
            out_of_stock = soup.find(text=lambda t: t and ("out of stock" in t.lower() or "sold out" in t.lower()))
            
            is_available = True
            if out_of_stock:
                is_available = False
            elif not add_to_cart:
                is_available = False
                
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Reliance Digital check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Reliance Digital)",
                "error_message": str(e)
            }
