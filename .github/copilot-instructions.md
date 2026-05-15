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

## Strict boundaries

- **UI files** (`ui/`) must never contain: API logic, database access, embedding logic, or threading logic.
- **Workers** (`workers/`) must never: update UI directly or access the database directly.
- **RAG module** (`rag/`) must never: call UI components or access Qt objects.
- **AI clients** (`ai/claude_client.py`, `ai/openai_client.py`) must remain provider-specific only. Business orchestration belongs in `AIManager`.

---

## Naming conventions

- Worker classes end with `Worker` → e.g. `AIWorker`, `CaptionWorker`
- Manager classes end with `Manager` → e.g. `AIManager`, `SessionManager`
- AI provider wrappers end with `Client` → e.g. `OpenAIClient`, `ClaudeClient`
- Qt widgets end with `Widget`, dialogs end with `Dialog`
- Retrieval-related classes use `Retriever`

---

## Streaming rules

- AI responses must stream token-by-token — never buffer the full response before displaying.
- Never block the UI thread while streaming.
- Streaming updates must emit Qt signals (`chunk_received`, `response_finished`).
- Partial responses must be append-only to the UI.
- Errors must emit a dedicated `error_occurred` signal.

---

## Error handling

- Never silently swallow exceptions.
- Wrap external API failures (OpenAI, Anthropic) with user-friendly messages.
- Network and API failures must be logged with traceback.
- Worker exceptions must propagate through Qt signals, not raised directly.

---

## Logging

- Use module-level loggers: `log = logging.getLogger(__name__)`
- Log: startup lifecycle, RAG indexing events, retrieval results, AI provider failures, worker crashes.
- Never log: API keys, raw document contents, or raw embeddings.

---

## Performance

- Avoid re-indexing files already present in the vector store (check `indexed_sources()` first — already implemented).
- Heavy operations (indexing, embedding, AI streaming) must run in workers, never on the main thread.
- UI thread must not block for more than ~16ms.

---

## Security

- Never expose API keys in logs or UI.
- Never commit: `.env`, `*.db`, `.chroma/`, `models/`, `rag/uploads/`.
- Validate uploaded file types before passing to `document_loader` (supported: `.pdf`, `.txt`, `.md`).
- Sanitize file paths from UI input before any file operations.

---

## RAG chunking standards

- Current chunk size: **500 characters** with **80 character overlap** (defined in `rag/document_loader.py`).
- Do not change these values without testing retrieval quality.
- Preserve paragraph boundaries when possible during chunking.
- PDFs must be text-extractable — scanned image PDFs are not supported.

---

## Prompt architecture

- System prompts are built in `ai/ai_manager.py` via `_build_interview_prompt()` and `_INTERVIEW_SYSTEM_TEMPLATE`.
- Never hardcode prompts in UI files or workers.
- RAG context is injected into the system prompt inside `AIManager.stream()` only — do not inject it elsewhere.
- Conversation history is managed by `SessionManager` — do not pass raw history from UI code.

---

## Thread safety

- Qt widgets may only be modified on the main thread.
- Cross-thread communication uses Qt signals only — never direct method calls across threads.
- `AIWorker` owns its own asyncio event loop — do not share event loops between threads.

---

## Testing standards

- Core business logic must be unit-testable without launching the UI.
- Mock AI providers (`OpenAIClient`, `ClaudeClient`) during tests — never make real API calls in tests.
- Mock `VectorStore` during retrieval tests — do not require a real `.chroma/` folder.
- UI-independent logic belongs outside widget classes.

---

## AI coding priorities

When generating code for this project, prioritize in this order:

1. Separation of concerns (respect layer boundaries above)
2. Maintainability and readability
3. Thread safety
4. Streaming responsiveness
5. Testability
6. Performance

---

## Future scalability

CortexHub may later support:
- Multiple vector database backends
- Local LLM providers (Ollama, llama.cpp)
- Cloud sync for session history
- Multi-session memory
- Real-time meeting transcription
- Model plugin architecture

Design new features with these in mind — avoid hardcoding provider-specific assumptions.

---

## Git
- Active feature branch: `feature/cortexhub-rag-engine`
- Merge target: `main`
- Never commit: `.env`, `.venv/`, `.chroma/`, `*.db`, `models/`, `rag/uploads/`
