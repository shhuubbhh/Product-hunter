import httpx
import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.models.models import SystemSettings

logger = logging.getLogger("ps5_hunter.notifications")

async def send_telegram_notification(token: str, chat_id: str, message: str) -> bool:
    """Sends a Telegram bot notification."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Telegram: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False

async def send_discord_notification(webhook_url: str, message: str) -> bool:
    """Sends a Discord webhook notification."""
    payload = {
        "content": message
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            if response.status_code in (200, 204):
                logger.info("Discord notification sent successfully.")
                return True
            else:
                logger.error(f"Failed to send Discord: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False

def _send_email_sync(smtp_host: str, smtp_port: int, username: Optional[str], password: Optional[str], sender: str, recipient: str, subject: str, body: str):
    """Synchronously sends email using smtplib (meant to run in threadpool)."""
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if smtp_port == 587:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(sender, recipient, msg.as_string())

async def send_email_notification(settings: SystemSettings, recipient: str, subject: str, html_body: str) -> bool:
    """Asynchronously sends email notification using system settings."""
    if not settings.smtp_host or not settings.smtp_sender:
        logger.warning("SMTP not configured properly.")
        return False
        
    try:
        await asyncio.to_thread(
            _send_email_sync,
            settings.smtp_host,
            settings.smtp_port,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_sender,
            recipient,
            subject,
            html_body
        )
        logger.info("Email notification sent successfully.")
        return True
    except Exception as e:
        logger.error(f"Error sending Email notification: {e}")
        return False

async def dispatch_notifications(settings: SystemSettings, store_display_name: str, product_name: str, price: Optional[float], url: str):
    """Dispatches notifications across all enabled channels."""
    price_str = f"₹{price:,.2f}" if price else "Price not available"
    
    # Telegram Message (HTML support)
    tg_message = (
        f"🚨 <b>PS5 FOUND!</b>\n\n"
        f"<b>Store:</b> {store_display_name}\n"
        f"<b>Product:</b> {product_name}\n"
        f"<b>Price:</b> {price_str}\n\n"
        f"⚡ <a href='{url}'><b>BUY NOW</b></a>\n\n"
        f"<i>Status: IN STOCK</i>"
    )

    # Discord message
    discord_message = (
        f"🚨 **PS5 FOUND!**\n\n"
        f"**Store:** {store_display_name}\n"
        f"**Product:** {product_name}\n"
        f"**Price:** {price_str}\n\n"
        f"⚡ **[BUY NOW]({url})**"
    )

    # HTML Email body
    email_body = f"""
    <html>
    <body>
        <h2>🚨 PS5 Stock Alert!</h2>
        <p><strong>Store:</strong> {store_display_name}</p>
        <p><strong>Product:</strong> {product_name}</p>
        <p><strong>Price:</strong> {price_str}</p>
        <p><a href="{url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;"><strong>BUY NOW</strong></a></p>
    </body>
    </html>
    """

    tasks = []
    
    if settings.telegram_enabled and settings.telegram_bot_token and settings.telegram_chat_id:
        tasks.append(send_telegram_notification(settings.telegram_bot_token, settings.telegram_chat_id, tg_message))
        
    if settings.discord_enabled and settings.discord_webhook_url:
        tasks.append(send_discord_notification(settings.discord_webhook_url, discord_message))
        
    if settings.email_enabled and settings.smtp_username:
        # Send to the configured SMTP username as the recipient for self-notifications
        tasks.append(send_email_notification(settings, settings.smtp_username, f"PS5 Stock Alert: {store_display_name}", email_body))
        
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
