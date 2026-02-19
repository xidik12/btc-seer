"""WebSocket endpoint for real-time BTC price and prediction updates."""
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


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info(f"WebSocket connected. Total: {len(self.active)}")

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


manager = ConnectionManager()


async def _get_latest_price() -> dict | None:
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


async def _get_latest_predictions() -> dict:
    """Fetch latest predictions for all timeframes."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Prediction)
                .order_by(desc(Prediction.created_at))
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

    Sends updates every 5 seconds with:
    - type: "price"       — latest OHLCV candle
    - type: "predictions" — latest predictions by timeframe (every 30s)
    - type: "ping"        — heartbeat every 30s
    """
    await manager.connect(websocket)
    tick = 0
    try:
        while True:
            # Send price every 5s
            price_data = await _get_latest_price()
            if price_data:
                await websocket.send_json({
                    "type": "price",
                    "data": price_data,
                    "ts": time.time(),
                })

            # Every 6th tick (30s): send predictions + heartbeat
            if tick % 6 == 0:
                predictions = await _get_latest_predictions()
                if predictions:
                    await websocket.send_json({
                        "type": "predictions",
                        "data": predictions,
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
