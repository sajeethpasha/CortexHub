"""Public RAG API used by AIManager and the UI.

Auto-ingestion flow
-------------------
On first import this module scans  rag/documents/  and indexes any file
that is not yet in the vector store.  This means:

  1. You add a PDF/TXT/MD to  rag/documents/  and push to git.
  2. Your teammate pulls.
  3. On next app launch the file is automatically indexed on their machine.

Neither developer has to remember to run an ingest command.
"""
from __future__ import annotations

import logging
import os

from rag.document_loader import load_file
from rag.vector_store import VectorStore

log = logging.getLogger(__name__)

# All committed documents live here — this folder IS tracked by git.
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")

_store = VectorStore()


# ------------------------------------------------------------------ public API


def ingest(path: str) -> int:
    """Index a single file. Returns the number of chunks added.

    Called from the UI when the user clicks 'Load Document'.
    """
    source = os.path.basename(path)
    chunks = load_file(path)
    _store.add(chunks, source=source)
    log.info("RAG: indexed %d chunks from '%s'", len(chunks), source)
    return len(chunks)


def retrieve(query: str, top_k: int = 4) -> str:
    """Return a formatted context block ready to inject into a prompt.

    Returns an empty string when no documents are indexed.
    """
    chunks = _store.query(query, top_k=top_k)
    if not chunks:
        return ""
    joined = "\n---\n".join(chunks)
    return f"═══ RELEVANT CONTEXT (from your documents) ═══\n{joined}\n═══ END CONTEXT ═══"


def clear() -> None:
    """Remove all indexed documents from the local vector store."""
    _store.clear()
    log.info("RAG: vector store cleared")


def status() -> dict:
    """Return indexing stats useful for the UI status bar."""
    return {
        "total_chunks": _store.count(),
        "sources": _store.indexed_sources(),
    }


# ------------------------------------------------------------------ auto-ingest


def _auto_ingest_documents_folder() -> None:
    """Index any file in rag/documents/ not yet in the vector store."""
    if not os.path.isdir(DOCUMENTS_DIR):
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)
        return

    already_indexed = set(_store.indexed_sources())
    supported = {".pdf", ".txt", ".md"}

    for filename in os.listdir(DOCUMENTS_DIR):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in supported:
            continue
        if filename in already_indexed:
            log.debug("RAG: '%s' already indexed, skipping", filename)
            continue
        path = os.path.join(DOCUMENTS_DIR, filename)
        try:
            count = ingest(path)
            log.info("RAG auto-ingest: '%s' → %d chunks", filename, count)
        except Exception as exc:  # noqa: BLE001
            log.warning("RAG auto-ingest failed for '%s': %s", filename, exc)


# Run once at import time — fast when nothing new to index.
_auto_ingest_documents_folder()
