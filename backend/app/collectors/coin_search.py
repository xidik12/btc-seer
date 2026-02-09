import json
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.database import async_session, CoinReport

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Chain detection by address format
CHAIN_PLATFORMS = {
    "ethereum": "ethereum",
    "bsc": "binance-smart-chain",
    "polygon": "polygon-pos",
    "arbitrum": "arbitrum-one",
    "base": "base",
}


def detect_chain(address: str) -> str | None:
    """Auto-detect blockchain from address format."""
    address = address.strip()
    # 0x + 40 hex chars → EVM chain (Ethereum, BSC, Polygon, etc.)
    if re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return "ethereum"
    # Base58, 32-44 chars → Solana
    if re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
        return "solana"
    return None


class CoinSearchService(BaseCollector):
    """Search coins by name/symbol or contract address, generate reports."""

    async def collect(self) -> dict:
        return {}

    async def search_by_name(self, query: str) -> list:
        """Search coins by name or symbol via CoinGecko."""
        url = f"{COINGECKO_BASE}/search"
        data = await self.fetch_json(url, params={"query": query})
        if not data or "coins" not in data:
            return []

        results = []
        for coin in data["coins"][:10]:
            results.append({
                "id": coin.get("id"),
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "thumb": coin.get("thumb"),
                "large": coin.get("large"),
                "market_cap_rank": coin.get("market_cap_rank"),
            })
        return results

    async def search_by_address(self, address: str) -> dict | None:
        """Look up a token by its contract address."""
        chain = detect_chain(address)
        if not chain:
            return {"error": "Could not detect chain from address format"}

        if chain == "solana":
            platform = "solana"
        else:
            # Try EVM platforms in order
            for chain_name, platform_id in CHAIN_PLATFORMS.items():
                result = await self._fetch_contract(platform_id, address)
                if result:
                    result["chain"] = chain_name
                    return result
            return {"error": f"Token not found on any EVM chain for address {address}"}

        result = await self._fetch_contract(platform, address)
        if result:
            result["chain"] = chain
            return result
        return {"error": f"Token not found on {chain} for address {address}"}

    async def _fetch_contract(self, platform: str, address: str) -> dict | None:
        """Fetch token info by contract address from CoinGecko."""
        url = f"{COINGECKO_BASE}/coins/{platform}/contract/{address.lower()}"
        data = await self.fetch_json(url)
        if not data or "error" in data:
            return None

        market = data.get("market_data", {})
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name"),
            "image": data.get("image", {}).get("large"),
            "price_usd": market.get("current_price", {}).get("usd"),
            "market_cap": market.get("market_cap", {}).get("usd"),
            "volume_24h": market.get("total_volume", {}).get("usd"),
            "change_24h": market.get("price_change_percentage_24h"),
            "change_7d": market.get("price_change_percentage_7d"),
            "contract_address": address,
            "platform": platform,
        }

    async def get_coin_detail(self, coin_id: str) -> dict | None:
        """Get comprehensive coin data from CoinGecko."""
        url = f"{COINGECKO_BASE}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        data = await self.fetch_json(url, params=params)
        if not data or "error" in data:
            return None

        market = data.get("market_data", {})
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name"),
            "image": data.get("image", {}).get("large"),
            "description": (data.get("description", {}).get("en") or "")[:500],
            "market_data": {
                "price_usd": market.get("current_price", {}).get("usd"),
                "market_cap": market.get("market_cap", {}).get("usd"),
                "market_cap_rank": market.get("market_cap_rank"),
                "volume_24h": market.get("total_volume", {}).get("usd"),
                "change_1h": market.get("price_change_percentage_1h_in_currency", {}).get("usd"),
                "change_24h": market.get("price_change_percentage_24h"),
                "change_7d": market.get("price_change_percentage_7d"),
                "change_30d": market.get("price_change_percentage_30d"),
                "ath": market.get("ath", {}).get("usd"),
                "ath_date": market.get("ath_date", {}).get("usd"),
                "ath_change_pct": market.get("ath_change_percentage", {}).get("usd"),
                "atl": market.get("atl", {}).get("usd"),
                "atl_date": market.get("atl_date", {}).get("usd"),
                "atl_change_pct": market.get("atl_change_percentage", {}).get("usd"),
                "circulating_supply": market.get("circulating_supply"),
                "total_supply": market.get("total_supply"),
                "max_supply": market.get("max_supply"),
                "fully_diluted_valuation": market.get("fully_diluted_valuation", {}).get("usd"),
            },
            "categories": data.get("categories", []),
            "genesis_date": data.get("genesis_date"),
            "platforms": data.get("platforms", {}),
        }

    async def get_chart_data(self, coin_id: str, days: int = 7) -> list:
        """Get price chart data for a coin."""
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": str(days)}
        data = await self.fetch_json(url, params=params)
        if not data or "prices" not in data:
            return []

        return [
            {"timestamp": int(p[0]), "price": p[1]}
            for p in data["prices"]
        ]

    async def generate_report(self, address: str) -> dict:
        """Generate or fetch cached report for a contract address."""
        # Check cache (1h TTL)
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(CoinReport)
                .where(CoinReport.address == address.lower())
                .where(CoinReport.created_at >= cutoff)
                .limit(1)
            )
            cached = result.scalar_one_or_none()
            if cached and cached.report_data:
                return json.loads(cached.report_data)

        # Fetch fresh data
        token_info = await self.search_by_address(address)
        if not token_info or "error" in token_info:
            return token_info or {"error": "Token not found"}

        # Get full detail if we have an ID
        detail = None
        if token_info.get("id"):
            detail = await self.get_coin_detail(token_info["id"])

        report = {
            "address": address,
            "chain": token_info.get("chain", "unknown"),
            "basic": {
                "name": token_info.get("name"),
                "symbol": token_info.get("symbol"),
                "image": token_info.get("image"),
            },
            "market": {
                "price_usd": token_info.get("price_usd"),
                "market_cap": token_info.get("market_cap"),
                "volume_24h": token_info.get("volume_24h"),
                "change_24h": token_info.get("change_24h"),
                "change_7d": token_info.get("change_7d"),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        if detail:
            md = detail.get("market_data", {})
            report["detail"] = {
                "market_cap_rank": md.get("market_cap_rank"),
                "ath": md.get("ath"),
                "ath_date": md.get("ath_date"),
                "ath_change_pct": md.get("ath_change_pct"),
                "atl": md.get("atl"),
                "atl_date": md.get("atl_date"),
                "atl_change_pct": md.get("atl_change_pct"),
                "circulating_supply": md.get("circulating_supply"),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
                "fully_diluted_valuation": md.get("fully_diluted_valuation"),
                "change_30d": md.get("change_30d"),
            }
            report["categories"] = detail.get("categories", [])
            report["description"] = detail.get("description", "")

            # Risk scoring
            mcap = token_info.get("market_cap") or 0
            vol = token_info.get("volume_24h") or 0
            vol_mcap_ratio = (vol / mcap) if mcap > 0 else 0

            if mcap >= 10_000_000_000:
                tier = "Large Cap"
                risk = "Low"
            elif mcap >= 1_000_000_000:
                tier = "Mid Cap"
                risk = "Medium"
            elif mcap >= 100_000_000:
                tier = "Small Cap"
                risk = "High"
            else:
                tier = "Micro Cap"
                risk = "Very High"

            report["risk"] = {
                "tier": tier,
                "risk_level": risk,
                "volume_mcap_ratio": round(vol_mcap_ratio, 4),
            }

        # Cache the report
        async with async_session() as session:
            session.add(CoinReport(
                address=address.lower(),
                chain=token_info.get("chain", "unknown"),
                coin_id=token_info.get("id"),
                symbol=token_info.get("symbol"),
                name=token_info.get("name"),
                report_data=json.dumps(report),
            ))
            await session.commit()

        return report
