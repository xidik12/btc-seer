__all__ = [
    "MarketCollector",
    "NewsCollector",
    "FearGreedCollector",
    "MacroCollector",
    "OnChainCollector",
    "RedditCollector",
    "BinanceNewsCollector",
    "InfluencerCollector",
    "CoinCollector",
    "CoinSearchService",
    "ETFCollector",
    "ExchangeFlowCollector",
    "DerivativesExtendedCollector",
    "StablecoinCollector",
    "WhaleCollector",
    "EthWhaleCollector",
    "SolWhaleCollector",
    "EthOnChainCollector",
    "CryptoPanicV2Collector",
    "NewListingCollector",
    "DexScannerCollector",
    "MemecoinCollector",
    "TokenAnalyticsCollector",
]


_IMPORTS = {
    "MarketCollector": "app.collectors.market",
    "NewsCollector": "app.collectors.news",
    "FearGreedCollector": "app.collectors.fear_greed",
    "MacroCollector": "app.collectors.macro",
    "OnChainCollector": "app.collectors.onchain",
    "RedditCollector": "app.collectors.reddit",
    "BinanceNewsCollector": "app.collectors.binance_news",
    "InfluencerCollector": "app.collectors.influencers",
    "CoinCollector": "app.collectors.coins",
    "CoinSearchService": "app.collectors.coin_search",
    "ETFCollector": "app.collectors.etf",
    "ExchangeFlowCollector": "app.collectors.exchange_flows",
    "DerivativesExtendedCollector": "app.collectors.derivatives_extended",
    "StablecoinCollector": "app.collectors.stablecoin",
    "WhaleCollector": "app.collectors.whale",
    "EthWhaleCollector": "app.collectors.eth_whale",
    "SolWhaleCollector": "app.collectors.sol_whale",
    "EthOnChainCollector": "app.collectors.eth_onchain",
    "CryptoPanicV2Collector": "app.collectors.cryptopanic_v2",
    "NewListingCollector": "app.collectors.new_listings",
    "DexScannerCollector": "app.collectors.dex_scanner",
    "MemecoinCollector": "app.collectors.memecoin",
    "TokenAnalyticsCollector": "app.collectors.token_analytics",
}


def __getattr__(name):
    if name in _IMPORTS:
        import importlib
        module = importlib.import_module(_IMPORTS[name])
        attr = getattr(module, name)
        globals()[name] = attr  # Cache so __getattr__ is only called once per name
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
