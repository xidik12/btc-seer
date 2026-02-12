import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Known exchange addresses (expandable)
KNOWN_EXCHANGES = {
    # Binance
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": "Binance",
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": "Binance",
    "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb": "Binance",
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": "Binance",
    "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j": "Binance",
    # Coinbase
    "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS": "Coinbase",
    "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh": "Coinbase",
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B": "Coinbase",
    # Kraken
    "3AfwmhssDGJYCzFNhUf79sMFfbXsBBymqq": "Kraken",
    "bc1qx9t2l3pyny2spqpqlye8svce70nppwtaxwdrp4": "Kraken",
    # Bitfinex
    "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r": "Bitfinex",
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": "Bitfinex",
    # Gemini
    "3P3QsMVK89JBNqZQv5zMAKG8FK3kJM4rjt": "Gemini",
    # Huobi/HTX
    "1HckjUpRGcrrRAtFaaCAUaGjsPSPLYdkuR": "Huobi",
    # OKX
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a": "OKX",
}

# Amount thresholds for severity (BTC -> severity)
SEVERITY_THRESHOLDS = [
    (10000, 10),
    (5000, 9),
    (2000, 8),
    (1000, 7),
    (500, 6),
    (200, 5),
    (100, 4),
]


def calculate_severity(amount_btc: float) -> int:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if amount_btc >= threshold:
            return severity
    return 3


class WhaleCollector(BaseCollector):
    """Collects large BTC transactions (>100 BTC) from Blockchair API."""

    # 100 BTC in satoshis = 10,000,000,000
    BLOCKCHAIR_TX_URL = "https://api.blockchair.com/bitcoin/transactions"

    def __init__(self):
        super().__init__()
        self._last_seen_hashes: set = set()

    async def collect(self) -> dict:
        """Collect large BTC transactions from Blockchair."""
        params = {
            "q": "output_total(10000000000..)",
            "s": "time(desc)",
            "limit": "10",
        }

        data = await self.fetch_json(self.BLOCKCHAIR_TX_URL, params=params)
        if not data:
            return {"transactions": [], "count": 0}

        raw_txs = data.get("data", [])
        if not raw_txs:
            return {"transactions": [], "count": 0}

        transactions = []
        new_hashes = set()

        for tx in raw_txs:
            tx_hash = tx.get("hash", "")
            if not tx_hash:
                continue

            new_hashes.add(tx_hash)

            # Skip already seen
            if tx_hash in self._last_seen_hashes:
                continue

            # Amount in satoshis -> BTC
            output_total = tx.get("output_total", 0)
            amount_btc = output_total / 1e8

            if amount_btc < 100:
                continue

            # Classify direction using known exchange addresses
            direction, from_entity, to_entity = self._classify_transaction(tx)

            transactions.append({
                "tx_hash": tx_hash,
                "amount_btc": round(amount_btc, 4),
                "timestamp": tx.get("time", ""),
                "direction": direction,
                "from_entity": from_entity,
                "to_entity": to_entity,
                "severity": calculate_severity(amount_btc),
                "raw_data": tx,
            })

        # Update seen hashes (keep only current batch to avoid memory bloat)
        self._last_seen_hashes = new_hashes

        logger.info(f"Whale collector: {len(transactions)} new large txs found")
        return {"transactions": transactions, "count": len(transactions)}

    def _classify_transaction(self, tx: dict) -> tuple[str, str, str]:
        """Classify transaction direction based on known exchange addresses."""
        input_addrs = tx.get("input_addresses", []) or []
        output_addrs = tx.get("output_addresses", []) or []

        from_exchange = None
        to_exchange = None

        # Check inputs (sender)
        if isinstance(input_addrs, list):
            for addr in input_addrs:
                if addr in KNOWN_EXCHANGES:
                    from_exchange = KNOWN_EXCHANGES[addr]
                    break

        # Check outputs (receiver)
        if isinstance(output_addrs, list):
            for addr in output_addrs:
                if addr in KNOWN_EXCHANGES:
                    to_exchange = KNOWN_EXCHANGES[addr]
                    break

        from_entity = from_exchange or "unknown"
        to_entity = to_exchange or "unknown"

        if from_exchange and not to_exchange:
            direction = "exchange_out"  # Withdrawal from exchange (bullish)
        elif not from_exchange and to_exchange:
            direction = "exchange_in"  # Deposit to exchange (bearish)
        elif from_exchange and to_exchange:
            direction = "exchange_in"  # Inter-exchange transfer, treat as neutral/in
        else:
            direction = "unknown"

        return direction, from_entity, to_entity
