# Bitcoin Market Cycle Theories & Prediction Models
## Comprehensive Research for BTC Oracle Implementation

---

## Table of Contents
1. [Bitcoin Halving Cycle Theory](#1-bitcoin-halving-cycle-theory)
2. [Wyckoff Method Applied to BTC](#2-wyckoff-method-applied-to-btc)
3. [Elliott Wave Theory for BTC](#3-elliott-wave-theory-for-btc)
4. [Market Microstructure Signals](#4-market-microstructure-signals)
5. [Sentiment-Based Models](#5-sentiment-based-models)
6. [Correlation-Based Models](#6-correlation-based-models)
7. [Volatility Models (GARCH)](#7-volatility-models-garch)
8. [Mean Reversion vs Momentum](#8-mean-reversion-vs-momentum)
9. [Key Price Levels](#9-key-price-levels)
10. [Professional Trading Strategies](#10-professional-trading-strategies)
11. [On-Chain Valuation Models](#11-on-chain-valuation-models)
12. [Combining Multiple Signals](#12-combining-multiple-signals)

---

## 1. Bitcoin Halving Cycle Theory

### Core Theory
Bitcoin's block reward halves approximately every 210,000 blocks (~4 years), reducing new supply by 50%. This supply shock historically triggers bull markets 12-18 months post-halving.

### Historical Data

| Halving | Date | Price at Halving | Cycle Peak | Peak Date | ROI to Peak | Days to Peak |
|---------|------|-----------------|------------|-----------|-------------|--------------|
| 1st | Nov 2012 | ~$12 | ~$1,100 | Dec 2013 | ~9,000% | ~365 |
| 2nd | Jul 2016 | ~$650 | ~$19,700 | Dec 2017 | ~2,930% | ~525 |
| 3rd | May 2020 | ~$8,700 | ~$69,000 | Nov 2021 | ~690% | ~546 |
| 4th | Apr 2024 | ~$64,000 | TBD | TBD | TBD | TBD |

### Diminishing Returns Pattern
Each cycle produces diminishing returns: ~9,000% -> ~2,930% -> ~690%. Applying this decay pattern:
- **Decay factor**: roughly 1/3 to 1/4 of previous cycle
- **Projected 4th cycle ROI**: ~150-250% from halving price
- **Implied peak range**: ~$160,000-$224,000

### Formula for Cycle Position
```
cycle_progress = (current_block - last_halving_block) / 210000
days_since_halving = (current_date - halving_date).days
typical_peak_window = 480 to 550 days post-halving
```

### Implementation Parameters
- **Best timeframe**: Weekly/Monthly (macro view)
- **Typical peak window**: 480-550 days post-halving (historically within 3 days accuracy for Pi Cycle)
- **Buy zone**: 12-18 months BEFORE halving (accumulation)
- **Sell zone**: 12-18 months AFTER halving (distribution)

### Historical Accuracy
- The 4-year cycle pattern has held for 3 consecutive cycles
- Post-2024 halving: BTC rose 41.2% in first 200 days (underperforming prior cycles of 53.3% and 122.5%)
- Supply shock becoming more subdued: supply reduction went from 1.7% to 0.85%
- Institutional capital (ETFs) may be dampening volatility and elongating cycles

### Limitations
- Only 4 data points (small sample)
- ETF inflows are changing market structure
- "This time is different" risk from institutional adoption

---

## 2. Wyckoff Method Applied to BTC

### Core Theory
Markets move through 4 phases driven by institutional ("Composite Man") activity:
1. **Accumulation** (smart money buys)
2. **Markup** (price rises)
3. **Distribution** (smart money sells)
4. **Markdown** (price falls)

### Accumulation Schematic — Phases & Events

#### Phase A: Stopping the Downtrend
| Event | Abbreviation | Detection Criteria |
|-------|-------------|-------------------|
| Preliminary Support | PS | First buying interest; moderate volume increase on down move |
| Selling Climax | SC | Wide spread, heavy volume, panic selling; sharp low |
| Automatic Rally | AR | Short covering bounce; sets upper range boundary |
| Secondary Test | ST | Retest of SC low with LOWER volume; confirms selling exhaustion |

#### Phase B: Building the Cause (Consolidation)
- Multiple STs within the range
- Volume gradually decreases
- Range-bound price action with tests of both support (SC area) and resistance (AR area)
- Duration: typically 30-90 days for BTC

#### Phase C: The Spring (Shakeout)
- **Spring**: Price briefly breaks BELOW the trading range (below SC low), then reverses sharply
- **Purpose**: Triggers stop losses, shakes out weak hands, allows institutions to buy cheaply
- **Detection**: Low volume break below range + immediate reversal back into range
- **Test of Spring**: Low-volume retest that holds above the Spring low — confirms supply is exhausted

#### Phase D: Sign of Strength
| Event | Detection |
|-------|-----------|
| Sign of Strength (SOS) | Strong up move with high volume and widening spread |
| Last Point of Support (LPS) | Pullback on low volume; higher low than Spring |
| Backup (BU) | Retest of resistance (former AR level) as new support |

#### Phase E: Markup
- Price leaves the trading range
- Demand in full control
- Reactions are short-lived

### Algorithmic Detection Rules
```python
def detect_wyckoff_accumulation(candles, volume):
    # Phase A Detection
    sc = find_selling_climax(candles, volume)
    # Criteria: Largest volume bar in last N periods + sharp price drop
    # sc_volume > 2 * avg_volume(20) AND price_drop > 2 * ATR(14)

    ar = find_automatic_rally(candles, after=sc)
    # Criteria: Sharp bounce within 1-5 bars of SC

    range_high = ar.high
    range_low = sc.low

    st = find_secondary_test(candles, volume, sc_low=range_low)
    # Criteria: Price approaches SC low but volume < 70% of SC volume

    # Phase B: Consolidation
    # Price stays within range for 20+ bars on declining volume

    # Phase C: Spring Detection
    spring = detect_spring(candles, volume, range_low)
    # Criteria: Price breaks below range_low by 0.5-3%
    # Then closes back inside range within 1-3 bars
    # Volume at spring < 50% of SC volume

    # Phase D: SOS
    sos = detect_sign_of_strength(candles, volume, range_high)
    # Criteria: Price breaks above range_high with volume > 1.5x average

    return WyckoffAccumulation(sc, ar, st, spring, sos)
```

### Best Timeframe
- **Primary**: 4H and Daily charts for BTC
- **Confirmation**: Weekly chart for major cycle identification
- **Historical accuracy**: Previous Wyckoff patterns have preceded 40%+ BTC rallies

### Limitations
- Subjective: different traders see different patterns
- False springs (fakeouts) are common in crypto
- Requires patience — full accumulation can take 1-6 months

---

## 3. Elliott Wave Theory for BTC

### Core Structure
Price moves in **5 waves** with the trend (impulse) and **3 waves** against (correction):

```
Impulse (Motive) Wave:
Wave 1: Initial move up
Wave 2: Correction (typically 50-61.8% retracement of Wave 1)
Wave 3: Strongest wave (typically 1.618x or 2.618x of Wave 1)
Wave 4: Correction (typically 38.2% retracement of Wave 3)
Wave 5: Final push (often equal to Wave 1 or 0.618x of Wave 1-3)

Corrective Wave:
Wave A: First move down
Wave B: Partial retracement (50-78.6% of Wave A)
Wave C: Final move down (typically equal to Wave A or 1.618x Wave A)
```

### Rules (Must NEVER be violated)
1. Wave 2 cannot retrace more than 100% of Wave 1
2. Wave 3 can never be the shortest of waves 1, 3, and 5
3. Wave 4 cannot enter the price territory of Wave 1

### Key Fibonacci Ratios
| Wave | Typical Fibonacci Relationship |
|------|-------------------------------|
| Wave 2 | 0.500, 0.618, 0.786 of Wave 1 |
| Wave 3 | 1.618, 2.000, 2.618 of Wave 1 |
| Wave 4 | 0.236, 0.382 of Wave 3 |
| Wave 5 | 0.618, 1.000 of Wave 1; or 0.382 of Wave 1-3 |
| Wave A | 0.382, 0.500, 0.618 of Wave 5 |
| Wave B | 0.382, 0.500, 0.618 of Wave A |
| Wave C | 1.000, 1.618 of Wave A |

### Implementation
```python
def identify_wave(price_data, lookback=200):
    # Find significant swing highs and lows
    swings = find_swing_points(price_data, threshold=ATR(14) * 1.5)

    # Attempt wave counting
    for possible_wave_1_start in swings:
        wave_1_end = next_swing(swings, after=possible_wave_1_start)
        wave_1_size = abs(wave_1_end - possible_wave_1_start)

        wave_2_end = next_swing(swings, after=wave_1_end)
        wave_2_retrace = abs(wave_2_end - wave_1_end) / wave_1_size

        # Rule check: Wave 2 must not retrace > 100%
        if wave_2_retrace > 1.0:
            continue

        # Check if Wave 2 retracement is in valid Fibonacci zone
        if wave_2_retrace in [0.382, 0.500, 0.618, 0.786]:  # with tolerance
            # Continue counting Wave 3, 4, 5...
            pass

    return wave_count
```

### Historical Accuracy
- **50-72% accuracy** in studies — critics describe this as near-random
- **65% of assets**: Elliott Waves deemed too unreliable for trading
- **Best use case**: Identifying major trend changes and turning points
- **Must combine** with other methods (RSI, volume, support/resistance)

### Best Timeframe
- **Weekly/Monthly**: For identifying macro Bitcoin supercycles
- **4H/Daily**: For sub-wave counting within a known macro wave
- **Never rely on alone** — always confirm with momentum indicators

---

## 4. Market Microstructure Signals

### 4.1 Funding Rates

#### Formula
```
Funding Rate = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
Typical range: -0.1% to +0.3% per 8 hours
```

#### Signal Interpretation
| Funding Rate | Signal | Action |
|-------------|--------|--------|
| > 0.05%/8h | Extreme long leverage | Bearish warning — longs overcrowded |
| > 0.1%/8h | Critical leverage | High probability of long squeeze |
| < -0.01%/8h | Shorts paying | Bullish — shorts overcrowded |
| < -0.05%/8h | Extreme short leverage | High probability of short squeeze |
| ~0.01%/8h | Neutral | Normal market conditions |

#### Historical Accuracy
- Funding rates > 0.05%/8h have preceded 70%+ of major corrections
- Sustained negative funding during uptrends = strong bullish signal

### 4.2 Open Interest (OI)

#### Signals
| OI Change | Price Change | Interpretation |
|-----------|-------------|----------------|
| OI Rising | Price Rising | New longs opening — trend continuation |
| OI Rising | Price Falling | New shorts opening — trend continuation down |
| OI Falling | Price Rising | Short covering rally — potential fakeout |
| OI Falling | Price Falling | Long liquidation — capitulation |

#### Formula for OI-Price Divergence
```python
oi_change_pct = (current_oi - oi_24h_ago) / oi_24h_ago * 100
price_change_pct = (current_price - price_24h_ago) / price_24h_ago * 100

# Divergence signal
if oi_change_pct > 5 and price_change_pct < -2:
    signal = "aggressive_short_opening"  # bearish
elif oi_change_pct < -10 and price_change_pct < -5:
    signal = "long_liquidation_cascade"  # capitulation — often a bottom
elif oi_change_pct > 5 and price_change_pct > 3:
    signal = "new_longs_trend_continuation"
```

### 4.3 Liquidation Cascades

#### Detection Algorithm
```python
def detect_liquidation_cascade(liquidation_data, threshold_multiplier=5):
    avg_hourly_liquidations = rolling_mean(liquidation_data, window=24)
    current_hourly = liquidation_data[-1]

    if current_hourly > avg_hourly_liquidations * threshold_multiplier:
        cascade_detected = True
        # During Oct 2025 crash: baseline $0.71B/hr -> $10.39B/hr (14.6x)
        # Spreads widened 1,321x (0.02 bps -> 26.43 bps)

    # Cascade conditions:
    # 1. Funding rate > 0.05%/hr
    # 2. OI declining rapidly (>10% in 1 hour)
    # 3. Liquidation volume > 5x baseline
    # 4. Bid-ask spread widening > 10x normal
```

### 4.4 Order Book Analysis

#### Key Metrics
```python
# Bid-Ask Imbalance
imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
# Range: -1 (all asks, bearish) to +1 (all bids, bullish)

# Order Book Depth Ratio
depth_ratio = bid_depth_within_1pct / ask_depth_within_1pct
# > 1.5: Strong support (bullish)
# < 0.67: Strong resistance (bearish)

# Spoofing Detection
if large_order_appeared and large_order_cancelled_within_seconds:
    possible_spoof = True
```

### Best Timeframe
- **Funding rates**: 8H periods, but monitor continuously
- **OI**: 4H and Daily
- **Liquidations**: Real-time / 1H
- **Order book**: Real-time (5s-1min snapshots)

---

## 5. Sentiment-Based Models

### 5.1 Fear & Greed Index

#### Components & Weights
| Component | Weight | Source |
|-----------|--------|--------|
| Volatility | 25% | BTC 30/90-day volatility vs averages |
| Market Momentum/Volume | 25% | Current volume vs 30/90-day averages |
| Social Media | 15% | Twitter/Reddit mention rate and sentiment |
| Surveys | 15% | Polling data (when available) |
| Bitcoin Dominance | 10% | BTC market cap % vs altcoins |
| Google Trends | 10% | Search volume for "Bitcoin" related terms |

#### Signal Zones
| Index Value | Zone | Historical Signal |
|------------|------|------------------|
| 0-10 | Extreme Fear | Strong buy signal (contrarian) |
| 10-25 | Fear | Buy signal |
| 25-45 | Neutral-Fear | Mild buy |
| 45-55 | Neutral | No signal |
| 55-75 | Greed | Caution |
| 75-90 | Extreme Greed | Sell/reduce signal |
| 90-100 | Peak Euphoria | Strong sell signal |

#### Implementation
```python
def fear_greed_signal(index_value, lookback_days=7):
    # Extreme reversals
    if index_value < 15:
        return {"signal": "STRONG_BUY", "confidence": 0.75}
    elif index_value < 25:
        return {"signal": "BUY", "confidence": 0.60}
    elif index_value > 85:
        return {"signal": "STRONG_SELL", "confidence": 0.70}
    elif index_value > 75:
        return {"signal": "SELL", "confidence": 0.55}

    # Trend change detection
    avg_7d = rolling_mean(index_history, 7)
    if index_value < 20 and avg_7d > 30:
        return {"signal": "CAPITULATION_BUY", "confidence": 0.80}
```

#### Historical Accuracy
- Extreme Fear (<15) has historically been followed by positive returns 70-80% of the time within 30 days
- Extreme Greed (>85) has preceded corrections 60-70% of the time
- **Best used as contrarian indicator at extremes only**
- Not useful in the neutral zone (40-60)

### 5.2 Social Sentiment Analysis

#### NLP Scoring System
```python
def crypto_sentiment_score(text):
    # Weighted keyword scoring
    bullish_keywords = {
        "moon": 2, "pump": 2, "bullish": 3, "buy": 1, "accumulate": 2,
        "breakout": 2, "ATH": 3, "adoption": 2, "institutional": 2
    }
    bearish_keywords = {
        "crash": -3, "dump": -2, "bearish": -3, "sell": -1, "scam": -2,
        "bubble": -3, "dead": -2, "capitulation": -2, "recession": -2
    }

    # Aggregate social sentiment from multiple sources
    # Twitter/X, Reddit r/bitcoin, r/cryptocurrency, Telegram, Discord

    # Contrarian signal: extreme social bullishness = bearish
    if aggregate_sentiment > 0.8:
        contrarian_signal = "SELL"
    elif aggregate_sentiment < -0.8:
        contrarian_signal = "BUY"
```

### Best Timeframe
- **Fear & Greed**: Daily readings, but act on 7-day sustained extremes
- **Social sentiment**: 4H-Daily for swing trades, real-time for scalping

---

## 6. Correlation-Based Models

### 6.1 BTC vs DXY (Dollar Index)

#### Correlation Strength
| Period | Correlation | Notes |
|--------|------------|-------|
| 2020 | 0.05 | Near zero — uncorrelated |
| 2022 | -0.45 | Moderate inverse |
| 2023 | -0.58 | Strengthening inverse |
| 2024 | -0.72 | Strong inverse |

#### Formula
```python
# DXY-based BTC signal
dxy_change_20d = (dxy_current - dxy_20d_ago) / dxy_20d_ago
btc_expected_direction = -1 * sign(dxy_change_20d)

# Signal strength based on DXY momentum
if abs(dxy_change_20d) > 0.02:  # >2% DXY move
    signal_strength = "STRONG"
    # Each 1% DXY decline ~ 3-5% BTC appreciation (rough estimate)
```

### 6.2 BTC vs Gold

#### Current State
- Correlation near zero in short term (rolling 30-day)
- Both move **inversely** to DXY and real yields
- Both move **positively** with M2 money supply
- "Digital gold" narrative strengthens during macro uncertainty

### 6.3 BTC vs S&P 500

#### Correlation Evolution
| Period | Correlation | Regime |
|--------|------------|--------|
| Pre-2020 | 0.10-0.30 | Weak positive |
| 2021-2022 | 0.60-0.77 | Strong positive (risk-on) |
| Post-ETF 2024 | 0.77+ | High beta risk asset |

#### Implementation
```python
def macro_correlation_signal(btc_price, sp500, dxy, m2_supply, treasury_10y):
    signals = {}

    # DXY inverse signal (strongest single correlation)
    dxy_momentum = calculate_momentum(dxy, period=20)
    if dxy_momentum < -0.01:
        signals['dxy'] = {"direction": "BULLISH", "weight": 0.30}
    elif dxy_momentum > 0.01:
        signals['dxy'] = {"direction": "BEARISH", "weight": 0.30}

    # S&P 500 co-movement
    sp500_momentum = calculate_momentum(sp500, period=20)
    if sp500_momentum > 0.02:
        signals['sp500'] = {"direction": "BULLISH", "weight": 0.20}

    # M2 Money Supply (with 70-90 day lag)
    m2_change_90d_ago = calculate_change(m2_supply, lag=90, period=30)
    if m2_change_90d_ago > 0.02:
        signals['m2'] = {"direction": "BULLISH", "weight": 0.25}

    # 10Y Treasury (inverse)
    treasury_change = calculate_momentum(treasury_10y, period=20)
    if treasury_change < -0.005:  # Yields falling
        signals['treasury'] = {"direction": "BULLISH", "weight": 0.15}

    return weighted_composite(signals)
```

### 6.4 BTC vs M2 Money Supply (Critical Model)

#### Correlation Data
- **Current correlation**: 0.94 with global M2 (as of 2024)
- **Lag**: 70-90 days (most studies find ~84 days or ~12 weeks)
- **M2 explains up to 90% of BTC price movements**

#### Formula
```python
def m2_btc_prediction(m2_data, btc_price, lag_days=84):
    # Shift M2 data forward by lag period
    m2_shifted = m2_data.shift(periods=lag_days)

    # Calculate M2 rate of change
    m2_roc = (m2_shifted - m2_shifted.shift(30)) / m2_shifted.shift(30)

    # BTC typically amplifies M2 moves by 5-10x
    btc_expected_roc = m2_roc * amplification_factor  # 5-10x

    # Signal
    if m2_roc > 0.01:  # M2 growing > 1% monthly (from 84 days ago)
        return "BULLISH"
    elif m2_roc < -0.005:
        return "BEARISH"
```

#### Historical Accuracy
- Very high correlation (0.94) but other variables (ETF flows, halving, macro shocks) can modulate the signal
- Best used as a directional macro indicator, not precise price prediction

### Best Timeframe
- **DXY/S&P**: Daily-Weekly
- **M2 Money Supply**: Weekly-Monthly (with 84-day lag)
- **Treasury Yields**: Daily-Weekly

---

## 7. Volatility Models (GARCH)

### 7.1 GARCH(1,1) Model

#### Formula
```
σ²_t = ω + α * r²_{t-1} + β * σ²_{t-1}

Where:
- σ²_t = conditional variance (predicted volatility) at time t
- ω (omega) = long-run average variance (constant)
- α (alpha) = weight of previous squared return (shock impact)
- r²_{t-1} = squared return at t-1 (yesterday's shock)
- β (beta) = weight of previous variance (persistence)
- σ²_{t-1} = conditional variance at t-1 (yesterday's predicted volatility)

Constraint: α + β < 1 (for stationarity)
Long-run variance = ω / (1 - α - β)
```

#### Typical Bitcoin Parameters
| Parameter | Range for BTC | Typical Value | Interpretation |
|-----------|--------------|---------------|----------------|
| α (alpha) | 0.10 - 0.41 | ~0.20 | Shock impact; higher = more reactive |
| β (beta) | 0.40 - 0.97 | ~0.75 | Persistence; higher = slower decay |
| ω (omega) | 1e-5 - 0.02 | ~0.0001 | Baseline volatility |
| α + β | 0.85 - 0.99 | ~0.95 | Total persistence |

#### Implementation (Python)
```python
from arch import arch_model
import numpy as np

def fit_garch_btc(returns):
    """
    Fit GARCH(1,1) model to BTC returns
    returns: pandas Series of log returns * 100
    """
    model = arch_model(returns, vol='Garch', p=1, q=1, dist='t')
    result = model.fit(disp='off')

    # Extract parameters
    omega = result.params['omega']
    alpha = result.params['alpha[1]']
    beta = result.params['beta[1]']

    # Forecast next-day volatility
    forecast = result.forecast(horizon=5)
    next_day_vol = np.sqrt(forecast.variance.iloc[-1])

    return {
        'omega': omega,
        'alpha': alpha,
        'beta': beta,
        'persistence': alpha + beta,
        'long_run_vol': np.sqrt(omega / (1 - alpha - beta)) * np.sqrt(252),  # annualized
        'next_day_vol': next_day_vol,
        'model': result
    }
```

### 7.2 EGARCH(1,1) — Better for BTC (Asymmetric)

#### Formula
```
ln(σ²_t) = ω + α * [|z_{t-1}| - E|z_{t-1}|] + γ * z_{t-1} + β * ln(σ²_{t-1})

Where z_{t-1} = r_{t-1} / σ_{t-1} (standardized residual)
γ = asymmetry parameter (negative = bad news increases vol more)
```

#### Why EGARCH is Better for BTC
- Captures **leverage effect**: negative returns increase volatility more than positive returns
- No positivity constraint on parameters (uses log variance)
- EGARCH(1,1) consistently outperforms GARCH(1,1) for crypto

### 7.3 Implied vs Realized Volatility

#### Signals
```python
def vol_signal(implied_vol, realized_vol_30d):
    """
    Compare implied volatility (from options) to realized volatility
    """
    vol_spread = implied_vol - realized_vol_30d

    if vol_spread > 0.15:  # IV >> RV
        # Market pricing in more volatility than occurring
        # Options are expensive — potential mean reversion trade
        return "SELL_VOLATILITY"
    elif vol_spread < -0.10:  # IV << RV
        # Market underpricing volatility
        # Options are cheap — potential breakout incoming
        return "BUY_VOLATILITY"
    else:
        return "NEUTRAL"
```

### Best Timeframe
- **GARCH fitting**: Daily returns (minimum 252 data points)
- **Volatility forecasting**: 1-5 day horizon (most accurate)
- **IV vs RV comparison**: Daily-Weekly

### Historical Accuracy
- GARCH(1,1) provides reasonable 1-3 day volatility forecasts
- EGARCH outperforms in both in-sample and out-of-sample contexts
- HAR (Heterogeneous Autoregressive) models outperform GARCH for short-term
- Hybrid GARCH-LSTM approaches show best results in recent research

---

## 8. Mean Reversion vs Momentum

### 8.1 Timeframe Performance Matrix

| Strategy | Timeframe | Sharpe Ratio | Best Market Condition |
|----------|-----------|-------------|----------------------|
| Momentum (trend-following) | 3-12 months | ~1.0 | Trending/Bull markets |
| Mean Reversion | < 3 months | ~2.3 (BTC-neutral) | Range-bound/Choppy |
| Momentum | Intraday | Variable | Strong intraday trends |
| Mean Reversion | Intraday | Higher frequency | Mean-reverting microstructure |

### 8.2 Momentum Strategy Implementation

```python
def momentum_signal(prices, short_lookback=20, long_lookback=100):
    """
    Dual momentum: absolute + relative
    """
    # Absolute momentum (time-series)
    returns_short = (prices[-1] / prices[-short_lookback]) - 1
    returns_long = (prices[-1] / prices[-long_lookback]) - 1

    # Z-score of returns
    z_score = (returns_short - mean(returns_short_history)) / std(returns_short_history)

    if z_score > 1.5 and returns_long > 0:
        return {"signal": "STRONG_BULLISH_MOMENTUM", "confidence": 0.70}
    elif z_score > 0.5 and returns_long > 0:
        return {"signal": "BULLISH_MOMENTUM", "confidence": 0.55}
    elif z_score < -1.5 and returns_long < 0:
        return {"signal": "STRONG_BEARISH_MOMENTUM", "confidence": 0.70}

    # Momentum decay detection
    if returns_short < 0 and returns_long > 0:
        return {"signal": "MOMENTUM_FADING", "confidence": 0.50}
```

### 8.3 Mean Reversion Strategy Implementation

```python
def mean_reversion_signal(prices, period=20, entry_z=2.0, exit_z=0.5):
    """
    Bollinger Band / Z-score mean reversion
    """
    sma = rolling_mean(prices, period)
    std = rolling_std(prices, period)
    z_score = (prices[-1] - sma[-1]) / std[-1]

    if z_score < -entry_z:
        return {"signal": "BUY", "target": sma[-1], "confidence": 0.65}
    elif z_score > entry_z:
        return {"signal": "SELL", "target": sma[-1], "confidence": 0.60}
    elif abs(z_score) < exit_z:
        return {"signal": "EXIT_POSITION", "confidence": 0.70}
```

### 8.4 Regime Detection (Which to Use)

```python
def detect_regime(prices, volume, lookback=60):
    """
    Determine if market is trending or mean-reverting
    """
    # Hurst Exponent
    hurst = calculate_hurst_exponent(prices, lookback)
    # H > 0.5: trending (use momentum)
    # H < 0.5: mean-reverting (use mean reversion)
    # H ≈ 0.5: random walk (neither works well)

    # ADX (Average Directional Index)
    adx = calculate_adx(prices, period=14)
    # ADX > 25: trending
    # ADX < 20: range-bound

    # Volatility regime
    vol_ratio = std(prices[-20:]) / std(prices[-60:])
    # > 1.5: expanding vol (momentum)
    # < 0.7: contracting vol (mean reversion)

    if hurst > 0.55 and adx > 25:
        return "TRENDING"  # Use momentum
    elif hurst < 0.45 and adx < 20:
        return "MEAN_REVERTING"  # Use mean reversion
    else:
        return "UNCERTAIN"  # Reduce position size
```

### Key Finding
- Post-2021, BTC-neutral residual mean reversion (Sharpe ~2.3) has significantly outperformed pure momentum (Sharpe ~1.0)
- Shorter lookback periods perform better at BTC price extremes
- Regime-switching models that alternate between strategies based on market conditions outperform static approaches

---

## 9. Key Price Levels

### 9.1 Round Number Psychology

#### Effect on BTC
- Round numbers ($10K, $20K, $50K, $100K) act as **psychological magnets**
- Cluster analysis shows 3-5x more orders at round numbers
- First approach to a round number = resistance; after breakout = support

#### Implementation
```python
def round_number_levels(current_price):
    """
    Generate significant round number levels
    """
    levels = []

    # Major round numbers
    magnitudes = [1000, 5000, 10000, 25000, 50000, 100000]

    for mag in magnitudes:
        nearest_below = (current_price // mag) * mag
        nearest_above = nearest_below + mag

        levels.append({
            'price': nearest_below,
            'type': 'support' if current_price > nearest_below else 'resistance',
            'strength': mag / current_price  # relative significance
        })
        levels.append({
            'price': nearest_above,
            'type': 'resistance' if current_price < nearest_above else 'support',
            'strength': mag / current_price
        })

    return sorted(levels, key=lambda x: abs(x['price'] - current_price))
```

### 9.2 Previous ATH/ATL as Magnets

#### Historical Pattern
| Previous ATH | Approached | Broke Through | Time to Break | Next Peak After Break |
|-------------|-----------|--------------|--------------|---------------------|
| ~$1,100 (2013) | Multiple times 2017 | Feb 2017 | ~3 years | $19,700 (18x) |
| ~$19,700 (2017) | Multiple times 2020 | Dec 2020 | ~3 years | $69,000 (3.5x) |
| ~$69,000 (2021) | Multiple times 2024 | Mar 2024 | ~2.5 years | TBD |

#### Self-Fulfilling Prophecy Effect
```python
def ath_atl_signal(current_price, historical_ath, historical_atl):
    """
    Price behavior near ATH/ATL levels
    """
    ath_distance = (historical_ath - current_price) / historical_ath
    atl_distance = (current_price - historical_atl) / current_price

    # Near ATH (within 5%)
    if ath_distance < 0.05 and ath_distance > 0:
        return {
            "signal": "ATH_RESISTANCE",
            "note": "Expect 2-3 tests before breakout",
            "breakout_probability": 0.60  # Historical avg
        }

    # Just broke ATH
    if ath_distance < 0:  # Price > ATH
        return {
            "signal": "ATH_BREAKOUT",
            "note": "Price discovery mode — momentum typically continues",
            "typical_extension": "1.5x-3x above old ATH in bull cycles"
        }
```

### 9.3 Volume Profile (VPVR) Key Levels

```python
def volume_profile_levels(price_data, volume_data, num_bins=50):
    """
    Find high-volume nodes (HVN) and low-volume nodes (LVN)
    HVN = support/resistance (price tends to consolidate)
    LVN = price moves through quickly
    """
    price_range = max(price_data) - min(price_data)
    bin_size = price_range / num_bins

    volume_at_price = {}
    for price, vol in zip(price_data, volume_data):
        bin_idx = int((price - min(price_data)) / bin_size)
        volume_at_price[bin_idx] = volume_at_price.get(bin_idx, 0) + vol

    # Point of Control (POC) — highest volume price
    poc_bin = max(volume_at_price, key=volume_at_price.get)
    poc_price = min(price_data) + (poc_bin + 0.5) * bin_size

    # Value Area (70% of volume)
    total_vol = sum(volume_at_price.values())
    sorted_bins = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)

    cumulative = 0
    value_area_bins = []
    for bin_idx, vol in sorted_bins:
        cumulative += vol
        value_area_bins.append(bin_idx)
        if cumulative >= total_vol * 0.70:
            break

    vah = min(price_data) + (max(value_area_bins) + 1) * bin_size  # Value Area High
    val_ = min(price_data) + min(value_area_bins) * bin_size  # Value Area Low

    return {"poc": poc_price, "vah": vah, "val": val_}
```

### Best Timeframe
- **Round numbers**: All timeframes (psychological effect is universal)
- **ATH/ATL**: Weekly/Monthly (cycle-level significance)
- **Volume Profile**: Daily-Weekly (200-day lookback typical)

---

## 10. Professional Trading Strategies

### 10.1 Market Making (Wintermute, Jump Crypto Style)

#### Avellaneda-Stoikov Model (Industry Standard)

```python
def avellaneda_stoikov(mid_price, inventory, sigma, gamma, kappa, T, t):
    """
    Optimal bid/ask placement for market makers

    Parameters:
    - mid_price (S): Current mid-price
    - inventory (q): Current position (-n to +n)
    - sigma: Volatility estimate
    - gamma: Risk aversion parameter (0.01-1.0)
    - kappa: Order book liquidity parameter
    - T: Terminal time
    - t: Current time

    Returns: optimal bid price, optimal ask price
    """
    # Reservation price (internal valuation adjusted for inventory)
    reservation_price = mid_price - inventory * gamma * sigma**2 * (T - t)

    # Optimal spread
    optimal_spread = gamma * sigma**2 * (T - t) + (2/gamma) * np.log(1 + gamma/kappa)

    # Bid and Ask
    bid = reservation_price - optimal_spread / 2
    ask = reservation_price + optimal_spread / 2

    return bid, ask

# Typical parameters for BTC:
# gamma = 0.1 (moderate risk aversion)
# kappa = 1.5 (moderate liquidity)
# sigma = daily_realized_vol / sqrt(252)
```

#### Key Concepts
- **Inventory skewing**: When long, lower the reservation price to attract sells
- **Dynamic spreads**: Widen during high volatility, tighten during calm
- **Profit source**: Bid-ask spread capture at high frequency
- **Risk**: Adverse selection (getting picked off by informed traders)

### 10.2 Statistical Arbitrage

```python
def cross_exchange_arbitrage(prices_by_exchange):
    """
    Detect price discrepancies across exchanges
    """
    opportunities = []
    exchanges = list(prices_by_exchange.keys())

    for i, ex1 in enumerate(exchanges):
        for ex2 in exchanges[i+1:]:
            spread = prices_by_exchange[ex1] - prices_by_exchange[ex2]
            spread_pct = abs(spread) / min(prices_by_exchange[ex1], prices_by_exchange[ex2])

            if spread_pct > 0.001:  # > 10 bps
                opportunities.append({
                    'buy_exchange': ex2 if spread > 0 else ex1,
                    'sell_exchange': ex1 if spread > 0 else ex2,
                    'spread_bps': spread_pct * 10000,
                    'profit_after_fees': spread_pct - 0.0005  # typical taker fee
                })

    return opportunities
```

### 10.3 Funding Rate Arbitrage

```python
def funding_rate_arb(spot_price, perp_price, funding_rate, funding_interval_hours=8):
    """
    Cash-and-carry: Long spot + Short perpetual when funding is positive
    """
    annualized_funding = funding_rate * (365 * 24 / funding_interval_hours)

    if annualized_funding > 0.20:  # > 20% APY
        return {
            "strategy": "LONG_SPOT_SHORT_PERP",
            "annualized_yield": annualized_funding,
            "risk": "Liquidation risk on short perp if price spikes",
            "position_size": "Max 2-5x leverage on perp side"
        }
    elif annualized_funding < -0.15:
        return {
            "strategy": "SHORT_SPOT_LONG_PERP",
            "annualized_yield": abs(annualized_funding),
            "risk": "Need to borrow spot to short"
        }
```

### 10.4 Liquidation Hunting

```python
def identify_liquidation_clusters(order_book, open_interest_data, leverage_data):
    """
    Identify price levels where large liquidations would trigger
    Used by sophisticated traders to anticipate price magnets
    """
    liquidation_levels = []

    # Estimate liquidation prices based on typical leverage
    for leverage in [5, 10, 20, 50, 100]:
        # Long liquidation price
        long_liq = current_price * (1 - 1/leverage + 0.005)  # with maintenance margin
        # Short liquidation price
        short_liq = current_price * (1 + 1/leverage - 0.005)

        liquidation_levels.append({
            'price': long_liq,
            'type': 'long_liquidation',
            'leverage': leverage,
            'estimated_volume': estimate_oi_at_leverage(open_interest_data, leverage)
        })

    # Cluster analysis — where are the biggest liquidation walls?
    # Price tends to be attracted to large liquidation clusters
    return sorted(liquidation_levels, key=lambda x: x['estimated_volume'], reverse=True)
```

### 10.5 Mean Reversion on Funding/Basis

```python
def basis_mean_reversion(spot_price, futures_price, days_to_expiry):
    """
    Trade the basis between spot and dated futures
    """
    basis = (futures_price - spot_price) / spot_price
    annualized_basis = basis * (365 / days_to_expiry)

    historical_basis_mean = 0.08  # ~8% typical BTC basis
    historical_basis_std = 0.05

    z_score = (annualized_basis - historical_basis_mean) / historical_basis_std

    if z_score > 2.0:
        return "SELL_BASIS"  # Short futures, long spot
    elif z_score < -1.0:
        return "BUY_BASIS"  # Long futures, short spot
```

---

## 11. On-Chain Valuation Models

### 11.1 Stock-to-Flow (S2F)

#### Formula
```
S2F Ratio = Stock / Flow = Current Supply / Annual Production
Model Price = exp(-1.84) * S2F^3.36

Current (post-2024 halving):
- Stock: ~19.6M BTC
- Flow: ~164,250 BTC/year (3.125 BTC per block * 52,560 blocks/year)
- S2F = 19,600,000 / 164,250 ≈ 119.3
- Model Price = e^(-1.84) * 119.3^3.36 ≈ very high
```

#### Accuracy Issues
- Predicted ~$100K for 2022; actual was ~$16K-$47K
- Post-2021 predictions deviated by >500%
- **Ignores demand side entirely** — only models supply scarcity
- Best viewed as a directional "floor price" concept, not precise prediction

### 11.2 MVRV Z-Score

#### Formula
```
MVRV Z-Score = (Market Value - Realized Value) / StdDev(Market Value)

Market Value = Current Price * Circulating Supply
Realized Value = Sum of (price at which each UTXO last moved * amount)
```

#### Signal Zones
| Z-Score | Zone | Historical Signal |
|---------|------|-------------------|
| > 7.0 | Red (extreme) | Market top — strong sell |
| 5.0-7.0 | Orange | Overvalued — begin taking profits |
| 2.0-5.0 | Yellow | Moderately overvalued |
| 0.0-2.0 | Green | Fair value to undervalued |
| < 0.0 | Deep Green | Extreme undervaluation — strong buy |

#### Historical Accuracy
- MVRV Z-Score > 7 has called **every major cycle top** (2011, 2013, 2017, 2021)
- MVRV Z-Score < 0 has called **every major cycle bottom** (2011, 2015, 2018, 2022)
- One of the most reliable on-chain indicators

### 11.3 Puell Multiple

#### Formula
```
Puell Multiple = Daily BTC Issuance Value (USD) / 365-day MA of Daily Issuance Value

Daily Issuance Value = Blocks Mined Today * Block Reward * BTC Price
```

#### Signal Zones
| Puell Multiple | Signal | Historical Accuracy |
|---------------|--------|-------------------|
| < 0.5 (Green) | Strong buy — miner capitulation | Called bottoms in 2011, 2015, 2018, 2020 |
| 0.5-4.0 | Neutral | Normal market |
| > 4.0 (Red) | Strong sell — miners taking profits | Called tops in 2011, 2013, 2017 |

### 11.4 NVT Ratio

#### Formula
```
NVT Ratio = Network Value (Market Cap) / Daily Transaction Volume (USD)
NVT Signal = Network Value / 90-day MA of Transaction Volume
```

#### Signal Zones
| NVT Range | Interpretation |
|-----------|---------------|
| < 30-50 | Undervalued (high utility relative to price) |
| 50-70 | Fair value |
| 70-100 | Overvalued (speculative premium) |
| > 100 | Extreme overvaluation |

### 11.5 Pi Cycle Top Indicator

#### Formula
```
Line 1: 111-day Moving Average (111DMA)
Line 2: 350-day Moving Average * 2 (350DMA * 2)

SELL signal: When 111DMA crosses ABOVE 350DMA * 2

Note: 350 / 111 = 3.153 ≈ Pi (3.14159)
```

#### Historical Accuracy
- Called tops in 2013, 2017, and 2021 **within 3 days**
- One of the most accurate top indicators in Bitcoin history
- **Caveat**: May lose relevance with ETF-driven market structure changes

### 11.6 Rainbow Chart (Log Regression)

#### Formula
```
Base curve: log10(price) = 2.6521 * ln(weeks_since_jan_2009) - 18.163

Bands are created by multiplying/dividing the base curve by constant factors:
- Band 1 (Fire Sale): base * 0.4
- Band 2 (BUY!): base * 0.6
- Band 3 (Accumulate): base * 0.8
- Band 4 (Still Cheap): base * 1.0
- Band 5 (HODL!): base * 1.2
- Band 6 (Is this a bubble?): base * 1.5
- Band 7 (FOMO intensifies): base * 2.0
- Band 8 (Sell. Seriously, sell): base * 2.5
- Band 9 (Maximum Bubble): base * 3.0
```

---

## 12. Combining Multiple Signals

### 12.1 Composite Scoring System

```python
class BTCOracleSignalCombiner:
    """
    Weighted composite signal from multiple models
    Score range: -100 (extreme bearish) to +100 (extreme bullish)
    """

    SIGNAL_WEIGHTS = {
        # On-chain (most reliable for cycle timing)
        'mvrv_zscore': 0.12,
        'puell_multiple': 0.08,
        'nvt_ratio': 0.06,
        'pi_cycle': 0.05,

        # Macro correlations
        'm2_money_supply': 0.10,
        'dxy_correlation': 0.08,
        'sp500_momentum': 0.05,

        # Market microstructure
        'funding_rate': 0.08,
        'open_interest_divergence': 0.06,
        'liquidation_risk': 0.05,

        # Technical
        'halving_cycle_position': 0.07,
        'momentum_regime': 0.05,
        'mean_reversion_zscore': 0.05,

        # Sentiment
        'fear_greed_index': 0.05,
        'social_sentiment': 0.03,

        # Volatility
        'garch_forecast': 0.02,  # vol direction, not price
    }
    # Total: 1.00

    def calculate_composite(self, signals):
        """
        Each signal provides:
        - direction: -1 to +1
        - confidence: 0 to 1
        """
        weighted_score = 0
        total_confidence = 0

        for signal_name, signal_data in signals.items():
            weight = self.SIGNAL_WEIGHTS.get(signal_name, 0)
            direction = signal_data['direction']  # -1 to +1
            confidence = signal_data['confidence']  # 0 to 1

            weighted_score += weight * direction * confidence
            total_confidence += weight * confidence

        # Normalize to -100 to +100
        if total_confidence > 0:
            composite = (weighted_score / total_confidence) * 100
        else:
            composite = 0

        return {
            'score': composite,
            'signal': self._interpret_score(composite),
            'confidence': total_confidence,
            'breakdown': self._get_breakdown(signals)
        }

    def _interpret_score(self, score):
        if score > 60:
            return "STRONG_BUY"
        elif score > 30:
            return "BUY"
        elif score > 10:
            return "LEAN_BULLISH"
        elif score > -10:
            return "NEUTRAL"
        elif score > -30:
            return "LEAN_BEARISH"
        elif score > -60:
            return "SELL"
        else:
            return "STRONG_SELL"
```

### 12.2 Multi-Timeframe Confirmation

```python
def multi_timeframe_signal(signals_by_timeframe):
    """
    Require confirmation across timeframes for high-confidence trades

    Timeframes:
    - Monthly/Weekly: Macro trend (halving cycle, MVRV, M2)
    - Daily: Primary trend (momentum, moving averages, funding)
    - 4H/1H: Entry timing (mean reversion, order book, liquidations)
    """
    macro = signals_by_timeframe['weekly']    # Weight: 40%
    primary = signals_by_timeframe['daily']    # Weight: 35%
    entry = signals_by_timeframe['4h']         # Weight: 25%

    # Confirmed trend: macro + primary agree
    if macro['direction'] == primary['direction']:
        confidence_boost = 1.3  # 30% confidence boost

        # Triple confirmation: all three agree
        if entry['direction'] == macro['direction']:
            confidence_boost = 1.5
            return {
                'signal': macro['direction'],
                'confidence': min(1.0, macro['confidence'] * confidence_boost),
                'type': 'TRIPLE_CONFIRMED'
            }

    # Divergence: macro and primary disagree
    if macro['direction'] != primary['direction']:
        return {
            'signal': 'NEUTRAL',
            'confidence': 0.3,
            'type': 'TIMEFRAME_DIVERGENCE',
            'note': 'Wait for alignment'
        }
```

### 12.3 Signal Priority by Market Regime

| Market Regime | Primary Signals (60%) | Secondary Signals (30%) | Tertiary (10%) |
|--------------|----------------------|------------------------|----------------|
| **Bull Trend** | Momentum, Halving Cycle, M2 | MVRV, Funding Rate, OI | Fear/Greed, Social |
| **Bear Trend** | MVRV, NVT, Puell Multiple | DXY, Treasury Yields | Pi Cycle, Rainbow |
| **Range-Bound** | Mean Reversion, Funding Rate | Order Book, Liquidation Levels | Volume Profile |
| **High Vol / Crisis** | Liquidation Cascade, OI | Funding Rate, Fear/Greed | Volatility (GARCH) |
| **Pre-Halving** | Halving Cycle Position, S2F | M2, MVRV | Historical Patterns |

### 12.4 Confidence Calibration Rules

```python
def adjust_confidence(base_confidence, conditions):
    """
    Adjust signal confidence based on market conditions
    """
    adjusted = base_confidence

    # Boost confidence
    if conditions['multiple_signals_agree'] >= 3:
        adjusted *= 1.2
    if conditions['volume_confirms']:
        adjusted *= 1.15
    if conditions['on_chain_confirms']:
        adjusted *= 1.1

    # Reduce confidence
    if conditions['macro_uncertainty']:  # FOMC, elections, etc.
        adjusted *= 0.7
    if conditions['weekend']:  # Lower liquidity
        adjusted *= 0.85
    if conditions['opposing_timeframe_signal']:
        adjusted *= 0.6
    if conditions['black_swan_risk']:  # Exchange hack, regulation, etc.
        adjusted *= 0.5

    return min(1.0, max(0.0, adjusted))
```

---

## Summary: Model Reliability Rankings

| Rank | Model/Signal | Reliability | Best For | Timeframe |
|------|-------------|------------|----------|-----------|
| 1 | MVRV Z-Score | Very High | Cycle tops/bottoms | Monthly |
| 2 | M2 Money Supply (84d lag) | Very High | Directional bias | Weekly |
| 3 | Pi Cycle Top | High (tops only) | Cycle tops | Weekly |
| 4 | Puell Multiple | High | Cycle bottoms | Monthly |
| 5 | Halving Cycle Position | High | Macro positioning | Monthly |
| 6 | Funding Rate Extremes | High | Short-term reversals | 8H |
| 7 | DXY Inverse Correlation | High | Directional bias | Daily |
| 8 | Liquidation Cascades | High | Capitulation detection | Real-time |
| 9 | NVT Ratio | Moderate-High | Valuation | Weekly |
| 10 | Fear & Greed (extremes) | Moderate | Contrarian signals | Daily |
| 11 | Mean Reversion Z-Score | Moderate | Range trading | 4H-Daily |
| 12 | GARCH Volatility | Moderate | Vol forecasting | Daily |
| 13 | Momentum Strategies | Moderate | Trend following | Daily-Weekly |
| 14 | Elliott Wave | Low-Moderate | Pattern recognition | Weekly |
| 15 | Stock-to-Flow | Low (post-2021) | Long-term floor | Yearly |

---

## Data Sources for Implementation

| Data Type | Source | API |
|-----------|--------|-----|
| On-chain metrics | Glassnode, CryptoQuant | REST API |
| MVRV, NVT, Puell | Glassnode, Blockchain.com | REST API |
| Funding rates | CoinGlass, Binance | WebSocket/REST |
| Open interest | CoinGlass, Coinalyze | REST API |
| Liquidation data | CoinGlass, Coinalyze | WebSocket |
| Fear & Greed | Alternative.me | REST API |
| DXY, S&P, Gold | Yahoo Finance, FRED | REST API |
| M2 Money Supply | FRED (Federal Reserve) | REST API |
| Social sentiment | LunarCrush, Santiment | REST API |
| Order book | Exchange APIs (Binance, etc.) | WebSocket |
| Price/Volume | CoinGecko, Binance | REST/WebSocket |
| Options IV | Deribit | REST API |
