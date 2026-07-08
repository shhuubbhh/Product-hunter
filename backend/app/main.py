import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import Base, engine
from app.api.endpoints import router as api_router
from app.services.scheduler import scheduler
from app.services.websocket import manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ps5_hunter")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup - Create database schemas if SQLite/Postgres
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas created.")
        
    # 2. Startup - Start background monitoring task
    scheduler.start()
    
    yield
    
    # 3. Shutdown - Cancel and join monitoring task
    await scheduler.stop()
    logger.info("Database connection and background task cleaned up.")

app = FastAPI(
    title="PS5 Hunter API",
    description="Real-time Indian retailer stock monitoring API for PlayStation 5",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(api_router, prefix="/api")

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection alive, ignore incoming messages or use for heartbeat
            data = await websocket.receive_text()
            # Send back heartbeat if needed
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
