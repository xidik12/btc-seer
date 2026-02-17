"""
Arbitrage Collector — scans 10 major exchanges for cross-exchange price
discrepancies on tracked coins.

Uses ccxt (async) when available for uniform ticker fetching; falls back
to raw HTTP via BaseCollector.fetch_json for Binance if ccxt is missing.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.collectors.base import BaseCollector
from app.database import async_session, ExchangeTicker, ArbitrageOpportunity, CoinInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional ccxt import
# ---------------------------------------------------------------------------
try:
    import ccxt.async_support as ccxt

    CCXT_AVAILABLE = True
except ImportError:
    ccxt = None  # type: ignore[assignment]
    CCXT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Exchange configuration
# ---------------------------------------------------------------------------
EXCHANGE_IDS = [
    "binance",
    "coinbase",
    "kraken",
    "bybit",
    "okx",
    "kucoin",
    "gateio",
    "bitfinex",
    "htx",
    "mexc",
]

# Map coin_id (CoinGecko-style) to the typical USDT trading pair symbol
# used across most exchanges.  ccxt normalises to "BTC/USDT" format.
_COIN_SYMBOL_MAP: dict[str, str] = {
    "bitcoin": "BTC/USDT",
    "ethereum": "ETH/USDT",
    "ripple": "XRP/USDT",
    "solana": "SOL/USDT",
    "binancecoin": "BNB/USDT",
    "cardano": "ADA/USDT",
    "dogecoin": "DOGE/USDT",
    "avalanche-2": "AVAX/USDT",
    "polkadot": "DOT/USDT",
    "chainlink": "LINK/USDT",
    "matic-network": "MATIC/USDT",
    "shiba-inu": "SHIB/USDT",
    "uniswap": "UNI/USDT",
    "litecoin": "LTC/USDT",
    "cosmos": "ATOM/USDT",
    "near": "NEAR/USDT",
    "aptos": "APT/USDT",
    "arbitrum": "ARB/USDT",
    "optimism": "OP/USDT",
    "sui": "SUI/USDT",
}

# Reverse lookup: "BTC/USDT" -> "bitcoin"
_SYMBOL_COIN_MAP: dict[str, str] = {v: k for k, v in _COIN_SYMBOL_MAP.items()}

# ---------------------------------------------------------------------------
# Fee assumptions (maker + taker one side)
# ---------------------------------------------------------------------------
FEE_PER_SIDE_PCT = 0.1  # 0.1% per trade (typical maker/taker)
TOTAL_FEES_PCT = FEE_PER_SIDE_PCT * 2  # buy side + sell side
ACTIONABLE_THRESHOLD_PCT = 0.3  # net profit must exceed this


class ArbitrageCollector(BaseCollector):
    """Scans multiple exchanges for arbitrage opportunities on tracked coins."""

    def __init__(self):
        super().__init__()
        self._exchanges: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # ccxt exchange lifecycle
    # ------------------------------------------------------------------
    def _get_exchange(self, exchange_id: str) -> Any:
        """Lazily create a ccxt async exchange instance."""
        if not CCXT_AVAILABLE:
            return None
        if exchange_id not in self._exchanges:
            try:
                exchange_cls = getattr(ccxt, exchange_id, None)
                if exchange_cls is None:
                    logger.warning(f"ccxt has no exchange class for '{exchange_id}'")
                    return None
                self._exchanges[exchange_id] = exchange_cls({
                    "enableRateLimit": True,
                    "timeout": 20000,
                })
            except Exception as e:
                logger.error(f"Failed to create ccxt exchange '{exchange_id}': {e}")
                return None
        return self._exchanges[exchange_id]

    async def close(self):
        """Close all ccxt exchange sessions, then the base aiohttp session."""
        for ex in self._exchanges.values():
            try:
                await ex.close()
            except Exception:
                pass
        self._exchanges.clear()
        await super().close()

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------
    async def _fetch_tickers_ccxt(self, exchange_id: str) -> dict[str, dict] | None:
        """Fetch all tickers from an exchange via ccxt.

        Returns a dict keyed by normalised symbol, e.g.::

            {"BTC/USDT": {"bid": 97000.0, "ask": 97010.0, ...}, ...}
        """
        ex = self._get_exchange(exchange_id)
        if ex is None:
            return None
        try:
            tickers = await ex.fetch_tickers()
            return tickers
        except Exception as e:
            logger.warning(f"ccxt fetch_tickers failed for {exchange_id}: {e}")
            return None

    async def _fetch_tickers_binance_raw(self) -> dict[str, dict] | None:
        """Fallback: fetch Binance book tickers using raw HTTP (no ccxt)."""
        url = "https://api.binance.com/api/v3/ticker/bookTicker"
        data = await self.fetch_json(url)
        if not data:
            return None
        tickers: dict[str, dict] = {}
        for item in data:
            raw_symbol = item.get("symbol", "")
            # Convert BTCUSDT -> BTC/USDT
            if raw_symbol.endswith("USDT"):
                base = raw_symbol[: -4]
                symbol = f"{base}/USDT"
                tickers[symbol] = {
                    "bid": float(item.get("bidPrice", 0)),
                    "ask": float(item.get("askPrice", 0)),
                    "last": None,  # bookTicker doesn't return last
                    "baseVolume": None,
                }
        return tickers

    async def _fetch_exchange_tickers(self, exchange_id: str) -> dict[str, dict] | None:
        """Fetch tickers for one exchange, preferring ccxt, with Binance raw
        fallback when ccxt is unavailable."""
        if CCXT_AVAILABLE:
            return await self._fetch_tickers_ccxt(exchange_id)
        # Without ccxt only Binance raw HTTP is supported
        if exchange_id == "binance":
            return await self._fetch_tickers_binance_raw()
        return None

    # ------------------------------------------------------------------
    # Main collect
    # ------------------------------------------------------------------
    async def collect(self) -> dict:
        """Collect tickers from all exchanges, store ExchangeTicker rows,
        compute arbitrage, and store ArbitrageOpportunity rows.

        Returns a summary dict.
        """
        now = datetime.utcnow()

        # Determine which symbols we care about
        symbols_of_interest = set(_SYMBOL_COIN_MAP.keys())

        # Fetch tickers from all exchanges concurrently
        tasks = {
            eid: self._fetch_exchange_tickers(eid)
            for eid in EXCHANGE_IDS
        }
        results: dict[str, dict[str, dict] | None] = {}
        for eid, coro in tasks.items():
            try:
                results[eid] = await coro
            except Exception as e:
                logger.error(f"Unexpected error fetching {eid}: {e}")
                results[eid] = None

        # ------------------------------------------------------------------
        # 1. Collect per-coin, per-exchange data and persist ExchangeTicker
        # ------------------------------------------------------------------
        # Structure: {coin_id: {exchange: {"bid": ..., "ask": ..., ...}}}
        coin_exchange_data: dict[str, dict[str, dict]] = {}
        ticker_rows: list[ExchangeTicker] = []

        for exchange_id, tickers in results.items():
            if not tickers:
                continue
            for symbol in symbols_of_interest:
                if symbol not in tickers:
                    continue
                t = tickers[symbol]
                coin_id = _SYMBOL_COIN_MAP[symbol]

                bid = _safe_float(t.get("bid"))
                ask = _safe_float(t.get("ask"))
                last = _safe_float(t.get("last"))
                volume = _safe_float(t.get("baseVolume"))

                # Skip if no usable price data
                if bid is None and ask is None and last is None:
                    continue

                coin_exchange_data.setdefault(coin_id, {})[exchange_id] = {
                    "bid": bid,
                    "ask": ask,
                    "last": last,
                    "volume_24h": volume,
                }

                ticker_rows.append(ExchangeTicker(
                    coin_id=coin_id,
                    exchange=exchange_id,
                    bid=bid,
                    ask=ask,
                    last=last,
                    volume_24h=volume,
                    timestamp=now,
                ))

        # Persist tickers
        tickers_saved = 0
        if ticker_rows:
            try:
                async with async_session() as session:
                    session.add_all(ticker_rows)
                    await session.commit()
                    tickers_saved = len(ticker_rows)
            except Exception as e:
                logger.error(f"Failed to save ExchangeTicker rows: {e}")

        # ------------------------------------------------------------------
        # 2. Compute arbitrage opportunities per coin
        # ------------------------------------------------------------------
        opportunities: list[ArbitrageOpportunity] = []

        for coin_id, exchanges in coin_exchange_data.items():
            opp = self._compute_arbitrage(coin_id, exchanges, now)
            if opp is not None:
                opportunities.append(opp)

        # Persist opportunities
        opps_saved = 0
        if opportunities:
            try:
                async with async_session() as session:
                    session.add_all(opportunities)
                    await session.commit()
                    opps_saved = len(opportunities)
            except Exception as e:
                logger.error(f"Failed to save ArbitrageOpportunity rows: {e}")

        actionable = sum(1 for o in opportunities if o.is_actionable)
        logger.info(
            f"Arbitrage scan complete: {tickers_saved} tickers, "
            f"{opps_saved} opportunities ({actionable} actionable)"
        )

        return {
            "tickers_saved": tickers_saved,
            "opportunities": opps_saved,
            "actionable": actionable,
            "timestamp": now.isoformat(),
        }

    # ------------------------------------------------------------------
    # Arbitrage calculation
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_arbitrage(
        coin_id: str,
        exchanges: dict[str, dict],
        now: datetime,
    ) -> ArbitrageOpportunity | None:
        """Find the best buy (lowest ask) and best sell (highest bid) across
        exchanges for a single coin.

        Returns an ArbitrageOpportunity row or None if insufficient data.
        """
        best_ask: float | None = None
        best_ask_exchange: str | None = None
        best_bid: float | None = None
        best_bid_exchange: str | None = None

        # Build exchange_prices JSON snapshot
        exchange_prices: dict[str, dict] = {}

        for exchange_id, data in exchanges.items():
            bid = data.get("bid")
            ask = data.get("ask")
            last = data.get("last")

            exchange_prices[exchange_id] = {
                "bid": bid,
                "ask": ask,
                "last": last,
                "volume_24h": data.get("volume_24h"),
            }

            # Use ask for buying (we pay the ask price)
            if ask is not None and ask > 0:
                if best_ask is None or ask < best_ask:
                    best_ask = ask
                    best_ask_exchange = exchange_id

            # Use bid for selling (we receive the bid price)
            if bid is not None and bid > 0:
                if best_bid is None or bid > best_bid:
                    best_bid = bid
                    best_bid_exchange = exchange_id

        # Need both sides
        if (
            best_ask is None
            or best_bid is None
            or best_ask_exchange is None
            or best_bid_exchange is None
        ):
            return None

        # Don't count same-exchange "arb"
        if best_ask_exchange == best_bid_exchange:
            # Still store the opportunity for record-keeping but spread is
            # effectively zero.  We could skip it, but let's keep it for
            # the history endpoint.
            pass

        spread_pct = (best_bid - best_ask) / best_ask * 100 if best_ask > 0 else 0.0
        net_profit_pct = spread_pct - TOTAL_FEES_PCT
        is_actionable = (
            net_profit_pct > ACTIONABLE_THRESHOLD_PCT
            and best_ask_exchange != best_bid_exchange
        )

        return ArbitrageOpportunity(
            coin_id=coin_id,
            timestamp=now,
            buy_exchange=best_ask_exchange,
            buy_price=best_ask,
            sell_exchange=best_bid_exchange,
            sell_price=best_bid,
            spread_pct=round(spread_pct, 4),
            net_profit_pct=round(net_profit_pct, 4),
            estimated_fees_pct=TOTAL_FEES_PCT,
            is_actionable=is_actionable,
            exchange_prices=exchange_prices,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _safe_float(val: Any) -> float | None:
    """Convert a value to float or return None."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Scheduled job entry-point
# ---------------------------------------------------------------------------
async def scan_arbitrage():
    """Scheduled job: scan for arbitrage opportunities every 30 seconds."""
    collector = ArbitrageCollector()
    try:
        await collector.collect()
    except Exception as e:
        logger.error(f"scan_arbitrage error: {e}", exc_info=True)
    finally:
        await collector.close()
