"""Top-k similarity retrieval with metadata filtering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ingestion.embedder import Embedder
from rag.vectorstore import VectorStore


@dataclass
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]
    score: float  # cosine similarity (1 - distance)


class Retriever:
    def __init__(self, vectorstore: VectorStore, embedder: Embedder, top_k: int = 5):
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        *,
        slug: str | None = None,
        source: str | None = None,
        difficulty: str | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        where = self._build_filter(slug=slug, source=source, difficulty=difficulty)
        embedding = self.embedder.embed_query(query)
        k = top_k or self.top_k

        results = self.vectorstore.query(embedding, top_k=k, where=where)
        return self._parse_results(results)

    def retrieve_similar_problems(self, slug: str, top_k: int = 5) -> list[RetrievedChunk]:
        """Find chunks from problems with similar patterns/tags (single retrieval pass)."""
        title = slug.replace("-", " ")
        query = (
            f"similar LeetCode problems to {title} — same patterns, tags, "
            f"and difficulty level for practice"
        )
        return self.retrieve(query, top_k=top_k)

    def _build_filter(
        self,
        *,
        slug: str | None,
        source: str | None,
        difficulty: str | None,
    ) -> dict[str, Any] | None:
        clauses: list[dict[str, Any]] = []
        if slug:
            clauses.append({"slug": slug})
        if source:
            clauses.append({"source": source})
        if difficulty:
            clauses.append({"difficulty": difficulty})

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @staticmethod
    def _parse_results(results: dict) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for text, meta, dist in zip(docs, metas, distances):
            chunks.append(
                RetrievedChunk(
                    text=text,
                    metadata=meta or {},
                    score=round(1.0 - dist, 4),
                )
            )
        return chunks
