import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.flipkart")

class FlipkartMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("flipkart", "Flipkart")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            html = await self.fetch_html(url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for bot / captcha blocks
            is_blocked = "cloudflare" in html.lower() or "captcha" in html.lower() or "robot check" in html.lower() or "access denied" in html.lower() or "checking your browser" in html.lower()
            
            # Extract product title
            title_el = soup.find("span", class_="VU-ZEz") or soup.find("span", class_="B_NuCI")
            if not title_el or is_blocked:
                raise Exception("Blocked by Flipkart anti-bot / CAPTCHA detection")
                
            product_name = title_el.get_text(strip=True)
            
            # Extract price
            price_el = soup.find("div", class_="Nx9n7B") or soup.find("div", class_="_30jeq3")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))

            # Stock check
            # Flipkart shows "Sold Out" or disables the add to cart / buy now buttons
            sold_out_el = soup.find("div", class_="_1dV5cZ") or soup.find("div", class_="_12C57C")
            sold_out_text = sold_out_el.get_text(strip=True).lower() if sold_out_el else ""
            
            is_available = True
            if "sold out" in sold_out_text or "temporarily unavailable" in sold_out_text:
                is_available = False
                
            # If buy button or add to cart button exists, we are in stock
            buy_btn = soup.find("button", class_="_2KpZ6l") # Common button class
            cart_btn = soup.find("button", class_="_2KpZ6l _2U9uOA _3v1-ww")
            
            if not buy_btn and not cart_btn and not sold_out_text:
                is_available = False
            elif buy_btn or cart_btn:
                is_available = True
                
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Flipkart check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Flipkart)",
                "error_message": str(e)
            }
