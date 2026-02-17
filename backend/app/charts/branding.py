"""BTC Seer chart branding — colors, fonts, watermark."""
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Brand colors
BG_COLOR = "#0D1117"
BG_RGB = (13, 17, 23)
TEXT_COLOR = "#E6EDF3"
TEXT_RGB = (230, 237, 243)
GREEN = "#3FB950"
GREEN_RGB = (63, 185, 80)
RED = "#F85149"
RED_RGB = (248, 81, 73)
YELLOW = "#D29922"
YELLOW_RGB = (210, 153, 34)
BLUE = "#58A6FF"
BLUE_RGB = (88, 166, 255)
GRAY = "#484F58"
GRAY_RGB = (72, 79, 88)
BORDER_COLOR = "#30363D"
BORDER_RGB = (48, 54, 61)

# Platform sizes
SIZES = {
    "twitter": (1200, 675),
    "instagram": (1080, 1080),
    "telegram": (800, 600),
    "default": (800, 600),
}

WATERMARK_TEXT = "BTC Seer AI — t.me/BTCSeerBot"


def get_size(size_name: str) -> tuple[int, int]:
    return SIZES.get(size_name, SIZES["default"])


def apply_matplotlib_theme():
    """Apply dark theme to matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "axes.edgecolor": BORDER_COLOR,
        "axes.labelcolor": TEXT_COLOR,
        "text.color": TEXT_COLOR,
        "xtick.color": TEXT_COLOR,
        "ytick.color": TEXT_COLOR,
        "grid.color": BORDER_COLOR,
        "grid.alpha": 0.3,
        "legend.facecolor": BG_COLOR,
        "legend.edgecolor": BORDER_COLOR,
        "legend.labelcolor": TEXT_COLOR,
    })


def add_watermark(draw: ImageDraw.ImageDraw, width: int, height: int):
    """Add BTC Seer branding watermark to bottom-right corner."""
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    tw = bbox[2] - bbox[0]
    x = width - tw - 15
    y = height - 25
    draw.text((x, y), WATERMARK_TEXT, fill=(130, 130, 130), font=font)


def create_base_image(size_name: str = "default") -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    """Create a base image with dark background."""
    w, h = get_size(size_name)
    img = Image.new("RGB", (w, h), BG_RGB)
    draw = ImageDraw.Draw(img)
    return img, draw, w, h


def get_font(size: int = 16, bold: bool = False):
    """Get a font, falling back to default if system fonts unavailable."""
    try:
        path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        return ImageFont.truetype(path, size)
    except (OSError, IOError):
        return ImageFont.load_default()
