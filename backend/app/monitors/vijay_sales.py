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
            
            # Check availability, price and product name via LD-JSON schema first
            is_available = False
            price = None
            schema_found = False
            schema_product_name = None
            ld_json_tags = soup.find_all("script", type="application/ld+json")
            
            for tag in ld_json_tags:
                try:
                    import json
                    data = json.loads(tag.string)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            schema_product_name = item.get("name")
                            offers = item.get("offers", {})
                            if isinstance(offers, dict):
                                availability = offers.get("availability", "")
                                if availability:
                                    schema_found = True
                                    if "instock" in availability.lower():
                                        is_available = True
                                    else:
                                        is_available = False
                                        
                                offer_price = offers.get("price") or offers.get("lowPrice")
                                if offer_price:
                                    price = float(offer_price)
                                break
                    if schema_found:
                        break
                except Exception:
                    pass

            is_blocked = "cloudflare" in html.lower() or "captcha" in html.lower() or "robot check" in html.lower() or "access denied" in html.lower() or "checking your browser" in html.lower()
            
            title_el = soup.find("h1") or soup.find(id="h1ProductName")
            if (not title_el and not schema_product_name) or is_blocked:
                raise Exception("Blocked by Vijay Sales anti-bot / CAPTCHA detection")
                
            product_name = schema_product_name or title_el.get_text(strip=True)

            # Fallback to robust DOM parsing if LD-JSON schema is not found
            if not schema_found:
                price_el = soup.find(class_="price") or soup.find(id="spanVSP")
                if price_el:
                    price = self.parse_price(price_el.get_text(strip=True))

                visible_add_to_cart = False
                for btn in soup.find_all("button"):
                    btn_text = btn.get_text(strip=True).lower()
                    if "add to cart" in btn_text or "buy now" in btn_text:
                        # Check if this button or any of its ancestors has "d-none" or display: none style
                        is_hidden = False
                        curr = btn
                        while curr:
                            classes = curr.get("class", [])
                            if "d-none" in classes:
                                is_hidden = True
                                break
                            style = curr.get("style", "")
                            if "display:none" in style.replace(" ", "").lower():
                                is_hidden = True
                                break
                            curr = curr.parent
                        if not is_hidden:
                            visible_add_to_cart = True
                            break
                is_available = visible_add_to_cart
                
            if product_name:
                product_name = product_name.replace("\ufffd", "®")
                
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
