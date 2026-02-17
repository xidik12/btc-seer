import logging

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)


class RedditCollector(BaseCollector):
    """Collects posts from Bitcoin/crypto subreddits via Reddit's public JSON API."""

    SUBREDDITS = [
        "bitcoin", "cryptocurrency", "ethereum", "solana",
        "cardano", "ripple", "dogecoin", "chainlink",
        "polkadot", "CryptoMoonShots",
    ]
    REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/hot.json"

    async def collect(self) -> dict:
        """Collect top posts from crypto subreddits."""
        all_posts = []

        for subreddit in self.SUBREDDITS:
            posts = await self._get_subreddit_posts(subreddit)
            if posts:
                all_posts.extend(posts)

        return {
            "posts": all_posts,
            "count": len(all_posts),
            "timestamp": self.now().isoformat(),
        }

    async def _get_subreddit_posts(self, subreddit: str) -> list[dict] | None:
        """Get hot posts from a subreddit using public JSON API."""
        try:
            session = await self.get_session()
            url = self.REDDIT_JSON_URL.format(subreddit=subreddit)
            headers = {"User-Agent": settings.reddit_user_agent}

            async with session.get(url, headers=headers, params={"limit": 25}) as resp:
                if resp.status != 200:
                    logger.warning(f"Reddit HTTP {resp.status} for r/{subreddit}")
                    return None

                data = await resp.json()

            posts = []
            for child in data.get("data", {}).get("children", []):
                post_data = child.get("data", {})
                posts.append({
                    "subreddit": subreddit,
                    "title": post_data.get("title", ""),
                    "score": post_data.get("score", 0),
                    "num_comments": post_data.get("num_comments", 0),
                    "upvote_ratio": post_data.get("upvote_ratio", 0),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "created_utc": post_data.get("created_utc", 0),
                    "sentiment_score": None,  # To be scored later
                })

            return posts

        except Exception as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
            return None
