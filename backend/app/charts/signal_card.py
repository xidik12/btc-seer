"""Trading signal card with entry/target/stop-loss on mini price chart."""
import io
from PIL import Image, ImageDraw
from app.charts.branding import (
    create_base_image, add_watermark, get_font,
    BG_RGB, TEXT_RGB, GREEN_RGB, RED_RGB, YELLOW_RGB, BLUE_RGB, GRAY_RGB, BORDER_RGB,
)


def render_signal_card(
    action: str,
    entry_price: float,
    target_price: float,
    stop_loss: float,
    confidence: float,
    risk_rating: int,
    timeframe: str,
    reasoning: str | None = None,
    size: str = "telegram",
) -> bytes:
    """Render signal card as PNG bytes."""
    img, draw, w, h = create_base_image(size)

    title_font = get_font(26, bold=True)
    big_font = get_font(36, bold=True)
    medium_font = get_font(20)
    small_font = get_font(14)

    # Title
    draw.text((w // 2, 25), "BTC SEER TRADING SIGNAL", fill=BLUE_RGB, font=title_font, anchor="mt")

    # Action badge
    is_buy = "buy" in action.lower()
    action_color = GREEN_RGB if is_buy else RED_RGB
    action_text = action.upper().replace("_", " ")
    badge_w = 200
    draw.rounded_rectangle([w // 2 - badge_w // 2, 60, w // 2 + badge_w // 2, 95], radius=12, fill=action_color)
    draw.text((w // 2, 77), action_text, fill=(255, 255, 255), font=medium_font, anchor="mm")

    # Timeframe
    draw.text((w // 2, 110), f"Timeframe: {timeframe.upper()}", fill=GRAY_RGB + (100,) if len(GRAY_RGB) == 3 else GRAY_RGB, font=small_font, anchor="mt")

    # Price levels
    y_start = 145
    levels = [
        ("ENTRY", entry_price, BLUE_RGB),
        ("TARGET", target_price, GREEN_RGB),
        ("STOP-LOSS", stop_loss, RED_RGB),
    ]

    for i, (label, price, color) in enumerate(levels):
        y = y_start + i * 60
        # Label
        draw.text((w * 0.2, y), label, fill=color, font=medium_font, anchor="mm")
        # Price
        draw.text((w * 0.65, y), f"${price:,.0f}", fill=TEXT_RGB, font=big_font, anchor="mm")
        # Separator line
        if i < len(levels) - 1:
            draw.line([(50, y + 30), (w - 50, y + 30)], fill=BORDER_RGB, width=1)

    # R:R ratio
    if entry_price and target_price and stop_loss and abs(entry_price - stop_loss) > 0:
        rr = abs(target_price - entry_price) / abs(entry_price - stop_loss)
        rr_text = f"R:R = 1:{rr:.1f}"
    else:
        rr_text = ""

    # Confidence and risk
    info_y = y_start + 200
    draw.text((w * 0.3, info_y), f"Confidence: {confidence:.0f}%", fill=TEXT_RGB, font=medium_font, anchor="mm")

    risk_bar = "█" * risk_rating + "░" * (10 - risk_rating)
    risk_color = GREEN_RGB if risk_rating <= 3 else YELLOW_RGB if risk_rating <= 6 else RED_RGB
    draw.text((w * 0.7, info_y), f"Risk: {risk_bar}", fill=risk_color, font=small_font, anchor="mm")

    if rr_text:
        draw.text((w // 2, info_y + 30), rr_text, fill=YELLOW_RGB, font=medium_font, anchor="mt")

    # Reasoning (truncated)
    if reasoning:
        reason_text = reasoning[:120] + "..." if len(reasoning) > 120 else reasoning
        # Word wrap
        max_chars = w // 8
        lines = [reason_text[i:i + max_chars] for i in range(0, len(reason_text), max_chars)]
        for j, line in enumerate(lines[:3]):
            draw.text((w // 2, info_y + 65 + j * 18), line, fill=GRAY_RGB, font=small_font, anchor="mt")

    add_watermark(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
