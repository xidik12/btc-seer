"""Event Impact Memory — classifies news events and recalls historical price impact.

This module gives the prediction system a 'memory' of how past events
(war, politics, Fed decisions, hacks, ETF news, etc.) have affected BTC price,
so it can anticipate the impact of similar new events.
"""
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# ── Event categories and their keyword mappings ──

EVENT_CATEGORIES = {
    "war_conflict": {
        "keywords": [
            # English
            "war", "invasion", "military", "missile", "strike", "bomb",
            "conflict", "troops", "army", "attack", "hostage", "ceasefire",
            "nato", "nuclear", "weapons", "sanctions military", "drone strike",
            "escalation", "tension", "geopolitical", "territorial",
            # Russian
            "война", "вторжение", "военный", "ракета", "удар", "бомба",
            "конфликт", "войска", "армия", "атака", "заложник", "перемирие",
            "ядерный", "оружие", "эскалация", "напряжённость", "геополитика",
            # Chinese
            "战争", "入侵", "军事", "导弹", "袭击", "炸弹", "冲突",
            "军队", "攻击", "人质", "停火", "核武器", "升级", "地缘政治",
            # Spanish
            "guerra", "invasión", "militar", "misil", "ataque", "bomba",
            "conflicto", "tropas", "ejército", "rehén", "alto el fuego",
            "escalada", "tensión", "geopolítica",
            # Arabic
            "حرب", "غزو", "عسكري", "صاروخ", "هجوم", "قنبلة",
            "صراع", "قوات", "جيش", "رهينة", "وقف إطلاق النار",
            "تصعيد", "توتر", "جيوسياسي",
        ],
        "severity_boost": 2,
    },
    "politics_regulation": {
        "keywords": [
            # English
            "regulation", "ban", "bans", "banned", "crackdown", "sec", "cftc", "congress",
            "senate", "legislation", "law", "executive order", "policy",
            "tax", "compliance", "kyc", "aml", "enforcement", "subpoena",
            "stablecoin bill", "framework", "gensler", "warren",
            "trump", "biden", "white house", "treasury department",
            # Russian
            "регулирование", "запрет", "закон", "законопроект",
            "центробанк", "минфин", "госдума", "налог", "путин",
            "цифровой рубль", "криптовалюта запрет",
            # Chinese
            "监管", "禁令", "法律", "法规", "政策", "税收",
            "合规", "执法", "数字人民币", "央行",
            "国务院", "习近平",
            # Spanish
            "regulación", "prohibición", "ley", "legislación",
            "impuesto", "cumplimiento", "banco central",
            # Arabic
            "تنظيم", "حظر", "قانون", "تشريع", "ضريبة",
            "بنك مركزي", "سياسة",
            # Japanese/Korean (major regulatory markets)
            "規制", "禁止", "法律", "금지", "규제", "법률",
            # Turkish
            "düzenleme", "yasakla", "kripto düzenleme", "kripto para",
            # Hindi
            "नीति", "विनियमन", "प्रतिबंध", "कानून",
        ],
        "severity_boost": 1,
    },
    "monetary_policy": {
        "keywords": [
            # English
            "federal reserve", "fed", "interest rate", "rate hike", "rate cut",
            "fomc", "powell", "inflation", "cpi", "ppi", "employment",
            "jobs report", "nonfarm", "gdp", "recession", "quantitative",
            "tightening", "easing", "dovish", "hawkish", "yield curve",
            "debt ceiling", "treasury", "bond", "basis points",
            # Russian (stem forms for case flexibility)
            "ставк", "инфляци", "ввп", "рецесси", "набиуллина",
            "ключев", "денежн полити", "центробанк",
            # Chinese
            "利率", "通胀", "降息", "加息", "货币政策",
            "量化宽松", "经济衰退", "央行",
            # Spanish
            "tasa de interés", "inflación", "recesión",
            "política monetaria", "banco central",
            # Arabic
            "سعر الفائدة", "تضخم", "ركود", "سياسة نقدية",
            # Japanese
            "金利", "インフレ", "利上げ", "利下げ", "日銀",
        ],
        "severity_boost": 2,
    },
    "tariff_trade": {
        "keywords": [
            # English
            "tariff", "trade war", "import duty", "export ban", "trade deal",
            "sanctions", "embargo", "trade deficit", "customs", "wto",
            "retaliatory", "trade policy", "protectionism", "free trade",
            # Russian
            "тариф", "торговая война", "санкции", "эмбарго",
            "пошлина", "импорт", "экспорт", "торговый дефицит",
            # Chinese
            "关税", "贸易战", "制裁", "禁运", "进口",
            "出口", "贸易逆差", "贸易协议",
            # Spanish
            "arancel", "guerra comercial", "sanciones", "embargo",
            # Arabic
            "تعرفة", "حرب تجارية", "عقوبات", "حصار",
        ],
        "severity_boost": 1,
    },
    "stock_market": {
        "keywords": [
            # English
            "s&p 500", "nasdaq", "dow jones", "stock market", "wall street",
            "equity", "stock crash", "correction", "bear market", "bull market",
            "earnings", "tech stocks", "magnificent 7", "ipo", "buyback",
            "market cap", "index", "futures", "options expiry",
            # Russian
            "фондовый рынок", "акции", "биржа", "мосбиржа",
            "обвал", "коррекция", "медвежий рынок", "бычий рынок",
            # Chinese
            "股市", "纳斯达克", "道琼斯", "标普500", "股票",
            "崩盘", "牛市", "熊市", "上证",
            # Japanese
            "株式市場", "日経", "暴落", "株価",
        ],
        "severity_boost": 0,
    },
    "etf_institutional": {
        "keywords": [
            # English
            "etf", "bitcoin etf", "spot etf", "etf approval", "etf filing",
            "etf inflow", "etf outflow", "grayscale", "blackrock", "fidelity",
            "ark invest", "institutional", "custody", "asset manager",
            "fund", "investment vehicle", "ibit", "gbtc",
            # Russian
            "биткоин etf", "институциональный", "фонд",
            # Chinese
            "比特币etf", "机构投资", "基金",
            "资产管理", "托管",
            # Spanish
            "fondo", "institucional", "custodia",
            # Arabic
            "صندوق", "مؤسسي", "استثمار مؤسسي",
        ],
        "severity_boost": 2,
    },
    "exchange_hack": {
        "keywords": [
            # English
            "hack", "exploit", "breach", "stolen", "drained", "vulnerability",
            "rug pull", "scam", "phishing", "flash loan", "oracle attack",
            "bridge hack", "defi exploit", "funds stolen", "security incident",
            # Russian
            "взлом", "украдено", "уязвимость", "мошенничество",
            "фишинг", "скам", "средства похищены",
            # Chinese
            "黑客", "漏洞", "被盗", "诈骗", "钓鱼",
            "闪电贷攻击", "资金被盗", "安全事件",
            # Spanish
            "hackeo", "robado", "estafa", "vulnerabilidad",
            # Arabic
            "اختراق", "سرقة", "احتيال", "ثغرة",
        ],
        "severity_boost": 2,
    },
    "company_announcement": {
        "keywords": [
            # English
            "partnership", "acquisition", "merger", "launch", "listing",
            "delisting", "bankruptcy", "insolvency", "layoff", "restructuring",
            "revenue", "profit", "loss", "quarterly", "annual report",
            "tesla", "microstrategy", "coinbase", "binance", "kraken",
            # Russian
            "партнёрство", "приобретение", "слияние", "банкротство",
            "листинг", "делистинг", "увольнения",
            # Chinese
            "合作", "收购", "合并", "上市", "退市",
            "破产", "裁员", "特斯拉",
            # Spanish
            "asociación", "adquisición", "fusión", "quiebra",
        ],
        "severity_boost": 0,
    },
    "whale_movement": {
        "keywords": [
            # English
            "whale", "large transfer", "whale alert", "dormant", "moved",
            "exchange deposit", "exchange withdrawal", "accumulation",
            "distribution", "on-chain", "wallet", "cold storage",
            # Russian
            "кит", "крупный перевод", "накопление", "кошелёк",
            # Chinese
            "巨鲸", "大额转账", "链上", "钱包", "冷存储",
            # Spanish
            "ballena", "transferencia grande", "acumulación",
        ],
        "severity_boost": 1,
    },
    "technology": {
        "keywords": [
            # English
            "halving", "upgrade", "fork", "taproot", "lightning network",
            "layer 2", "protocol", "mining", "hash rate", "difficulty",
            "ordinals", "inscription", "brc-20", "runes", "segwit",
            # Russian
            "халвинг", "обновление", "форк", "майнинг", "хешрейт",
            # Chinese
            "减半", "升级", "分叉", "闪电网络", "挖矿",
            "算力", "难度", "铭文",
            # Spanish
            "reducción a la mitad", "actualización", "minería",
        ],
        "severity_boost": 1,
    },
    "macro_economic": {
        "keywords": [
            # English
            "dollar", "dxy", "gold", "oil", "commodity", "currency",
            "euro", "yen", "yuan", "emerging market", "sovereign debt",
            "banking crisis", "liquidity", "money supply", "m2",
            "real estate", "housing", "consumer confidence",
            # Russian
            "доллар", "золото", "нефть", "рубль", "валюта",
            "банковский кризис", "ликвидность", "денежная масса",
            # Chinese
            "美元", "黄金", "石油", "人民币", "大宗商品",
            "银行危机", "流动性", "货币供应",
            # Spanish
            "dólar", "oro", "petróleo", "crisis bancaria",
            # Arabic
            "دولار", "ذهب", "نفط", "أزمة مصرفية",
        ],
        "severity_boost": 0,
    },
    "country_adoption": {
        "keywords": [
            # English — sovereign/national BTC events
            "bitcoin reserve", "strategic reserve", "national reserve",
            "sovereign wealth fund", "sovereign fund", "country buys bitcoin", "government bitcoin",
            "legal tender", "bitcoin legal", "central bank bitcoin",
            "el salvador", "bukele", "bitcoin city",
            "bitcoin treasury", "state bitcoin", "national bitcoin",
            "bitcoin adoption country", "crypto friendly country",
            "digital asset reserve", "btc reserve",
            # Country-specific entities
            "saudi arabia bitcoin", "saudi bitcoin", "saudi crypto",
            "uae bitcoin", "uae crypto", "dubai crypto", "abu dhabi crypto",
            "qatar bitcoin", "bahrain bitcoin", "kuwait bitcoin",
            "israel bitcoin", "israel crypto",
            "russia bitcoin", "russia crypto", "digital ruble",
            "china bitcoin", "china crypto", "hong kong crypto",
            "japan bitcoin", "japan crypto",
            "india bitcoin", "india crypto",
            "brazil bitcoin", "brazil crypto",
            "turkey bitcoin", "turkey crypto",
            "nigeria bitcoin", "nigeria crypto",
            "argentina bitcoin", "argentina crypto",
            "south korea bitcoin", "korea crypto",
            "thailand bitcoin", "indonesia bitcoin",
            "pakistan bitcoin", "pakistan crypto",
            "iran bitcoin", "iran crypto",
            "uk bitcoin", "uk crypto regulation",
            "eu bitcoin", "mica regulation",
            "germany bitcoin", "france bitcoin",
            "switzerland bitcoin", "swiss crypto",
            "singapore bitcoin", "singapore crypto",
            # Russian (stem forms to match all grammatical cases)
            "биткоин резерв", "резерв биткоин", "резерве биткоин",
            "стратегическ", "национальн резерв", "россия биткоин",
            "цифровой рубль", "цифровых валют", "крипто резерв",
            "государственн биткоин", "страна покупает биткоин",
            "суверенн фонд", "биткоин легал",
            "саудовск", "эмират", "израиль крипто", "катар крипто",
            # Chinese
            "比特币储备", "国家储备", "战略储备", "主权基金",
            "法定货币", "国家比特币", "香港加密",
            # Spanish
            "reserva bitcoin", "reserva estratégica", "moneda legal",
            "adopción bitcoin", "reserva nacional",
            # Arabic (standalone roots — Arabic prefixes break multi-word)
            "احتياطي", "عملة قانونية", "تبني بيتكوين",
            "صندوق سيادي", "السعودية", "الإمارات",
            "إسرائيل", "قطر", "البحرين", "الكويت",
            "بيتكوين احتياطي", "شراء بيتكوين",
            # Turkish
            "bitcoin rezerv", "stratejik rezerv",
            # Hindi
            "बिटकॉइन रिज़र्व", "भारत बिटकॉइन", "भारत क्रिप्टो",
            # Japanese
            "ビットコイン準備金", "国家準備金",
            # Korean
            "비트코인 준비금", "국가 비트코인",
        ],
        "severity_boost": 3,  # Sovereign adoption is highest-impact
    },
}


class EventClassifier:
    """Classifies news headlines into event categories with severity scoring."""

    def classify(self, title: str, sentiment_score: float = 0.0) -> dict | None:
        """Classify a news headline into an event category.

        Returns None if the headline doesn't match any significant category.
        Returns dict with category, subcategory, keywords, severity.
        """
        title_lower = title.lower()

        best_category = None
        best_score = 0
        matched_keywords = []

        for category, config in EVENT_CATEGORIES.items():
            cat_keywords = []
            cat_score = 0

            for kw in config["keywords"]:
                # Use word boundary matching for short ASCII keywords to avoid
                # false positives like "war" in "rewards"
                # Non-ASCII keywords (CJK, Arabic, Cyrillic) use substring match
                if len(kw) <= 4 and kw.isascii():
                    if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2
                else:
                    if kw in title_lower:
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2

            if cat_score > best_score:
                best_score = cat_score
                best_category = category
                matched_keywords = cat_keywords

        if not best_category or best_score < 2:
            return None  # Not significant enough to track

        # Calculate severity (1-10)
        config = EVENT_CATEGORIES[best_category]
        severity = min(10, max(1,
            3  # base
            + config["severity_boost"]
            + len(matched_keywords)  # more keywords = more relevant
            + int(abs(sentiment_score) * 3)  # strong sentiment = more impactful
        ))

        return {
            "category": best_category,
            "subcategory": matched_keywords[0] if matched_keywords else None,
            "keywords": ",".join(matched_keywords),
            "severity": severity,
        }


class EventPatternMatcher:
    """Finds similar past events and returns their average price impact."""

    def find_similar_events(
        self,
        category: str,
        keywords: str,
        past_events: list[dict],
        min_similarity: float = 0.3,
    ) -> list[dict]:
        """Find past events in the same category with similar keywords."""
        current_kw_set = set(keywords.lower().split(",")) if keywords else set()
        similar = []

        for event in past_events:
            if event.get("category") != category:
                continue

            past_kw_set = set(
                (event.get("keywords") or "").lower().split(",")
            )

            # Jaccard similarity on keywords
            intersection = current_kw_set & past_kw_set
            union = current_kw_set | past_kw_set
            if not union:
                continue

            similarity = len(intersection) / len(union)
            if similarity >= min_similarity:
                event["similarity"] = similarity
                similar.append(event)

        # Sort by similarity (highest first)
        similar.sort(key=lambda x: -x.get("similarity", 0))
        return similar[:20]  # Top 20 most similar

    def get_expected_impact(self, similar_events: list[dict]) -> dict:
        """Calculate expected price impact from similar past events.

        Returns weighted average of historical impacts, with more similar
        events weighted higher.
        """
        if not similar_events:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
            }

        total_weight = 0.0
        weighted_1h = 0.0
        weighted_4h = 0.0
        weighted_24h = 0.0
        predictive_count = 0
        total_predictive = 0

        for event in similar_events:
            sim = event.get("similarity", 0.5)
            weight = sim * sim  # Quadratic weighting — very similar events matter more

            c1h = event.get("change_pct_1h")
            c4h = event.get("change_pct_4h")
            c24h = event.get("change_pct_24h")

            if c1h is not None:
                weighted_1h += c1h * weight
                total_weight += weight

            if c4h is not None:
                weighted_4h += c4h * weight

            if c24h is not None:
                weighted_24h += c24h * weight

            if event.get("sentiment_was_predictive") is not None:
                total_predictive += 1
                if event["sentiment_was_predictive"]:
                    predictive_count += 1

        if total_weight == 0:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
            }

        avg_1h = weighted_1h / total_weight
        avg_4h = weighted_4h / total_weight
        avg_24h = weighted_24h / total_weight

        # Confidence: more events + higher similarity = higher confidence
        confidence = min(1.0,
            (len(similar_events) / 10)  # More events = more confident
            * (sum(e.get("similarity", 0) for e in similar_events) / len(similar_events))  # Avg similarity
        )

        avg_predictive = (predictive_count / total_predictive) if total_predictive > 0 else 0.5

        return {
            "expected_1h": round(avg_1h, 4),
            "expected_4h": round(avg_4h, 4),
            "expected_24h": round(avg_24h, 4),
            "confidence": round(confidence, 4),
            "sample_size": len(similar_events),
            "avg_sentiment_predictive": round(avg_predictive, 4),
        }

    def get_category_stats(self, past_events: list[dict]) -> dict:
        """Get average impact stats per event category.

        Returns dict like: {"war_conflict": {"avg_1h": -0.5, "avg_24h": -2.1, "count": 15}, ...}
        """
        stats = {}

        for event in past_events:
            cat = event.get("category")
            if not cat:
                continue

            if cat not in stats:
                stats[cat] = {
                    "impacts_1h": [], "impacts_4h": [], "impacts_24h": [],
                    "count": 0
                }

            stats[cat]["count"] += 1
            if event.get("change_pct_1h") is not None:
                stats[cat]["impacts_1h"].append(event["change_pct_1h"])
            if event.get("change_pct_4h") is not None:
                stats[cat]["impacts_4h"].append(event["change_pct_4h"])
            if event.get("change_pct_24h") is not None:
                stats[cat]["impacts_24h"].append(event["change_pct_24h"])

        result = {}
        for cat, data in stats.items():
            result[cat] = {
                "count": data["count"],
                "avg_1h": round(sum(data["impacts_1h"]) / len(data["impacts_1h"]), 4) if data["impacts_1h"] else 0.0,
                "avg_4h": round(sum(data["impacts_4h"]) / len(data["impacts_4h"]), 4) if data["impacts_4h"] else 0.0,
                "avg_24h": round(sum(data["impacts_24h"]) / len(data["impacts_24h"]), 4) if data["impacts_24h"] else 0.0,
            }
        return result
