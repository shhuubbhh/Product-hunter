import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./ps5_hunter.db"
    SECRET_KEY: str = "supersecretkeychangeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    DEFAULT_POLLING_INTERVAL: int = 60
    NOTIFICATION_COOLDOWN_MINUTES: int = 10
    
    # Notification Settings
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SENDER: str = "noreply@ps5hunter.com"
    
    # Product URLs
    AMAZON_URL: str = "https://www.amazon.in/dp/B0CLV37ZCB"
    FLIPKART_URL: str = "https://www.flipkart.com/sony-playstation-5-slim-1-tb/p/itm2ef42cd894f09"
    BLINKIT_URL: str = "https://blinkit.com/prn/sony-playstation-5-slim-cfi-2008a01-disc-edition/id/526738"
    ZEPTO_URL: str = "https://www.zepto.com/p/sony-playstation-5-slim-console/p/440539c3-1f1f-4ee7-8509-f80e051c91ee"
    RELIANCE_DIGITAL_URL: str = "https://www.reliancedigital.in/sony-playstation-5-console-slim/p/494352777"
    CROMA_URL: str = "https://www.croma.com/sony-playstation-5-slim/p/305260"
    VIJAY_SALES_URL: str = "https://www.vijaysales.com/sony-playstation-5-console-slim/p/vsp-23425"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
