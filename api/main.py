"""FastAPI endpoints for the LeetCode Mentor RAG pipeline."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import get_settings
from ingestion.chunker import MarkdownChunker
from ingestion.embedder import Embedder
from ingestion.scraper import LeetCodeScraper, MarkdownSourceLoader, NeetCodeScraper
from rag.prompt_builder import ResponseMode
from rag.service import get_mentor_service
from rag.vectorstore import VectorStore

logger = logging.getLogger(__name__)


def _preload_rag_pipeline() -> None:
    """Load embedding model and warm ChromaDB before first user request."""
    service = get_mentor_service()
    service.retriever.embedder.embed_query("warmup")
    logger.info("RAG pipeline preloaded (embedder + ChromaDB warm)")


class UserPrefs(BaseModel):
    language: str = "python"
    level: str = "intermediate"


class AskRequest(BaseModel):
    mode: ResponseMode
    problem_slug: str
    problem_title: str | None = None
    message: str = ""
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    user_prefs: UserPrefs | None = None


class IngestRequest(BaseModel):
    source: str = "all"  # all | leetcode | neetcode | discuss | user_strategy


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_preload_rag_pipeline)
    yield


app = FastAPI(
    title="LeetCode Mentor Bot API",
    description="RAG-powered hints, explanations, and complexity analysis",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    store = VectorStore(settings.chroma_persist_dir, settings.chroma_collection)
    return {
        "status": "ok",
        "chunks_indexed": store.count(),
        "model": settings.groq_model,
    }


@app.post("/ask")
async def ask(req: AskRequest) -> dict[str, Any]:
    try:
        service = get_mentor_service()
        prefs = req.user_prefs.model_dump() if req.user_prefs else None
        return await asyncio.to_thread(
            service.ask,
            req.mode,
            req.problem_slug,
            req.problem_title,
            req.message,
            req.conversation_history,
            prefs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ingest")
async def ingest(req: IngestRequest) -> dict[str, Any]:
    settings = get_settings()
    settings.raw_data_dir.mkdir(parents=True, exist_ok=True)

    documents = []
    lc_scraper = LeetCodeScraper()
    neet_scraper = NeetCodeScraper()
    md_loader = MarkdownSourceLoader()

    if req.source in ("all", "leetcode"):
        json_path = settings.raw_data_dir / "leetcode" / "problems.json"
        md_dir = settings.raw_data_dir / "leetcode"
        if json_path.exists():
            documents.extend(lc_scraper.load_from_json(json_path))
        if md_dir.exists():
            documents.extend(lc_scraper.load_from_markdown_dir(md_dir))

    if req.source in ("all", "neetcode"):
        neet_dir = settings.raw_data_dir / "neetcode"
        if neet_dir.exists():
            documents.extend(neet_scraper.load_transcripts_dir(neet_dir))

    if req.source in ("all", "discuss"):
        discuss_dir = settings.raw_data_dir / "discuss"
        if discuss_dir.exists():
            documents.extend(md_loader.load_directory(discuss_dir, "discuss"))

    if req.source in ("all", "user_strategy"):
        strategy_dir = settings.raw_data_dir / "strategies"
        if strategy_dir.exists():
            documents.extend(md_loader.load_directory(strategy_dir, "user_strategy"))

    if not documents:
        raise HTTPException(
            status_code=404,
            detail=f"No documents found for source '{req.source}'. Add files under data/raw/.",
        )

    chunker = MarkdownChunker(settings.chunk_size, settings.chunk_overlap)
    chunks = chunker.chunk_many(documents)
    embedder = Embedder(settings.embedding_model)
    store = VectorStore(settings.chroma_persist_dir, settings.chroma_collection)
    count = store.ingest(chunks, embedder)

    return {
        "documents": len(documents),
        "chunks_ingested": count,
        "total_chunks": store.count(),
    }


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run("api.main:app", host=s.api_host, port=s.api_port, reload=True)
