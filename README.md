# CORTEXHUB

A modern Python desktop application that compares responses from **two AI models** (OpenAI GPT and Anthropic Claude) **side-by-side** with **live streaming** like ChatGPT.

Built with **PySide6**.

---

## Features

- One prompt, two models — answered in parallel
- Live token streaming into split response panels (no waiting for full response)
- Independent conversation history per model (stored in SQLite)
- Non-blocking UI (worker thread + asyncio)
- Dark modern UI with resizable splitter and fullscreen mode
- Per-model error isolation (one failure does not break the other)

---

## Project Structure

```
cortexhub/
├── main.py
├── requirements.txt
├── README.md
├── .env.example
├── ui/
│   ├── main_window.py
│   ├── response_panel.py
│   └── styles.py
├── ai/
│   ├── ai_manager.py
│   ├── openai_client.py
│   └── claude_client.py
├── workers/
│   └── ai_worker.py
├── sessions/
│   ├── session_manager.py
│   └── database.py
└── utils/
    └── helpers.py
```

---

## Quick Start (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then edit keys
python main.py
```

👉 **See [RUN_COMMANDS.md](RUN_COMMANDS.md) for detailed setup and run instructions.**

---

## Setup (Windows)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and add your real API keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
python main.py
```

---

## Usage

1. Type your question in the prompt box at the top.
2. Click **Send** (or press `Ctrl+Enter`).
3. Watch both panels stream their responses live.
4. Click **Clear** to wipe the visible panels (history is kept internally).
5. Click **Fullscreen** to toggle fullscreen mode.

When you ask a new question, the visible panels are cleared and streaming starts fresh — but each model still receives its previous conversation history internally for context.

---

## Models

Defaults (override via `.env`):

- OpenAI: `gpt-4o-mini`
- Anthropic: `claude-3-5-haiku-latest`

---

## Notes

- Requires Python 3.11+
- Each model's history is persisted in `cortexhub.db` (SQLite, created automatically).
