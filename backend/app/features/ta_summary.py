"""TradingView-style Technical Analysis Summary Rating engine."""
import logging

logger = logging.getLogger(__name__)


class TASummaryRating:
    """Computes a TradingView-style TA summary from indicator data."""

    @staticmethod
    def compute(indicators: dict) -> dict:
        """Map 26 indicators to BUY/NEUTRAL/SELL votes and return summary."""
        if not indicators:
            return {"error": "No indicator data"}

        ma_signals = []
        osc_signals = []

        price = indicators.get("price") or indicators.get("current_price", 0)

        # ── Moving Averages (12 signals) ──
        ma_keys = {
            "EMA 9": indicators.get("ema_9"),
            "EMA 21": indicators.get("ema_21"),
            "EMA 50": indicators.get("ema_50"),
            "EMA 200": indicators.get("ema_200"),
            "SMA 20": indicators.get("sma_20"),
            "SMA 50": indicators.get("sma_50"),
            "SMA 111": indicators.get("sma_111"),
            "SMA 200": indicators.get("sma_200"),
            "SMA 350": indicators.get("sma_350"),
            "Ichimoku Tenkan": indicators.get("ichimoku", {}).get("tenkan") if isinstance(indicators.get("ichimoku"), dict) else None,
            "Ichimoku Kijun": indicators.get("ichimoku", {}).get("kijun") if isinstance(indicators.get("ichimoku"), dict) else None,
            "VWAP": indicators.get("vwap"),
        }

        for name, ma_val in ma_keys.items():
            if ma_val is not None and price:
                if price > ma_val:
                    ma_signals.append({"name": name, "value": ma_val, "action": "BUY"})
                elif price < ma_val:
                    ma_signals.append({"name": name, "value": ma_val, "action": "SELL"})
                else:
                    ma_signals.append({"name": name, "value": ma_val, "action": "NEUTRAL"})

        # ── Oscillators (14 signals) ──

        # RSI(14)
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30:
                osc_signals.append({"name": "RSI(14)", "value": rsi, "action": "BUY"})
            elif rsi > 70:
                osc_signals.append({"name": "RSI(14)", "value": rsi, "action": "SELL"})
            else:
                osc_signals.append({"name": "RSI(14)", "value": rsi, "action": "NEUTRAL"})

        # MACD histogram
        macd_hist = indicators.get("macd_histogram") or indicators.get("macd", {}).get("histogram") if isinstance(indicators.get("macd"), dict) else indicators.get("macd_histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                osc_signals.append({"name": "MACD", "value": macd_hist, "action": "BUY"})
            elif macd_hist < 0:
                osc_signals.append({"name": "MACD", "value": macd_hist, "action": "SELL"})
            else:
                osc_signals.append({"name": "MACD", "value": macd_hist, "action": "NEUTRAL"})

        # Stochastic RSI K
        stoch_rsi = indicators.get("stoch_rsi", {})
        stoch_k = stoch_rsi.get("k") if isinstance(stoch_rsi, dict) else indicators.get("stoch_rsi_k")
        if stoch_k is not None:
            if stoch_k < 20:
                osc_signals.append({"name": "Stoch RSI", "value": stoch_k, "action": "BUY"})
            elif stoch_k > 80:
                osc_signals.append({"name": "Stoch RSI", "value": stoch_k, "action": "SELL"})
            else:
                osc_signals.append({"name": "Stoch RSI", "value": stoch_k, "action": "NEUTRAL"})

        # Williams %R
        williams_r = indicators.get("williams_r")
        if williams_r is not None:
            if williams_r < -80:
                osc_signals.append({"name": "Williams %R", "value": williams_r, "action": "BUY"})
            elif williams_r > -20:
                osc_signals.append({"name": "Williams %R", "value": williams_r, "action": "SELL"})
            else:
                osc_signals.append({"name": "Williams %R", "value": williams_r, "action": "NEUTRAL"})

        # ADX
        adx = indicators.get("adx")
        if adx is not None:
            trend_short = indicators.get("trend_short") or indicators.get("trend", {}).get("short") if isinstance(indicators.get("trend"), dict) else None
            if adx > 25 and trend_short == "bullish":
                osc_signals.append({"name": "ADX", "value": adx, "action": "BUY"})
            elif adx > 25 and trend_short == "bearish":
                osc_signals.append({"name": "ADX", "value": adx, "action": "SELL"})
            else:
                osc_signals.append({"name": "ADX", "value": adx, "action": "NEUTRAL"})

        # Bollinger Band position
        bb = indicators.get("bollinger", {}) if isinstance(indicators.get("bollinger"), dict) else {}
        bb_lower = bb.get("lower")
        bb_upper = bb.get("upper")
        bb_position = bb.get("position")
        if bb_position is not None:
            if bb_position < 0.2:
                osc_signals.append({"name": "Bollinger Bands", "value": bb_position, "action": "BUY"})
            elif bb_position > 0.8:
                osc_signals.append({"name": "Bollinger Bands", "value": bb_position, "action": "SELL"})
            else:
                osc_signals.append({"name": "Bollinger Bands", "value": bb_position, "action": "NEUTRAL"})
        elif price and bb_lower and bb_upper:
            if price <= bb_lower:
                osc_signals.append({"name": "Bollinger Bands", "value": price, "action": "BUY"})
            elif price >= bb_upper:
                osc_signals.append({"name": "Bollinger Bands", "value": price, "action": "SELL"})
            else:
                osc_signals.append({"name": "Bollinger Bands", "value": price, "action": "NEUTRAL"})

        # CCI (Commodity Channel Index) — use if available
        cci = indicators.get("cci")
        if cci is not None:
            if cci < -100:
                osc_signals.append({"name": "CCI", "value": cci, "action": "BUY"})
            elif cci > 100:
                osc_signals.append({"name": "CCI", "value": cci, "action": "SELL"})
            else:
                osc_signals.append({"name": "CCI", "value": cci, "action": "NEUTRAL"})

        # MFI (Money Flow Index)
        mfi = indicators.get("mfi")
        if mfi is not None:
            if mfi < 20:
                osc_signals.append({"name": "MFI", "value": mfi, "action": "BUY"})
            elif mfi > 80:
                osc_signals.append({"name": "MFI", "value": mfi, "action": "SELL"})
            else:
                osc_signals.append({"name": "MFI", "value": mfi, "action": "NEUTRAL"})

        # Awesome Oscillator
        ao = indicators.get("awesome_oscillator") or indicators.get("ao")
        if ao is not None:
            if ao > 0:
                osc_signals.append({"name": "AO", "value": ao, "action": "BUY"})
            elif ao < 0:
                osc_signals.append({"name": "AO", "value": ao, "action": "SELL"})
            else:
                osc_signals.append({"name": "AO", "value": ao, "action": "NEUTRAL"})

        # Stochastic K/D
        stoch = indicators.get("stochastic", {}) if isinstance(indicators.get("stochastic"), dict) else {}
        stoch_k_main = stoch.get("k") or indicators.get("stoch_k")
        stoch_d_main = stoch.get("d") or indicators.get("stoch_d")
        if stoch_k_main is not None and stoch_d_main is not None:
            if stoch_k_main < 20 and stoch_k_main > stoch_d_main:
                osc_signals.append({"name": "Stochastic", "value": stoch_k_main, "action": "BUY"})
            elif stoch_k_main > 80 and stoch_k_main < stoch_d_main:
                osc_signals.append({"name": "Stochastic", "value": stoch_k_main, "action": "SELL"})
            else:
                osc_signals.append({"name": "Stochastic", "value": stoch_k_main, "action": "NEUTRAL"})

        # Ultimate Oscillator
        uo = indicators.get("ultimate_oscillator") or indicators.get("uo")
        if uo is not None:
            if uo < 30:
                osc_signals.append({"name": "UO", "value": uo, "action": "BUY"})
            elif uo > 70:
                osc_signals.append({"name": "UO", "value": uo, "action": "SELL"})
            else:
                osc_signals.append({"name": "UO", "value": uo, "action": "NEUTRAL"})

        # BOP (Balance of Power)
        bop = indicators.get("balance_of_power") or indicators.get("bop")
        if bop is not None:
            if bop > 0:
                osc_signals.append({"name": "BOP", "value": bop, "action": "BUY"})
            elif bop < 0:
                osc_signals.append({"name": "BOP", "value": bop, "action": "SELL"})
            else:
                osc_signals.append({"name": "BOP", "value": bop, "action": "NEUTRAL"})

        # Trend Short
        trend_short = indicators.get("trend_short") or (indicators.get("trend", {}).get("short") if isinstance(indicators.get("trend"), dict) else None)
        if trend_short:
            if trend_short == "bullish":
                osc_signals.append({"name": "Trend (Short)", "value": trend_short, "action": "BUY"})
            elif trend_short == "bearish":
                osc_signals.append({"name": "Trend (Short)", "value": trend_short, "action": "SELL"})
            else:
                osc_signals.append({"name": "Trend (Short)", "value": trend_short, "action": "NEUTRAL"})

        # ── Compute totals ──
        all_signals = ma_signals + osc_signals
        buy_count = sum(1 for s in all_signals if s["action"] == "BUY")
        neutral_count = sum(1 for s in all_signals if s["action"] == "NEUTRAL")
        sell_count = sum(1 for s in all_signals if s["action"] == "SELL")
        total = len(all_signals) or 1

        ma_buy = sum(1 for s in ma_signals if s["action"] == "BUY")
        ma_neutral = sum(1 for s in ma_signals if s["action"] == "NEUTRAL")
        ma_sell = sum(1 for s in ma_signals if s["action"] == "SELL")

        osc_buy = sum(1 for s in osc_signals if s["action"] == "BUY")
        osc_neutral = sum(1 for s in osc_signals if s["action"] == "NEUTRAL")
        osc_sell = sum(1 for s in osc_signals if s["action"] == "SELL")

        # Score: -1 (all sell) to +1 (all buy)
        score = (buy_count - sell_count) / total

        # Overall rating
        if score >= 0.5:
            overall = "STRONG_BUY"
        elif score >= 0.1:
            overall = "BUY"
        elif score <= -0.5:
            overall = "STRONG_SELL"
        elif score <= -0.1:
            overall = "SELL"
        else:
            overall = "NEUTRAL"

        return {
            "overall": overall,
            "overall_score": round(score, 4),
            "summary": {
                "buy": buy_count,
                "neutral": neutral_count,
                "sell": sell_count,
                "total": total,
            },
            "moving_averages": {
                "rating": "BUY" if ma_buy > ma_sell else "SELL" if ma_sell > ma_buy else "NEUTRAL",
                "buy": ma_buy,
                "neutral": ma_neutral,
                "sell": ma_sell,
                "signals": ma_signals,
            },
            "oscillators": {
                "rating": "BUY" if osc_buy > osc_sell else "SELL" if osc_sell > osc_buy else "NEUTRAL",
                "buy": osc_buy,
                "neutral": osc_neutral,
                "sell": osc_sell,
                "signals": osc_signals,
            },
        }
