"""Bot entry point.

Run modes:
  uv run bot.py                          — start Telegram bot
  uv run bot.py --test "/start"          — test a command offline (no Telegram)
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
from services.lms_client import LMSClient


def make_client() -> LMSClient:
    return LMSClient(base_url=settings.lms_api_url, api_key=settings.lms_api_key)


async def dispatch(text: str) -> str:
    """Route a command string to the right handler and return its response."""
    client = make_client()
    text = text.strip()

    if text == "/start":
        return await handle_start()
    if text == "/help":
        return await handle_help()
    if text == "/health":
        return await handle_health(client)
    if text == "/labs":
        return await handle_labs(client)
    if text.startswith("/scores"):
        parts = text.split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else ""
        return await handle_scores(lab, client)

    return "Unknown command. Type /help to see available commands."


# ---------------------------------------------------------------------------
# --test mode
# ---------------------------------------------------------------------------


async def run_test(command: str) -> None:
    response = await dispatch(command)
    print(response)


# ---------------------------------------------------------------------------
# Telegram bot
# ---------------------------------------------------------------------------


async def run_bot() -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.filters import Command
    from aiogram.types import Message

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def on_start(message: Message) -> None:
        await message.answer(await handle_start())

    @dp.message(Command("help"))
    async def on_help(message: Message) -> None:
        await message.answer(await handle_help())

    @dp.message(Command("health"))
    async def on_health(message: Message) -> None:
        await message.answer(await handle_health(make_client()))

    @dp.message(Command("labs"))
    async def on_labs(message: Message) -> None:
        await message.answer(await handle_labs(make_client()))

    @dp.message(Command("scores"))
    async def on_scores(message: Message) -> None:
        parts = (message.text or "").split(maxsplit=1)
        lab = parts[1] if len(parts) > 1 else ""
        await message.answer(await handle_scores(lab, make_client()))

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
