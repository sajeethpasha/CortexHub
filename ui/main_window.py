"""CORTEXHUB main window."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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


class _ResponseSplitter(QSplitter):
    """Thin divider splitter between the two response panels."""
    pass


class _FloatWindow(QWidget):
    """Standalone floating window for a detached panel. Docks back on request or close."""

    dock_requested = Signal(object)

    def __init__(self, content: QWidget, title: str, stylesheet: str) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle(f"CORTEXHUB  —  {title}")
        self.setStyleSheet(stylesheet)
        self.resize(800, 560)
        self._content = content
        self._docked = False

        lbl = QLabel(title)
        lbl.setObjectName("ContextLabel")

        dock_btn = QPushButton("⊟  Dock Back")
        dock_btn.setObjectName("TopBarButtonSecondary")
        dock_btn.clicked.connect(self._request_dock)

        bar = QWidget()
        bar.setObjectName("TopBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 0, 14, 0)
        bl.setSpacing(8)
        bl.addWidget(lbl)
        bl.addStretch(1)
        bl.addWidget(dock_btn)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(bar)
        outer.addWidget(content, 1)

    def _request_dock(self) -> None:
        if not self._docked:
            self._docked = True
            self.dock_requested.emit(self._content)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._request_dock()
        event.accept()

from ai.ai_manager import AIManager
from sessions.database import Database
from sessions.session_manager import MODEL_CLAUDE, MODEL_OPENAI, SessionManager
from ui.response_panel import ResponsePanel
from ui.styles import DARK_QSS
from workers.ai_worker import AIWorker
from workers.caption_worker import CaptionWorker


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
        self._openai_float: _FloatWindow | None = None
        self._openai_placeholder: QWidget | None = None
        self._claude_float: _FloatWindow | None = None
        self._claude_placeholder: QWidget | None = None
        self._prompt_float: _FloatWindow | None = None
        self._prompt_placeholder: QWidget | None = None
        self._caption_active = False
        self._caption_worker = CaptionWorker(self)
        self._caption_worker.text_ready.connect(self._on_caption_text)
        self._caption_worker.status_changed.connect(self._on_caption_status)
        self._build_ui()

    # ---------------------------------------------------------------- ui setup
    def _build_ui(self) -> None:
        # ---- top header bar (context label left, buttons right) ----------
        context_label = QLabel("CORTEXHUB")
        context_label.setObjectName("ContextLabel")

        self._status = QLabel("● Ready")
        self._status.setObjectName("StatusLabel")

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("TopBarButton")
        self._send_btn.clicked.connect(self._on_send_clicked)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("TopBarButtonSecondary")
        self._clear_btn.setToolTip("Clear the question / prompt")
        self._clear_btn.clicked.connect(self._clear_prompt)

        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setObjectName("TopBarButtonSecondary")
        self._edit_btn.setToolTip("Edit the current question")
        self._edit_btn.clicked.connect(self._edit_prompt)
        self._edit_btn.setVisible(False)

        self._fullscreen_btn = QPushButton("Fullscreen")
        self._fullscreen_btn.setObjectName("TopBarButtonSecondary")
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 0, 14, 0)
        top_layout.setSpacing(8)
        top_layout.addWidget(context_label)
        top_layout.addStretch(1)
        top_layout.addWidget(self._status)
        top_layout.addSpacing(12)
        top_layout.addWidget(self._send_btn)
        top_layout.addWidget(self._clear_btn)
        top_layout.addWidget(self._edit_btn)
        top_layout.addWidget(self._fullscreen_btn)

        # ---- prompt input ------------------------------------------------
        self._prompt = QTextEdit()
        self._prompt.setObjectName("PromptInput")
        self._prompt.setPlaceholderText(
            "Ask anything…   (Ctrl+Enter to send)"
        )
        self._prompt.setFixedHeight(116)

        prompt_hdr = QWidget()
        prompt_hdr.setObjectName("PanelTitleBar")
        ph_layout = QHBoxLayout(prompt_hdr)
        ph_layout.setContentsMargins(8, 0, 6, 0)
        ph_layout.setSpacing(4)
        ph_lbl = QLabel("Question")
        ph_lbl.setObjectName("PanelTitle")
        ph_layout.addWidget(ph_lbl, 1)
        prompt_detach_btn = QPushButton("Detach")
        prompt_detach_btn.setObjectName("PanelToolButton")
        prompt_detach_btn.setToolTip("Detach question box to floating window")
        prompt_detach_btn.setFixedHeight(26)
        prompt_detach_btn.clicked.connect(self._detach_prompt)
        ph_layout.addWidget(prompt_detach_btn)

        self._caption_btn = QPushButton("⏺ Live Caption")
        self._caption_btn.setObjectName("PanelToolButton")
        self._caption_btn.setToolTip(
            "Start / stop live captioning of system audio into the question box"
        )
        self._caption_btn.setFixedHeight(26)
        self._caption_btn.clicked.connect(self._toggle_live_caption)
        ph_layout.addWidget(self._caption_btn)

        self._prompt_container = QWidget()
        self._prompt_container.setObjectName("PromptContainer")
        prompt_inner = QVBoxLayout(self._prompt_container)
        prompt_inner.setContentsMargins(0, 0, 0, 0)
        prompt_inner.setSpacing(0)
        prompt_inner.addWidget(prompt_hdr)
        prompt_inner.addWidget(self._prompt)

        # ---- response panels in a horizontal splitter --------------------
        self._openai_panel = ResponsePanel("OpenAI GPT Response", show_tools=True)
        self._claude_panel = ResponsePanel("Claude Response", show_tools=True)
        self._openai_panel.detach_requested.connect(self._detach_openai)
        self._claude_panel.detach_requested.connect(self._detach_claude)

        self._splitter = _ResponseSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._openai_panel)
        self._splitter.addWidget(self._claude_panel)
        self._splitter.setSizes([640, 640])
        self._splitter.setHandleWidth(5)

        # ---- central layout ----------------------------------------------
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(top_bar)

        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(12, 6, 12, 10)
        self._inner_layout.setSpacing(6)
        self._inner_layout.addWidget(self._prompt_container)
        self._inner_layout.addWidget(self._splitter, 1)

        layout.addWidget(inner, 1)
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
        self._prompt.setReadOnly(True)
        self._edit_btn.setVisible(False)
        self._status.setText("● Streaming…")

        self._worker.submit(prompt)
        # Keep the question visible — do not clear the prompt

    def _on_clear_clicked(self) -> None:
        self._openai_panel.clear()
        self._claude_panel.clear()

    def _clear_prompt(self) -> None:
        """Clear prompt AND both response panels, unlock for new input."""
        self._prompt.setReadOnly(False)
        self._prompt.clear()
        self._openai_panel.clear()
        self._claude_panel.clear()
        self._send_btn.setEnabled(True)
        self._edit_btn.setVisible(False)
        self._status.setText("● Ready")

    def _edit_prompt(self) -> None:
        self._prompt.setReadOnly(False)
        self._prompt.setFocus()
        self._send_btn.setEnabled(True)
        self._edit_btn.setVisible(False)
        self._status.setText("● Ready")

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
        self._panel_for(model_name).finalize_render()
        self._busy_models.discard(model_name)

    def _on_error(self, model_name: str, message: str) -> None:
        label = "OpenAI" if model_name == MODEL_OPENAI else "Claude"
        self._panel_for(model_name).show_error(f"{label}: {message}")
        self._busy_models.discard(model_name)

    def _on_all_done(self) -> None:
        self._busy_models.clear()
        # Prompt stays locked — user must press Clear or Edit first
        self._edit_btn.setVisible(True)
        self._status.setText("● Done")

    # ── Live Caption ────────────────────────────────────────────────────────────────────
    def _toggle_live_caption(self) -> None:
        if self._caption_active:
            self._caption_active = False
            self._caption_btn.setText("⏺ Live Caption")
            self._caption_btn.setObjectName("PanelToolButton")
            self._caption_btn.setStyleSheet("")
            self._caption_worker.stop_caption()
        else:
            self._caption_active = True
            self._caption_btn.setText("⏹ Stop Caption")
            self._caption_btn.setObjectName("CaptionButtonActive")
            self._caption_btn.setStyleSheet(
                "QPushButton{background:#1a3a1a;color:#4ecb71;"
                "border:1px solid #2a6a2a;border-radius:5px;}"
                "QPushButton:hover{background:#204a20;}"
            )
            self._caption_worker.start_caption()

    def _on_caption_text(self, text: str) -> None:
        """Append recognised text to the prompt box."""
        was_readonly = self._prompt.isReadOnly()
        self._prompt.setReadOnly(False)
        from PySide6.QtGui import QTextCursor
        cursor = self._prompt.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._prompt.setTextCursor(cursor)
        self._prompt.insertPlainText(text)
        self._prompt.setReadOnly(was_readonly)

    def _on_caption_status(self, status: str) -> None:
        self._status.setText(status)
        if status.startswith("Error"):
            # Reset button state on error
            self._caption_active = False
            self._caption_btn.setText("⏺ Live Caption")
            self._caption_btn.setObjectName("PanelToolButton")
            self._caption_btn.setStyleSheet("")

    # ─── Detach / Dock ─────────────────────────────────────────────────────────────────────────
    def _detach_openai(self) -> None:
        if self._openai_float:
            self._openai_float.raise_()
            return
        self._openai_placeholder = QWidget()
        self._splitter.replaceWidget(0, self._openai_placeholder)
        self._openai_float = _FloatWindow(
            self._openai_panel, "OpenAI GPT Response", self.styleSheet()
        )
        self._openai_float.dock_requested.connect(self._dock_openai)
        self._openai_float.show()

    def _dock_openai(self, _=None) -> None:
        self._splitter.replaceWidget(0, self._openai_panel)
        self._openai_placeholder.deleteLater()
        self._openai_placeholder = None
        win, self._openai_float = self._openai_float, None
        win.hide()
        win.deleteLater()

    def _detach_claude(self) -> None:
        if self._claude_float:
            self._claude_float.raise_()
            return
        self._claude_placeholder = QWidget()
        self._splitter.replaceWidget(1, self._claude_placeholder)
        self._claude_float = _FloatWindow(
            self._claude_panel, "Claude Response", self.styleSheet()
        )
        self._claude_float.dock_requested.connect(self._dock_claude)
        self._claude_float.show()

    def _dock_claude(self, _=None) -> None:
        self._splitter.replaceWidget(1, self._claude_panel)
        self._claude_placeholder.deleteLater()
        self._claude_placeholder = None
        win, self._claude_float = self._claude_float, None
        win.hide()
        win.deleteLater()

    def _detach_prompt(self) -> None:
        if self._prompt_float:
            self._prompt_float.raise_()
            return
        self._prompt_placeholder = QWidget()
        self._prompt_placeholder.setFixedHeight(10)
        idx = self._inner_layout.indexOf(self._prompt_container)
        self._inner_layout.removeWidget(self._prompt_container)
        self._inner_layout.insertWidget(idx, self._prompt_placeholder)
        self._prompt_float = _FloatWindow(
            self._prompt_container, "Question Box", self.styleSheet()
        )
        self._prompt_float.dock_requested.connect(self._dock_prompt)
        self._prompt_float.show()

    def _dock_prompt(self, _=None) -> None:
        idx = self._inner_layout.indexOf(self._prompt_placeholder)
        self._inner_layout.removeWidget(self._prompt_placeholder)
        self._inner_layout.insertWidget(idx, self._prompt_container)
        self._prompt_placeholder.deleteLater()
        self._prompt_placeholder = None
        win, self._prompt_float = self._prompt_float, None
        win.hide()
        win.deleteLater()

    # ---------------------------------------------------------------- shutdown
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        for win in (self._openai_float, self._claude_float, self._prompt_float):
            if win:
                win._docked = True  # suppress dock signal
                win.close()
        self._caption_worker.stop_caption()
        self._caption_worker.wait(3000)
        try:
            self._worker.stop()
        finally:
            self._db.close()
        super().closeEvent(event)
