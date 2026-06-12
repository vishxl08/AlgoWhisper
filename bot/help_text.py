"""Rich /help message formatter."""

from __future__ import annotations

from bot.commands_catalog import CATEGORIES


def format_help_message() -> str:
    lines = [
        "📖 *LeetCode Mentor — Command Guide*",
        "",
        "Tap `/menu` for an interactive keyboard, or use any command below.",
        "",
    ]

    for cat in CATEGORIES:
        lines.append(f"{cat.emoji} *{cat.title}*")
        for cmd in cat.commands:
            usage = cmd.usage or f"/{cmd.name}"
            lines.append(f"• `{usage}` — {cmd.help_detail}")
        lines.append("")

    lines.append("_Tip: Set a problem first with `/set two-sum`, then use learning or interview commands._")
    return "\n".join(lines).strip()
