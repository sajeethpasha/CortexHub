# CortexHub — Copilot Instructions

## What this project is
CortexHub is a PySide6 desktop application that acts as a live AI-powered interview coach.
It runs two AI models side by side (OpenAI and Claude) and supports voice input, live captions,
and RAG (Retrieval-Augmented Generation) from local documents.

---

## Project structure

```
ai/          → AI client wrappers and AIManager (central coordinator)
rag/         → RAG engine: document loading, vector store, retrieval
sessions/    → SQLite-backed session and conversation history
ui/          → All PySide6 UI components
workers/     → QThread workers: AI streaming, voice input, captions
utils/       → Shared helpers
```

---

## Architecture rules

### AI calls always go through AIManager
- Never call `OpenAIClient` or `ClaudeClient` directly from UI or workers.
- All AI streaming goes through `AIManager.stream()` in `ai/ai_manager.py`.

### RAG — always use `rag/retriever.py`
- Never call `VectorStore` or `document_loader` directly from outside the `rag/` module.
- The only public RAG API is in `rag/retriever.py`:
  - `ingest(path)` — index a document file
  - `retrieve(query)` — get relevant context for a prompt
  - `status()` — chunk count and indexed sources
  - `clear()` — wipe the local vector store
- RAG context is injected into the system prompt inside `AIManager.stream()`. Do not inject it anywhere else.

### Documents folder
- Committed documents live in `rag/documents/`. They are auto-indexed at startup.
- The `.chroma/` vector store is local-only (gitignored). Never commit it.
- Uploaded documents from the UI go to `rag/uploads/` (also gitignored).

### Session history
- All conversation history is managed by `SessionManager` in `sessions/session_manager.py`.
- Database writes go through `Database` in `sessions/database.py`.
- Never write to the SQLite database directly from UI or worker code.

### Workers
- All long-running or async operations (AI streaming, voice input, captions) run in QThread workers inside `workers/`.
- Workers communicate with the UI only via Qt signals — never direct method calls.

---

## Code style
- All files use `from __future__ import annotations`.
- Use type hints on all function signatures.
- Keep UI code in `ui/`, business logic out of UI files.
- Use `logging` for debug/info output — never `print()` in production code.

---

## Dependencies
- `chromadb` — local vector store for RAG
- `pypdf` — PDF text extraction
- `openai` — OpenAI API + embeddings (`text-embedding-3-small`)
- `anthropic` — Claude API
- `PySide6` — desktop UI framework
- `vosk` — offline speech recognition

---

## Git
- Active feature branch: `feature/cortexhub-rag-engine`
- Merge target: `main`
- Never commit: `.env`, `.venv/`, `.chroma/`, `*.db`, `models/`, `rag/uploads/`
