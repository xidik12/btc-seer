"""Semi-circle Fear & Greed Index gauge."""
import io
import math
from PIL import Image, ImageDraw
from app.charts.branding import (
    create_base_image, add_watermark, get_font,
    BG_RGB, TEXT_RGB, GREEN_RGB, RED_RGB, YELLOW_RGB, BLUE_RGB, GRAY_RGB,
)


def render_fear_greed(
    index: int,
    label: str | None = None,
    size: str = "default",
) -> bytes:
    """Render Fear & Greed gauge as PNG bytes."""
    img, draw, w, h = create_base_image(size)

    title_font = get_font(26, bold=True)
    big_font = get_font(72, bold=True)
    medium_font = get_font(22)
    small_font = get_font(16)

    # Title
    draw.text((w // 2, 30), "FEAR & GREED INDEX", fill=BLUE_RGB, font=title_font, anchor="mt")

    # Semi-circle gauge
    cx, cy = w // 2, h // 2 + 40
    radius = min(w, h) // 3

    # Draw gauge segments (arc from 180° to 0°)
    segments = [
        (RED_RGB, 0, 25),       # Extreme Fear
        ((255, 150, 50), 25, 45),  # Fear
        (YELLOW_RGB, 45, 55),    # Neutral
        ((150, 220, 80), 55, 75),  # Greed
        (GREEN_RGB, 75, 100),    # Extreme Greed
    ]

    for color, start_val, end_val in segments:
        start_angle = 180 - (start_val / 100 * 180)
        end_angle = 180 - (end_val / 100 * 180)
        bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.arc(bbox, end_angle, start_angle, fill=color, width=20)

    # Needle
    angle_deg = 180 - (index / 100 * 180)
    angle_rad = math.radians(angle_deg)
    needle_len = radius - 30
    nx = cx + needle_len * math.cos(angle_rad)
    ny = cy - needle_len * math.sin(angle_rad)
    draw.line([(cx, cy), (nx, ny)], fill=TEXT_RGB, width=3)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=TEXT_RGB)

    # Value
    if index <= 20:
        val_color = RED_RGB
    elif index <= 40:
        val_color = (255, 150, 50)
    elif index <= 60:
        val_color = YELLOW_RGB
    elif index <= 80:
        val_color = (150, 220, 80)
    else:
        val_color = GREEN_RGB

    draw.text((cx, cy + 30), str(index), fill=val_color, font=big_font, anchor="mt")

    # Label
    if label is None:
        if index <= 20:
            label = "Extreme Fear"
        elif index <= 40:
            label = "Fear"
        elif index <= 60:
            label = "Neutral"
        elif index <= 80:
            label = "Greed"
        else:
            label = "Extreme Greed"

    draw.text((cx, cy + 110), label.upper(), fill=val_color, font=medium_font, anchor="mt")

    # Scale labels
    draw.text((cx - radius - 10, cy + 10), "0", fill=RED_RGB, font=small_font, anchor="rm")
    draw.text((cx + radius + 10, cy + 10), "100", fill=GREEN_RGB, font=small_font, anchor="lm")
    draw.text((cx, cy - radius - 15), "50", fill=YELLOW_RGB, font=small_font, anchor="mb")

    add_watermark(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
