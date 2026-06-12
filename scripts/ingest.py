#!/usr/bin/env python3
"""CLI script to ingest data into ChromaDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings
from ingestion.chunker import MarkdownChunker
from ingestion.embedder import Embedder
from ingestion.scraper import LeetCodeScraper, MarkdownSourceLoader, NeetCodeScraper
from rag.vectorstore import VectorStore


def collect_documents(source: str):
    settings = get_settings()
    raw = settings.raw_data_dir
    documents = []

    lc = LeetCodeScraper()
    neet = NeetCodeScraper()
    md = MarkdownSourceLoader()

    if source in ("all", "leetcode"):
        json_path = raw / "leetcode" / "problems.json"
        md_dir = raw / "leetcode"
        if json_path.exists():
            documents.extend(lc.load_from_json(json_path))
            print(f"  Loaded {json_path}")
        if md_dir.exists():
            docs = lc.load_from_markdown_dir(md_dir)
            documents.extend(docs)
            print(f"  Loaded {len(docs)} markdown files from {md_dir}")

    if source in ("all", "neetcode"):
        neet_dir = raw / "neetcode"
        if neet_dir.exists():
            docs = neet.load_transcripts_dir(neet_dir)
            documents.extend(docs)
            print(f"  Loaded {len(docs)} NeetCode transcripts")

    if source in ("all", "discuss"):
        discuss_dir = raw / "discuss"
        if discuss_dir.exists():
            documents.extend(md.load_directory(discuss_dir, "discuss"))

    if source in ("all", "user_strategy"):
        strategy_dir = raw / "strategies"
        if strategy_dir.exists():
            documents.extend(md.load_directory(strategy_dir, "user_strategy"))

    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest LeetCode mentor data into ChromaDB")
    parser.add_argument(
        "--source",
        choices=["all", "leetcode", "neetcode", "discuss", "user_strategy"],
        default="all",
    )
    args = parser.parse_args()

    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting documents (source={args.source})...")
    documents = collect_documents(args.source)

    if not documents:
        print("No documents found. Add data under data/raw/ and retry.")
        sys.exit(1)

    print(f"Chunking {len(documents)} documents...")
    chunker = MarkdownChunker(settings.chunk_size, settings.chunk_overlap)
    chunks = chunker.chunk_many(documents)
    print(f"  -> {len(chunks)} chunks")

    print("Embedding and storing...")
    embedder = Embedder(settings.embedding_model)
    store = VectorStore(settings.chroma_persist_dir, settings.chroma_collection)
    count = store.ingest(chunks, embedder)
    print(f"Done! Ingested {count} chunks. Total in store: {store.count()}")


if __name__ == "__main__":
    main()
