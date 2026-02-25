"""WebSocket endpoint for real-time BTC price and prediction updates.

Optimization: A single background task refreshes price/prediction caches.
All WebSocket connections read from the shared cache (zero DB queries per client).
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc

from app.database import async_session, Price, Prediction

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])

# ── Shared caches (populated by background tasks) ──
_price_cache: dict | None = None
_prediction_cache: dict = {}
_cache_lock = asyncio.Lock()


MAX_CONNECTIONS = 200
ALLOWED_WS_ORIGINS = {
    "https://web.telegram.org",
    "https://webk.telegram.org",
    "https://webz.telegram.org",
}


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()
        self._refresh_task: asyncio.Task | None = None

    async def connect(self, ws: WebSocket) -> bool:
        if len(self.active) >= MAX_CONNECTIONS:
            await ws.close(code=1013, reason="Server at capacity")
            return False
        await ws.accept()
        self.active.add(ws)
        # Start the shared refresh task on first connection
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info(f"WebSocket connected. Total: {len(self.active)}")
        return True

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info(f"WebSocket disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        dead = set()
        for ws in self.active.copy():
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active.discard(ws)

    async def _refresh_loop(self):
        """Single background task that refreshes price & prediction caches."""
        global _price_cache, _prediction_cache
        tick = 0
        while self.active:  # Stop when no clients
            try:
                # Refresh price every 5s
                price_data = await _fetch_latest_price()
                if price_data:
                    _price_cache = price_data

                # Refresh predictions every 30s (every 6th tick)
                if tick % 6 == 0:
                    pred_data = await _fetch_latest_predictions()
                    if pred_data:
                        _prediction_cache = pred_data

                tick += 1
            except Exception as e:
                logger.error(f"Cache refresh error: {e}")

            await asyncio.sleep(5)

        logger.info("WebSocket refresh loop stopped (no clients)")


manager = ConnectionManager()


async def _fetch_latest_price() -> dict | None:
    """Fetch the most recent price from DB."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price = result.scalar_one_or_none()
            if price:
                return {
                    "open": price.open,
                    "high": price.high,
                    "low": price.low,
                    "close": price.close,
                    "volume": price.volume,
                    "timestamp": price.timestamp.isoformat() if price.timestamp else None,
                }
    except Exception as e:
        logger.error(f"WebSocket price fetch error: {e}")
    return None


async def _fetch_latest_predictions() -> dict:
    """Fetch latest predictions for all timeframes."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Prediction)
                .order_by(desc(Prediction.timestamp))  # Fixed: was created_at (doesn't exist)
                .limit(6)
            )
            preds = result.scalars().all()
            by_tf = {}
            for p in preds:
                if p.timeframe not in by_tf:
                    by_tf[p.timeframe] = {
                        "direction": p.direction,
                        "confidence": p.confidence,
                        "timeframe": p.timeframe,
                    }
            return by_tf
    except Exception as e:
        logger.error(f"WebSocket prediction fetch error: {e}")
    return {}


@router.websocket("/ws/live")
async def live_feed(websocket: WebSocket):
    """
    WebSocket endpoint streaming real-time BTC price and predictions.

    All clients read from a shared cache refreshed by a single background task.
    Sends updates every 5 seconds with:
    - type: "price"       — latest OHLCV candle
    - type: "predictions" — latest predictions by timeframe (every 30s)
    - type: "ping"        — heartbeat every 30s
    """
    # Validate origin
    origin = (websocket.headers.get("origin") or "").rstrip("/")
    if origin and origin not in ALLOWED_WS_ORIGINS:
        if not origin.startswith("http://localhost"):
            await websocket.close(code=1008, reason="Origin not allowed")
            return

    connected = await manager.connect(websocket)
    if not connected:
        return
    tick = 0
    try:
        while True:
            # Send cached price (no DB query per client)
            if _price_cache:
                await websocket.send_json({
                    "type": "price",
                    "data": _price_cache,
                    "ts": time.time(),
                })

            # Every 6th tick (30s): send predictions + heartbeat
            if tick % 6 == 0:
                if _prediction_cache:
                    await websocket.send_json({
                        "type": "predictions",
                        "data": _prediction_cache,
                        "ts": time.time(),
                    })
                await websocket.send_json({"type": "ping", "ts": time.time()})

            tick += 1
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
