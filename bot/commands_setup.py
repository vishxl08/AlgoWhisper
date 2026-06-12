"""Register Telegram slash-command menu on bot startup."""

from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import Application

from bot.commands_catalog import telegram_bot_commands

logger = logging.getLogger(__name__)


async def register_bot_commands(application: Application) -> None:
    commands = [BotCommand(name, desc) for name, desc in telegram_bot_commands()]
    await application.bot.set_my_commands(commands)
    logger.info("Registered %s Telegram bot commands", len(commands))
