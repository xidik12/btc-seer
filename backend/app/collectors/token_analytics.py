"""Token Analytics Collector — retrieves on-chain analytics for ERC-20 tokens
using the Etherscan V2 API (chainid=1 for Ethereum mainnet).

Capabilities:
  - Top 10 holder distribution (top_holder_pct)
  - Contract verification status
  - Holder count

Rate limit: 5 calls/sec free tier -> asyncio.sleep(0.2) between calls.
API key from settings.etherscan_api_key (graceful fallback if empty).
"""

import asyncio
import logging

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# ── Etherscan V2 Endpoints ───────────────────────────────────────────────────
ETHERSCAN_V2_BASE = "https://api.etherscan.io/v2/api"

# Rate limit: 5 calls/sec -> 200ms between requests
RATE_LIMIT_DELAY = 0.2


class TokenAnalyticsCollector(BaseCollector):
    """Fetches on-chain token analytics from Etherscan V2 (Ethereum mainnet)."""

    def __init__(self):
        super().__init__()

    async def collect(self) -> dict:
        """Not used as a standalone collector — call get_token_analytics() directly."""
        return {}

    async def get_token_analytics(self, contract_address: str) -> dict:
        """Retrieve holder distribution and contract verification for an ERC-20 token.

        Args:
            contract_address: The ERC-20 token contract address on Ethereum mainnet.

        Returns:
            {
                "top_holder_pct": float | None,
                "contract_verified": bool | None,
                "holder_count": int | None,
                "error": str | None,
            }
        """
        result = {
            "top_holder_pct": None,
            "contract_verified": None,
            "holder_count": None,
            "error": None,
        }

        api_key = settings.etherscan_api_key
        if not api_key:
            result["error"] = "etherscan_api_key not configured"
            logger.debug("TokenAnalytics: no Etherscan API key configured, skipping")
            return result

        # Step 1: Top holders
        holder_data = await self._fetch_top_holders(contract_address, api_key)
        await asyncio.sleep(RATE_LIMIT_DELAY)

        if holder_data is not None:
            result["top_holder_pct"] = holder_data["top_holder_pct"]
            result["holder_count"] = holder_data["holder_count"]

        # Step 2: Contract verification
        verified = await self._check_contract_verified(contract_address, api_key)
        result["contract_verified"] = verified

        return result

    async def get_multi_token_analytics(
        self, addresses: list[str]
    ) -> dict[str, dict]:
        """Fetch analytics for multiple tokens sequentially (respecting rate limits).

        Args:
            addresses: List of ERC-20 contract addresses.

        Returns:
            Dict mapping address -> analytics dict.
        """
        results = {}
        for addr in addresses:
            results[addr] = await self.get_token_analytics(addr)
            # Extra delay between full token lookups (each does 2 API calls)
            await asyncio.sleep(RATE_LIMIT_DELAY)
        return results

    # ── Private API methods ───────────────────────────────────────────────────

    async def _fetch_top_holders(
        self, contract_address: str, api_key: str
    ) -> dict | None:
        """Fetch top 10 token holders and calculate concentration percentage.

        Endpoint:
            GET /v2/api?chainid=1&module=token&action=tokenholderlist
                &contractaddress={addr}&page=1&offset=10&apikey={key}

        Returns:
            {"top_holder_pct": float, "holder_count": int} or None on error.
        """
        params = {
            "chainid": "1",
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": contract_address,
            "page": "1",
            "offset": "10",
            "apikey": api_key,
        }

        data = await self.fetch_json(ETHERSCAN_V2_BASE, params=params)
        if not data:
            logger.debug(
                f"TokenAnalytics: no response for holders of {contract_address[:10]}..."
            )
            return None

        # Etherscan error responses have status "0"
        if data.get("status") == "0":
            msg = data.get("message", "") or data.get("result", "")
            logger.debug(
                f"TokenAnalytics: holder query error for {contract_address[:10]}...: {msg}"
            )
            return None

        holders = data.get("result", [])
        if not isinstance(holders, list) or not holders:
            return None

        # Calculate top holder concentration
        # Each holder has "TokenHolderQuantity" (raw token units as string)
        total_supply = 0
        top_balances = []
        for h in holders:
            try:
                balance = int(h.get("TokenHolderQuantity", "0"))
                top_balances.append(balance)
                total_supply += balance
            except (ValueError, TypeError):
                continue

        if total_supply == 0:
            return {"top_holder_pct": 0.0, "holder_count": len(holders)}

        # The top holder % is relative to total supply of all fetched holders
        # This is approximate since we only have top 10, but a useful signal
        top_1_pct = (max(top_balances) / total_supply * 100) if top_balances else 0.0

        return {
            "top_holder_pct": round(top_1_pct, 2),
            "holder_count": len(holders),
        }

    async def _check_contract_verified(
        self, contract_address: str, api_key: str
    ) -> bool | None:
        """Check if a contract is verified on Etherscan.

        Endpoint:
            GET /v2/api?chainid=1&module=contract&action=getabi
                &address={addr}&apikey={key}

        Returns:
            True if verified, False if not, None on error.
        """
        params = {
            "chainid": "1",
            "module": "contract",
            "action": "getabi",
            "address": contract_address,
            "apikey": api_key,
        }

        data = await self.fetch_json(ETHERSCAN_V2_BASE, params=params)
        if not data:
            logger.debug(
                f"TokenAnalytics: no response for ABI of {contract_address[:10]}..."
            )
            return None

        # status "1" = verified (result contains ABI JSON)
        # status "0" = not verified or error
        if data.get("status") == "1":
            return True

        result_msg = data.get("result", "")
        if "not verified" in str(result_msg).lower():
            return False

        # Could be a rate limit or other error — return None (unknown)
        logger.debug(
            f"TokenAnalytics: ABI check ambiguous for {contract_address[:10]}...: "
            f"{data.get('message', '')}"
        )
        return None


# ── Module-level convenience functions ────────────────────────────────────────

_collector: TokenAnalyticsCollector | None = None


def _get_collector() -> TokenAnalyticsCollector:
    global _collector
    if _collector is None:
        _collector = TokenAnalyticsCollector()
    return _collector


async def get_token_analytics(contract_address: str) -> dict:
    """Convenience wrapper: get analytics for a single ERC-20 token."""
    collector = _get_collector()
    try:
        return await collector.get_token_analytics(contract_address)
    except Exception as e:
        logger.error(f"get_token_analytics error: {e}", exc_info=True)
        return {
            "top_holder_pct": None,
            "contract_verified": None,
            "holder_count": None,
            "error": str(e),
        }


async def get_multi_token_analytics(addresses: list[str]) -> dict[str, dict]:
    """Convenience wrapper: get analytics for multiple tokens."""
    collector = _get_collector()
    try:
        return await collector.get_multi_token_analytics(addresses)
    except Exception as e:
        logger.error(f"get_multi_token_analytics error: {e}", exc_info=True)
        return {
            addr: {
                "top_holder_pct": None,
                "contract_verified": None,
                "holder_count": None,
                "error": str(e),
            }
            for addr in addresses
        }
