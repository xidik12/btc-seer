"""Power Law regression engine for Bitcoin price modeling."""
import math
from datetime import datetime, timedelta

BTC_GENESIS = datetime(2009, 1, 3)

# Default Power Law parameters (fitted from 2009-2025 data)
DEFAULT_INTERCEPT = -17.016
DEFAULT_SLOPE = 5.845


class PowerLawEngine:
    """BTC Power Law model: log10(Price) = intercept + slope * log10(days_since_genesis)"""

    def __init__(self, intercept=None, slope=None):
        self.intercept = intercept or DEFAULT_INTERCEPT
        self.slope = slope or DEFAULT_SLOPE

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
        log_target = math.log10(target_price)
        log_days = (log_target - self.intercept) / self.slope
        days = 10 ** log_days
        result_date = BTC_GENESIS + timedelta(days=days)
        return result_date.strftime("%Y-%m-%d")

    def get_stats(self, current_price, target_date=None):
        """Get comprehensive stats dictionary for dashboard endpoint."""
        if target_date is None:
            target_date = datetime.utcnow()

        fv = self.fair_value(target_date)
        days = (target_date - BTC_GENESIS).days
        mult = current_price / fv if fv > 0 else 0

        # Calculate CAGR from genesis
        years = days / 365.25
        if years > 0 and current_price > 0:
            cagr = ((current_price / 0.001) ** (1 / years) - 1) * 100  # From ~$0.001
        else:
            cagr = 0

        # Projections
        projections = {}
        for key, d in {
            "dec_2026": datetime(2026, 12, 31),
            "dec_2030": datetime(2030, 12, 31),
            "dec_2035": datetime(2035, 12, 31),
            "dec_2045": datetime(2045, 12, 31),
        }.items():
            projections[key] = round(self.fair_value(d), 2)

        # Milestones
        milestones = {}
        for target in [1_000_000, 10_000_000]:
            label = f"${target:,.0f}"
            milestones[label] = self.find_milestone_date(target)

        deviation_pct = ((current_price - fv) / fv * 100) if fv > 0 else 0

        return {
            "current_price": current_price,
            "model_price": round(fv, 2),
            "multiplier": round(mult, 4),
            "deviation_pct": round(deviation_pct, 2),
            "days_since_genesis": days,
            "slope": self.slope,
            "intercept": self.intercept,
            "r_squared": 0.951,  # Published R² for BTC power law
            "log_volatility": 0.32,  # Typical log-volatility
            "cagr": round(cagr, 1),
            "projections": projections,
            "milestones": milestones,
        }


class RatioModel:
    """Power law model for BTC ratios (BTC/Gold, BTC/M2, BTC/SPX)."""

    def __init__(self, intercept=None, slope=None, r_squared=None):
        self.intercept = intercept or -14.0
        self.slope = slope or 4.5
        self.r_squared = r_squared or 0.90

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
        if target_ratio <= 0:
            return "N/A"
        log_target = math.log10(target_ratio)
        log_days = (log_target - self.intercept) / self.slope
        days = 10 ** log_days
        result_date = BTC_GENESIS + timedelta(days=days)
        # Sanity check
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
            "r_squared": self.r_squared,
        }
