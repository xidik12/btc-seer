"""Live liquidation feed collector — fetches forced liquidation orders from Binance."""

import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class LiquidationFeedCollector(BaseCollector):
    """Fetches BTCUSDT forced liquidation (auto-deleveraging) orders from Binance Futures."""

    BINANCE_FORCE_ORDERS_URL = "https://fapi.binance.com/fapi/v1/allForceOrders"

    async def collect(self, limit: int = 100) -> dict:
        data = await self.fetch_json(
            self.BINANCE_FORCE_ORDERS_URL,
            params={"symbol": "BTCUSDT", "limit": limit},
        )

        if not data:
            logger.warning("Binance force orders returned no data")
            return {"events": []}

        events = []
        for order in data:
            side = order.get("side", "")  # BUY or SELL
            qty = float(order.get("origQty", 0) or 0)
            price = float(order.get("price", 0) or 0)
            avg_price = float(order.get("averagePrice", 0) or 0)
            actual_price = avg_price if avg_price > 0 else price
            usd_value = qty * actual_price
            ts = order.get("time", 0)

            # BUY force order = short position liquidated (SHORT LIQ)
            # SELL force order = long position liquidated (LONG LIQ)
            position = "SHORT" if side == "BUY" else "LONG"

            events.append({
                "exchange": "Binance",
                "symbol": "BTCUSDT",
                "position": position,
                "qty_btc": round(qty, 6),
                "price": round(actual_price, 2),
                "usd_value": round(usd_value, 2),
                "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else None,
                "side": side,
            })

        # Sort newest first
        events.sort(key=lambda e: e["timestamp"] or "", reverse=True)

        return {"events": events}
