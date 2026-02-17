"""BTC price prediction card with direction arrow and confidence gauge."""
import io
from PIL import Image, ImageDraw
from app.charts.branding import (
    create_base_image, add_watermark, get_font,
    BG_RGB, TEXT_RGB, GREEN_RGB, RED_RGB, YELLOW_RGB, BLUE_RGB, GRAY_RGB, BORDER_RGB,
)


def render_prediction_card(
    current_price: float,
    direction: str,
    confidence: float,
    predicted_change_pct: float | None,
    timeframe: str,
    predicted_price: float | None = None,
    fear_greed: int | None = None,
    size: str = "default",
) -> bytes:
    """Render a prediction card as PNG bytes."""
    img, draw, w, h = create_base_image(size)

    title_font = get_font(28, bold=True)
    big_font = get_font(48, bold=True)
    medium_font = get_font(22)
    small_font = get_font(16)

    # Title
    draw.text((w // 2, 30), "BTC SEER PREDICTION", fill=BLUE_RGB, font=title_font, anchor="mt")

    # Timeframe badge
    tf_text = f"{timeframe.upper()} OUTLOOK"
    draw.rounded_rectangle([w // 2 - 80, 65, w // 2 + 80, 90], radius=10, fill=GRAY_RGB)
    draw.text((w // 2, 77), tf_text, fill=TEXT_RGB, font=small_font, anchor="mm")

    # Current price
    price_text = f"${current_price:,.0f}"
    draw.text((w // 2, 140), price_text, fill=TEXT_RGB, font=big_font, anchor="mm")

    # Direction arrow and label
    is_bullish = direction.lower() in ("bullish", "up")
    is_bearish = direction.lower() in ("bearish", "down")
    arrow_color = GREEN_RGB if is_bullish else RED_RGB if is_bearish else YELLOW_RGB
    arrow_text = "▲ BULLISH" if is_bullish else "▼ BEARISH" if is_bearish else "◄► NEUTRAL"

    dir_font = get_font(36, bold=True)
    draw.text((w // 2, 200), arrow_text, fill=arrow_color, font=dir_font, anchor="mm")

    # Predicted change
    if predicted_change_pct is not None:
        change_color = GREEN_RGB if predicted_change_pct >= 0 else RED_RGB
        change_text = f"{predicted_change_pct:+.2f}%"
        draw.text((w // 2, 245), change_text, fill=change_color, font=medium_font, anchor="mm")

    if predicted_price is not None:
        target_text = f"Target: ${predicted_price:,.0f}"
        draw.text((w // 2, 275), target_text, fill=TEXT_RGB, font=small_font, anchor="mm")

    # Confidence gauge (horizontal bar)
    gauge_y = 320
    gauge_w = int(w * 0.6)
    gauge_x = (w - gauge_w) // 2
    gauge_h = 30

    # Background bar
    draw.rounded_rectangle([gauge_x, gauge_y, gauge_x + gauge_w, gauge_y + gauge_h], radius=8, fill=GRAY_RGB)

    # Fill bar
    fill_w = int(gauge_w * confidence / 100)
    if fill_w > 0:
        conf_color = GREEN_RGB if confidence >= 65 else YELLOW_RGB if confidence >= 50 else RED_RGB
        draw.rounded_rectangle([gauge_x, gauge_y, gauge_x + fill_w, gauge_y + gauge_h], radius=8, fill=conf_color)

    # Confidence text
    draw.text((w // 2, gauge_y + gauge_h + 20), f"Confidence: {confidence:.0f}%", fill=TEXT_RGB, font=medium_font, anchor="mt")

    # Fear & Greed if available
    if fear_greed is not None:
        fg_y = gauge_y + gauge_h + 60
        fg_label = "Extreme Fear" if fear_greed <= 20 else "Fear" if fear_greed <= 40 else "Neutral" if fear_greed <= 60 else "Greed" if fear_greed <= 80 else "Extreme Greed"
        fg_color = RED_RGB if fear_greed <= 25 else YELLOW_RGB if fear_greed <= 50 else GREEN_RGB if fear_greed <= 75 else BLUE_RGB
        draw.text((w // 2, fg_y), f"Fear & Greed: {fear_greed} — {fg_label}", fill=fg_color, font=small_font, anchor="mt")

    # Watermark
    add_watermark(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
