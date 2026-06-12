"""APScheduler daily digest — pushes a problem of the day to subscribed users."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from config import get_settings

logger = logging.getLogger(__name__)

DAILY_PROBLEMS = [
    {"slug": "two-sum", "title": "Two Sum", "difficulty": "Easy"},
    {"slug": "valid-parentheses", "title": "Valid Parentheses", "difficulty": "Easy"},
    {"slug": "merge-two-sorted-lists", "title": "Merge Two Sorted Lists", "difficulty": "Easy"},
    {"slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy"},
    {"slug": "maximum-subarray", "title": "Maximum Subarray", "difficulty": "Medium"},
    {"slug": "3sum", "title": "3Sum", "difficulty": "Medium"},
    {"slug": "longest-substring-without-repeating-characters", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium"},
    {"slug": "coin-change", "title": "Coin Change", "difficulty": "Medium"},
]


class DailyDigestScheduler:
    def __init__(self, application: Application):
        self.app = application
        self.scheduler = AsyncIOScheduler()
        settings = get_settings()
        self.subscribers_file = settings.data_dir / "digest_subscribers.json"
        self.subscribers_file.parent.mkdir(parents=True, exist_ok=True)

    def load_subscribers(self) -> set[int]:
        if not self.subscribers_file.exists():
            return set()
        return set(json.loads(self.subscribers_file.read_text(encoding="utf-8")))

    def save_subscribers(self, subscribers: set[int]) -> None:
        self.subscribers_file.write_text(json.dumps(sorted(subscribers)), encoding="utf-8")

    def subscribe(self, user_id: int) -> None:
        subs = self.load_subscribers()
        subs.add(user_id)
        self.save_subscribers(subs)

    def unsubscribe(self, user_id: int) -> None:
        subs = self.load_subscribers()
        subs.discard(user_id)
        self.save_subscribers(subs)

    def pick_daily_problem(self) -> dict[str, str]:
        raw_path = get_settings().raw_data_dir / "leetcode" / "problems.json"
        pool = DAILY_PROBLEMS
        if raw_path.exists():
            import json as _json

            items = _json.loads(raw_path.read_text(encoding="utf-8"))
            if isinstance(items, list) and items:
                pool = [
                    {
                        "slug": p.get("slug", p.get("titleSlug", "")),
                        "title": p["title"],
                        "difficulty": p.get("difficulty", "Unknown"),
                    }
                    for p in items
                    if p.get("slug") or p.get("titleSlug")
                ]
        return random.choice(pool)

    async def send_digest(self) -> None:
        subscribers = self.load_subscribers()
        if not subscribers:
            logger.info("No digest subscribers — skipping")
            return

        problem = self.pick_daily_problem()
        message = (
            f"📅 *Problem of the Day*\n\n"
            f"*{problem['title']}* (`{problem['slug']}`)\n"
            f"Difficulty: {problem['difficulty']}\n\n"
            f"Use `/set {problem['slug']}` then `/hint` to get started!"
        )

        for user_id in subscribers:
            try:
                await self.app.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                )
            except Exception:
                logger.warning("Failed to send digest to user %s", user_id)

    def start(self) -> None:
        settings = get_settings()
        self.scheduler.add_job(
            self.send_digest,
            trigger="cron",
            hour=settings.daily_digest_hour,
            minute=settings.daily_digest_minute,
            id="daily_digest",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            "Daily digest scheduled at %02d:%02d",
            settings.daily_digest_hour,
            settings.daily_digest_minute,
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
