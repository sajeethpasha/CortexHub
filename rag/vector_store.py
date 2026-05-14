"""ChromaDB vector store with OpenAI embeddings."""
from __future__ import annotations

import os

import chromadb
from openai import OpenAI

_CHROMA_PATH = os.path.join(os.getcwd(), ".chroma")
_EMBED_MODEL = "text-embedding-3-small"

# Reuse the same OpenAI client (reads OPENAI_API_KEY from env)
_openai = OpenAI()


def _embed(texts: list[str]) -> list[list[float]]:
    resp = _openai.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [e.embedding for e in resp.data]


class VectorStore:
    """Persistent local vector store backed by ChromaDB."""

    def __init__(self, collection_name: str = "cortexhub_rag") -> None:
        self._db = chromadb.PersistentClient(path=_CHROMA_PATH)
        self._col = self._db.get_or_create_collection(collection_name)

    # ------------------------------------------------------------------ writes

    def add(self, chunks: list[str], source: str) -> None:
        """Embed and upsert chunks. Safe to call multiple times (upsert)."""
        if not chunks:
            return
        ids = [f"{source}__{i}" for i in range(len(chunks))]
        embeddings = _embed(chunks)
        self._col.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{"source": source}] * len(chunks),
        )

    def clear(self) -> None:
        """Remove all indexed chunks."""
        all_ids = self._col.get()["ids"]
        if all_ids:
            self._col.delete(ids=all_ids)

    # ------------------------------------------------------------------ reads

    def query(self, text: str, top_k: int = 4) -> list[str]:
        """Return top-k most relevant chunks for the given query text."""
        if self._col.count() == 0:
            return []
        embedding = _embed([text])[0]
        results = self._col.query(query_embeddings=[embedding], n_results=min(top_k, self._col.count()))
        return results["documents"][0]

    def count(self) -> int:
        return self._col.count()

    def indexed_sources(self) -> list[str]:
        """Return the unique source file names already indexed."""
        meta = self._col.get(include=["metadatas"])["metadatas"]
        return list({m["source"] for m in meta})
