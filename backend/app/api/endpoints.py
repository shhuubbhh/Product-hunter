from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Integer, cast
from typing import List
from datetime import datetime, timezone, timedelta
from app.core.database import get_db
from app.models.models import StoreConfig, SystemSettings, StockHistory, CheckLog
from app.schemas.schemas import (
    StoreConfigResponse, StoreConfigUpdate,
    SystemSettingsResponse, SystemSettingsBase,
    StockHistoryResponse, GlobalStats, StoreStats
)
from app.services.notifications import dispatch_notifications

router = APIRouter()

@router.get("/status", response_model=List[StoreConfigResponse])
async def get_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoreConfig))
    return result.scalars().all()

@router.get("/stores", response_model=List[StoreConfigResponse])
async def get_stores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoreConfig))
    return result.scalars().all()

@router.put("/stores/{store_id}", response_model=StoreConfigResponse)
async def update_store(store_id: int, store_in: StoreConfigUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoreConfig).where(StoreConfig.id == store_id))
    store = result.scalar_one_or_none()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
        
    update_data = store_in.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(store, key, val)
        
    await db.commit()
    await db.refresh(store)
    return store

@router.get("/settings", response_model=SystemSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@router.put("/settings", response_model=SystemSettingsResponse)
async def update_settings(settings_in: SystemSettingsBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
        
    update_data = settings_in.dict()
    for key, val in update_data.items():
        setattr(settings, key, val)
        
    await db.commit()
    await db.refresh(settings)
    return settings

@router.get("/history", response_model=List[StockHistoryResponse])
async def get_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StockHistory)
        .order_by(desc(StockHistory.timestamp))
        .limit(limit)
    )
    histories = result.scalars().all()
    
    # Calculate duration dynamically
    res_list = []
    for h in histories:
        duration = None
        if h.went_out_of_stock_at:
            duration = int((h.went_out_of_stock_at - h.timestamp).total_seconds())
        elif h.timestamp:
            duration = int((datetime.now(timezone.utc) - h.timestamp.replace(tzinfo=timezone.utc)).total_seconds())
            
        res_list.append(StockHistoryResponse(
            id=h.id,
            store_name=h.store_name,
            product_name=h.product_name,
            price=h.price,
            timestamp=h.timestamp,
            went_out_of_stock_at=h.went_out_of_stock_at,
            duration_seconds=max(0, duration) if duration is not None else None
        ))
    return res_list

@router.get("/metrics", response_model=GlobalStats)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    # Total checks
    total_checks_res = await db.execute(select(func.count()).select_from(CheckLog))
    total_checks = total_checks_res.scalar() or 0
    
    # Successful checks
    success_checks_res = await db.execute(select(func.count()).select_from(CheckLog).where(CheckLog.success == True))
    success_checks = success_checks_res.scalar() or 0
    
    failed_checks = total_checks - success_checks
    
    # Average response time
    avg_response_res = await db.execute(select(func.avg(CheckLog.response_time_ms)))
    avg_response = avg_response_res.scalar() or 0.0
    
    # Total Stock Detections
    total_stock_res = await db.execute(select(func.count()).select_from(StockHistory))
    total_stock_detections = total_stock_res.scalar() or 0
    
    # Store-specific statistics
    stores_res = await db.execute(select(StoreConfig))
    stores = stores_res.scalars().all()
    
    store_stats_list = []
    for store in stores:
        # Check logs for this store
        sc_res = await db.execute(
            select(
                func.count().label("total"),
                func.sum(cast(CheckLog.success, Integer)).label("success"),
                func.avg(CheckLog.response_time_ms).label("avg_time")
            )
            .where(CheckLog.store_name == store.name)
        )
        stats_row = sc_res.first()
        
        checks = stats_row.total if stats_row and stats_row.total else 0
        success = stats_row.success if stats_row and stats_row.success else 0
        avg_time = stats_row.avg_time if stats_row and stats_row.avg_time else 0.0
        
        uptime = (success / checks * 100.0) if checks > 0 else 100.0
        
        store_stats_list.append(StoreStats(
            store_name=store.name,
            checks_performed=checks,
            successful_checks=success,
            failed_checks=checks - success,
            uptime_percentage=round(uptime, 2),
            avg_response_time_ms=round(avg_time, 2),
            last_stock_seen=store.last_stock_seen
        ))
        
    return GlobalStats(
        checks_performed=total_checks,
        successful_checks=success_checks,
        failed_checks=failed_checks,
        avg_response_time_ms=round(avg_response, 2),
        last_notification=None, # Updated dynamically if needed
        total_stock_detections=total_stock_detections,
        store_stats=store_stats_list
    )

@router.post("/test-notification")
async def test_notification(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
        
    await dispatch_notifications(
        settings,
        store_display_name="Test Store",
        product_name="Sony PlayStation 5 Slim Disc (Test Alert)",
        price=54990.00,
        url="https://www.playstation.com"
    )
    return {"message": "Test notification dispatched"}

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(1))
        db_ok = True
    except Exception:
        db_ok = False
        
    from app.services.scheduler import scheduler
    
    return {
        "status": "healthy" if (db_ok and scheduler.is_running) else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "scheduler_running": scheduler.is_running
    }
