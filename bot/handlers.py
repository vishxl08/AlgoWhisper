"""Telegram command handlers for all mentor bot commands."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from bot.api_client import MentorAPIClient
from bot.commands_catalog import command_by_name as get_command
from bot.help_text import format_help_message
from bot.menu import category_help_text, category_menu_keyboard, main_menu_keyboard
from bot.progress import ProgressTracker
from bot.scheduler import DAILY_PROBLEMS
from bot.session import SessionStore
from config import get_settings
from rag.prompt_builder import MODE_HEADERS, ResponseMode

logger = logging.getLogger(__name__)

session_store = SessionStore()
progress_tracker = ProgressTracker()

VALID_LANGS = {"python", "cpp", "java", "javascript", "go", "rust", "csharp", "c"}
VALID_LEVELS = {"beginner", "intermediate", "advanced"}


def _extract_slug(text: str) -> str | None:
    parts = text.strip().split()
    if len(parts) >= 2 and parts[0].startswith("/"):
        slug = parts[1].lower()
    elif parts and not parts[0].startswith("/"):
        slug = parts[0].lower()
    else:
        return None
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug or None


def _extract_args(text: str) -> str:
    parts = (text or "").strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _mode_from_name(name: str) -> ResponseMode | None:
    try:
        return ResponseMode(name)
    except ValueError:
        return None


async def _get_problem(user_id: int, text: str) -> tuple[str, str] | None:
    slug = _extract_slug(text)
    if slug:
        title = slug.replace("-", " ").title()
        session_store.set_current_problem(user_id, slug, title)
        return slug, title
    problem = session_store.get_current_problem(user_id)
    if problem:
        return problem["slug"], problem["title"]
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    progress_tracker.ensure_user(user.id, user.username)
    await update.message.reply_text(
        "👋 *Welcome to LeetCode Mentor Bot!*\n\n"
        "Your AI-powered DSA practice companion.\n\n"
        "• `/set two-sum` — set a problem\n"
        "• `/hint` — get a nudge\n"
        "• `/menu` — browse commands by category\n"
        "• `/help` — full command guide\n\n"
        "_Make sure `run_api.py` is running before using RAG commands._",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(format_help_message(), parse_mode="Markdown")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "📂 *Command Menu*\n\nChoose a category:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    if data == "menu:main":
        await query.edit_message_text(
            "📂 *Command Menu*\n\nChoose a category:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "menu:help":
        await query.edit_message_text(format_help_message(), parse_mode="Markdown")
        return

    if data.startswith("menu:cat:"):
        cat_id = data.split(":", 2)[2]
        await query.edit_message_text(
            category_help_text(cat_id),
            parse_mode="Markdown",
            reply_markup=category_menu_keyboard(cat_id),
        )
        return

    if data.startswith("menu:cmd:"):
        cmd_name = data.split(":", 2)[2]
        await query.edit_message_text(f"Running `/{cmd_name}`...", parse_mode="Markdown")
        await execute_command_by_name(update, context, cmd_name, from_callback=True)


async def execute_command_by_name(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cmd_name: str,
    from_callback: bool = False,
) -> None:
    cmd = get_command(cmd_name)
    if not cmd:
        target = update.callback_query.message if from_callback and update.callback_query else update.message
        if target:
            await target.reply_text(f"Unknown command: /{cmd_name}")
        return

    if cmd.kind == "rag" and cmd.mode:
        mode = _mode_from_name(cmd.mode)
        if mode:
            await _run_mode(update, mode, from_callback=from_callback)
            return

    dispatch = {
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
    handler = dispatch.get(cmd_name)
    if handler:
        await handler(update, context)


async def set_problem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    slug = _extract_slug(update.message.text or "")
    if not slug:
        await update.message.reply_text("Usage: `/set two-sum`", parse_mode="Markdown")
        return
    title = slug.replace("-", " ").title()
    session_store.set_current_problem(user.id, slug, title)
    session_store.clear_history(user.id)
    await update.message.reply_text(f"✅ Current problem set to *{title}* (`{slug}`)", parse_mode="Markdown")


async def _run_mode(
    update: Update,
    mode: ResponseMode,
    from_callback: bool = False,
) -> None:
    user = update.effective_user
    if not user:
        return

    text = ""
    if update.message:
        text = update.message.text or ""
    elif from_callback and update.callback_query and update.callback_query.message:
        text = ""

    problem = await _get_problem(user.id, text)
    reply_target = update.message
    if from_callback and update.callback_query:
        reply_target = update.callback_query.message

    if not problem:
        if reply_target:
            await reply_target.reply_text(
                "No problem set. Use `/set two-sum` first or pass a slug: `/hint two-sum`",
                parse_mode="Markdown",
            )
        return

    slug, title = problem
    chat = update.effective_chat
    if chat:
        await chat.send_action("typing")

    user_message = ""
    if mode == ResponseMode.CHECK:
        user_message = _extract_args(text)
        if not user_message:
            if reply_target:
                await reply_target.reply_text(
                    "Paste your code after the command:\n`/check def twoSum(nums, target): ...`",
                    parse_mode="Markdown",
                )
            return

    try:
        history = session_store.get_history(user.id)
        prefs = session_store.get_prefs(user.id)
        api: MentorAPIClient = context.bot_data["api_client"]
        result = await api.ask(
            mode=mode,
            problem_slug=slug,
            problem_title=title,
            message=user_message,
            conversation_history=history,
            user_prefs={"language": prefs["language"], "level": prefs["level"]},
        )
        answer = result["answer"]
        session_store.append_history(user.id, "user", f"/{mode.value} {slug}")
        session_store.append_history(user.id, "assistant", answer)

        header = MODE_HEADERS.get(mode.value, mode.value.title())
        if reply_target:
            await reply_target.reply_text(f"*{header}* — {title}\n\n{answer}", parse_mode="Markdown")
    except Exception as exc:
        logger.exception("RAG request failed")
        if reply_target:
            await reply_target.reply_text(f"❌ Error: {exc}")


def _make_mode_handler(mode: ResponseMode):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _run_mode(update, mode)

    handler.__name__ = f"{mode.value}_command"
    return handler


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    arg = _extract_args(update.message.text or "").lower()
    if arg not in VALID_LANGS:
        langs = ", ".join(sorted(VALID_LANGS))
        await update.message.reply_text(
            f"Usage: `/lang python`\n\nSupported: {langs}",
            parse_mode="Markdown",
        )
        return
    session_store.set_prefs(user.id, {"language": arg})
    await update.message.reply_text(f"✅ Code language set to *{arg}*", parse_mode="Markdown")


async def level_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    arg = _extract_args(update.message.text or "").lower()
    if arg not in VALID_LEVELS:
        await update.message.reply_text(
            "Usage: `/level beginner`\n\nOptions: beginner, intermediate, advanced",
            parse_mode="Markdown",
        )
        return
    session_store.set_prefs(user.id, {"level": arg})
    await update.message.reply_text(f"✅ Skill level set to *{arg}*", parse_mode="Markdown")


async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    arg = _extract_args(update.message.text or "")
    if not arg.isdigit():
        await update.message.reply_text("Usage: `/goal 30`", parse_mode="Markdown")
        return
    target = int(arg)
    session_store.set_prefs(user.id, {"goal": target})
    stats = progress_tracker.get_stats(user.id)
    await update.message.reply_text(
        f"🎯 Monthly goal set to *{target}* problems.\n"
        f"Current progress: {stats['solved_count']} solved.",
        parse_mode="Markdown",
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    stats = progress_tracker.get_stats(user.id)
    today_count = progress_tracker.get_solved_today(user.id)
    await update.message.reply_text(
        f"📅 *Today*\n"
        f"• Solved today: {today_count}\n"
        f"• Current streak: {stats['current_streak']} days\n"
        f"• Total solved: {stats['solved_count']}",
        parse_mode="Markdown",
    )


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    week_count = progress_tracker.get_solved_this_week(user.id)
    stats = progress_tracker.get_stats(user.id)
    await update.message.reply_text(
        f"📆 *This Week*\n"
        f"• Solved this week: {week_count}\n"
        f"• Total solved: {stats['solved_count']}\n"
        f"• Streak: {stats['current_streak']} days",
        parse_mode="Markdown",
    )


async def weak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    solved = progress_tracker.list_solved_slugs(user.id)
    suggestions = progress_tracker.get_unsolved_suggestions(user.id, DAILY_PROBLEMS, limit=5)
    lines = ["📉 *Practice More In These Areas*", ""]
    if not solved:
        lines.append("You have not marked any problems solved yet. Start with easy classics:")
    else:
        lines.append(f"You have solved {len(solved)} problems. Try these next:")
    for p in suggestions:
        lines.append(f"• *{p['title']}* (`{p['slug']}`) — {p['difficulty']}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def comeback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    stats = progress_tracker.get_stats(user.id)
    easy = progress_tracker.get_unsolved_suggestions(user.id, DAILY_PROBLEMS, limit=1)
    if not easy:
        await update.message.reply_text("🎉 You have cleared the warm-up pool! Pick any medium problem.")
        return
    p = easy[0]
    await update.message.reply_text(
        f"💪 *Comeback Mode*\n"
        f"Streak: {stats['current_streak']} days\n\n"
        f"Warm up with *{p['title']}* (`{p['slug']}`)\n"
        f"Use `/set {p['slug']}` then `/hint`",
        parse_mode="Markdown",
    )


async def celebrate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    stats = progress_tracker.get_stats(user.id)
    count = stats["solved_count"]
    milestones = [1, 5, 10, 25, 50, 100]
    milestone = max((m for m in milestones if count >= m), default=0)
    msg = f"🎉 *Celebration Time!*\n\nYou have solved *{count}* problems!"
    if milestone:
        msg += f"\n🏆 Milestone reached: *{milestone}+* solves!"
    msg += f"\n🔥 Streak: {stats['current_streak']} days"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def save_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    problem = session_store.get_current_problem(user.id)
    last = session_store.get_last_assistant_message(user.id)
    if not problem or not last:
        await update.message.reply_text("Nothing to save. Run `/hint` or `/explain` first on a set problem.")
        return

    settings = get_settings()
    out_dir = settings.raw_data_dir / "strategies"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{problem['slug']}.md"
    content = f"# {problem['title']}\n\nSaved on {datetime.utcnow().isoformat()}\n\n{last}\n"
    path.write_text(content, encoding="utf-8")
    await update.message.reply_text(f"💾 Saved to `{path.name}`. Re-ingest with `python scripts/ingest.py` to index it.", parse_mode="Markdown")


async def timer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    arg = _extract_args(update.message.text or "")
    minutes = int(arg) if arg.isdigit() else 25
    end = datetime.utcnow() + timedelta(minutes=minutes)
    await update.message.reply_text(
        f"⏱ *Pomodoro started* — {minutes} minutes.\n"
        f"Focus until ~{end.strftime('%H:%M')} UTC.\n"
        "Use `/set <slug>` and practice until the timer ends!",
        parse_mode="Markdown",
    )


async def duel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "⚔️ *Duel mode* is coming soon!\n"
        "You will be able to challenge a friend on the same problem and compare solve times.",
        parse_mode="Markdown",
    )


async def solved_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    problem = session_store.get_current_problem(user.id)
    if not problem:
        await update.message.reply_text("Set a problem first with `/set <slug>`.", parse_mode="Markdown")
        return
    progress_tracker.mark_solved(user.id, problem["slug"])
    stats = progress_tracker.get_stats(user.id)
    await update.message.reply_text(
        f"🎉 Marked *{problem['title']}* as solved!\n"
        f"Solved: {stats['solved_count']} | Streak: {stats['current_streak']} days",
        parse_mode="Markdown",
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    stats = progress_tracker.get_stats(user.id)
    prefs = session_store.get_prefs(user.id)
    problem = session_store.get_current_problem(user.id)
    current = f"{problem['title']} (`{problem['slug']}`)" if problem else "None"
    await update.message.reply_text(
        f"📊 *Your Stats*\n"
        f"• Solved: {stats['solved_count']} / {prefs.get('goal', 30)} goal\n"
        f"• Streak: {stats['current_streak']} days\n"
        f"• Time spent: {stats['total_time_minutes']} min\n"
        f"• Language: {prefs.get('language', 'python')}\n"
        f"• Level: {prefs.get('level', 'intermediate')}\n"
        f"• Current problem: {current}",
        parse_mode="Markdown",
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return
    session_store.clear_history(user.id)
    await update.message.reply_text("🧹 Conversation history cleared.")


# RAG mode command handlers
hint_command = _make_mode_handler(ResponseMode.HINT)
explain_command = _make_mode_handler(ResponseMode.EXPLAIN)
complexity_command = _make_mode_handler(ResponseMode.COMPLEXITY)
similar_command = _make_mode_handler(ResponseMode.SIMILAR)
pattern_command = _make_mode_handler(ResponseMode.PATTERN)
bruteforce_command = _make_mode_handler(ResponseMode.BRUTEFORCE)
optimal_command = _make_mode_handler(ResponseMode.OPTIMAL)
mistake_command = _make_mode_handler(ResponseMode.MISTAKE)
stuck_command = _make_mode_handler(ResponseMode.STUCK)
interview_command = _make_mode_handler(ResponseMode.INTERVIEW)
think_command = _make_mode_handler(ResponseMode.THINK)
check_command = _make_mode_handler(ResponseMode.CHECK)
edge_command = _make_mode_handler(ResponseMode.EDGE)
dryrun_command = _make_mode_handler(ResponseMode.DRYRUN)
mystrategy_command = _make_mode_handler(ResponseMode.MYSTRATEGY)
neet_command = _make_mode_handler(ResponseMode.NEET)
compare_command = _make_mode_handler(ResponseMode.COMPARE)
recall_command = _make_mode_handler(ResponseMode.RECALL)
roast_command = _make_mode_handler(ResponseMode.ROAST)
eli5_command = _make_mode_handler(ResponseMode.ELI5)
company_command = _make_mode_handler(ResponseMode.COMPANY)
visual_command = _make_mode_handler(ResponseMode.VISUAL)

RAG_HANDLERS: dict[str, object] = {
    "hint": hint_command,
    "explain": explain_command,
    "complexity": complexity_command,
    "similar": similar_command,
    "pattern": pattern_command,
    "bruteforce": bruteforce_command,
    "optimal": optimal_command,
    "mistake": mistake_command,
    "stuck": stuck_command,
    "interview": interview_command,
    "think": think_command,
    "check": check_command,
    "edge": edge_command,
    "dryrun": dryrun_command,
    "mystrategy": mystrategy_command,
    "neet": neet_command,
    "compare": compare_command,
    "recall": recall_command,
    "roast": roast_command,
    "eli5": eli5_command,
    "company": company_command,
    "visual": visual_command,
}
