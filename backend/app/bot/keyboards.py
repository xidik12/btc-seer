from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import settings


def main_keyboard() -> InlineKeyboardMarkup:
    """Main bot keyboard with quick actions."""
    buttons = [
        [
            InlineKeyboardButton(text="📊 Prediction", callback_data="predict"),
            InlineKeyboardButton(text="📈 Signal", callback_data="signal"),
        ],
        [
            InlineKeyboardButton(text="📰 News", callback_data="news"),
            InlineKeyboardButton(text="🎯 Accuracy", callback_data="accuracy"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
        ],
    ]

    # Add Mini App button if URL is configured
    if settings.telegram_webapp_url:
        buttons.insert(0, [
            InlineKeyboardButton(
                text="🔮 Open BTC Oracle",
                web_app=WebAppInfo(url=settings.telegram_webapp_url),
            ),
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_keyboard(current_interval: str = "1h") -> InlineKeyboardMarkup:
    """Alert settings keyboard."""
    intervals = [
        ("Every hour", "1h"),
        ("Every 4 hours", "4h"),
        ("Daily", "24h"),
    ]

    buttons = []
    for label, value in intervals:
        check = " ✓" if value == current_interval else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{label}{check}",
                callback_data=f"set_interval:{value}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🔕 Unsubscribe", callback_data="unsubscribe"),
    ])
    buttons.append([
        InlineKeyboardButton(text="« Back", callback_data="back_to_main"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def timeframe_keyboard() -> InlineKeyboardMarkup:
    """Timeframe selection keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="1H", callback_data="tf:1h"),
            InlineKeyboardButton(text="4H", callback_data="tf:4h"),
            InlineKeyboardButton(text="24H", callback_data="tf:24h"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_keyboard() -> InlineKeyboardMarkup:
    """Simple back button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="« Back", callback_data="back_to_main")],
    ])
