"""Session store with Redis backend and in-memory fallback."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from config import get_settings

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 86400):
        settings = get_settings()
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl_seconds
        self._client: redis.Redis | None = None
        self._memory: dict[str, str] = {}
        self._use_redis = self._connect_redis()

    def _connect_redis(self) -> bool:
        try:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            self._client.ping()
            logger.info("Session store: using Redis at %s", self.redis_url)
            return True
        except (redis.RedisError, ConnectionError, OSError) as exc:
            logger.warning("Redis unavailable (%s) — using in-memory session store", exc)
            self._client = None
            return False

    def _key(self, user_id: int, suffix: str) -> str:
        return f"mentor:{user_id}:{suffix}"

    def _get(self, key: str) -> str | None:
        if self._use_redis and self._client:
            return self._client.get(key)
        return self._memory.get(key)

    def _set(self, key: str, value: str) -> None:
        if self._use_redis and self._client:
            self._client.setex(key, self.ttl, value)
        else:
            self._memory[key] = value

    def _delete(self, key: str) -> None:
        if self._use_redis and self._client:
            self._client.delete(key)
        else:
            self._memory.pop(key, None)

    def get_current_problem(self, user_id: int) -> dict[str, Any] | None:
        raw = self._get(self._key(user_id, "problem"))
        return json.loads(raw) if raw else None

    def set_current_problem(self, user_id: int, slug: str, title: str | None = None) -> None:
        payload = {"slug": slug, "title": title or slug.replace("-", " ").title()}
        self._set(self._key(user_id, "problem"), json.dumps(payload))

    def clear_current_problem(self, user_id: int) -> None:
        self._delete(self._key(user_id, "problem"))

    def get_history(self, user_id: int) -> list[dict[str, str]]:
        raw = self._get(self._key(user_id, "history"))
        return json.loads(raw) if raw else []

    def append_history(self, user_id: int, role: str, content: str) -> None:
        history = self.get_history(user_id)
        history.append({"role": role, "content": content})
        history = history[-20:]
        self._set(self._key(user_id, "history"), json.dumps(history))

    def clear_history(self, user_id: int) -> None:
        self._delete(self._key(user_id, "history"))

    def get_prefs(self, user_id: int) -> dict[str, Any]:
        raw = self._get(self._key(user_id, "prefs"))
        if raw:
            return json.loads(raw)
        return {"language": "python", "level": "intermediate", "goal": 30}

    def set_prefs(self, user_id: int, prefs: dict[str, Any]) -> None:
        current = self.get_prefs(user_id)
        current.update(prefs)
        self._set(self._key(user_id, "prefs"), json.dumps(current))

    def get_last_assistant_message(self, user_id: int) -> str | None:
        history = self.get_history(user_id)
        for entry in reversed(history):
            if entry.get("role") == "assistant":
                return entry.get("content")
        return None
