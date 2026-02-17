"""Candlestick/line chart with prediction markers."""
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from app.charts.branding import apply_matplotlib_theme, SIZES, GREEN, RED, BLUE, YELLOW, BG_COLOR, TEXT_COLOR, BORDER_COLOR


async def render_price_chart(
    prices: list[dict],
    predictions: list[dict] | None = None,
    hours: int = 24,
    size: str = "default",
) -> bytes:
    """Render price line chart as PNG bytes.

    prices: list of {"timestamp": datetime, "close": float, "high": float, "low": float}
    predictions: list of {"timestamp": datetime, "direction": str, "confidence": float}
    """
    apply_matplotlib_theme()
    w, h = SIZES.get(size, SIZES["default"])
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)

    if not prices:
        ax.text(0.5, 0.5, "No price data available", ha='center', va='center', fontsize=16, color=TEXT_COLOR)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        return buf.getvalue()

    times = [p["timestamp"] for p in prices]
    closes = [p["close"] for p in prices]

    # Price line
    ax.plot(times, closes, color=BLUE, linewidth=2, label="BTC Price")

    # Fill area under the curve
    ax.fill_between(times, closes, alpha=0.1, color=BLUE)

    # Add prediction markers
    if predictions:
        for pred in predictions:
            color = GREEN if pred["direction"] == "bullish" else RED if pred["direction"] == "bearish" else YELLOW
            marker = "^" if pred["direction"] == "bullish" else "v" if pred["direction"] == "bearish" else "o"
            ax.scatter([pred["timestamp"]], [pred.get("price", closes[-1])],
                      color=color, marker=marker, s=100, zorder=5, edgecolors='white', linewidth=1)

    # Format
    ax.set_title(f"BTC Price — Last {hours}h", fontsize=14, fontweight='bold', pad=10)
    ax.set_ylabel("USD", fontsize=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.grid(True, alpha=0.2)
    ax.legend(loc='upper left', fontsize=9)

    # Watermark
    fig.text(0.98, 0.02, "BTC Seer AI — t.me/BTCSeerBot", ha='right', va='bottom', fontsize=8, color='gray', alpha=0.7)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=BG_COLOR)
    plt.close(fig)
    return buf.getvalue()
