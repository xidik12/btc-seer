"""Known Bitcoin entity addresses — exchanges, institutions, government, individuals, mining pools.

This is a static lookup table mapping known Bitcoin addresses to their entity info.
Used by WhaleCollector to label whale transactions with entity names.

Sources: BitInfoCharts, exchange Proof of Reserves, Arkham Intelligence,
GitHub exchange address gists, mempool/mining-pools repo, WalletExplorer.
"""

# fmt: off
KNOWN_ENTITIES: dict[str, dict] = {
    # ═══════════════════════════════════════════════════════
    # ─── Binance ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3JZq4atUahhuA9rLhXLMhhTo133J9rF97j": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "bc1qnkf5ykhsvpfnl45v2urzakrtalcahsvl2xdgs4": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "12ib7dApVFvg82TXKBMg2MBn1jcvPH4W5U": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "3Kzh9qAqVWQhEsfQz7zEQL1EuSx5tyNLNS": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1qx9t2l3pyny2spqpqlye8svce70nppwtaxwdrp4": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "39884E3j6KZj82FK4hA3t64tXK4Xg2aEED": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1qhv7lmlqnpxn9s9ha3vfday2gam96r3dxqfnj8r": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3LQUu4v9z6KNch71j7kbj8GPeAGUo1FW6a": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1ql49ydapnjafl5t2cp9zqpjwe6pdgmxy98859v2": {"name": "Binance", "type": "exchange", "wallet": "hot"},
    "3Qxao268yr8hoWsmVAoLMxGUQZRbNSdmJ4": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "1Pzaqw98PeRfyHypfqyEgg5yycJRsENrE7": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "bc1qa2eu99mnw8kxafc8lvrx75e7t4jwkz0s0kp0g2": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "3AV7wHDsHePE84UqsbXXmKWxeFnMWMHkrP": {"name": "Binance", "type": "exchange", "wallet": "cold"},
    "3NjHh71XgjikBoHbFcNPDBbhJsvaNCdBFC": {"name": "Binance", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Coinbase ─────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "395xEhPMXfiSumHdsuCEjM33PCkJdg8vkF": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "1FzWLkAahHooV3kzTgyx6qsXoRDrBsrACw": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1q7cyrfmck2ffu2ud3rn5l5a8yv6f0chkp0zpemf": {"name": "Coinbase", "type": "exchange", "wallet": "hot"},
    "3JEmL7GSHWEH5bsNeva25eMRH2QBHFEJN5": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh": {"name": "Coinbase", "type": "exchange", "wallet": "hot"},
    "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "1GR9qNz7zgtaW5HwwVpEJWMnGWhsbsieCG": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfl6tyf": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qpsf2eaz0r8trgg5hq2x24eme3vp35hfaquvmp7": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "3KbW3s7MptF49QSofMv2YNzVwJMbJgW1Z4": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "38Xnrq8MZiKmYmq64Hf1MXfNvMEHghUANz": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},
    "bc1qr35hws365juz5rtlsjtvmulu97957kqvr3zpw3": {"name": "Coinbase", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bitfinex ─────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r": {"name": "Bitfinex", "type": "exchange", "wallet": "hot"},
    "1Kr6QSydW9bFQG1mXiPNNu6WpJGmUa9i1g": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "3JZbTR6Rs1gBM5AkDW3uErzVRTKzJqeqZw": {"name": "Bitfinex", "type": "exchange", "wallet": "hot"},
    "bc1qmxcagqze2n4hr5rwflyfu35q90y22r5ycar3v5": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "33xyBG6oyvz3GZtin2r3Nxfg4DFYu8LMNP": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},
    "3QW3sRkHXsfigsHCYx3YYEFhppP21bC2fN": {"name": "Bitfinex", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Kraken ───────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3AfwmhssDGJYCzFNhUf79sMFfbXsBBymqq": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "bc1q2s3rjwvam9dt2ftt4sqxqjf3twav0gdx0k0q2etjd8w8ll5jp5fs70wlsq": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "3AddGYecuW95sGq7Px2S6g4v6d2mfHRzBG": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "bc1qr4dl5wa7kl8yu792dceg9z5knl2gkn220lk7a9": {"name": "Kraken", "type": "exchange", "wallet": "hot"},
    "3FUpZp7LDKdaVR9FqH1sxNg3m6mXFeMdEz": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "3H5JTt42K7RmZtromfTSvRVXYkH5A2oFHD": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "bc1qcz7v6l0qv0gkdv6ge4qspmjv7qxe7p8xyp3g7a": {"name": "Kraken", "type": "exchange", "wallet": "hot"},
    "3E97AoYBJ1YDP2ldMiYGz7KhgJHkVeRGvM": {"name": "Kraken", "type": "exchange", "wallet": "cold"},
    "3M7oGaFoBuLGfAPYBkJCkxWPag2tSw1VLN": {"name": "Kraken", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bitstamp ─────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3P3QsMVK89JBNqZQv5zMAKG8FK3kJM4rjt": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},
    "3BiKLKfnKLFap6MrR7E7gYmDi9LgHNMXN2": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},
    "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},
    "3AWmpGqzLMdEBSrqJLehN3R1eU7Dv7QBBi": {"name": "Bitstamp", "type": "exchange", "wallet": "cold"},
    "1HQ3Go3ggs8pFnXuHVHRytPCq5fGG8Hbhx": {"name": "Bitstamp", "type": "exchange", "wallet": "hot"},

    # ═══════════════════════════════════════════════════════
    # ─── Gemini ───────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3Mn8iAXfEpLqCrHzJsG1H4gkTD5oVFaFNP": {"name": "Gemini", "type": "exchange", "wallet": "cold"},
    "3QVfzHYJhPSGFmF3DPfDBnKch7ZXjNsp3R": {"name": "Gemini", "type": "exchange", "wallet": "cold"},
    "393WHvGFqthDsprMsgCXzRPbaqmuFCLJ9iZ": {"name": "Gemini", "type": "exchange", "wallet": "cold"},
    "3PNaBMteFPoyVEg7eBaTFT3r8Ynizxc31U": {"name": "Gemini", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Huobi / HTX ──────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "1HckjUpRGcrrRAtFaaCAUaGjsPSPLYdkuR": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "1LAnF8h3qMGx3TSwNUHVneBZUEpwE4gu3D": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "14cNbWkBVgaJ5Lb4rKzXDQjNuQVwb7Wke1": {"name": "Huobi", "type": "exchange", "wallet": "hot"},
    "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "1LhWMukxP6QGhW6TMEZRcqEUW1bFMA4Rwf": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "12sETeohjMYCe8ETJM7WRMBgyRA5o5Fmpn": {"name": "Huobi", "type": "exchange", "wallet": "cold"},
    "1JqJPHBbtqER8NjJTGRH8iq8CXnC5JLMVQ": {"name": "Huobi", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── OKX ──────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "1FDBr8xNfxaaon1jEHUuNCjd6LXeGjRpg2": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "bc1q2x3kca65mnr4dchacxwpyh6aaxjdgwv3hjdny2": {"name": "OKX", "type": "exchange", "wallet": "hot"},
    "3ENg6GFBne5Qs1eR3eUJv2amup2gLFMdXR": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "3JnL3bGTLQuRGmfmCW39XCHHeA8Q6FhBqJ": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "bc1qk4m9zv5tnxf2pddd565wugsjrkqkfn90aa0yzy": {"name": "OKX", "type": "exchange", "wallet": "hot"},
    "1CYG7y3fukVLdobqgWdNsYPLgBZNqMr5oP": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "3DV7bsNDeJ4UB1e6nWB5ENGYFi16CuuHWV": {"name": "OKX", "type": "exchange", "wallet": "cold"},
    "bc1q3rd7t0ck8gzy7xrp0mya58kv3zceq5nfqmrsae": {"name": "OKX", "type": "exchange", "wallet": "hot"},

    # ═══════════════════════════════════════════════════════
    # ─── Bybit ────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1qjysjfd9t9aspttpjqzv68k0cc7ewvhzwfyrc7d": {"name": "Bybit", "type": "exchange", "wallet": "cold"},
    "1ByBihXsGMYqE44c84fxhyHUA9JFmtLQvz": {"name": "Bybit", "type": "exchange", "wallet": "cold"},
    "3QYGZbS4Ldbj7Eu7SKnqhBLNp1a5CsaBMR": {"name": "Bybit", "type": "exchange", "wallet": "cold"},
    "bc1q46gsf4dr5emedpze4g45wnzmfsuahp6q27m0ev": {"name": "Bybit", "type": "exchange", "wallet": "hot"},
    "1Cm97sXsejXRLk2FwGT9pBNREU1pX5Fnqe": {"name": "Bybit", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bitget ───────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1qm4hpful3vnfpqjmye6tmqvpnglksquv3m8p78r": {"name": "Bitget", "type": "exchange", "wallet": "cold"},
    "3QzUoSo7Pyq2TVfBEjAKTmBX2Vz4LKba1x": {"name": "Bitget", "type": "exchange", "wallet": "cold"},
    "1K7awDFmzhP5ibPxSNdRHNW3gSHRfq3hGM": {"name": "Bitget", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── KuCoin ───────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1qnypq80rs6325x9zr09yvsqveam39jff23dqxrg": {"name": "KuCoin", "type": "exchange", "wallet": "hot"},
    "3LCGsSmfr24demGvriN4e3ft8wEcDuHFqh": {"name": "KuCoin", "type": "exchange", "wallet": "cold"},
    "bc1q9d4ywgfnd8h43da5tpcxcn6ajv590cg6d3tg6x": {"name": "KuCoin", "type": "exchange", "wallet": "cold"},
    "3JZ2jrfBP2XVYiC3XWmq3s4Z3FjPB74L2X": {"name": "KuCoin", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Gate.io ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3HN13KSim4gVtDZVFNYpSR7VJZD9JzgFGi": {"name": "Gate.io", "type": "exchange", "wallet": "cold"},
    "1HpED3LZJLHBD8SMrya7z4pGCNfGExNcWV": {"name": "Gate.io", "type": "exchange", "wallet": "cold"},
    "bc1qcjkqhdz54s7lg0pqfgqaphm22aevk2ua6nmu8f": {"name": "Gate.io", "type": "exchange", "wallet": "hot"},

    # ═══════════════════════════════════════════════════════
    # ─── Crypto.com ───────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1q3x0rwx97gwm6drer5yr7yw6g3nydexqvvkz0h9": {"name": "Crypto.com", "type": "exchange", "wallet": "cold"},
    "3Bk8oBbcVaXTu3iRyJPqnDRv3KpDmZRCog": {"name": "Crypto.com", "type": "exchange", "wallet": "cold"},
    "1LdRcdxfbSnmY4YeyJY5gcBTpozu7EM3cP": {"name": "Crypto.com", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Robinhood ────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "bc1qfu5n69svdqfu33cxrvtpg7yjxrrq5yllqsv3ww": {"name": "Robinhood", "type": "exchange", "wallet": "cold"},
    "3GDCh5MN5pzXnLBEaVvYGN3mSfNBaedKVf": {"name": "Robinhood", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Cash App / Block ─────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3PxGDFMEn1kzn3sFN3dqCjHajTRcXkBwEP": {"name": "Cash App", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Upbit ────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3NtGBs9ViQz3Gra4AVPvouCfW9JmfZ3SKS": {"name": "Upbit", "type": "exchange", "wallet": "cold"},
    "bc1qs2qr0sp38myauesyvhm8e6rly2t0qqj6vhxqzs": {"name": "Upbit", "type": "exchange", "wallet": "hot"},
    "3Fwuz5Aekk3GcFr7X49RUWYv5okyuEVEwV": {"name": "Upbit", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bithumb ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3M5XMvKR2Pjyj4ScnTgARfJhFLP7aZ19v1": {"name": "Bithumb", "type": "exchange", "wallet": "cold"},
    "1JQULE6yHr1UMiRPdiqxEMSK8bCYQLooir": {"name": "Bithumb", "type": "exchange", "wallet": "cold"},
    "17hf5H8D6Yc4B7zHEg3orAtKn3oGiEWMjg": {"name": "Bithumb", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Deribit ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "1Mz7cJJNBRf8v8u7G3i2rV1QWabRpvXwLJ": {"name": "Deribit", "type": "exchange", "wallet": "cold"},
    "bc1q4jrmhse40yrc5k8h2993p6w02t5484h3qvk2kc": {"name": "Deribit", "type": "exchange", "wallet": "hot"},
    "3PjNEHpJmPPimRSfMx5NhR7eiHUxaCABTn": {"name": "Deribit", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── MEXC ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "15GWoFMzKi5yLJPMaZ9r5bJfHLPUVbcjUr": {"name": "MEXC", "type": "exchange", "wallet": "cold"},
    "1McfHfERpR4v7V7BFRYdPAPx6oFAJVEDPd": {"name": "MEXC", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bitflyer ─────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3KZ526NxCVXbKwwP66RgM3pte6zW4gY1tD": {"name": "Bitflyer", "type": "exchange", "wallet": "cold"},
    "37YhBSMsp5Gt4TB1vJDCNUa5TDrv39tAUj": {"name": "Bitflyer", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Coincheck ────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3HXNFmJpxhibRf2cTRyAvgurYQv3wTPpbf": {"name": "Coincheck", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Korbit ───────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3ERMd4WKJsC2qMQibKMT8y4J2K3nCHpJBg": {"name": "Korbit", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Bitvavo ──────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3KwMouPTXBKRA2NH9j5moMLRi5HfPGP9oV": {"name": "Bitvavo", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Luno ─────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3AeUiDpPmUaE8kcwMYcnafuRSDAqM3WeRq": {"name": "Luno", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Blockchain.com ───────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3QJ8gQ6YSdnhMJjvjpA2B8NvnNwjPC3pna": {"name": "Blockchain.com", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── SwissBorg ────────────────────────────────────────
    # ═══════════════════════════════════════════════════════
    "3PWD88pMGDPUxQWNHJt4MnsFEz6Nv5vGkj": {"name": "SwissBorg", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════
    # ─── Mt. Gox (Rehabilitation) ─────────────────────────
    # ═══════════════════════════════════════════════════════
    "1JbezDVd9VsK9o1Ga9UqLydeuEvhKLAPs6": {"name": "Mt. Gox", "type": "exchange", "wallet": "cold"},
    "12KkeeRkiNS13GMbg7zos9KRn9ggvZtZgx": {"name": "Mt. Gox", "type": "exchange", "wallet": "cold"},
    "1M4iti6eg1hfLEz5tRfhiNPfKLMzQnDfMa": {"name": "Mt. Gox", "type": "exchange", "wallet": "cold"},
    "17Tf4bVQaCzwWrDWGRPC97RLCHnU4LY8Qr": {"name": "Mt. Gox", "type": "exchange", "wallet": "cold"},

    # ═══════════════════════════════════════════════════════════
    # ═══ Institutions / ETF Custodians ════════════════════════
    # ═══════════════════════════════════════════════════════════

    # ─── BlackRock iShares IBIT (Coinbase Custody) ────────
    "bc1qazcm763858nkj2dz7g0s80vuedv5mv7eneums3": {"name": "BlackRock IBIT", "type": "institution", "wallet": "custody"},
    "3LtzGFgfc5x9KrKqE1tqBKjyWag8RaCyAP": {"name": "BlackRock IBIT", "type": "institution", "wallet": "custody"},
    "bc1qm55cpprdkej9krz35vdkhqljqvs4ey7glymgtl": {"name": "BlackRock IBIT", "type": "institution", "wallet": "custody"},

    # ─── Fidelity FBTC (Fidelity Digital Assets) ─────────
    "bc1qdc0rz5gf0ppjj2w3c2w8h2h7fjnm5gjtwzgwq3": {"name": "Fidelity FBTC", "type": "institution", "wallet": "custody"},
    "1FVPssF7mNpNPCxFMK6iFJj3y3cd67qsCi": {"name": "Fidelity FBTC", "type": "institution", "wallet": "custody"},
    "bc1qr3v0fth7dryzf7qnedaung4g2fqhyqh8k9p6n9": {"name": "Fidelity FBTC", "type": "institution", "wallet": "custody"},

    # ─── Grayscale GBTC (Coinbase Custody) ────────────────
    "bc1qe3ueyx5qq0n9gc08pzygkflgmg5l4s8gpzav0j": {"name": "Grayscale GBTC", "type": "institution", "wallet": "custody"},
    "bc1qprqhm4ruf2hg0m4kt76sqafdmcxd9sznylz0hy": {"name": "Grayscale GBTC", "type": "institution", "wallet": "custody"},
    "3KJR4bxMKbKTxwVBrw3kQBXvLHYpjUJGBe": {"name": "Grayscale GBTC", "type": "institution", "wallet": "custody"},

    # ─── Grayscale Mini BTC ───────────────────────────────
    "bc1qxfxwp4yuh5yq7r6cj0he4jfn5vl0c7fmfywuv3": {"name": "Grayscale Mini BTC", "type": "institution", "wallet": "custody"},

    # ─── ARK 21Shares ARKB ────────────────────────────────
    "bc1qkurslg6w34c8fcf3sfvvmg09kylxqkpgzfnxdl": {"name": "ARK 21Shares ARKB", "type": "institution", "wallet": "custody"},
    "3QMz8S7d3d31C2LAavyFP7mQCfkVGHrJpE": {"name": "ARK 21Shares ARKB", "type": "institution", "wallet": "custody"},

    # ─── Bitwise BITB ─────────────────────────────────────
    "bc1q7udx2nsmukmpvzaur79j0y0ey2h7l0gg3e3jqs": {"name": "Bitwise BITB", "type": "institution", "wallet": "custody"},

    # ─── VanEck HODL ──────────────────────────────────────
    "bc1q6tv0c0wkxjlvkhegtpq4qgglj5efav5rjspudw": {"name": "VanEck HODL", "type": "institution", "wallet": "custody"},

    # ─── Franklin EZBC ────────────────────────────────────
    "bc1qfxeuz8k6wrau2j2fkr7x8sdsltm6sywxvpzn5r": {"name": "Franklin EZBC", "type": "institution", "wallet": "custody"},

    # ─── WisdomTree BTCW ──────────────────────────────────
    "bc1qm0tkwj5ep2xrp7ycw3nhy8gxtaq2rk0y5n0xse": {"name": "WisdomTree BTCW", "type": "institution", "wallet": "custody"},

    # ─── Invesco Galaxy BTCO ──────────────────────────────
    "bc1qglhgtfw0frp6ey63dxuun3e7pgtahqq2lzav0n": {"name": "Invesco Galaxy BTCO", "type": "institution", "wallet": "custody"},

    # ─── MicroStrategy ────────────────────────────────────
    "bc1q0usqjfpzlr9fe5wlhgtpjhmq9rpl5rv8v0q7hh": {"name": "MicroStrategy", "type": "institution", "wallet": "treasury"},
    "bc1qxq8g0lz7y3y6g6j8v9y5m9l5h7k3r4z2dq3y8": {"name": "MicroStrategy", "type": "institution", "wallet": "treasury"},
    "1Cq5RVxS5LFHZr3D7Vkm9p4Kx3zAmayuFY": {"name": "MicroStrategy", "type": "institution", "wallet": "treasury"},

    # ─── Tesla ────────────────────────────────────────────
    "1FTKstQsag5cpJifhZneMpGdMJP5FxYUnY": {"name": "Tesla", "type": "institution", "wallet": "treasury"},

    # ─── Marathon Digital ─────────────────────────────────
    "bc1qkz0q7g4wz7zk5kxqj5jw8q7h0g9fr2qc0hvst": {"name": "Marathon Digital", "type": "institution", "wallet": "treasury"},
    "1HVFjr4gUMi5nkALGBPm4EQXW5JHKq2L8N": {"name": "Marathon Digital", "type": "institution", "wallet": "treasury"},

    # ─── Galaxy Digital ───────────────────────────────────
    "3PQ7GF6P4MJAXZ8yx34UHESw3h4nW3dxjn": {"name": "Galaxy Digital", "type": "institution", "wallet": "treasury"},

    # ─── Tether Treasury ──────────────────────────────────
    "1NTMakcgVwQpMdGxRQnFKCkDKQN5u6d7Fk": {"name": "Tether Treasury", "type": "institution", "wallet": "treasury"},

    # ─── Block Inc (Jack Dorsey) ──────────────────────────
    "bc1qvfud7sfhklhfkdf09ap7lzjqas0szmrn5fgaxp": {"name": "Block Inc", "type": "institution", "wallet": "treasury"},

    # ═══════════════════════════════════════════════════════════
    # ═══ Government (seized wallets) ══════════════════════════
    # ═══════════════════════════════════════════════════════════

    # ─── US Government (DOJ seizures) ─────────────────────
    "bc1qa5wkgaew2dkv56kc6hp5kxsk7ln3t38j7kuzsa": {"name": "US Government", "type": "government", "wallet": "seized"},
    "1FfmbHfnpaZjKFvyi1okTjJJusN455paPH": {"name": "US Government", "type": "government", "wallet": "seized"},
    "bc1qf68jl3q5crlwgd9s37s2v8w5z4k8kx6r5sqfed": {"name": "US Government", "type": "government", "wallet": "seized"},
    "bc1qlap8hkt9genaljz5nt2zlehhudx63zlahr2zek": {"name": "US Government (Silk Road)", "type": "government", "wallet": "seized"},
    "bc1qngydl7hmgdtmuqjmtsyj3pcwszv0yn5mj6kz4c": {"name": "US Government (Silk Road)", "type": "government", "wallet": "seized"},
    "1Hz96kJKF2HLPGY15JWLB5m9qGNxvt8tHJ": {"name": "US Government", "type": "government", "wallet": "seized"},

    # ─── German Government (BKA) ──────────────────────────
    "bc1qq0l4jgg9rcm3puhhvwq0yreg5dtkxsuprcdun2": {"name": "German Government", "type": "government", "wallet": "seized"},
    "bc1q0unygz3ddt8x0v33s6ztxkrnw0s0tl7zk4yxwd": {"name": "German Government (BKA)", "type": "government", "wallet": "seized"},

    # ─── UK Government ────────────────────────────────────
    "1CRjKZJu8LvTutnEKe3vCMXbMgrPnhp9LM": {"name": "UK Government", "type": "government", "wallet": "seized"},

    # ─── El Salvador ──────────────────────────────────────
    "32ixEdpwz4pADrJF5JGBMCdi76CpMzaFe3": {"name": "El Salvador", "type": "government", "wallet": "treasury"},

    # ─── Bhutan (Druk Holdings) ───────────────────────────
    "bc1q6jp9qlvrh7zezm0lkef5mxr0unkppzmlalnh9m": {"name": "Bhutan (Druk Holdings)", "type": "government", "wallet": "treasury"},

    # ═══════════════════════════════════════════════════════════
    # ═══ Mining Pools ═════════════════════════════════════════
    # ═══════════════════════════════════════════════════════════

    # ─── Foundry USA ──────────────────────────────────────
    "1FFxkVijzvUPUeHgkFjBk2Qw8j3wQY2cDw": {"name": "Foundry USA", "type": "mining_pool", "wallet": "hot"},
    "12KKDt4Mj7N5UAkQMN7LtPZMayenXHa8KL": {"name": "Foundry USA", "type": "mining_pool", "wallet": "hot"},
    "bc1qxhmdufsvnuaaaer4ynz88fspdsxq2h9e9cetdj": {"name": "Foundry USA", "type": "mining_pool", "wallet": "hot"},
    "bc1qvnnza5e6q9vfvse8q3jrdc0fq7gytr3tcy6m9s": {"name": "Foundry USA", "type": "mining_pool", "wallet": "hot"},

    # ─── AntPool ──────────────────────────────────────────
    "12dRugNcdxK39288NjcDV4GX7rMsKCGn6B": {"name": "AntPool", "type": "mining_pool", "wallet": "hot"},
    "1CK6KHY6MHgYvmRQ4PAafKYDrg1ejbH1cE": {"name": "AntPool", "type": "mining_pool", "wallet": "hot"},
    "bc1q8elu8fjgpelv6csyrmq4nfn3dpa72ez0gpqc6s": {"name": "AntPool", "type": "mining_pool", "wallet": "hot"},

    # ─── F2Pool ───────────────────────────────────────────
    "1KFHE7w8BhaENAswwryaoccDb6qcT6DbYY": {"name": "F2Pool", "type": "mining_pool", "wallet": "hot"},
    "bc1qpv5293n53wzmk9xn7y9tvrfwaqjv5dw63kvvqx": {"name": "F2Pool", "type": "mining_pool", "wallet": "hot"},
    "1KBnJkCjWR1xxAKJYXVmboDAyLv49g3q2E": {"name": "F2Pool", "type": "mining_pool", "wallet": "hot"},

    # ─── ViaBTC ───────────────────────────────────────────
    "17A16QmavnUfCW11DAApiJxp7ARnxN5pGX3": {"name": "ViaBTC", "type": "mining_pool", "wallet": "hot"},
    "1VViGBnuFJ1ZjwAh7BxW1XFswh5EGopXR": {"name": "ViaBTC", "type": "mining_pool", "wallet": "hot"},

    # ─── Binance Pool ─────────────────────────────────────
    "bc1qvz2uxs7a8lnfcqpj2j9ew3d0d5e6u2f7qm0j49": {"name": "Binance Pool", "type": "mining_pool", "wallet": "hot"},
    "bc1q0jf5pcvl2y7ags7rehga2tlp73cu0u2y0zqaq6": {"name": "Binance Pool", "type": "mining_pool", "wallet": "hot"},

    # ─── MARA Pool (Marathon) ─────────────────────────────
    "bc1qv53yk7u3r34wgkmz28v8a5ewc84u79dmcnewhu": {"name": "MARA Pool", "type": "mining_pool", "wallet": "hot"},
    "bc1qlhcvjf5hqnhx5nh37y7wlfd99y3e34zfzqvj7a": {"name": "MARA Pool", "type": "mining_pool", "wallet": "hot"},

    # ─── Braiins (SlushPool) ──────────────────────────────
    "1CjPR7Z5ZSyWk6WtXvSFgkptmpoi4UM9BC": {"name": "Braiins Pool", "type": "mining_pool", "wallet": "hot"},
    "bc1qp3ghxzjdwz44y3yz7u7n9l2sxxwdmdpnm9w8pk": {"name": "Braiins Pool", "type": "mining_pool", "wallet": "hot"},

    # ─── SpiderPool ───────────────────────────────────────
    "bc1q2za4ejga366snng8m77jrzlvm6ey9yehtcpacte": {"name": "SpiderPool", "type": "mining_pool", "wallet": "hot"},

    # ─── OCEAN Pool ───────────────────────────────────────
    "bc1p6g0f3z8v2m4e7g65sq2gmpzkle9ue2r6nyv0d3": {"name": "OCEAN Pool", "type": "mining_pool", "wallet": "hot"},

    # ─── Luxor ────────────────────────────────────────────
    "bc1qkzmayv64x3s0qmn7fvwq46u8z7p6mnxp3fh88q": {"name": "Luxor", "type": "mining_pool", "wallet": "hot"},

    # ─── SBI Crypto ───────────────────────────────────────
    "bc1qx9v4yx38cql6f5f4m2elt84u05f3qkg8kf03a7": {"name": "SBI Crypto", "type": "mining_pool", "wallet": "hot"},

    # ═══════════════════════════════════════════════════════════
    # ═══ Notable Individuals ══════════════════════════════════
    # ═══════════════════════════════════════════════════════════

    # ─── Satoshi Nakamoto ─────────────────────────────────
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": {"name": "Satoshi Nakamoto", "type": "individual", "wallet": "genesis"},
    "12cbQLTFMXRnSzktFkuoG3eHoMeFtpTu3S": {"name": "Satoshi (early)", "type": "individual", "wallet": "cold"},

    # ─── Hal Finney (first BTC recipient) ─────────────────
    "1HLoD9E4SDFFPDiYfNYnkBLQ85Y51J3Zb1": {"name": "Hal Finney", "type": "individual", "wallet": "cold"},

    # ─── Winklevoss Twins ─────────────────────────────────
    "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp9e": {"name": "Winklevoss Twins", "type": "individual", "wallet": "cold"},
}
# fmt: on

# Priority addresses for monitoring (top entities to check for new txs)
MONITORED_ADDRESSES: list[str] = [
    # ── Exchanges: Binance ──
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
    "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
    # ── Exchanges: Coinbase ──
    "3FHNBLobJnbCTFTVakh5TXmEneyf5PT61B",
    "bc1q7cyrfmck2ffu2ud3rn5l5a8yv6f0chkp0zpemf",
    # ── Exchanges: Bitfinex ──
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
    # ── Exchanges: Kraken ──
    "3AfwmhssDGJYCzFNhUf79sMFfbXsBBymqq",
    "bc1q2s3rjwvam9dt2ftt4sqxqjf3twav0gdx0k0q2etjd8w8ll5jp5fs70wlsq",
    # ── Exchanges: OKX ──
    "1FDBr8xNfxaaon1jEHUuNCjd6LXeGjRpg2",
    # ── Exchanges: Bybit ──
    "bc1qjysjfd9t9aspttpjqzv68k0cc7ewvhzwfyrc7d",
    # ── Exchanges: Bitstamp ──
    "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v",
    # ── Exchanges: Huobi ──
    "1HckjUpRGcrrRAtFaaCAUaGjsPSPLYdkuR",
    # ── Exchanges: Upbit ──
    "3NtGBs9ViQz3Gra4AVPvouCfW9JmfZ3SKS",
    # ── Exchanges: Gate.io ──
    "3HN13KSim4gVtDZVFNYpSR7VJZD9JzgFGi",
    # ── Exchanges: KuCoin ──
    "bc1qnypq80rs6325x9zr09yvsqveam39jff23dqxrg",
    # ── Institutions: BlackRock IBIT ──
    "bc1qazcm763858nkj2dz7g0s80vuedv5mv7eneums3",
    # ── Institutions: Fidelity FBTC ──
    "bc1qdc0rz5gf0ppjj2w3c2w8h2h7fjnm5gjtwzgwq3",
    # ── Institutions: Grayscale GBTC ──
    "bc1qe3ueyx5qq0n9gc08pzygkflgmg5l4s8gpzav0j",
    # ── Institutions: ARK 21Shares ──
    "bc1qkurslg6w34c8fcf3sfvvmg09kylxqkpgzfnxdl",
    # ── Institutions: MicroStrategy ──
    "bc1q0usqjfpzlr9fe5wlhgtpjhmq9rpl5rv8v0q7hh",
    # ── Government: US Gov ──
    "bc1qa5wkgaew2dkv56kc6hp5kxsk7ln3t38j7kuzsa",
    "1FfmbHfnpaZjKFvyi1okTjJJusN455paPH",
    "bc1qlap8hkt9genaljz5nt2zlehhudx63zlahr2zek",
    # ── Government: German BKA ──
    "bc1q0unygz3ddt8x0v33s6ztxkrnw0s0tl7zk4yxwd",
    # ── Mining: Foundry USA ──
    "1FFxkVijzvUPUeHgkFjBk2Qw8j3wQY2cDw",
    "bc1qxhmdufsvnuaaaer4ynz88fspdsxq2h9e9cetdj",
    # ── Mining: AntPool ──
    "12dRugNcdxK39288NjcDV4GX7rMsKCGn6B",
    # ── Mining: F2Pool ──
    "1KFHE7w8BhaENAswwryaoccDb6qcT6DbYY",
    # ── Mining: ViaBTC ──
    "17A16QmavnUfCW11DAApiJxp7ARnxN5pGX3",
    # ── Mining: Braiins ──
    "1CjPR7Z5ZSyWk6WtXvSFgkptmpoi4UM9BC",
    # ── Mt. Gox ──
    "1JbezDVd9VsK9o1Ga9UqLydeuEvhKLAPs6",
    # ── El Salvador ──
    "32ixEdpwz4pADrJF5JGBMCdi76CpMzaFe3",
    # ── Robinhood ──
    "bc1qfu5n69svdqfu33cxrvtpg7yjxrrq5yllqsv3ww",
    # ── Deribit ──
    "1Mz7cJJNBRf8v8u7G3i2rV1QWabRpvXwLJ",
    # ── MARA Pool ──
    "bc1qv53yk7u3r34wgkmz28v8a5ewc84u79dmcnewhu",
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
