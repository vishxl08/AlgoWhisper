"""Quick demo: retrieval without Groq API key."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_settings
from ingestion.embedder import Embedder
from rag.retriever import Retriever
from rag.vectorstore import VectorStore


def main() -> None:
    settings = get_settings()
    embedder = Embedder(settings.embedding_model)
    store = VectorStore(settings.chroma_persist_dir, settings.chroma_collection)
    retriever = Retriever(store, embedder, top_k=3)

    chunks = retriever.retrieve("hash map complement lookup", slug="two-sum")

    print("=== RETRIEVAL TEST (no API key needed) ===")
    print(f"ChromaDB total chunks: {store.count()}\n")

    for i, chunk in enumerate(chunks, 1):
        title = chunk.metadata.get("title", "")
        source = chunk.metadata.get("source", "")
        preview = chunk.text[:150].replace("\n", " ")
        print(f"[{i}] score={chunk.score} | {title} | source={source}")
        print(f"    {preview}...")
        print()


if __name__ == "__main__":
    main()
