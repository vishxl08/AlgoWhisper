"""Orchestrates retrieval, prompting, and LLM generation."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from config import get_settings
from ingestion.embedder import Embedder
from rag.llm import GroqLLM
from rag.prompt_builder import PromptBuilder, ResponseMode
from rag.retriever import Retriever
from rag.vectorstore import VectorStore

SOURCE_FILTER: dict[ResponseMode, str] = {
    ResponseMode.MYSTRATEGY: "user_strategy",
    ResponseMode.NEET: "neetcode",
}


class MentorService:
    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        llm: GroqLLM,
    ):
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.llm = llm

    def ask(
        self,
        mode: ResponseMode,
        problem_slug: str,
        problem_title: str | None = None,
        user_message: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        user_prefs: dict[str, Any] | None = None,
    ) -> dict:
        title = problem_title or problem_slug.replace("-", " ").title()
        chunks = self._retrieve(mode, problem_slug, title, user_message)

        messages = self.prompt_builder.build(
            mode=mode,
            problem_title=title,
            problem_slug=problem_slug,
            context_chunks=chunks,
            user_message=user_message,
            conversation_history=conversation_history,
            user_prefs=user_prefs,
        )

        answer = self.llm.generate(messages)
        return {
            "mode": mode.value,
            "problem_slug": problem_slug,
            "problem_title": title,
            "answer": answer,
            "sources": [
                {
                    "title": c.metadata.get("title", ""),
                    "source": c.metadata.get("source", ""),
                    "score": c.score,
                }
                for c in chunks[:3]
            ],
        }

    def _retrieve(
        self,
        mode: ResponseMode,
        problem_slug: str,
        title: str,
        user_message: str,
    ):
        if mode == ResponseMode.SIMILAR:
            return self.retriever.retrieve_similar_problems(problem_slug)

        source = SOURCE_FILTER.get(mode)
        query = user_message or f"{mode.value} for {title}"

        if mode == ResponseMode.COMPARE:
            return self.retriever.retrieve(
                f"user strategy and optimal solution for {title}",
                slug=problem_slug,
            )

        if mode in (ResponseMode.MYSTRATEGY, ResponseMode.NEET):
            return self.retriever.retrieve(query, slug=problem_slug, source=source)

        if source:
            return self.retriever.retrieve(query, slug=problem_slug, source=source)

        return self.retriever.retrieve(query, slug=problem_slug)


@lru_cache
def get_mentor_service() -> MentorService:
    settings = get_settings()
    embedder = Embedder(settings.embedding_model)
    vectorstore = VectorStore(settings.chroma_persist_dir, settings.chroma_collection)
    retriever = Retriever(vectorstore, embedder, top_k=settings.retrieval_top_k)
    return MentorService(retriever, PromptBuilder(), GroqLLM())
