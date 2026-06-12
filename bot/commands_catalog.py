"""Central catalog of all bot commands grouped by category."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDef:
    name: str
    description: str
    help_detail: str
    kind: str  # rag | pref | stats | action | stub
    mode: str | None = None
    usage: str | None = None
    menu_emoji: str = "•"


@dataclass(frozen=True)
class CategoryDef:
    id: str
    title: str
    emoji: str
    commands: tuple[CommandDef, ...]


CATEGORIES: tuple[CategoryDef, ...] = (
    CategoryDef(
        id="core",
        title="Core",
        emoji="⚡",
        commands=(
            CommandDef("start", "Welcome message and quick intro", "Show welcome message", "action"),
            CommandDef("help", "Full categorized command guide", "Show all commands by category", "action"),
            CommandDef("menu", "Interactive command menu", "Open inline keyboard by category", "action"),
            CommandDef("set", "Set current problem", "Lock a problem as your active session", "action", usage="/set two-sum"),
            CommandDef("hint", "Nudge without full answer", "Get a hint without the full solution", "rag", "hint"),
            CommandDef("explain", "Step-by-step walkthrough", "Full explanation with approach outline", "rag", "explain"),
            CommandDef("complexity", "Time and space analysis", "Analyze time and space complexity", "rag", "complexity"),
            CommandDef("similar", "Related practice problems", "Get similar problems to practice next", "rag", "similar"),
            CommandDef("solved", "Mark problem as solved", "Mark the current problem as solved", "action"),
            CommandDef("clear", "Reset conversation history", "Clear chat history for current problem", "action"),
            CommandDef("digest", "Daily problem subscription", "Subscribe or unsubscribe from daily digest", "action", usage="/digest on"),
        ),
    ),
    CategoryDef(
        id="learning",
        title="Learning Style",
        emoji="📚",
        commands=(
            CommandDef("lang", "Set preferred code language", "Save Python, C++, Java, etc. for code examples", "pref", usage="/lang python"),
            CommandDef("level", "Set skill level", "Adjust hint depth for beginner or intermediate", "pref", usage="/level beginner"),
            CommandDef("pattern", "Name the DSA pattern only", "Identify the pattern without full solution", "rag", "pattern"),
            CommandDef("bruteforce", "Explain brute force first", "Walk through brute force before optimal", "rag", "bruteforce"),
            CommandDef("optimal", "Best approach and why", "Explain only the optimal approach", "rag", "optimal"),
            CommandDef("mistake", "Common mistakes to avoid", "List typical mistakes for this problem", "rag", "mistake"),
        ),
    ),
    CategoryDef(
        id="interview",
        title="Stuck and Interview",
        emoji="🧠",
        commands=(
            CommandDef("stuck", "Small nudge when stuck", "Context-aware nudge from your session", "rag", "stuck"),
            CommandDef("interview", "Mock interview mode", "Fewer hints, more interview-style questions", "rag", "interview"),
            CommandDef("think", "Guiding questions only", "Ask questions without giving answers", "rag", "think"),
            CommandDef("check", "Review your code or approach", "Paste code after the command for feedback", "rag", "check", usage="/check <your code>"),
            CommandDef("edge", "Edge cases and test cases", "List edge cases and suggested tests", "rag", "edge"),
            CommandDef("dryrun", "Trace example step by step", "Dry-run an example input step by step", "rag", "dryrun"),
        ),
    ),
    CategoryDef(
        id="progress",
        title="Progress and Motivation",
        emoji="📈",
        commands=(
            CommandDef("stats", "Overall progress summary", "Solved count, streak, and time spent", "stats"),
            CommandDef("weak", "Topics to improve", "See areas where you should practice more", "stats"),
            CommandDef("goal", "Set monthly solve target", "Set a monthly problem-solving goal", "pref", usage="/goal 30"),
            CommandDef("today", "Today's activity summary", "Problems solved and streak today", "stats"),
            CommandDef("week", "This week's summary", "Weekly solve count and activity", "stats"),
            CommandDef("comeback", "Easy warm-up after break", "Get an easy problem to restart your streak", "stats"),
            CommandDef("celebrate", "Milestone celebration", "Celebrate solve milestones with stats", "stats"),
        ),
    ),
    CategoryDef(
        id="content",
        title="Your Notes and Sources",
        emoji="📝",
        commands=(
            CommandDef("mystrategy", "Answer from your saved notes", "Retrieve only from your strategy notes", "rag", "mystrategy"),
            CommandDef("neet", "Answer from NeetCode transcripts", "Retrieve only from NeetCode content", "rag", "neet"),
            CommandDef("compare", "Your notes vs optimal", "Compare your strategy with optimal approach", "rag", "compare"),
            CommandDef("save", "Save last reply as a note", "Save the last bot reply to your notes", "action"),
            CommandDef("recall", "Quick revision of solved problems", "Revise problems you already solved", "rag", "recall"),
        ),
    ),
    CategoryDef(
        id="fun",
        title="Fun and Unique",
        emoji="🎮",
        commands=(
            CommandDef("roast", "Friendly roast of bad approach", "Playful roast plus constructive fix", "rag", "roast"),
            CommandDef("eli5", "Explain like I am five", "Explain the problem in very simple terms", "rag", "eli5"),
            CommandDef("company", "FAANG-style interview angle", "How this might be asked in top interviews", "rag", "company"),
            CommandDef("visual", "ASCII flow explanation", "Explain using a simple ASCII diagram", "rag", "visual"),
            CommandDef("timer", "Start a Pomodoro timer", "Start a focused practice timer in minutes", "stub", usage="/timer 25"),
            CommandDef("duel", "Challenge a friend", "Challenge a friend on the same problem", "stub", usage="/duel @friend"),
        ),
    ),
)


def all_commands() -> list[CommandDef]:
    seen: set[str] = set()
    result: list[CommandDef] = []
    for cat in CATEGORIES:
        for cmd in cat.commands:
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
    return result


def command_by_name(name: str) -> CommandDef | None:
    for cmd in all_commands():
        if cmd.name == name:
            return cmd
    return None


def category_by_id(cat_id: str) -> CategoryDef | None:
    for cat in CATEGORIES:
        if cat.id == cat_id:
            return cat
    return None


def telegram_bot_commands() -> list[tuple[str, str]]:
    """Flat list for setMyCommands — emoji prefixes simulate grouping."""
    emoji_map = {
        "core": "⚡",
        "learning": "📚",
        "interview": "🧠",
        "progress": "📈",
        "content": "📝",
        "fun": "🎮",
    }
    result: list[tuple[str, str]] = []
    for cat in CATEGORIES:
        prefix = emoji_map.get(cat.id, "•")
        for cmd in cat.commands:
            if cmd.name in ("start", "help", "menu"):
                desc = cmd.description
            else:
                desc = f"{prefix} {cmd.description}"
            result.append((cmd.name, desc[:256]))
    return result
