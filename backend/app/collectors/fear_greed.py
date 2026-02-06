import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

FEAR_GREED_URL = "https://api.alternative.me/fng/"


class FearGreedCollector(BaseCollector):
    """Collects Bitcoin Fear & Greed Index from alternative.me."""

    async def collect(self) -> dict:
        """Get current Fear & Greed Index."""
        data = await self.fetch_json(FEAR_GREED_URL, params={"limit": 1})

        if not data or "data" not in data:
            return {
                "value": None,
                "label": None,
                "timestamp": self.now().isoformat(),
            }

        entry = data["data"][0]
        return {
            "value": int(entry.get("value", 0)),
            "label": entry.get("value_classification", ""),
            "timestamp": entry.get("timestamp", self.now().isoformat()),
        }

    async def get_historical(self, days: int = 30) -> list[dict] | None:
        """Get historical Fear & Greed data."""
        data = await self.fetch_json(FEAR_GREED_URL, params={"limit": days})

        if not data or "data" not in data:
            return None

        return [
            {
                "value": int(entry.get("value", 0)),
                "label": entry.get("value_classification", ""),
                "timestamp": entry.get("timestamp", ""),
            }
            for entry in data["data"]
        ]
