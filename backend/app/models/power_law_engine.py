"""Power Law regression engine for Bitcoin price modeling.

All parameters (slope, intercept, R², log volatility, CAGR) are computed
from actual historical price data via OLS regression on log-log space.
No hardcoded model parameters.
"""
import math
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BTC_GENESIS = datetime(2009, 1, 3)
DATA_DIR = Path(__file__).parent.parent / "data"


def _ols_log_log(dates, values, resample_days=0):
    """Ordinary Least Squares regression in log10-log10 space.

    Args:
        dates: list of datetime objects
        values: list of float prices/ratios (must be > 0)
        resample_days: if > 0, keep only one point per N days to ensure
                       uniform weighting across time periods

    Returns:
        dict with intercept, slope, r_squared, residuals_std
    """
    # Optional resampling to prevent overweighting dense data regions
    if resample_days > 0:
        sampled = {}
        for d, v in zip(dates, values):
            if v is not None and v > 0:
                bucket = (d - BTC_GENESIS).days // resample_days
                sampled[bucket] = (d, v)  # last value per bucket wins
        pairs = sorted(sampled.values(), key=lambda x: x[0])
        dates = [p[0] for p in pairs]
        values = [p[1] for p in pairs]

    xs, ys = [], []
    for d, v in zip(dates, values):
        if v is not None and v > 0:
            days = (d - BTC_GENESIS).days
            if days > 0:
                xs.append(math.log10(days))
                ys.append(math.log10(v))

    n = len(xs)
    if n < 10:
        return None

    # OLS: y = a + b*x
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    mean_x = sum_x / n
    mean_y = sum_y / n

    denom = sum_x2 - sum_x * sum_x / n
    if denom == 0:
        return None

    slope = (sum_xy - sum_x * sum_y / n) / denom
    intercept = mean_y - slope * mean_x

    # R² and residual std
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    residuals_std = math.sqrt(ss_res / (n - 2)) if n > 2 else 0

    return {
        "intercept": intercept,
        "slope": slope,
        "r_squared": r_squared,
        "residuals_std": residuals_std,
        "n_points": n,
    }


class PowerLawEngine:
    """BTC Power Law model: log10(Price) = intercept + slope * log10(days_since_genesis)

    All parameters are computed from data via fit(). No hardcoded defaults.
    """

    def __init__(self, intercept, slope, r_squared, log_volatility, cagr):
        self.intercept = intercept
        self.slope = slope
        self.r_squared = r_squared
        self.log_volatility = log_volatility
        self.cagr = cagr

    @classmethod
    def fit(cls, price_data):
        """Fit power law from price data.

        Args:
            price_data: list of dicts with 'date' (datetime or str) and 'price' (float)
                        OR list of (datetime, float) tuples.

        Returns:
            PowerLawEngine instance with computed parameters.
        """
        dates, prices = [], []
        for item in price_data:
            if isinstance(item, dict):
                d = item["date"] if isinstance(item["date"], datetime) else datetime.fromisoformat(str(item["date"]))
                p = float(item["price"])
            else:
                d, p = item[0], float(item[1])
            if p > 0:
                dates.append(d)
                prices.append(p)

        # Resample to ~weekly to ensure uniform time weighting
        result = _ols_log_log(dates, prices, resample_days=7)
        if result is None:
            raise ValueError("Not enough valid data points for regression")

        # Compute CAGR from the model
        now = datetime.utcnow()
        genesis_price = 0.001  # approximate genesis value
        days = (now - BTC_GENESIS).days
        years = days / 365.25
        current_model = 10 ** (result["intercept"] + result["slope"] * math.log10(days))
        cagr = ((current_model / genesis_price) ** (1 / years) - 1) * 100 if years > 0 else 0

        return cls(
            intercept=round(result["intercept"], 4),
            slope=round(result["slope"], 4),
            r_squared=round(result["r_squared"], 4),
            log_volatility=round(result["residuals_std"], 2),
            cagr=round(cagr, 1),
        )

    @classmethod
    def from_db_prices(cls, price_rows):
        """Fit from SQLAlchemy Price rows (have .timestamp and .close)."""
        data = [(p.timestamp, p.close) for p in price_rows if p.close and p.close > 0]
        # Always supplement with early prices to ensure full historical coverage.
        # The weekly resampling in _ols_log_log handles deduplication.
        early = cls._load_early_prices()
        return cls.fit(early + data)

    @classmethod
    def from_early_prices(cls):
        """Fit from static early prices file only (fallback when DB is empty)."""
        data = cls._load_early_prices()
        return cls.fit(data)

    @staticmethod
    def _load_early_prices():
        """Load early BTC prices from static JSON.

        Filters to exchange-era data (2010-07-17 onwards) for accurate
        regression. Pre-exchange prices are unreliable and skew the fit.
        """
        path = DATA_DIR / "btc_early_prices.json"
        if not path.exists():
            return []
        with open(path) as f:
            raw = json.load(f)
        # Start from Mt. Gox era (first exchange) for reliable pricing
        min_date = datetime(2010, 7, 17)
        result = []
        for item in raw:
            if item["price"] > 0:
                d = datetime.fromisoformat(item["date"])
                if d >= min_date:
                    result.append((d, item["price"]))
        return result

    def fair_value(self, target_date=None):
        """Calculate fair value for a given date."""
        if target_date is None:
            target_date = datetime.utcnow()
        days = (target_date - BTC_GENESIS).days
        if days <= 0:
            return 0.0
        log_price = self.intercept + self.slope * math.log10(days)
        return 10 ** log_price

    def multiplier(self, current_price, target_date=None):
        """Current price / fair value ratio."""
        fv = self.fair_value(target_date)
        return current_price / fv if fv > 0 else 0.0

    def project_future(self, dates):
        """Project prices for a list of dates."""
        return [{"date": d.strftime("%Y-%m-%d"), "price": round(self.fair_value(d), 2)} for d in dates]

    def find_milestone_date(self, target_price):
        """Find the date when model predicts target_price."""
        if self.slope == 0:
            return "N/A"
        log_target = math.log10(target_price)
        log_days = (log_target - self.intercept) / self.slope
        days = 10 ** log_days
        result_date = BTC_GENESIS + timedelta(days=days)
        if result_date.year > 2100:
            return "2100+"
        return result_date.strftime("%Y-%m-%d")

    def get_stats(self, current_price, target_date=None):
        """Get comprehensive stats dictionary for dashboard endpoint."""
        if target_date is None:
            target_date = datetime.utcnow()

        fv = self.fair_value(target_date)
        days = (target_date - BTC_GENESIS).days
        mult = current_price / fv if fv > 0 else 0
        deviation_pct = ((current_price - fv) / fv * 100) if fv > 0 else 0

        # Projections
        projections = {}
        for key, d in {
            "dec_2026": datetime(2026, 12, 31),
            "dec_2030": datetime(2030, 12, 31),
            "dec_2035": datetime(2035, 12, 31),
            "dec_2045": datetime(2045, 12, 31),
        }.items():
            projections[key] = round(self.fair_value(d), 2)

        # Milestones — trendline date + earliest possible (at 4x upper band)
        milestones = {}
        for target in [1_000_000, 10_000_000]:
            label = f"${target:,.0f}"
            milestones[label] = {
                "trendline": self.find_milestone_date(target),
                "earliest": self.find_milestone_date(target / 4.0),
            }

        return {
            "current_price": current_price,
            "model_price": round(fv, 2),
            "multiplier": round(mult, 4),
            "deviation_pct": round(deviation_pct, 2),
            "days_since_genesis": days,
            "slope": self.slope,
            "intercept": self.intercept,
            "r_squared": self.r_squared,
            "log_volatility": self.log_volatility,
            "cagr": self.cagr,
            "projections": projections,
            "milestones": milestones,
        }


class RatioModel:
    """Power law model for BTC ratios (BTC/Gold, BTC/M2, BTC/SPX).

    All parameters computed from data via fit().
    """

    def __init__(self, intercept, slope, r_squared, log_volatility=0, cagr=0):
        self.intercept = intercept
        self.slope = slope
        self.r_squared = r_squared
        self.log_volatility = log_volatility
        self.cagr = cagr

    @classmethod
    def fit(cls, ratio_data):
        """Fit ratio model from historical ratio data.

        Args:
            ratio_data: list of (datetime, float_ratio) tuples
        """
        result = _ols_log_log(
            [d for d, _ in ratio_data],
            [v for _, v in ratio_data],
            resample_days=7,
        )
        if result is None:
            raise ValueError("Not enough valid data points for ratio regression")

        # Compute CAGR of the ratio model
        now = datetime.utcnow()
        days = (now - BTC_GENESIS).days
        years = days / 365.25
        start_days = 365  # ~1 year after genesis
        start_ratio = 10 ** (result["intercept"] + result["slope"] * math.log10(start_days))
        current_ratio = 10 ** (result["intercept"] + result["slope"] * math.log10(days))
        cagr = ((current_ratio / start_ratio) ** (1 / (years - 1)) - 1) * 100 if years > 1 and start_ratio > 0 else 0

        return cls(
            intercept=round(result["intercept"], 4),
            slope=round(result["slope"], 4),
            r_squared=round(result["r_squared"], 4),
            log_volatility=round(result["residuals_std"], 2),
            cagr=round(cagr, 1),
        )

    def model_ratio(self, target_date=None):
        """Calculate model ratio for a given date."""
        if target_date is None:
            target_date = datetime.utcnow()
        days = (target_date - BTC_GENESIS).days
        if days <= 0:
            return 0.0
        log_ratio = self.intercept + self.slope * math.log10(days)
        return 10 ** log_ratio

    def find_milestone_date(self, target_ratio):
        """Find date when model predicts the target ratio."""
        if target_ratio <= 0 or self.slope == 0:
            return "N/A"
        log_target = math.log10(target_ratio)
        log_days = (log_target - self.intercept) / self.slope
        days = 10 ** log_days
        result_date = BTC_GENESIS + timedelta(days=days)
        if result_date.year > 2100:
            return "2100+"
        return result_date.strftime("%Y-%m-%d")

    def get_stats(self, actual_ratio):
        """Get stats for the ratio model."""
        model = self.model_ratio()
        mult = actual_ratio / model if model > 0 else 0
        deviation = ((actual_ratio - model) / model * 100) if model > 0 else 0
        return {
            "actual": round(actual_ratio, 4),
            "model": round(model, 4),
            "multiplier": round(mult, 4),
            "deviation_pct": round(deviation, 2),
            "slope": self.slope,
            "r_squared": self.r_squared,
            "log_volatility": self.log_volatility,
            "cagr": self.cagr,
        }
