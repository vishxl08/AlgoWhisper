"""SQLite progress tracker for streaks, solved problems, and time spent."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Generator

from config import get_settings


class ProgressTracker:
    def __init__(self, db_path: str | Path | None = None):
        settings = get_settings()
        self.db_path = Path(db_path or settings.sqlite_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS solved_problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    problem_slug TEXT NOT NULL,
                    solved_at TEXT NOT NULL,
                    time_spent_minutes INTEGER DEFAULT 0,
                    UNIQUE(user_id, problem_slug)
                );
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_date TEXT NOT NULL,
                    UNIQUE(user_id, activity_date)
                );
                """
            )

    def ensure_user(self, user_id: int, username: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
                (user_id, username, datetime.utcnow().isoformat()),
            )

    def mark_solved(self, user_id: int, problem_slug: str, time_spent_minutes: int = 0) -> None:
        self.ensure_user(user_id)
        today = date.today().isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO solved_problems (user_id, problem_slug, solved_at, time_spent_minutes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, problem_slug) DO UPDATE SET
                    solved_at = excluded.solved_at,
                    time_spent_minutes = excluded.time_spent_minutes
                """,
                (user_id, problem_slug, datetime.utcnow().isoformat(), time_spent_minutes),
            )
            conn.execute(
                "INSERT OR IGNORE INTO activity_log (user_id, activity_date) VALUES (?, ?)",
                (user_id, today),
            )

    def get_stats(self, user_id: int) -> dict[str, Any]:
        self.ensure_user(user_id)
        with self._conn() as conn:
            solved = conn.execute(
                "SELECT COUNT(*) AS cnt FROM solved_problems WHERE user_id = ?",
                (user_id,),
            ).fetchone()["cnt"]
            total_time = conn.execute(
                "SELECT COALESCE(SUM(time_spent_minutes), 0) AS t FROM solved_problems WHERE user_id = ?",
                (user_id,),
            ).fetchone()["t"]
            streak = self._calc_streak(conn, user_id)

        return {
            "solved_count": solved,
            "total_time_minutes": total_time,
            "current_streak": streak,
        }

    def _calc_streak(self, conn: sqlite3.Connection, user_id: int) -> int:
        rows = conn.execute(
            "SELECT activity_date FROM activity_log WHERE user_id = ? ORDER BY activity_date DESC",
            (user_id,),
        ).fetchall()

        if not rows:
            return 0

        streak = 0
        expected = date.today()
        for row in rows:
            activity = date.fromisoformat(row["activity_date"])
            if activity == expected:
                streak += 1
                expected = date.fromordinal(expected.toordinal() - 1)
            elif activity == expected and streak == 0:
                continue
            else:
                break
        return streak

    def get_solved_today(self, user_id: int) -> int:
        self.ensure_user(user_id)
        today = date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM solved_problems
                WHERE user_id = ? AND date(solved_at) = ?
                """,
                (user_id, today),
            ).fetchone()
            return row["cnt"]

    def get_solved_this_week(self, user_id: int) -> int:
        self.ensure_user(user_id)
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM solved_problems
                WHERE user_id = ? AND date(solved_at) >= ?
                """,
                (user_id, week_start),
            ).fetchone()
            return row["cnt"]

    def list_solved_slugs(self, user_id: int) -> list[str]:
        self.ensure_user(user_id)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT problem_slug FROM solved_problems WHERE user_id = ? ORDER BY solved_at DESC",
                (user_id,),
            ).fetchall()
            return [row["problem_slug"] for row in rows]

    def get_unsolved_suggestions(self, user_id: int, pool: list[dict[str, str]], limit: int = 3) -> list[dict[str, str]]:
        solved = set(self.list_solved_slugs(user_id))
        unsolved = [p for p in pool if p.get("slug") not in solved]
        easy = [p for p in unsolved if p.get("difficulty", "").lower() == "easy"]
        return (easy or unsolved)[:limit]
