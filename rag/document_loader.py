"""Load and chunk documents (PDF, TXT, MD) for RAG indexing."""
from __future__ import annotations

import os

from pypdf import PdfReader

CHUNK_SIZE = 500      # characters per chunk
CHUNK_OVERLAP = 80    # overlap between consecutive chunks


def load_file(path: str) -> list[str]:
    """Detect file type and return a list of text chunks."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _chunk(_extract_pdf(path))
    if ext in (".txt", ".md"):
        return _chunk(_extract_text(path))
    raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .txt, .md")


def _extract_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _chunk(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks
