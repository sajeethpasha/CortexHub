"""CORTEXHUB main window."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai.ai_manager import AIManager
from sessions.database import Database
from sessions.session_manager import MODEL_CLAUDE, MODEL_OPENAI, SessionManager
from ui.response_panel import ResponsePanel
from ui.styles import DARK_QSS
from workers.ai_worker import AIWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CORTEXHUB")
        self.resize(1280, 800)
        self.setStyleSheet(DARK_QSS)

        # ---- backend ------------------------------------------------------
        self._db = Database()
        self._session = SessionManager(self._db)
        self._ai_manager = AIManager(self._session)

        self._worker = AIWorker(self._ai_manager)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.response_finished.connect(self._on_finished)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

        # ---- ui -----------------------------------------------------------
        self._busy_models: set[str] = set()
        self._build_ui()

    # ---------------------------------------------------------------- ui setup
    def _build_ui(self) -> None:
        title = QLabel("CORTEXHUB")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Prompt input
        self._prompt = QTextEdit()
        self._prompt.setObjectName("PromptInput")
        self._prompt.setPlaceholderText(
            "Enter your question here...  (Ctrl+Enter to send)"
        )
        self._prompt.setFixedHeight(110)

        # Buttons
        self._send_btn = QPushButton("Send")
        self._send_btn.clicked.connect(self._on_send_clicked)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("SecondaryButton")
        self._clear_btn.clicked.connect(self._on_clear_clicked)

        self._fullscreen_btn = QPushButton("Fullscreen")
        self._fullscreen_btn.setObjectName("SecondaryButton")
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        self._status = QLabel("Ready.")
        self._status.setObjectName("StatusLabel")

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self._send_btn)
        button_row.addWidget(self._clear_btn)
        button_row.addWidget(self._fullscreen_btn)
        button_row.addStretch(1)
        button_row.addWidget(self._status)

        # Response panels in a horizontal splitter
        self._openai_panel = ResponsePanel("OpenAI GPT Response")
        self._claude_panel = ResponsePanel("Claude Response")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._openai_panel)
        splitter.addWidget(self._claude_panel)
        splitter.setSizes([640, 640])
        splitter.setHandleWidth(4)

        # Central layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(self._prompt)
        layout.addLayout(button_row)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_send_clicked)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_send_clicked)
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)

    # ----------------------------------------------------------------- actions
    def _on_send_clicked(self) -> None:
        prompt = self._prompt.toPlainText().strip()
        if not prompt or self._busy_models:
            return

        # Clear visible panels for the new question (history is kept in DB).
        self._openai_panel.clear()
        self._claude_panel.clear()

        self._busy_models = {MODEL_OPENAI, MODEL_CLAUDE}
        self._send_btn.setEnabled(False)
        self._status.setText("Streaming...")

        self._worker.submit(prompt)
        self._prompt.clear()

    def _on_clear_clicked(self) -> None:
        self._openai_panel.clear()
        self._claude_panel.clear()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ----------------------------------------------------------- worker events
    def _panel_for(self, model_name: str) -> ResponsePanel:
        return self._openai_panel if model_name == MODEL_OPENAI else self._claude_panel

    def _on_chunk(self, model_name: str, chunk: str) -> None:
        self._panel_for(model_name).append_chunk(chunk)

    def _on_finished(self, model_name: str) -> None:
        self._busy_models.discard(model_name)

    def _on_error(self, model_name: str, message: str) -> None:
        label = "OpenAI" if model_name == MODEL_OPENAI else "Claude"
        self._panel_for(model_name).show_error(f"{label}: {message}")
        self._busy_models.discard(model_name)

    def _on_all_done(self) -> None:
        self._busy_models.clear()
        self._send_btn.setEnabled(True)
        self._status.setText("Ready.")

    # ---------------------------------------------------------------- shutdown
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        try:
            self._worker.stop()
        finally:
            self._db.close()
        super().closeEvent(event)
