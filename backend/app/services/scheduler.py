import asyncio
import logging
import time
from datetime import datetime, timezone
from sqlalchemy import select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.models import StoreConfig, SystemSettings, StockHistory, CheckLog
from app.monitors.registry import get_monitor
from app.services.notifications import dispatch_notifications
from app.services.websocket import manager
from app.core.config import settings

logger = logging.getLogger("ps5_hunter.scheduler")

class MonitoringScheduler:
    def __init__(self):
        self.is_running = False
        self._task = None
        self._last_notification_time = {}

    async def initialize_db_defaults(self):
        """Pre-populates the database with default stores and system settings if empty."""
        async with AsyncSessionLocal() as session:
            # Check system settings
            result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
            sys_settings = result.scalar_one_or_none()
            if not sys_settings:
                sys_settings = SystemSettings(
                    id=1,
                    polling_interval=settings.DEFAULT_POLLING_INTERVAL,
                    notification_cooldown_minutes=settings.NOTIFICATION_COOLDOWN_MINUTES,
                    telegram_bot_token=settings.TELEGRAM_BOT_TOKEN,
                    telegram_chat_id=settings.TELEGRAM_CHAT_ID,
                    discord_webhook_url=settings.DISCORD_WEBHOOK_URL,
                    smtp_host=settings.SMTP_HOST,
                    smtp_port=settings.SMTP_PORT,
                    smtp_username=settings.SMTP_USERNAME,
                    smtp_password=settings.SMTP_PASSWORD,
                    smtp_sender=settings.SMTP_SENDER,
                )
                session.add(sys_settings)
                logger.info("Created default system settings.")
            else:
                if sys_settings.polling_interval == 20:
                    sys_settings.polling_interval = 60
                    logger.info("Updated default polling interval from 20s to 60s in database settings.")

            # Check store configs
            defaults = [
                ("amazon", "Amazon India", settings.AMAZON_URL),
                ("flipkart", "Flipkart", settings.FLIPKART_URL),
                ("blinkit", "Blinkit", settings.BLINKIT_URL),
                ("zepto", "Zepto", settings.ZEPTO_URL),
                ("reliance_digital", "Reliance Digital", settings.RELIANCE_DIGITAL_URL),
                ("croma", "Croma", settings.CROMA_URL),
                ("vijay_sales", "Vijay Sales", settings.VIJAY_SALES_URL),
            ]
            
            for name, display_name, url in defaults:
                res = await session.execute(select(StoreConfig).where(StoreConfig.name == name))
                store = res.scalar_one_or_none()
                if not store:
                    store = StoreConfig(
                        name=name,
                        display_name=display_name,
                        product_url=url,
                        enabled=True,
                        status="Out of Stock"
                    )
                    session.add(store)
                    logger.info(f"Created default store config for: {display_name}")
                else:
                    # Automatically update old incorrect URLs if still present
                    old_blinkit = "https://blinkit.com/prn/sony-playstation-5/id/526738"
                    old_zepto = "https://www.zepto.com/p/sony-playstation-5-console/id/ps5-console"
                    if name == "blinkit" and (store.product_url == old_blinkit or not store.product_url):
                        store.product_url = url
                        logger.info(f"Updated incorrect Blinkit URL to: {url}")
                    elif name == "zepto" and (store.product_url == old_zepto or not store.product_url):
                        store.product_url = url
                        logger.info(f"Updated incorrect Zepto URL to: {url}")
            
            await session.commit()

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Background monitoring scheduler started.")

    async def stop(self):
        if self.is_running:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            logger.info("Background monitoring scheduler stopped.")

    async def _run_loop(self):
        await self.initialize_db_defaults()
        
        while self.is_running:
            try:
                # 1. Fetch system settings
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
                    sys_settings = res.scalar_one_or_none()
                    if not sys_settings:
                        logger.error("No system settings found! Initializing defaults...")
                        await self.initialize_db_defaults()
                        continue
                    
                    polling_interval = sys_settings.polling_interval
                    
                    # 2. Fetch enabled stores
                    res = await session.execute(select(StoreConfig).where(StoreConfig.enabled == True))
                    enabled_stores = res.scalars().all()
                
                if enabled_stores:
                    # Run all check tasks concurrently using asyncio.gather
                    tasks = [self._check_store(store.name) for store in enabled_stores]
                    await asyncio.gather(*tasks)

                # Wait for next poll interval
                await asyncio.sleep(polling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler main loop: {e}", exc_info=True)
                await asyncio.sleep(15)

    async def _check_store(self, store_name: str):
        start_time = time.time()
        success = False
        error_msg = None
        
        async with AsyncSessionLocal() as session:
            # Get latest store info
            res = await session.execute(select(StoreConfig).where(StoreConfig.name == store_name))
            store = res.scalar_one_or_none()
            if not store:
                return

            url = store.product_url
            old_status = store.status
            display_name = store.display_name
            custom_headers = store.custom_headers
            
            # Fetch settings for notification configuration
            settings_res = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
            sys_settings = settings_res.scalar_one()

        # Update live status in WebSocket
        await manager.broadcast({
            "type": "store_status_checking",
            "store_name": store_name
        })

        try:
            # Dynamically fetch monitor plugin
            monitor = get_monitor(store_name)
            
            # Run the scraping check
            result = await monitor.check(url, custom_headers=custom_headers)
            
            is_available = result.get("is_available", False)
            price = result.get("price")
            product_name = result.get("product_name", "Sony PlayStation 5")
            error_msg = result.get("error_message")
            
            success = error_msg is None
            new_status = "In Stock" if is_available else "Out of Stock"
            if error_msg:
                new_status = "Error"
        except Exception as e:
            logger.error(f"Fatal error running monitor check for {store_name}: {e}")
            is_available = False
            price = None
            product_name = "Sony PlayStation 5"
            error_msg = str(e)
            success = False
            new_status = "Error"

        response_time_ms = int((time.time() - start_time) * 1000)
        now_dt = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # Retrieve store config object to update fields
            res = await session.execute(select(StoreConfig).where(StoreConfig.name == store_name))
            store = res.scalar_one()
            
            store.status = new_status
            store.last_checked = now_dt
            store.response_time_ms = response_time_ms
            store.last_error = error_msg
            if price:
                store.price = price
                
            if is_available:
                store.last_stock_seen = now_dt

            # Save check log
            log = CheckLog(
                store_name=store_name,
                success=success,
                response_time_ms=response_time_ms,
                error_message=error_msg
            )
            session.add(log)

            # Detect state transitions and notify
            if old_status != "In Stock" and new_status == "In Stock":
                # Changed from OUT OF STOCK to IN STOCK
                logger.info(f"🚨 PS5 IN STOCK at {display_name}!")
                
                # Check cooldown to prevent duplicate notification storms
                last_notify = self._last_notification_time.get(store_name)
                cooldown_passed = True
                if last_notify:
                    elapsed = (time.time() - last_notify) / 60
                    if elapsed < sys_settings.notification_cooldown_minutes:
                        cooldown_passed = False
                        
                if cooldown_passed:
                    self._last_notification_time[store_name] = time.time()
                    # Trigger async notifications dispatch
                    asyncio.create_task(dispatch_notifications(
                        sys_settings, display_name, product_name, price, url
                    ))
                
                # Add to stock history
                history = StockHistory(
                    store_name=store_name,
                    product_name=product_name,
                    price=price,
                    timestamp=now_dt
                )
                session.add(history)

            elif old_status == "In Stock" and new_status != "In Stock":
                # Changed from IN STOCK to OUT OF STOCK
                logger.info(f"📉 PS5 out of stock at {display_name}.")
                
                # Update the ended timestamp on the most recent stock event for this store
                hist_res = await session.execute(
                    select(StockHistory)
                    .where(StockHistory.store_name == store_name, StockHistory.went_out_of_stock_at == None)
                    .order_by(desc(StockHistory.timestamp))
                    .limit(1)
                )
                latest_history = hist_res.scalar_one_or_none()
                if latest_history:
                    latest_history.went_out_of_stock_at = now_dt

            await session.commit()

        # Broadcast update to web socket clients
        await manager.broadcast({
            "type": "store_update",
            "store": {
                "name": store_name,
                "display_name": display_name,
                "status": new_status,
                "last_checked": now_dt.isoformat(),
                "response_time_ms": response_time_ms,
                "price": price,
                "last_stock_seen": store.last_stock_seen.isoformat() if store.last_stock_seen else None,
                "product_url": url
            }
        })

# Single instance of scheduler
scheduler = MonitoringScheduler()
