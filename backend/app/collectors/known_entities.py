"""Known Bitcoin entity addresses — exchanges, institutions, government, individuals.

This is a static lookup table mapping known Bitcoin addresses to their entity info.
Used by WhaleCollector to label whale transactions with entity names.
"""

# fmt: off
KNOWN_ENTITIES: dict[str, dict] = {
    # ─── Binance ───
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "bc1qnkf5ykhsvpfnl45v2urzakrtalcahsvl2xdgs4": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "12ib7dApVFvg82TXKBMg2MBn1jcvPH4W5U": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": {"name": "Binance", "type": "exchange", "wallet": "cold"},

    # ─── Coinbase ───
    "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qx9t2l3pyny2spqpqlye8svce70nppwtaxwdrp4": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh": {"name": "Coinbase", "type": "exchange", "wallet": "hot"},
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "395xEhPMXfiSumHdsuCEjM33PCkJdg8vkF": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "1FzWLkAahHooV3kzTgyx6qsXoRDrBsrACw": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1q7cyrfmck2ffu2ud3rn5l5a8yv6f0chkp0zpemf": {"name": "Coinbase", "type": "exchange", "wallet": "hot"},
    "3JEmL7GSHWEH5bsNeva25eMRH2QBHFEJN5": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},

    # ─── Bitfinex ───
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r": {"name": "Bitfinex", "type": "exchange", "wallet": "hot"},
    "1Kr6QSydW9bFQG1mXiPNNu6WpJGmUa9i1g": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "3JZbTR6Rs1gBM5AkDW3uErzVRTKzJqeqZw": {"name": "Bitfinex", "type": "exchange", "wallet": "hot"},

    # ─── Kraken ───
    "3AfwmhssDGJYCzFNhUf79sMFfbXsBBymqq": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "bc1q2s3rjwvam9dt2ftt4sqxqjf3twav0gdx0k0q2etjd8w8ll5jp5fs70wlsq": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "3AddGYecuW95sGq7Px2S6g4v6d2mfHRzBG": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "bc1qr4dl5wa7kl8yu792dceg9z5knl2gkn220lk7a9": {"name": "Kraken", "type": "exchange", "wallet": "hot"},

    # ─── Bitstamp ───
    "3P3QsMVK89JBNqZQv5zMAKG8FK3kJM4rjt": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},
    "3BiKLKfnKLFap6MrR7E7gYmDi9LgHNMXN2": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},

    # ─── Gemini ───
    "3P3QsMVK89JBNqZQv5zMAKG8FK3kJM4rjt": {"name": "Gemini", "type": "exchange", "wallet": "cold"},
    "3Mn8iAXfEpLqCrHzJsG1H4gkTD5oVFaFNP": {"name": "Gemini", "type": "exchange", "wallet": "cold"},

    # ─── Huobi/HTX ───
    "1HckjUpRGcrrRAtFaaCAUaGjsPSPLYdkuR": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "1LAnF8h3qMGx3TSwNUHVneBZUEpwE4gu3D": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "14cNbWkBVgaJ5Lb4rKzXDQjNuQVwb7Wke1": {"name": "Huobi", "type": "exchange", "wallet": "hot"},

    # ─── OKX ───
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "1FDBr8xNfxaaon1jEHUuNCjd6LXeGjRpg2": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "bc1q2x3kca65mnr4dchacxwpyh6aaxjdgwv3hjdny2": {"name": "OKX", "type": "exchange", "wallet": "hot"},

    # ─── Bybit ───
    "bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfl6tyf": {"name": "Bybit", "type": "exchange", "wallet": "cold"},

    # ─── Bitget ───
    "bc1qm4hpful3vnfpqjmye6tmqvpnglksquv3m8p78r": {"name": "Bitget", "type": "exchange", "wallet": "cold"},

    # ─── KuCoin ───
    "bc1qnypq80rs6325x9zr09yvsqveam39jff23dqxrg": {"name": "KuCoin", "type": "exchange", "wallet": "hot"},

    # ─── Gate.io ───
    "3HN13KSim4gVtDZVFNYpSR7VJZD9JzgFGi": {"name": "Gate.io", "type": "exchange", "wallet": "cold"},

    # ─── Crypto.com ───
    "bc1qr4dl5wa7kl8yu792dceg9z5knl2gkn220lk7a9": {"name": "Crypto.com", "type": "exchange", "wallet": "cold"},

    # ─── Robinhood ───
    "bc1qfu5n69svdqfu33cxrvtpg7yjxrrq5yllqsv3ww": {"name": "Robinhood", "type": "exchange", "wallet": "cold"},

    # ─── Cash App / Block (Jack Dorsey) ───
    "3PxGDFMEn1kzn3sFN3dqCjHajTRcXkBwEP": {"name": "Cash App", "type": "exchange", "wallet": "cold"},

    # ═══ Institutions / ETF Custodians ═══

    # ─── BlackRock iShares IBIT (Coinbase Custody) ───
    "bc1qazcm763858nkj2dz7g0s80vuedv5mv7eneums3": {"name": "BlackRock IBIT", "type": "institution", "wallet": "custody"},

    # ─── Fidelity FBTC (Fidelity Digital Assets) ───
    "bc1qdc0rz5gf0ppjj2w3c2w8h2h7fjnm5gjtwzgwq3": {"name": "Fidelity FBTC", "type": "institution", "wallet": "custody"},

    # ─── Grayscale GBTC (Coinbase Custody) ───
    "bc1qe3ueyx5qq0n9gc08pzygkflgmg5l4s8gpzav0j": {"name": "Grayscale GBTC", "type": "institution", "wallet": "custody"},

    # ─── MicroStrategy (known cold storage) ───
    "bc1qazcm763858nkj2dz7g0s80vuedv5mv7eneums3": {"name": "MicroStrategy", "type": "institution", "wallet": "treasury"},

    # ─── Tesla ───
    "1FTKstQsag5cpJifhZneMpGdMJP5FxYUnY": {"name": "Tesla", "type": "institution", "wallet": "treasury"},

    # ─── Marathon Digital ───
    "bc1qkz0q7g4wz7zk5kxqj5jw8q7h0g9fr2qc0hvst": {"name": "Marathon Digital", "type": "institution", "wallet": "treasury"},

    # ═══ Government (seized wallets) ═══

    # ─── US Government (DOJ seizures) ───
    "bc1qa5wkgaew2dkv56kc6hp5kxsk7ln3t38j7kuzsa": {"name": "US Government", "type": "government", "wallet": "seized"},
    "1FfmbHfnpaZjKFvyi1okTjJJusN455paPH": {"name": "US Government", "type": "government", "wallet": "seized"},
    "bc1qf68jl3q5crlwgd9s37s2v8w5z4k8kx6r5sqfed": {"name": "US Government", "type": "government", "wallet": "seized"},

    # ─── German Government (BKA) ───
    "bc1qq0l4jgg9rcm3puhhvwq0yreg5dtkxsuprcdun2": {"name": "German Government", "type": "government", "wallet": "seized"},

    # ─── UK Government ───
    "1CRjKZJu8LvTutnEKe3vCMXbMgrPnhp9LM": {"name": "UK Government", "type": "government", "wallet": "seized"},

    # ═══ Notable Individuals ═══

    # ─── Satoshi Nakamoto (dormant, genesis era) ───
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": {"name": "Satoshi Nakamoto", "type": "individual", "wallet": "genesis"},

    # ─── Winklevoss Twins ───
    "3P3QsMVK89JBNqZQv5zMAKG8FK3kJM4rjt": {"name": "Winklevoss Twins", "type": "individual", "wallet": "cold"},
}
# fmt: on

# Priority addresses for monitoring (top entities to check for new txs)
MONITORED_ADDRESSES: list[str] = [
    # Exchanges: Binance
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
    # Exchanges: Coinbase
    "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS",
    "bc1qx9t2l3pyny2spqpqlye8svce70nppwtaxwdrp4",
    # Exchanges: Bitfinex
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
    # Exchanges: Kraken
    "3AfwmhssDGJYCzFNhUf79sMFfbXsBBymqq",
    "bc1q2s3rjwvam9dt2ftt4sqxqjf3twav0gdx0k0q2etjd8w8ll5jp5fs70wlsq",
    # Exchanges: OKX
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a",
    # Exchanges: Bybit
    "bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfl6tyf",
    # Institutions
    "bc1qazcm763858nkj2dz7g0s80vuedv5mv7eneums3",  # BlackRock IBIT
    "bc1qdc0rz5gf0ppjj2w3c2w8h2h7fjnm5gjtwzgwq3",  # Fidelity FBTC
    "bc1qe3ueyx5qq0n9gc08pzygkflgmg5l4s8gpzav0j",  # Grayscale GBTC
    # Government
    "bc1qa5wkgaew2dkv56kc6hp5kxsk7ln3t38j7kuzsa",  # US Gov
    "1FfmbHfnpaZjKFvyi1okTjJJusN455paPH",            # US Gov
]


def identify_entity(address: str) -> dict | None:
    """Look up a single address in the known entities database."""
    return KNOWN_ENTITIES.get(address)


def identify_any(addresses: list[str]) -> dict | None:
    """Return the first match from a list of addresses."""
    for addr in addresses:
        entity = KNOWN_ENTITIES.get(addr)
        if entity:
            return entity
    return None


def get_entities_summary() -> list[dict]:
    """Get deduplicated list of entities with their types for the /entities endpoint."""
    seen = set()
    entities = []
    for addr, info in KNOWN_ENTITIES.items():
        key = info["name"]
        if key not in seen:
            seen.add(key)
            entities.append({
                "name": info["name"],
                "type": info["type"],
                "address_count": sum(1 for v in KNOWN_ENTITIES.values() if v["name"] == info["name"]),
            })
    return sorted(entities, key=lambda e: (e["type"], e["name"]))
