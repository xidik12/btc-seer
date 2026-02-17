"""Accuracy bar chart by timeframe."""
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from app.charts.branding import apply_matplotlib_theme, SIZES, GREEN, RED, YELLOW, BLUE, BG_COLOR, TEXT_COLOR


def render_accuracy_chart(
    accuracy_data: dict,
    days: int = 7,
    size: str = "default",
) -> bytes:
    """Render accuracy bar chart as PNG bytes.

    accuracy_data: {"1h": {"correct": N, "total": N}, "4h": {...}, "24h": {...}, "overall": {"correct": N, "total": N}}
    """
    apply_matplotlib_theme()
    w, h = SIZES.get(size, SIZES["default"])
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)

    timeframes = []
    accuracies = []
    colors = []
    counts = []

    for tf in ["1h", "4h", "24h", "overall"]:
        data = accuracy_data.get(tf, {})
        total = data.get("total", 0)
        correct = data.get("correct", 0)
        if total > 0:
            acc = correct / total * 100
            timeframes.append(tf.upper() if tf != "overall" else "ALL")
            accuracies.append(acc)
            counts.append(f"{correct}/{total}")
            colors.append(GREEN if acc >= 60 else YELLOW if acc >= 50 else RED)

    if not timeframes:
        ax.text(0.5, 0.5, "No evaluated predictions yet", ha='center', va='center', fontsize=16, color=TEXT_COLOR)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        return buf.getvalue()

    x = np.arange(len(timeframes))
    bars = ax.bar(x, accuracies, color=colors, width=0.5, edgecolor='white', linewidth=0.5)

    # Add value labels
    for bar, acc, count in zip(bars, accuracies, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5,
                f"{acc:.1f}%\n({count})", ha='center', va='bottom', fontsize=11, fontweight='bold', color=TEXT_COLOR)

    ax.set_xticks(x)
    ax.set_xticklabels(timeframes, fontsize=12)
    ax.set_ylim(0, 110)
    ax.set_title(f"Prediction Accuracy — Last {days} Days", fontsize=14, fontweight='bold', pad=10)
    ax.set_ylabel("Accuracy %", fontsize=10)

    # Reference line at 50%
    ax.axhline(y=50, color=YELLOW, linestyle='--', alpha=0.5, label='50% baseline')
    ax.legend(fontsize=9)

    fig.text(0.98, 0.02, "BTC Seer AI — t.me/BTCSeerBot", ha='right', va='bottom', fontsize=8, color='gray', alpha=0.7)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', facecolor=BG_COLOR)
    plt.close(fig)
    return buf.getvalue()
