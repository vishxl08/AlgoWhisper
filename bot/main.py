"""Telegram bot entry point."""

from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.api_client import MentorAPIClient
from bot.commands_catalog import all_commands
from bot.commands_setup import register_bot_commands
from bot.handlers import (
    RAG_HANDLERS,
    celebrate_command,
    clear_command,
    comeback_command,
    duel_command,
    goal_command,
    help_command,
    lang_command,
    level_command,
    menu_callback,
    menu_command,
    save_command,
    set_problem_command,
    solved_command,
    start_command,
    stats_command,
    timer_command,
    today_command,
    weak_command,
    week_command,
)
from bot.scheduler import DailyDigestScheduler
from config import get_settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ACTION_HANDLERS = {
    "start": start_command,
    "help": help_command,
    "menu": menu_command,
    "set": set_problem_command,
    "solved": solved_command,
    "clear": clear_command,
    "stats": stats_command,
    "lang": lang_command,
    "level": level_command,
    "goal": goal_command,
    "today": today_command,
    "week": week_command,
    "weak": weak_command,
    "comeback": comeback_command,
    "celebrate": celebrate_command,
    "save": save_command,
    "timer": timer_command,
    "duel": duel_command,
}


async def post_init(application: Application) -> None:
    api_client: MentorAPIClient = application.bot_data["api_client"]
    await api_client.startup()
    await register_bot_commands(application)

    scheduler: DailyDigestScheduler = application.bot_data["scheduler"]
    scheduler.start()


async def post_shutdown(application: Application) -> None:
    api_client: MentorAPIClient = application.bot_data["api_client"]
    await api_client.shutdown()

    scheduler: DailyDigestScheduler = application.bot_data["scheduler"]
    scheduler.shutdown()


async def digest_on_command(update, context):
    """Subscribe/unsubscribe from daily digest."""
    user = update.effective_user
    if not user or not update.message:
        return

    scheduler: DailyDigestScheduler = context.bot_data["scheduler"]
    action = (update.message.text or "").split()
    subcommand = action[1].lower() if len(action) > 1 else "on"

    if subcommand == "off":
        scheduler.unsubscribe(user.id)
        await update.message.reply_text("🔕 Daily digest unsubscribed.")
    else:
        scheduler.subscribe(user.id)
        await update.message.reply_text(
            "🔔 Subscribed to daily digest! You'll get a problem each morning.\n"
            "Use `/digest off` to unsubscribe.",
            parse_mode="Markdown",
        )


def main() -> None:
    settings = get_settings()
    if not settings.telegram_token:
        raise ValueError("TELEGRAM_TOKEN is not set in .env")

    app = (
        Application.builder()
        .token(settings.telegram_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    registered: set[str] = set()
    for cmd in all_commands():
        if cmd.name in registered:
            continue
        registered.add(cmd.name)

        if cmd.name in ACTION_HANDLERS:
            app.add_handler(CommandHandler(cmd.name, ACTION_HANDLERS[cmd.name]))
        elif cmd.name in RAG_HANDLERS:
            app.add_handler(CommandHandler(cmd.name, RAG_HANDLERS[cmd.name]))
        elif cmd.name == "digest":
            app.add_handler(CommandHandler("digest", digest_on_command))

    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))

    app.bot_data["api_client"] = MentorAPIClient()
    app.bot_data["scheduler"] = DailyDigestScheduler(app)

    logger.info("LeetCode Mentor Bot starting with %s commands...", len(registered))
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
