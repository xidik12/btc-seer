"""Shared lazy-loaded singletons for scheduler jobs.

Avoids duplicate instances across domain_ml.py and domain_market.py.
Each getter imports on first call to defer heavy module loading from startup.
"""

from functools import lru_cache


@lru_cache(maxsize=1)
def get_market_collector():
    from app.collectors.market import MarketCollector
    return MarketCollector()


@lru_cache(maxsize=1)
def get_fear_greed_collector():
    from app.collectors.fear_greed import FearGreedCollector
    return FearGreedCollector()


@lru_cache(maxsize=1)
def get_macro_collector():
    from app.collectors.macro import MacroCollector
    return MacroCollector()


@lru_cache(maxsize=1)
def get_onchain_collector():
    from app.collectors.onchain import OnChainCollector
    return OnChainCollector()


@lru_cache(maxsize=1)
def get_feature_builder():
    from app.features.builder import FeatureBuilder
    return FeatureBuilder()


@lru_cache(maxsize=1)
def get_etf_collector():
    from app.collectors.etf import ETFCollector
    return ETFCollector()


@lru_cache(maxsize=1)
def get_exchange_flow_collector():
    from app.collectors.exchange_flows import ExchangeFlowCollector
    return ExchangeFlowCollector()


@lru_cache(maxsize=1)
def get_derivatives_extended_collector():
    from app.collectors.derivatives_extended import DerivativesExtendedCollector
    return DerivativesExtendedCollector()


@lru_cache(maxsize=1)
def get_stablecoin_collector():
    from app.collectors.stablecoin import StablecoinCollector
    return StablecoinCollector()


@lru_cache(maxsize=1)
def get_signal_generator():
    from app.signals.generator import SignalGenerator
    return SignalGenerator()


@lru_cache(maxsize=1)
def get_event_pattern_matcher():
    from app.models.event_memory import EventPatternMatcher
    return EventPatternMatcher()


@lru_cache(maxsize=1)
def get_ensemble():
    from app.models.ensemble import EnsemblePredictor
    from app.config import settings
    return EnsemblePredictor(
        model_dir=settings.model_dir,
        num_features=len(get_feature_builder().ALL_FEATURES),
    )
