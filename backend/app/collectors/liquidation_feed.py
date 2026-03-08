"""Live liquidation feed collector — fetches forced liquidation orders from OKX (free, no API key)."""

import logging
from datetime import datetime, timezone

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class LiquidationFeedCollector(BaseCollector):
    """Fetches BTC-USDT perpetual swap liquidation orders from OKX public API."""

    OKX_LIQUIDATION_URL = "https://www.okx.com/api/v5/public/liquidation-orders"

    async def collect(self, limit: int = 100) -> dict:
        # OKX returns liquidations grouped by state; we want filled orders
        data = await self.fetch_json(
            self.OKX_LIQUIDATION_URL,
            params={
                "instType": "SWAP",
                "instFamily": "BTC-USDT",
                "state": "filled",
                "limit": "1",  # OKX returns batches of events per entry
            },
        )

        if not data or data.get("code") != "0":
            msg = data.get("msg", "unknown") if data else "no response"
            logger.warning(f"OKX liquidation API error: {msg}")
            return {"events": []}

        events = []
        for entry in data.get("data", []):
            for detail in entry.get("details", []):
                pos_side = detail.get("posSide", "")  # "long" or "short"
                side = detail.get("side", "")  # "buy" or "sell"
                qty = float(detail.get("sz", 0) or 0)
                price = float(detail.get("bkPx", 0) or 0)
                ts = int(detail.get("ts", 0) or 0)
                usd_value = qty * price

                # posSide directly tells us: "long" = LONG LIQ, "short" = SHORT LIQ
                position = pos_side.upper() if pos_side else ("SHORT" if side == "buy" else "LONG")

                events.append({
                    "exchange": "OKX",
                    "symbol": "BTCUSDT",
                    "position": position,
                    "qty_btc": round(qty, 6),
                    "price": round(price, 2),
                    "usd_value": round(usd_value, 2),
                    "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else None,
                    "side": side,
                })

        # Sort newest first, limit
        events.sort(key=lambda e: e["timestamp"] or "", reverse=True)
        events = events[:limit]

        return {"events": events}
