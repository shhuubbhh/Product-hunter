from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class StoreConfigBase(BaseModel):
    name: str
    display_name: str
    enabled: bool
    product_url: str

class StoreConfigCreate(StoreConfigBase):
    pass

class StoreConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    product_url: Optional[str] = None
    display_name: Optional[str] = None
    custom_headers: Optional[str] = None

class StoreConfigResponse(StoreConfigBase):
    id: int
    status: str
    last_checked: Optional[datetime] = None
    response_time_ms: int
    price: Optional[float] = None
    last_stock_seen: Optional[datetime] = None
    last_error: Optional[str] = None
    custom_headers: Optional[str] = None

    class Config:
        from_attributes = True

class SystemSettingsBase(BaseModel):
    polling_interval: int = Field(20, ge=5, le=3600)
    notification_cooldown_minutes: int = Field(10, ge=0, le=1440)
    
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    discord_enabled: bool = False
    discord_webhook_url: Optional[str] = None
    
    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_sender: str = "noreply@ps5hunter.com"

class SystemSettingsResponse(SystemSettingsBase):
    id: int

    class Config:
        from_attributes = True

class StockHistoryResponse(BaseModel):
    id: int
    store_name: str
    product_name: str
    price: Optional[float] = None
    timestamp: datetime
    went_out_of_stock_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None # Calculated dynamically or returned

    class Config:
        from_attributes = True

class CheckLogResponse(BaseModel):
    id: int
    store_name: str
    timestamp: datetime
    success: bool
    response_time_ms: int
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class StoreStats(BaseModel):
    store_name: str
    checks_performed: int
    successful_checks: int
    failed_checks: int
    uptime_percentage: float
    avg_response_time_ms: float
    last_stock_seen: Optional[datetime] = None

class GlobalStats(BaseModel):
    checks_performed: int
    successful_checks: int
    failed_checks: int
    avg_response_time_ms: float
    last_notification: Optional[datetime] = None
    total_stock_detections: int
    store_stats: List[StoreStats]
