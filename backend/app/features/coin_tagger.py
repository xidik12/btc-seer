import logging
import re

logger = logging.getLogger(__name__)

# Coin aliases: maps coin_id → set of keywords to match in text
COIN_ALIASES = {
    "bitcoin": {"bitcoin", "btc", "satoshi", "sats", "lightning network"},
    "ethereum": {"ethereum", "eth", "ether", "vitalik", "erc-20", "erc20"},
    "ripple": {"xrp", "ripple", "ripplenet"},
    "solana": {"solana", "sol"},
    "binancecoin": {"bnb", "binance coin", "binance smart chain", "bsc"},
    "cardano": {"cardano", "ada"},
    "dogecoin": {"dogecoin", "doge", "elon musk doge"},
    "avalanche-2": {"avalanche", "avax"},
    "polkadot": {"polkadot", "dot", "parachain"},
    "chainlink": {"chainlink", "link", "oracle network"},
    "matic-network": {"polygon", "matic", "pol"},
    "shiba-inu": {"shiba inu", "shib", "shiba"},
    "uniswap": {"uniswap", "uni"},
    "litecoin": {"litecoin", "ltc"},
    "cosmos": {"cosmos", "atom", "ibc"},
    "near": {"near protocol", "near"},
    "aptos": {"aptos", "apt"},
    "arbitrum": {"arbitrum", "arb"},
    "optimism": {"optimism", " op "},  # space-bounded to avoid matching "operation" etc.
    "sui": {"sui", "sui network"},
}

# Symbols that are too short or ambiguous to match standalone (require context)
_AMBIGUOUS = {"sol", "dot", "link", "uni", "ada", "near", "apt", "arb", "op", "sui", "atom"}

# Pre-compile regex patterns for each coin
_COIN_PATTERNS: dict[str, re.Pattern] = {}
for _coin_id, _aliases in COIN_ALIASES.items():
    # Build pattern: word-boundary match for each alias
    parts = []
    for alias in _aliases:
        alias_clean = alias.strip()
        if alias_clean.lower() in _AMBIGUOUS and len(alias_clean) <= 4:
            # For short ambiguous tokens, require uppercase or $ prefix for exact match
            parts.append(rf'(?:\$|(?<=\s)){re.escape(alias_clean)}(?=\s|$|[.,!?;:\)])')
        else:
            parts.append(rf'\b{re.escape(alias_clean)}\b')
    _COIN_PATTERNS[_coin_id] = re.compile("|".join(parts), re.IGNORECASE)


class CoinTagger:
    """Tags text with relevant coin IDs based on keyword matching."""

    @staticmethod
    def tag_text(text: str) -> list[str]:
        """Return list of coin_ids mentioned in the text."""
        if not text:
            return []

        matched = []
        text_lower = f" {text} "  # pad with spaces for boundary matching

        for coin_id, pattern in _COIN_PATTERNS.items():
            if pattern.search(text_lower):
                matched.append(coin_id)

        return matched

    @staticmethod
    def tag_primary(text: str) -> str | None:
        """Return the single most likely coin_id for the text, or None."""
        matches = CoinTagger.tag_text(text)
        if not matches:
            return None
        # If BTC is mentioned alongside others, prefer the non-BTC coin
        # (since most crypto news mentions BTC as context)
        if len(matches) > 1 and "bitcoin" in matches:
            non_btc = [m for m in matches if m != "bitcoin"]
            if non_btc:
                return non_btc[0]
        return matches[0]
