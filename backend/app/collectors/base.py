import logging
import ssl
from abc import ABC, abstractmethod
from datetime import datetime

import aiohttp
import certifi

logger = logging.getLogger(__name__)

# Create SSL context using certifi's CA bundle
_ssl_ctx = ssl.create_default_context(cafile=certifi.where())


class BaseCollector(ABC):
    """Base class for all data collectors."""

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=_ssl_ctx)
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=connector,
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def collect(self) -> dict:
        """Collect data and return as dict."""
        pass

    async def fetch_json(self, url: str, params: dict = None, headers: dict = None) -> dict | None:
        try:
            session = await self.get_session()
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                logger.warning(f"[{self.__class__.__name__}] HTTP {resp.status} from {url}")
                return None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Error fetching {url}: {e}")
            return None

    @staticmethod
    def now() -> datetime:
        return datetime.utcnow()
