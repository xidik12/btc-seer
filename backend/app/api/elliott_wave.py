"""Elliott Wave Analysis API endpoints.

Detects swing points, labels impulse/corrective wave patterns,
calculates Fibonacci projections, and detects RSI/MACD divergences.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/elliott-wave", tags=["elliott-wave"])

FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.618]


# ── Technical helpers (standalone, mirroring TechnicalFeatures) ──


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def _macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return macd_line, signal, hist


# ── Swing Detection ──


def find_swing_points(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    atr_values: pd.Series,
    lookback: int = 5,
) -> List[dict]:
    """Detect swing highs and lows with ATR noise filter."""
    swings = []
    n = len(highs)

    for i in range(lookback, n - lookback):
        window_highs = highs.iloc[i - lookback : i + lookback + 1]
        window_lows = lows.iloc[i - lookback : i + lookback + 1]
        atr_val = atr_values.iloc[i]
        if pd.isna(atr_val) or atr_val == 0:
            continue

        is_swing_high = highs.iloc[i] >= window_highs.max()
        is_swing_low = lows.iloc[i] <= window_lows.min()

        if is_swing_high:
            price = float(highs.iloc[i])
            if swings and abs(price - swings[-1]["price"]) < 0.3 * atr_val:
                continue
            swings.append({
                "index": i,
                "type": "high",
                "price": price,
            })
        elif is_swing_low:
            price = float(lows.iloc[i])
            if swings and abs(price - swings[-1]["price"]) < 0.3 * atr_val:
                continue
            swings.append({
                "index": i,
                "type": "low",
                "price": price,
            })

    # Ensure alternating high/low
    filtered = []
    for s in swings:
        if not filtered or filtered[-1]["type"] != s["type"]:
            filtered.append(s)
        else:
            # Keep the more extreme one
            if s["type"] == "high" and s["price"] > filtered[-1]["price"]:
                filtered[-1] = s
            elif s["type"] == "low" and s["price"] < filtered[-1]["price"]:
                filtered[-1] = s

    return filtered


# ── Wave Labeling ──


def label_waves(swings: List[dict]) -> dict:
    """Try to fit impulse (5-wave) or corrective pattern from recent swings."""
    if len(swings) < 6:
        return {
            "pattern": "insufficient_data",
            "current_wave": "?",
            "direction": "neutral",
            "waves": [],
            "confidence": 0.0,
        }

    # Try impulse from the last 8+ swings
    result = _try_impulse(swings)
    if result:
        return result

    # Fallback to corrective
    result = _try_corrective(swings)
    if result:
        return result

    return {
        "pattern": "unclear",
        "current_wave": "?",
        "direction": "neutral",
        "waves": [],
        "confidence": 0.2,
    }


def _try_impulse(swings: List[dict]) -> Optional[dict]:
    """Try to identify a 5-wave impulse pattern."""
    # Need at least 6 swing points for 5 waves
    candidates = swings[-10:]  # Look at recent swings
    if len(candidates) < 6:
        return None

    # Determine direction from first two swings
    if candidates[0]["type"] == "low":
        direction = "bullish"
    else:
        direction = "bearish"

    # Try to extract 5 waves from the last 6+ swings
    wave_points = candidates[-6:]

    if direction == "bullish":
        # Bullish impulse: low-high-low-high-low-high (W1↑ W2↓ W3↑ W4↓ W5↑)
        if wave_points[0]["type"] != "low":
            wave_points = candidates[-7:-1] if len(candidates) >= 7 else None
            if not wave_points or wave_points[0]["type"] != "low":
                return None

        waves = [
            {"label": "1", "start_price": wave_points[0]["price"], "end_price": wave_points[1]["price"],
             "start_idx": wave_points[0]["index"], "end_idx": wave_points[1]["index"]},
            {"label": "2", "start_price": wave_points[1]["price"], "end_price": wave_points[2]["price"],
             "start_idx": wave_points[1]["index"], "end_idx": wave_points[2]["index"]},
            {"label": "3", "start_price": wave_points[2]["price"], "end_price": wave_points[3]["price"],
             "start_idx": wave_points[2]["index"], "end_idx": wave_points[3]["index"]},
            {"label": "4", "start_price": wave_points[3]["price"], "end_price": wave_points[4]["price"],
             "start_idx": wave_points[3]["index"], "end_idx": wave_points[4]["index"]},
            {"label": "5", "start_price": wave_points[4]["price"], "end_price": wave_points[5]["price"],
             "start_idx": wave_points[4]["index"], "end_idx": wave_points[5]["index"]},
        ]

        # Validate rules
        w1_range = waves[0]["end_price"] - waves[0]["start_price"]
        w2_retrace = waves[0]["end_price"] - waves[1]["end_price"]
        w3_range = waves[2]["end_price"] - waves[2]["start_price"]
        w5_range = waves[4]["end_price"] - waves[4]["start_price"]

        # Rule 1: Wave 2 never retraces > 100% of Wave 1
        if w2_retrace > w1_range:
            return None

        # Rule 2: Wave 3 never shortest of 1, 3, 5
        if w3_range < w1_range and w3_range < w5_range:
            return None

        # Rule 3: Wave 4 never overlaps Wave 1 territory
        if waves[3]["end_price"] < waves[0]["end_price"]:
            return None

    else:
        # Bearish impulse: high-low-high-low-high-low
        if wave_points[0]["type"] != "high":
            wave_points = candidates[-7:-1] if len(candidates) >= 7 else None
            if not wave_points or wave_points[0]["type"] != "high":
                return None

        waves = [
            {"label": "1", "start_price": wave_points[0]["price"], "end_price": wave_points[1]["price"],
             "start_idx": wave_points[0]["index"], "end_idx": wave_points[1]["index"]},
            {"label": "2", "start_price": wave_points[1]["price"], "end_price": wave_points[2]["price"],
             "start_idx": wave_points[1]["index"], "end_idx": wave_points[2]["index"]},
            {"label": "3", "start_price": wave_points[2]["price"], "end_price": wave_points[3]["price"],
             "start_idx": wave_points[2]["index"], "end_idx": wave_points[3]["index"]},
            {"label": "4", "start_price": wave_points[3]["price"], "end_price": wave_points[4]["price"],
             "start_idx": wave_points[3]["index"], "end_idx": wave_points[4]["index"]},
            {"label": "5", "start_price": wave_points[4]["price"], "end_price": wave_points[5]["price"],
             "start_idx": wave_points[4]["index"], "end_idx": wave_points[5]["index"]},
        ]

        w1_range = abs(waves[0]["start_price"] - waves[0]["end_price"])
        w2_retrace = abs(waves[1]["end_price"] - waves[1]["start_price"])
        w3_range = abs(waves[2]["start_price"] - waves[2]["end_price"])
        w5_range = abs(waves[4]["start_price"] - waves[4]["end_price"])

        if w2_retrace > w1_range:
            return None
        if w3_range < w1_range and w3_range < w5_range:
            return None
        if waves[3]["end_price"] > waves[0]["end_price"]:
            return None

    # Determine current wave (which one is still forming)
    current_wave = "5"
    confidence = 0.65

    # Higher confidence if wave 3 is longest
    if w3_range >= w1_range and w3_range >= w5_range:
        confidence += 0.15

    return {
        "pattern": "impulse",
        "current_wave": current_wave,
        "direction": direction,
        "waves": waves,
        "confidence": round(min(confidence, 1.0), 2),
    }


def _try_corrective(swings: List[dict]) -> Optional[dict]:
    """Try to identify a corrective (ABC) pattern from recent swings."""
    if len(swings) < 4:
        return None

    recent = swings[-4:]
    # ABC correction: 3 waves
    waves = [
        {"label": "A", "start_price": recent[0]["price"], "end_price": recent[1]["price"],
         "start_idx": recent[0]["index"], "end_idx": recent[1]["index"]},
        {"label": "B", "start_price": recent[1]["price"], "end_price": recent[2]["price"],
         "start_idx": recent[1]["index"], "end_idx": recent[2]["index"]},
        {"label": "C", "start_price": recent[2]["price"], "end_price": recent[3]["price"],
         "start_idx": recent[2]["index"], "end_idx": recent[3]["index"]},
    ]

    a_range = abs(waves[0]["end_price"] - waves[0]["start_price"])
    c_range = abs(waves[2]["end_price"] - waves[2]["start_price"])

    # Determine type: zigzag if C >= A, flat if C < A
    if recent[0]["type"] == "high":
        direction = "bearish"
    else:
        direction = "bullish"

    return {
        "pattern": "corrective",
        "current_wave": "C",
        "direction": direction,
        "waves": waves,
        "confidence": 0.5,
    }


# ── Fibonacci Projections ──


def calculate_fib_targets(waves: List[dict], direction: str) -> dict:
    """Calculate Fibonacci support/resistance levels from wave structure."""
    support_levels = []
    resistance_levels = []

    if not waves or len(waves) < 2:
        return {"support_levels": [], "resistance_levels": []}

    # Use wave 1 range as the base measurement
    w1 = waves[0]
    w1_range = abs(w1["end_price"] - w1["start_price"])

    if w1_range == 0:
        return {"support_levels": [], "resistance_levels": []}

    last_wave = waves[-1]
    ref_price = last_wave["end_price"]

    if direction == "bullish":
        # Resistance projections above current
        for ratio in FIB_RATIOS:
            price = ref_price + w1_range * ratio
            resistance_levels.append({
                "price": round(price, 2),
                "ratio": ratio,
                "label": f"{ratio:.3f} extension",
            })
        # Support retracement below current
        for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
            price = ref_price - w1_range * ratio
            support_levels.append({
                "price": round(price, 2),
                "ratio": ratio,
                "label": f"{ratio:.3f} retracement",
            })
    else:
        # Bearish — support below, resistance above
        for ratio in FIB_RATIOS:
            price = ref_price - w1_range * ratio
            support_levels.append({
                "price": round(price, 2),
                "ratio": ratio,
                "label": f"{ratio:.3f} extension",
            })
        for ratio in [0.236, 0.382, 0.5, 0.618, 0.786]:
            price = ref_price + w1_range * ratio
            resistance_levels.append({
                "price": round(price, 2),
                "ratio": ratio,
                "label": f"{ratio:.3f} retracement",
            })

    # Sort by price
    support_levels.sort(key=lambda x: x["price"], reverse=True)
    resistance_levels.sort(key=lambda x: x["price"])

    return {
        "support_levels": support_levels,
        "resistance_levels": resistance_levels,
    }


# ── Divergence Detection (Elder method) ──


def detect_divergences(
    closes: pd.Series,
    rsi: pd.Series,
    macd_hist: pd.Series,
    swing_points: List[dict],
) -> List[dict]:
    """Detect bullish/bearish divergences between price and indicators."""
    divergences = []

    # Need at least 2 swing lows and 2 swing highs
    swing_lows = [s for s in swing_points if s["type"] == "low"]
    swing_highs = [s for s in swing_points if s["type"] == "high"]

    # Bullish divergence: price makes lower low, indicator makes higher low
    for i in range(1, len(swing_lows)):
        prev = swing_lows[i - 1]
        curr = swing_lows[i]

        if curr["price"] < prev["price"]:
            # Check RSI
            prev_rsi = rsi.iloc[prev["index"]] if prev["index"] < len(rsi) else None
            curr_rsi = rsi.iloc[curr["index"]] if curr["index"] < len(rsi) else None
            if prev_rsi is not None and curr_rsi is not None and not pd.isna(prev_rsi) and not pd.isna(curr_rsi):
                if curr_rsi > prev_rsi:
                    strength = min(abs(curr_rsi - prev_rsi) / 20, 1.0)
                    divergences.append({
                        "type": "bullish",
                        "indicator": "RSI",
                        "strength": round(strength, 2),
                        "price": curr["price"],
                        "index": curr["index"],
                    })

            # Check MACD histogram
            prev_macd = macd_hist.iloc[prev["index"]] if prev["index"] < len(macd_hist) else None
            curr_macd = macd_hist.iloc[curr["index"]] if curr["index"] < len(macd_hist) else None
            if prev_macd is not None and curr_macd is not None and not pd.isna(prev_macd) and not pd.isna(curr_macd):
                if curr_macd > prev_macd:
                    strength = min(abs(curr_macd - prev_macd) / (abs(prev_macd) + 1e-9), 1.0)
                    divergences.append({
                        "type": "bullish",
                        "indicator": "MACD",
                        "strength": round(strength, 2),
                        "price": curr["price"],
                        "index": curr["index"],
                    })

    # Bearish divergence: price makes higher high, indicator makes lower high
    for i in range(1, len(swing_highs)):
        prev = swing_highs[i - 1]
        curr = swing_highs[i]

        if curr["price"] > prev["price"]:
            prev_rsi = rsi.iloc[prev["index"]] if prev["index"] < len(rsi) else None
            curr_rsi = rsi.iloc[curr["index"]] if curr["index"] < len(rsi) else None
            if prev_rsi is not None and curr_rsi is not None and not pd.isna(prev_rsi) and not pd.isna(curr_rsi):
                if curr_rsi < prev_rsi:
                    strength = min(abs(prev_rsi - curr_rsi) / 20, 1.0)
                    divergences.append({
                        "type": "bearish",
                        "indicator": "RSI",
                        "strength": round(strength, 2),
                        "price": curr["price"],
                        "index": curr["index"],
                    })

            prev_macd = macd_hist.iloc[prev["index"]] if prev["index"] < len(macd_hist) else None
            curr_macd = macd_hist.iloc[curr["index"]] if curr["index"] < len(macd_hist) else None
            if prev_macd is not None and curr_macd is not None and not pd.isna(prev_macd) and not pd.isna(curr_macd):
                if curr_macd < prev_macd:
                    strength = min(abs(prev_macd - curr_macd) / (abs(prev_macd) + 1e-9), 1.0)
                    divergences.append({
                        "type": "bearish",
                        "indicator": "MACD",
                        "strength": round(strength, 2),
                        "price": curr["price"],
                        "index": curr["index"],
                    })

    # Keep only recent divergences (last 3)
    return divergences[-6:]


# ── Build analysis from price data ──


def _analyze(df: pd.DataFrame, lookback: int = 5) -> dict:
    """Run full Elliott Wave analysis on a price DataFrame."""
    if df.empty or len(df) < 30:
        return {
            "wave_count": {
                "pattern": "insufficient_data",
                "current_wave": "?",
                "direction": "neutral",
                "waves": [],
            },
            "fibonacci_targets": {"support_levels": [], "resistance_levels": []},
            "divergences": [],
            "confidence": 0.0,
            "summary": "Not enough price data for Elliott Wave analysis.",
        }

    atr_vals = _atr(df, 14)
    rsi_vals = _rsi(df["close"], 14)
    _, _, macd_hist_vals = _macd(df["close"])

    swings = find_swing_points(df["high"], df["low"], df["close"], atr_vals, lookback=lookback)
    wave_count = label_waves(swings)
    fib_targets = calculate_fib_targets(wave_count["waves"], wave_count["direction"])
    divergences_raw = detect_divergences(df["close"], rsi_vals, macd_hist_vals, swings)

    # Add timestamps to divergences
    divergences = []
    for d in divergences_raw:
        idx = d["index"]
        ts = df["timestamp"].iloc[idx].isoformat() if idx < len(df) else None
        divergences.append({
            "type": d["type"],
            "indicator": d["indicator"],
            "strength": d["strength"],
            "price": d["price"],
            "timestamp": ts,
        })

    # Add dates to waves
    for w in wave_count["waves"]:
        si = w.pop("start_idx", None)
        ei = w.pop("end_idx", None)
        w["start_date"] = df["timestamp"].iloc[si].isoformat() if si is not None and si < len(df) else None
        w["end_date"] = df["timestamp"].iloc[ei].isoformat() if ei is not None and ei < len(df) else None

    # Generate summary
    direction = wave_count["direction"]
    pattern = wave_count["pattern"]
    current = wave_count["current_wave"]
    if pattern == "impulse":
        summary = f"BTC is in Wave {current} of a {direction} impulse pattern."
    elif pattern == "corrective":
        summary = f"BTC is in Wave {current} of a {direction} corrective pattern."
    else:
        summary = f"Elliott Wave pattern is {pattern}. More data needed for clear wave count."

    if divergences:
        last_div = divergences[-1]
        summary += f" {last_div['type'].capitalize()} divergence detected on {last_div['indicator']}."

    return {
        "wave_count": {
            "pattern": wave_count["pattern"],
            "current_wave": wave_count["current_wave"],
            "direction": wave_count["direction"],
            "waves": wave_count["waves"],
        },
        "fibonacci_targets": fib_targets,
        "divergences": divergences,
        "confidence": wave_count["confidence"],
        "summary": summary,
        "swings": swings,
    }


# ── Endpoints ──


TIMEFRAME_CONFIG = {
    "1h": {"resample": "1h", "days": 30, "lookback": 3},
    "4h": {"resample": "4h", "days": 120, "lookback": 5},
    "1d": {"resample": "1D", "days": 365, "lookback": 5},
    "1w": {"resample": "W", "days": 730, "lookback": 8},
    "1mo": {"resample": "ME", "days": 1095, "lookback": 10},
}


@router.get("/current")
async def get_elliott_wave_current(
    timeframe: str = Query("4h", regex="^(1h|4h|1d|1w|1mo)$"),
    session: AsyncSession = Depends(get_session),
):
    """Current Elliott Wave analysis for BTC."""
    cfg = TIMEFRAME_CONFIG[timeframe]
    since = datetime.utcnow() - timedelta(days=cfg["days"])
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    if not prices:
        return {
            "current_price": None,
            "timeframe": timeframe,
            "wave_count": {"pattern": "no_data", "current_wave": "?", "direction": "neutral", "waves": []},
            "fibonacci_targets": {"support_levels": [], "resistance_levels": []},
            "divergences": [],
            "confidence": 0.0,
            "summary": "No price data available.",
        }

    df = pd.DataFrame([
        {"timestamp": p.timestamp, "open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
        for p in prices
    ])

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").resample(cfg["resample"]).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna().reset_index()

    current_price = float(df["close"].iloc[-1]) if len(df) > 0 else None
    analysis = _analyze(df, lookback=cfg["lookback"])

    # Remove internal swings from response
    analysis.pop("swings", None)

    return {
        "current_price": current_price,
        "timeframe": timeframe,
        **analysis,
    }


@router.get("/historical")
async def get_elliott_wave_historical(
    days: int = Query(90, ge=7, le=1095),
    timeframe: str = Query("4h", regex="^(1h|4h|1d|1w|1mo)$"),
    session: AsyncSession = Depends(get_session),
):
    """Historical wave data for charting."""
    cfg = TIMEFRAME_CONFIG[timeframe]
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    if not prices:
        return {"days": days, "timeframe": timeframe, "points": [], "waves": [], "fib_levels": []}

    df = pd.DataFrame([
        {"timestamp": p.timestamp, "open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
        for p in prices
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").resample(cfg["resample"]).agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
    }).dropna().reset_index()

    analysis = _analyze(df, lookback=cfg["lookback"])
    swings = analysis.pop("swings", [])

    # Build swing set for quick lookup
    swing_indices = {s["index"] for s in swings}
    swing_labels = {}
    for w in analysis["wave_count"]["waves"]:
        # Find the swing point closest to wave start/end dates
        pass  # labels are already in waves

    # Daily points for the chart
    points = []
    for i, row in df.iterrows():
        is_swing = i in swing_indices
        swing_info = next((s for s in swings if s["index"] == i), None)
        points.append({
            "date": row["timestamp"].isoformat(),
            "price": round(float(row["close"]), 2),
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "wave_label": None,
            "is_swing": is_swing,
            "swing_type": swing_info["type"] if swing_info else None,
        })

    # Merge wave labels onto points
    for w in analysis["wave_count"]["waves"]:
        end_date = w.get("end_date")
        if end_date:
            for pt in points:
                if pt["date"] == end_date:
                    pt["wave_label"] = w["label"]
                    break

    # Combine fib levels
    fib_levels = []
    for lvl in analysis["fibonacci_targets"].get("support_levels", []):
        fib_levels.append({**lvl, "type": "support"})
    for lvl in analysis["fibonacci_targets"].get("resistance_levels", []):
        fib_levels.append({**lvl, "type": "resistance"})

    return {
        "days": days,
        "points": points,
        "waves": analysis["wave_count"]["waves"],
        "fib_levels": fib_levels,
    }
