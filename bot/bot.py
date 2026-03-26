"""Bot entry point.

Run modes:
  uv run bot.py                          — start Telegram bot
  uv run bot.py --test "/start"          — test a command offline (no Telegram)
  uv run bot.py --test "what labs?"      — test intent router offline
"""

import asyncio
import sys

from config import settings
from handlers.commands import (
    handle_health,
    handle_help,
    handle_labs,
    handle_scores,
    handle_start,
)
from handlers.router import route
from services.llm_client import LLMClient
from services.lms_client import LMSClient


def make_lms() -> LMSClient:
    return LMSClient(base_url=settings.lms_api_url, api_key=settings.lms_api_key)


def make_llm() -> LLMClient:
    return LLMClient(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_api_model,
    )


async def dispatch(text: str) -> str:
    """Route text to the right handler."""
    lms = make_lms()
    text = text.strip()

    if text == "/start":
        return await handle_start()
    if text == "/help":
        return await handle_help()
    if text == "/health":
        return await handle_health(lms)
    if text == "/labs":
        return await handle_labs(lms)
    if text.startswith("/scores"):
        parts = text.split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else ""
        return await handle_scores(lab, lms)
    if text.startswith("/"):
        return "Unknown command. Type /help to see available commands."

    # Plain text → intent router
    return await route(text, lms, make_llm())


# ---------------------------------------------------------------------------
# --test mode
# ---------------------------------------------------------------------------


async def run_test(command: str) -> None:
    print(await dispatch(command))


# ---------------------------------------------------------------------------
# Telegram bot
# ---------------------------------------------------------------------------


async def run_bot() -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.filters import Command
    from aiogram.types import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        Message,
        CallbackQuery,
    )

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    def start_keyboard() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Labs", callback_data="labs"),
                InlineKeyboardButton(text="❤️ Health", callback_data="health"),
            ],
            [
                InlineKeyboardButton(text="📊 Scores lab-04", callback_data="scores_lab-04"),
                InlineKeyboardButton(text="📊 Scores lab-07", callback_data="scores_lab-07"),
            ],
        ])

    @dp.message(Command("start"))
    async def on_start(message: Message) -> None:
        await message.answer(await handle_start(), reply_markup=start_keyboard())

    @dp.message(Command("help"))
    async def on_help(message: Message) -> None:
        await message.answer(await handle_help())

    @dp.message(Command("health"))
    async def on_health(message: Message) -> None:
        await message.answer(await handle_health(make_lms()))

    @dp.message(Command("labs"))
    async def on_labs(message: Message) -> None:
        await message.answer(await handle_labs(make_lms()))

    @dp.message(Command("scores"))
    async def on_scores(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else ""
        await message.answer(await handle_scores(lab, make_lms()))

    @dp.callback_query()
    async def on_callback(callback: CallbackQuery) -> None:
        data = callback.data or ""
        lms = make_lms()
        if data == "labs":
            text = await handle_labs(lms)
        elif data == "health":
            text = await handle_health(lms)
        elif data.startswith("scores_"):
            lab = data[len("scores_"):]
            text = await handle_scores(lab, lms)
        else:
            text = await route(data, lms, make_llm())
        await callback.message.answer(text)  # type: ignore[union-attr]
        await callback.answer()

    @dp.message()
    async def on_text(message: Message) -> None:
        text = message.text or ""
        await message.answer(await dispatch(text))

    await dp.start_polling(bot)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        command = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "/help"
        asyncio.run(run_test(command))
    else:
        asyncio.run(run_bot())
