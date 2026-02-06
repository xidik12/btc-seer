import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Binance public CMS API for announcements
BINANCE_CMS_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"

# Categories of interest
ANNOUNCEMENT_CATEGORIES = [
    48,   # New Cryptocurrency Listing
    49,   # Latest News
    161,  # Delisting
    128,  # Latest Activities
    131,  # Binance Earn
    198,  # Token Airdrop
]


class BinanceNewsCollector(BaseCollector):
    """Collects Binance announcements — new listings, delistings, airdrops, etc."""

    async def collect(self) -> dict:
        """Fetch latest Binance announcements from all important categories."""
        all_items = []

        for cat_id in ANNOUNCEMENT_CATEGORIES:
            items = await self._get_category(cat_id)
            if items:
                all_items.extend(items)

        return {
            "news": all_items,
            "count": len(all_items),
            "timestamp": self.now().isoformat(),
        }

    async def _get_category(self, category_id: int) -> list[dict] | None:
        """Get announcements for a specific category."""
        try:
            session = await self.get_session()
            payload = {
                "type": 1,
                "catalogId": category_id,
                "pageNo": 1,
                "pageSize": 20,
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            }

            async with session.post(
                BINANCE_CMS_URL, json=payload, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"Binance CMS HTTP {resp.status} for cat {category_id}")
                    return None
                data = await resp.json()

            articles = (
                data.get("data", {}).get("catalogs", [{}])[0].get("articles", [])
                if data.get("data", {}).get("catalogs")
                else []
            )

            cat_label = {
                48: "new_listing",
                49: "binance_news",
                161: "delisting",
                128: "binance_activity",
                131: "binance_earn",
                198: "token_airdrop",
            }.get(category_id, "binance")

            items = []
            for art in articles:
                title = art.get("title", "")
                code = art.get("code", "")
                release_date = art.get("releaseDate")

                items.append({
                    "source": f"binance_{cat_label}",
                    "title": title,
                    "url": f"https://www.binance.com/en/support/announcement/{code}" if code else "",
                    "published": (
                        datetime.fromtimestamp(release_date / 1000).isoformat()
                        if release_date
                        else ""
                    ),
                    "sentiment_score": None,
                    "raw_sentiment": None,
                })

            return items

        except Exception as e:
            logger.debug(f"Error fetching Binance cat {category_id}: {e}")
            return None
