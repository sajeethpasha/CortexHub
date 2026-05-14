# Run Commands - CORTEXHUB

Quick reference for running the CORTEXHUB application.

---

## One-Time Setup

Run these commands once to set up the project:

```bash
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate the virtual environment (Windows)
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
copy .env.example .env
```

Then edit `.env` and add your API keys:

```env
OPENAI_API_KEY=sk-proj-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## Running the Application

### Quick Start (from within activated venv)

```bash
python main.py
```

### From Outside the Virtual Environment

```bash
# Windows PowerShell
.venv\Scripts\python.exe main.py

# Windows Command Prompt
.venv\Scripts\python main.py
```

---

## Step-by-Step Launch (Full Command Chain)

### Windows PowerShell

```powershell
# Create venv
python -m venv .venv

# Activate and run
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Windows Command Prompt (cmd.exe)

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

---

## Application Controls

Once CORTEXHUB is running:

| Action | Control |
|--------|---------|
| Send prompt | Click **Send** or press `Ctrl+Enter` |
| Clear visible panels | Click **Clear** |
| Toggle fullscreen | Click **Fullscreen** or press `F11` |
| Close app | Close the window |

---

## Troubleshooting

### Missing API Key Error
**Problem:** `[Error] OpenAI: Error code: 401 - {'error': ...}`

**Solution:** Check that your `.env` file contains valid API keys.

### ModuleNotFoundError: No module named 'PySide6'
**Problem:** Dependencies not installed

**Solution:** 
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### Port/Permission Errors
The app uses no network ports — run it directly from the folder it was installed in.

---

## Reinstalling Dependencies

If you need to reinstall all packages:

```bash
.venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

---

## Environment Variables

Stored in `.env` (created from `.env.example`):

```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional: override default models
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

---

## File Structure Reference

```
cortexhub/
├── main.py              ← Entry point
├── requirements.txt     ← Dependencies
├── .env                 ← API keys (git ignored)
├── .env.example         ← Template
├── cortexhub.db         ← SQLite history (auto-created)
├── ai/
│   ├── openai_client.py
│   ├── claude_client.py
│   └── ai_manager.py
├── ui/
│   ├── main_window.py
│   ├── response_panel.py
│   └── styles.py
├── workers/
│   └── ai_worker.py
├── sessions/
│   ├── database.py
│   └── session_manager.py
└── utils/
    └── helpers.py
```
