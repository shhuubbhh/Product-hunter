from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class StoreConfig(Base):
    __tablename__ = "store_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. "amazon"
    display_name = Column(String, nullable=False) # e.g. "Amazon India"
    enabled = Column(Boolean, default=True)
    product_url = Column(String, nullable=False)
    
    # Live status fields updated by scheduler
    status = Column(String, default="Out of Stock") # "In Stock", "Out of Stock", "Unknown", "Checking", "Error"
    last_checked = Column(DateTime(timezone=True), nullable=True)
    response_time_ms = Column(Integer, default=0)
    price = Column(Float, nullable=True)
    last_stock_seen = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    custom_headers = Column(String, nullable=True) # JSON string for location cookies/headers

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, default=1)
    polling_interval = Column(Integer, default=20)
    notification_cooldown_minutes = Column(Integer, default=10)
    
    # Notifications config
    telegram_enabled = Column(Boolean, default=False)
    telegram_bot_token = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    
    discord_enabled = Column(Boolean, default=False)
    discord_webhook_url = Column(String, nullable=True)
    
    email_enabled = Column(Boolean, default=False)
    smtp_host = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String, nullable=True)
    smtp_password = Column(String, nullable=True)
    smtp_sender = Column(String, default="noreply@ps5hunter.com")

class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String, index=True, nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    went_out_of_stock_at = Column(DateTime(timezone=True), nullable=True) # when it went back out of stock

class CheckLog(Base):
    __tablename__ = "check_logs"

    id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    success = Column(Boolean, default=True)
    response_time_ms = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
