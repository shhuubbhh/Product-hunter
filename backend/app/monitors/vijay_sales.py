import logging
from bs4 import BeautifulSoup
from app.monitors.base import BaseMonitor

logger = logging.getLogger("ps5_hunter.monitor.vijay_sales")

class VijaySalesMonitor(BaseMonitor):
    def __init__(self):
        super().__init__("vijay_sales", "Vijay Sales")

    async def check(self, url: str, custom_headers: str = None) -> dict:
        try:
            html = await self.fetch_html(url)
            soup = BeautifulSoup(html, "html.parser")
            
            title_el = soup.find("h1") or soup.find(id="h1ProductName")
            product_name = title_el.get_text(strip=True) if title_el else "Sony PlayStation 5 (Vijay Sales)"
            
            price_el = soup.find(class_="price") or soup.find(id="spanVSP")
            price = None
            if price_el:
                price = self.parse_price(price_el.get_text(strip=True))
                
            # Check for Add to Cart / Buy Now buttons or "Temporarily Out of Stock" / "Notify Me"
            add_button = soup.find(id="btnAddToCart") or soup.find(string=lambda t: t and "add to cart" in t.lower())
            out_of_stock = (
                soup.find(string=lambda t: t and "out of stock" in t.lower())
                or soup.find(string=lambda t: t and "notify" in t.lower())
                or soup.find(id="btnNotifyMe")
            )
            
            is_available = False
            if add_button and not out_of_stock:
                is_available = True
                
            return {
                "is_available": is_available,
                "price": price or 54990.0,
                "product_name": product_name,
                "error_message": None
            }
        except Exception as e:
            logger.error(f"Vijay Sales check failed: {e}")
            return {
                "is_available": False,
                "price": None,
                "product_name": "Sony PlayStation 5 (Vijay Sales)",
                "error_message": str(e)
            }
