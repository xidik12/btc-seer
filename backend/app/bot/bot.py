import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.config import settings
from app.database import async_session, BotUser
from app.bot.commands import router as commands_router
from app.bot.keyboards import main_keyboard, settings_keyboard

logger = logging.getLogger(__name__)

# Callback query router
callback_router = Router()


@callback_router.callback_query(lambda c: c.data == "predict")
async def cb_predict(callback: CallbackQuery):
    from app.bot.commands import cmd_predict
    await callback.answer()
    await cmd_predict(callback.message)


@callback_router.callback_query(lambda c: c.data == "signal")
async def cb_signal(callback: CallbackQuery):
    from app.bot.commands import cmd_signal
    await callback.answer()
    await cmd_signal(callback.message)


@callback_router.callback_query(lambda c: c.data == "news")
async def cb_news(callback: CallbackQuery):
    from app.bot.commands import cmd_news
    await callback.answer()
    await cmd_news(callback.message)


@callback_router.callback_query(lambda c: c.data == "accuracy")
async def cb_accuracy(callback: CallbackQuery):
    from app.bot.commands import cmd_accuracy
    await callback.answer()
    await cmd_accuracy(callback.message)


@callback_router.callback_query(lambda c: c.data == "settings")
async def cb_settings(callback: CallbackQuery):
    from app.bot.commands import cmd_settings
    await callback.answer()
    await cmd_settings(callback.message)


@callback_router.callback_query(lambda c: c.data == "back_to_main")
async def cb_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🔮 <b>BTC Oracle</b> — What would you like to see?",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@callback_router.callback_query(lambda c: c.data and c.data.startswith("set_interval:"))
async def cb_set_interval(callback: CallbackQuery):
    interval = callback.data.split(":")[1]

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.alert_interval = interval
            await session.commit()

    await callback.answer(f"Alert interval set to {interval}")
    await callback.message.edit_text(
        f"⚙️ <b>Alert Settings</b>\n\nAlert interval: <b>{interval}</b>",
        parse_mode="HTML",
        reply_markup=settings_keyboard(interval),
    )


@callback_router.callback_query(lambda c: c.data == "unsubscribe")
async def cb_unsubscribe(callback: CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if user:
            user.subscribed = False
            await session.commit()

    await callback.answer("Unsubscribed from alerts")
    await callback.message.edit_text(
        "🔕 You've been unsubscribed from alerts.\n\n"
        "Use /start to re-subscribe anytime.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


def create_bot() -> tuple[Bot, Dispatcher]:
    """Create and configure the Telegram bot."""
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    dp.include_router(commands_router)
    dp.include_router(callback_router)

    return bot, dp
