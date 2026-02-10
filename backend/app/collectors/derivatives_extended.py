"""Extended derivatives data collector.

Sources:
- Binance Futures API (liquidations, leverage, long/short)
- Deribit public API (DVOL implied volatility index)
- CoinGlass public API (aggregated liquidations)
"""
import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class DerivativesExtendedCollector(BaseCollector):
    """Collects extended derivatives data beyond basic funding rate."""

    BINANCE_TAKER_VOLUME_URL = "https://fapi.binance.com/futures/data/takerlongshortRatio"
    DERIBIT_DVOL_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
    COINGLASS_LIQUIDATION_URL = "https://open-api.coinglass.com/public/v2/liquidation_history"

    async def collect(self) -> dict:
        """Collect extended derivatives metrics."""
        result = {
            # Binance extended
            "long_short_ratio": 1.0,          # Global long/short account ratio
            "long_account_pct": 0.5,          # % of accounts long
            "short_account_pct": 0.5,         # % of accounts short
            "top_trader_long_short": 1.0,     # Top trader position ratio
            "top_long_pct": 0.5,
            "top_short_pct": 0.5,
            "taker_buy_sell_ratio": 1.0,      # Taker buy/sell volume ratio
            # Deribit DVOL
            "dvol": 0.0,                      # BTC implied volatility index
            # Liquidations
            "liquidation_24h_usd": 0.0,       # Total liquidations in 24h
            "long_liquidation_24h": 0.0,      # Long liquidations
            "short_liquidation_24h": 0.0,     # Short liquidations
            # Derived
            "estimated_leverage_ratio": 0.0,  # OI / exchange reserve
            "timestamp": self.now().isoformat(),
        }

        # Fetch all sources
        ls_data = await self._get_long_short()
        if ls_data:
            result.update(ls_data)

        taker_data = await self._get_taker_volume()
        if taker_data:
            result.update(taker_data)

        dvol_data = await self._get_dvol()
        if dvol_data:
            result.update(dvol_data)

        liq_data = await self._get_liquidations()
        if liq_data:
            result.update(liq_data)

        return result

    async def _get_long_short(self) -> dict | None:
        """Get global and top trader long/short ratios from Binance."""
        try:
            # Global long/short
            data = await self.fetch_json(
                "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
                params={"symbol": "BTCUSDT", "period": "1h", "limit": 1},
            )
            result = {}
            if data and len(data) > 0:
                latest = data[0]
                result["long_short_ratio"] = float(latest.get("longShortRatio", 1.0))
                result["long_account_pct"] = float(latest.get("longAccount", 0.5))
                result["short_account_pct"] = float(latest.get("shortAccount", 0.5))

            # Top trader position ratio
            data = await self.fetch_json(
                "https://fapi.binance.com/futures/data/topLongShortPositionRatio",
                params={"symbol": "BTCUSDT", "period": "1h", "limit": 1},
            )
            if data and len(data) > 0:
                latest = data[0]
                result["top_trader_long_short"] = float(latest.get("longShortRatio", 1.0))
                result["top_long_pct"] = float(latest.get("longAccount", 0.5))
                result["top_short_pct"] = float(latest.get("shortAccount", 0.5))

            return result if result else None
        except Exception as e:
            logger.debug(f"Long/short ratio error: {e}")
            return None

    async def _get_taker_volume(self) -> dict | None:
        """Get taker buy/sell volume ratio."""
        try:
            data = await self.fetch_json(
                self.BINANCE_TAKER_VOLUME_URL,
                params={"symbol": "BTCUSDT", "period": "1h", "limit": 1},
            )
            if data and len(data) > 0:
                latest = data[0]
                return {
                    "taker_buy_sell_ratio": float(latest.get("buySellRatio", 1.0)),
                }
        except Exception as e:
            logger.debug(f"Taker volume error: {e}")
        return None

    async def _get_dvol(self) -> dict | None:
        """Get Deribit DVOL (BTC implied volatility index)."""
        try:
            data = await self.fetch_json(
                self.DERIBIT_DVOL_URL,
                params={
                    "currency": "BTC",
                    "resolution": "1",  # 1-hour resolution
                    "end_timestamp": int(self.now().timestamp() * 1000),
                    "start_timestamp": int(self.now().timestamp() * 1000) - 3600000,
                },
            )
            if data and "result" in data:
                records = data["result"].get("data", [])
                if records:
                    # Last record: [timestamp, open, high, low, close]
                    last = records[-1]
                    return {"dvol": float(last[4]) if len(last) >= 5 else 0.0}
        except Exception as e:
            logger.debug(f"DVOL error: {e}")
        return None

    async def _get_liquidations(self) -> dict | None:
        """Get aggregated liquidation data."""
        try:
            data = await self.fetch_json(
                self.COINGLASS_LIQUIDATION_URL,
                params={"symbol": "BTC", "time_type": 2},  # time_type 2 = 24h
            )
            if data and data.get("code") == "0" and "data" in data:
                d = data["data"]
                return {
                    "liquidation_24h_usd": float(d.get("total", 0) or 0),
                    "long_liquidation_24h": float(d.get("totalLong", 0) or 0),
                    "short_liquidation_24h": float(d.get("totalShort", 0) or 0),
                }
        except Exception as e:
            logger.debug(f"Liquidation data error: {e}")
        return None
