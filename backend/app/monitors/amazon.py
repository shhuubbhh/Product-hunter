import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.amazon")

class AmazonMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("amazon", "Amazon India")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            html = await self.fetch_html_playwright(url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for Amazon captcha page or block
            is_captcha = False
            if "captcha" in html.lower() or "/errors/validateCaptcha" in html or "robot check" in html.lower() or "field-keywords" in html:
                is_captcha = True
            
            # Extract product title
            title_el = soup.find(id="productTitle")
            
            if not title_el or is_captcha:
                raise Exception("Blocked by Amazon CAPTCHA / bot detection")
                
            product_name = title_el.get_text(strip=True)
            
            # Check availability
            avail_div = soup.find(id="availability")
            availability_text = avail_div.get_text(strip=True).lower() if avail_div else ""
            
            is_available = True
            if "currently unavailable" in availability_text or "out of stock" in availability_text:
                is_available = False
                
            # Verify if Add to Cart button exists
            add_to_cart = soup.find(id="add-to-cart-button")
            buy_now = soup.find(id="buy-now-button")
            
            if not add_to_cart and not buy_now and not availability_text:
                # If we couldn't find any indicators, fallback to checking buttons
                is_available = False
            elif add_to_cart or buy_now:
                is_available = True

            # Extract price
            price_el = soup.find(class_="a-price-whole")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))
            
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Amazon check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Amazon)",
                "error_message": str(e)
            }
        
# For testing/demo, we can also add dynamic mock response if the page is completely captcha blocked.
