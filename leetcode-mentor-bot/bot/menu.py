"""Inline keyboard menus grouped by category."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.commands_catalog import CATEGORIES, category_by_id


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row: list[InlineKeyboardButton] = []
    for cat in CATEGORIES:
        if cat.id == "core":
            continue
        row.append(
            InlineKeyboardButton(
                f"{cat.emoji} {cat.title}",
                callback_data=f"menu:cat:{cat.id}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⚡ Core Commands", callback_data="menu:cat:core")])
    rows.append([InlineKeyboardButton("📖 Full Help", callback_data="menu:help")])
    return InlineKeyboardMarkup(rows)


def category_menu_keyboard(cat_id: str) -> InlineKeyboardMarkup:
    cat = category_by_id(cat_id)
    if not cat:
        return main_menu_keyboard()

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for cmd in cat.commands:
        if cmd.kind == "stub":
            continue
        label = f"/{cmd.name}"
        row.append(InlineKeyboardButton(label, callback_data=f"menu:cmd:{cmd.name}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def category_help_text(cat_id: str) -> str:
    cat = category_by_id(cat_id)
    if not cat:
        return "Unknown category."

    lines = [f"{cat.emoji} *{cat.title}*", ""]
    for cmd in cat.commands:
        usage = cmd.usage or f"/{cmd.name}"
        lines.append(f"• `{usage}` — {cmd.help_detail}")
    lines.append("")
    lines.append("_Tap a button below to run a command (requires a set problem for RAG commands)._")
    return "\n".join(lines)
