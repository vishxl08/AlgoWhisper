"""Sliding-window text chunker with rich metadata preservation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ingestion.scraper import ScrapedDocument


@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MarkdownChunker:
    """Split documents into overlapping chunks while keeping metadata."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: ScrapedDocument) -> list[Chunk]:
        paragraphs = [p.strip() for p in doc.content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [doc.content] if doc.content.strip() else []

        chunks: list[Chunk] = []
        buffer = ""
        chunk_index = 0

        for para in paragraphs:
            candidate = f"{buffer}\n\n{para}".strip() if buffer else para
            if len(candidate) <= self.chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.append(self._make_chunk(doc, buffer, chunk_index))
                chunk_index += 1
                buffer = self._overlap_tail(buffer) + "\n\n" + para if self.chunk_overlap else para
            else:
                for piece in self._split_long_text(para):
                    chunks.append(self._make_chunk(doc, piece, chunk_index))
                    chunk_index += 1
                buffer = ""

        if buffer:
            chunks.append(self._make_chunk(doc, buffer, chunk_index))

        return chunks

    def chunk_many(self, documents: list[ScrapedDocument]) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks

    def _make_chunk(self, doc: ScrapedDocument, text: str, index: int) -> Chunk:
        meta = {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "source": doc.source,
            "chunk_index": index,
            **doc.metadata,
        }
        return Chunk(
            chunk_id=f"{doc.doc_id}_chunk_{index}",
            text=text.strip(),
            metadata=meta,
        )

    def _split_long_text(self, text: str) -> list[str]:
        words = text.split()
        pieces: list[str] = []
        current: list[str] = []
        current_len = 0

        for word in words:
            word_len = len(word) + 1
            if current_len + word_len > self.chunk_size and current:
                pieces.append(" ".join(current))
                overlap_words = current[-max(1, self.chunk_overlap // 5) :]
                current = overlap_words + [word]
                current_len = sum(len(w) + 1 for w in current)
            else:
                current.append(word)
                current_len += word_len

        if current:
            pieces.append(" ".join(current))
        return pieces

    def _overlap_tail(self, text: str) -> str:
        if self.chunk_overlap <= 0:
            return ""
        return text[-self.chunk_overlap :]
