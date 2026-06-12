"""ChromaDB vector store setup and ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import chromadb
from chromadb.config import Settings as ChromaSettings

if TYPE_CHECKING:
    from ingestion.chunker import Chunk
    from ingestion.embedder import Embedder


class VectorStore:
    def __init__(
        self,
        persist_dir: str | Path,
        collection_name: str = "leetcode_mentor",
    ):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [self._sanitize_metadata(c.metadata) for c in chunks]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict:
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def count(self) -> int:
        return self.collection.count()

    def ingest(self, chunks: list[Chunk], embedder: Embedder, batch_size: int = 64) -> int:
        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            vectors = embedder.embed_chunks(batch, batch_size=batch_size)
            total += self.upsert_chunks(batch, vectors)
        return total

    @staticmethod
    def _sanitize_metadata(meta: dict[str, Any]) -> dict[str, Any]:
        """ChromaDB only accepts str, int, float, bool metadata values."""
        clean: dict[str, Any] = {}
        for key, value in meta.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif isinstance(value, list):
                clean[key] = ", ".join(str(v) for v in value)
            else:
                clean[key] = str(value)
        return clean
