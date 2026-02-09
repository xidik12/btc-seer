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


def advisor_keyboard() -> InlineKeyboardMarkup:
    """Advisor menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Portfolio", callback_data="advisor_portfolio"),
            InlineKeyboardButton(text="Open Trades", callback_data="advisor_trades"),
        ],
        [
            InlineKeyboardButton(text="History", callback_data="advisor_history"),
            InlineKeyboardButton(text="Risk Settings", callback_data="advisor_risk"),
        ],
        [InlineKeyboardButton(text="« Back", callback_data="back_to_main")],
    ])


def trade_action_keyboard(trade_id: int) -> InlineKeyboardMarkup:
    """Trade action keyboard for new trade plans."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="I Opened This", callback_data=f"trade_opened:{trade_id}"),
            InlineKeyboardButton(text="Skip", callback_data=f"trade_cancel:{trade_id}"),
        ],
    ])


def trade_close_keyboard(trade_id: int) -> InlineKeyboardMarkup:
    """Trade close keyboard for open trades."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Close Trade", callback_data=f"trade_close:{trade_id}"),
        ],
    ])


def subscribe_keyboard() -> InlineKeyboardMarkup:
    """Subscribe prompt keyboard."""
    from app.config import settings
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Subscribe ({settings.premium_price_stars} Stars)", callback_data="subscribe")],
        [InlineKeyboardButton(text="Back", callback_data="back_to_main")],
    ])
