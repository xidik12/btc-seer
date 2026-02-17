"""Weekly summary infographic with multiple stats."""
import io
from PIL import Image, ImageDraw
from app.charts.branding import (
    create_base_image, add_watermark, get_font,
    BG_RGB, TEXT_RGB, GREEN_RGB, RED_RGB, YELLOW_RGB, BLUE_RGB, GRAY_RGB, BORDER_RGB,
)


def render_weekly_summary(
    stats: dict,
    size: str = "default",
) -> bytes:
    """Render weekly summary infographic as PNG bytes.

    stats keys:
    - accuracy_pct, total_predictions, correct_predictions
    - price_start, price_end, price_change_pct
    - signals_count, profitable_signals
    - streak, best_call (str), worst_call (str)
    - users_total, users_new, premium_count
    """
    img, draw, w, h = create_base_image(size)

    title_font = get_font(26, bold=True)
    section_font = get_font(20, bold=True)
    value_font = get_font(32, bold=True)
    label_font = get_font(14)
    small_font = get_font(12)

    # Title bar
    draw.rectangle([0, 0, w, 55], fill=(20, 27, 38))
    draw.text((w // 2, 28), "BTC SEER — WEEKLY REPORT", fill=BLUE_RGB, font=title_font, anchor="mm")

    # Grid layout: 2 columns, 3 rows
    col_w = w // 2
    row_h = (h - 55 - 30) // 3  # subtract title and watermark space

    def draw_stat_box(col, row, title, value, subtitle="", value_color=TEXT_RGB):
        x = col * col_w + col_w // 2
        y = 55 + row * row_h + 15

        # Box border
        bx1, by1 = col * col_w + 10, 55 + row * row_h + 5
        bx2, by2 = (col + 1) * col_w - 10, 55 + (row + 1) * row_h - 5
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=8, outline=BORDER_RGB, width=1)

        draw.text((x, y), title, fill=GRAY_RGB, font=label_font, anchor="mt")
        draw.text((x, y + 25), str(value), fill=value_color, font=value_font, anchor="mt")
        if subtitle:
            draw.text((x, y + 65), subtitle, fill=GRAY_RGB, font=small_font, anchor="mt")

    # Row 1: Accuracy + Price Change
    acc = stats.get("accuracy_pct", 0)
    acc_color = GREEN_RGB if acc >= 60 else YELLOW_RGB if acc >= 50 else RED_RGB
    total_pred = stats.get("total_predictions", 0)
    correct = stats.get("correct_predictions", 0)
    draw_stat_box(0, 0, "ACCURACY", f"{acc:.1f}%", f"{correct}/{total_pred} correct", acc_color)

    pct_change = stats.get("price_change_pct", 0)
    pct_color = GREEN_RGB if pct_change >= 0 else RED_RGB
    price_end = stats.get("price_end", 0)
    draw_stat_box(1, 0, "BTC PRICE", f"${price_end:,.0f}", f"{pct_change:+.2f}% this week", pct_color)

    # Row 2: Signals + Streak
    signals = stats.get("signals_count", 0)
    profitable = stats.get("profitable_signals", 0)
    sig_rate = f"{profitable}/{signals}" if signals > 0 else "N/A"
    draw_stat_box(0, 1, "SIGNALS", sig_rate, "profitable / total", GREEN_RGB)

    streak = stats.get("streak", 0)
    draw_stat_box(1, 1, "WIN STREAK", str(streak), "consecutive correct", YELLOW_RGB if streak >= 3 else TEXT_RGB)

    # Row 3: Users + Premium
    users_total = stats.get("users_total", 0)
    users_new = stats.get("users_new", 0)
    draw_stat_box(0, 2, "TOTAL USERS", f"{users_total:,}", f"+{users_new} this week", BLUE_RGB)

    premium = stats.get("premium_count", 0)
    draw_stat_box(1, 2, "PREMIUM", str(premium), "active subscribers", GREEN_RGB)

    add_watermark(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
