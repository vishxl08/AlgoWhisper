"""Async HTTP client — bot talks to FastAPI instead of loading RAG in-process."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from config import get_settings
from rag.prompt_builder import ResponseMode

logger = logging.getLogger(__name__)


class MentorAPIClient:
    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.api_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def startup(self, retries: int = 12, delay: float = 5.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(60.0, connect=5.0),
        )
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                resp = await self._client.get("/health")
                resp.raise_for_status()
                data = resp.json()
                logger.info(
                    "API ready at %s — %s chunks, model=%s",
                    self.base_url,
                    data.get("chunks_indexed"),
                    data.get("model"),
                )
                return
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
                logger.warning("API not ready (attempt %s/%s): %s", attempt, retries, exc)
                await asyncio.sleep(delay)
        raise RuntimeError(
            f"API at {self.base_url} did not start. Run `python run_api.py` first."
        ) from last_error

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def ask(
        self,
        mode: ResponseMode,
        problem_slug: str,
        problem_title: str | None = None,
        message: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        user_prefs: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("API client not started — is run_api.py running?")

        payload: dict[str, Any] = {
            "mode": mode.value,
            "problem_slug": problem_slug,
            "problem_title": problem_title,
            "message": message,
            "conversation_history": conversation_history or [],
        }
        if user_prefs:
            payload["user_prefs"] = user_prefs

        resp = await self._client.post("/ask", json=payload)
        if resp.status_code >= 400:
            detail = resp.json().get("detail", resp.text)
            raise RuntimeError(detail)
        return resp.json()
