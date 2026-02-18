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
                text="🔮 Open BTC Seer",
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


def subscription_tiers_keyboard() -> InlineKeyboardMarkup:
    """Subscription tier selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Monthly — {settings.premium_price_stars_monthly} Stars ($9.99)",
            callback_data="sub_tier:monthly",
        )],
        [InlineKeyboardButton(
            text=f"3 Months — {settings.premium_price_stars_quarterly} Stars (save 17%)",
            callback_data="sub_tier:quarterly",
        )],
        [InlineKeyboardButton(
            text=f"Yearly — {settings.premium_price_stars_yearly} Stars (save 25%)",
            callback_data="sub_tier:yearly",
        )],
        [InlineKeyboardButton(text="Back", callback_data="back_to_main")],
    ])


def subscribe_keyboard() -> InlineKeyboardMarkup:
    """Subscribe prompt keyboard (quick single button)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="View Plans", callback_data="subscribe")],
        [InlineKeyboardButton(text="Back", callback_data="back_to_main")],
    ])


def faq_keyboard() -> InlineKeyboardMarkup:
    """FAQ topic selection keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="What is BTC Seer?", callback_data="faq:what_is"),
            InlineKeyboardButton(text="How accurate?", callback_data="faq:accuracy"),
        ],
        [
            InlineKeyboardButton(text="How to subscribe?", callback_data="faq:subscribe"),
            InlineKeyboardButton(text="Free trial?", callback_data="faq:trial"),
        ],
        [
            InlineKeyboardButton(text="Trading advisor?", callback_data="faq:advisor"),
            InlineKeyboardButton(text="Data sources?", callback_data="faq:data"),
        ],
        [
            InlineKeyboardButton(text="Referral program?", callback_data="faq:referral"),
            InlineKeyboardButton(text="Not financial advice", callback_data="faq:disclaimer"),
        ],
        [InlineKeyboardButton(text="« Back", callback_data="back_to_main")],
    ])


def alert_list_keyboard(alerts: list) -> InlineKeyboardMarkup:
    """Keyboard with delete buttons for each active alert."""
    buttons = []
    for a in alerts[:10]:
        symbol = a.coin_id.upper()[:6] if hasattr(a, 'coin_id') else "BTC"
        direction = "↑" if a.direction == "above" else "↓"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ {symbol} {direction} ${a.target_price:,.0f}",
                callback_data=f"delete_alert:{a.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def game_keyboard() -> InlineKeyboardMarkup:
    """Prediction game UP/DOWN keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 UP", callback_data="game_predict:up"),
            InlineKeyboardButton(text="🔴 DOWN", callback_data="game_predict:down"),
        ],
        [InlineKeyboardButton(text="🏆 Leaderboard", callback_data="game_leaderboard")],
        [InlineKeyboardButton(text="« Back", callback_data="back_to_main")],
    ])


def feedback_keyboard(feedback_type: str, reference_id: int) -> InlineKeyboardMarkup:
    """Thumbs up/down feedback keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\ud83d\udc4d", callback_data=f"feedback:up:{feedback_type}:{reference_id}"),
            InlineKeyboardButton(text="\ud83d\udc4e", callback_data=f"feedback:down:{feedback_type}:{reference_id}"),
        ],
    ])
