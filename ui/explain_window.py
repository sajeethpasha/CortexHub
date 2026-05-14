"""Quick Explain / Ask window — one-shot AI streaming response."""
from __future__ import annotations

import asyncio
import html as _html_lib

from PySide6.QtCore import QEvent, QThread, Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from workers.voice_input_worker import VoiceInputWorker
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

_EXPLAIN_SYSTEM = (
    "You are a concise, expert explainer. "
    "Given a passage of text and a question, explain clearly in 1–4 short paragraphs. "
    "Use plain language and concrete examples. "
    "When the topic involves code, include a short illustrative snippet."
)


class _ExplainWorker(QThread):
    chunk_received = Signal(str)
    done = Signal()
    error = Signal(str)

    def __init__(self, prompt: str) -> None:
        super().__init__()
        self._prompt = prompt

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._stream())
        finally:
            loop.close()

    async def _stream(self) -> None:
        try:
            from ai.openai_client import OpenAIClient

            client = OpenAIClient()
            history = [{"role": "user", "content": self._prompt}]
            async for chunk in client.stream(history, system_prompt=_EXPLAIN_SYSTEM):
                self.chunk_received.emit(chunk)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
        finally:
            self.done.emit()


class ExplainWindow(QWidget):
    """Floating window that streams an explanation for selected text."""

    closed = Signal()  # emitted on close so MainWindow can purge from its list

    _BASE_FONT_SIZE = 18
    _MIN_FONT_SIZE = 8
    _MAX_FONT_SIZE = 72

    def __init__(
        self, selected_text: str, initial_query: str, stylesheet: str
    ) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("CortexHub — Quick Explain")
        self.setStyleSheet(stylesheet)
        self.setMinimumSize(500, 380)
        self.resize(760, 560)
        self._selected_text = selected_text
        self._buffer: list[str] = []
        self._font_size = self._BASE_FONT_SIZE
        self._worker: _ExplainWorker | None = None
        self._build_ui(selected_text)
        # Caller is responsible for calling show() + raise_()
        self._submit(initial_query)

    # ---------------------------------------------------------------------- UI
    def _build_ui(self, selected_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── top bar ────────────────────────────────────────────────────────
        bar = QWidget()
        bar.setObjectName("TopBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 0, 12, 0)
        bl.setSpacing(8)
        lbl = QLabel("✦  Quick Explain")
        lbl.setObjectName("ContextLabel")
        bl.addWidget(lbl)
        bl.addStretch(1)
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("StatusLabel")
        bl.addWidget(self._status_lbl)
        zoom_out_btn = QPushButton("A−")
        zoom_out_btn.setObjectName("PanelToolButton")
        zoom_out_btn.setToolTip("Zoom Out  (Ctrl+Scroll↓)")
        zoom_out_btn.setFixedSize(34, 26)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_reset_btn = QPushButton("A\u21ba")
        zoom_reset_btn.setObjectName("PanelToolButton")
        zoom_reset_btn.setToolTip("Reset font size to default")
        zoom_reset_btn.setFixedSize(34, 26)
        zoom_reset_btn.clicked.connect(self._zoom_reset)
        zoom_in_btn = QPushButton("A+")
        zoom_in_btn.setObjectName("PanelToolButton")
        zoom_in_btn.setToolTip("Zoom In  (Ctrl+Scroll\u2191)")
        zoom_in_btn.setFixedSize(34, 26)
        zoom_in_btn.clicked.connect(self._zoom_in)
        bl.addWidget(zoom_out_btn)
        bl.addWidget(zoom_reset_btn)
        bl.addWidget(zoom_in_btn)
        close_btn = QPushButton("✕  Close")
        close_btn.setObjectName("TopBarButtonSecondary")
        close_btn.clicked.connect(self.close)
        bl.addSpacing(4)
        bl.addWidget(close_btn)
        layout.addWidget(bar)

        # ── context strip ──────────────────────────────────────────────────
        ctx_strip = QWidget()
        ctx_strip.setObjectName("PanelTitleBar")
        cs = QHBoxLayout(ctx_strip)
        cs.setContentsMargins(12, 5, 12, 5)
        cs.setSpacing(6)
        preview = selected_text[:180].replace("\n", " ").strip()
        if len(selected_text) > 180:
            preview += "…"
        ctx_lbl = QLabel(
            f'<span style="color:#5a7a9a;font-size:11px">&#8220;</span>'
            f'<span style="font-style:italic;color:#8090a8;font-size:11px">'
            f"{_html_lib.escape(preview)}</span>"
            f'<span style="color:#5a7a9a;font-size:11px">&#8221;</span>'
        )
        ctx_lbl.setTextFormat(Qt.TextFormat.RichText)
        ctx_lbl.setWordWrap(False)
        cs.addWidget(ctx_lbl, 1)
        layout.addWidget(ctx_strip)

        # ── response view ──────────────────────────────────────────────────
        self._view = QTextEdit()
        self._view.setObjectName("ResponseView")
        self._view.setReadOnly(True)
        self._view.setAcceptRichText(True)
        self._view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._apply_font()
        self._view.installEventFilter(self)
        layout.addWidget(self._view, 1)

        # ── query bar ──────────────────────────────────────────────────────
        qbar = QWidget()
        qbar.setObjectName("PromptContainer")
        qbl = QHBoxLayout(qbar)
        qbl.setContentsMargins(10, 6, 10, 6)
        qbl.setSpacing(6)
        self._query_input = QLineEdit()
        self._query_input.setObjectName("ExplainQueryInput")
        self._query_input.setPlaceholderText(
            "Follow-up question… press Enter or click Ask →"
        )
        self._query_input.returnPressed.connect(self._on_ask_clicked)
        self._query_mic_btn = QPushButton("\U0001f3a4\\")
        self._query_mic_btn.setObjectName("PanelToolButton")
        self._query_mic_btn.setToolTip("Voice input into query box  (Ctrl+M)")
        self._query_mic_btn.setFixedSize(38, 26)
        self._query_mic_btn.setStyleSheet(
            "QPushButton{background:#2a0d0d;color:#e05252;"
            "border:1.5px solid #e05252;border-radius:4px;font-size:13px;}"
            "QPushButton:hover{background:#380f0f;}"
        )
        self._query_mic_btn.clicked.connect(self._toggle_query_mic)
        ask_btn = QPushButton("Ask \u2192")
        ask_btn.setObjectName("TopBarButton")
        ask_btn.setFixedWidth(80)
        ask_btn.clicked.connect(self._on_ask_clicked)
        qbl.addWidget(self._query_input, 1)
        qbl.addWidget(self._query_mic_btn)
        qbl.addWidget(ask_btn)
        layout.addWidget(qbar)

        # Voice worker for query bar
        self._query_voice_active = False
        self._query_voice_base = ""
        self._query_voice_worker = VoiceInputWorker(self)
        self._query_voice_worker.text_ready.connect(self._on_query_voice_text)
        self._query_voice_worker.partial_text.connect(self._on_query_voice_partial)
        self._query_voice_worker.status_changed.connect(self._on_query_voice_status)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self._toggle_query_mic)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._query_input.setFocus()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._clear_response()
            event.accept()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------ lifecycle
    def _clear_response(self) -> None:
        self._buffer.clear()
        self._view.clear()
        self._status_lbl.setText("")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._query_voice_active:
            self._query_voice_worker.stop_voice()
            self._query_voice_worker.wait(2000)
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        self.closed.emit()
        event.accept()

    # -------------------------------------------------------------------- zoom
    def _apply_font(self) -> None:
        font = QFont("Segoe UI")
        font.setPointSize(self._font_size)
        self._view.setFont(font)

    def _zoom_in(self) -> None:
        if self._font_size < self._MAX_FONT_SIZE:
            self._font_size += 1
            self._apply_font()
            self._do_render_update()

    def _zoom_out(self) -> None:
        if self._font_size > self._MIN_FONT_SIZE:
            self._font_size -= 1
            self._apply_font()
            self._do_render_update()

    def _zoom_reset(self) -> None:
        self._font_size = self._BASE_FONT_SIZE
        self._apply_font()
        self._do_render_update()

    def _toggle_query_mic(self) -> None:
        if self._query_voice_active:
            self._query_voice_worker.stop_voice()
            self._query_voice_active = False
            self._query_mic_btn.setText("\U0001f3a4\\")
            self._query_mic_btn.setStyleSheet(
                "QPushButton{background:#2a0d0d;color:#e05252;"
                "border:1.5px solid #e05252;border-radius:4px;font-size:13px;}"
                "QPushButton:hover{background:#380f0f;}"
            )
        else:
            self._query_voice_base = self._query_input.text()
            if self._query_voice_base and not self._query_voice_base.endswith(" "):
                self._query_voice_base += " "
            self._query_voice_worker.start_voice()
            self._query_voice_active = True
            self._query_mic_btn.setText("\U0001f3a4")
            self._query_mic_btn.setStyleSheet(
                "QPushButton{background:#0d2240;color:#1f9cf0;"
                "border:1.5px solid #1f9cf0;border-radius:4px;font-size:13px;}"
                "QPushButton:hover{background:#0e2e55;}"
            )

    def _on_query_voice_text(self, text: str) -> None:
        self._query_voice_base += text
        self._query_input.setText(self._query_voice_base.rstrip())

    def _on_query_voice_partial(self, text: str) -> None:
        self._query_input.setText((self._query_voice_base + text).rstrip())

    def _on_query_voice_status(self, status: str) -> None:
        """Reset mic button to OFF state on voice worker error."""
        if status.startswith("Error"):
            self._query_voice_active = False
            self._query_mic_btn.setText("\U0001f3a4\\")
            self._query_mic_btn.setStyleSheet(
                "QPushButton{background:#2a0d0d;color:#e05252;"
                "border:1.5px solid #e05252;border-radius:4px;font-size:13px;}"
                "QPushButton:hover{background:#380f0f;}"
            )

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._view:
            if event.type() == QEvent.Type.Wheel:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if event.angleDelta().y() > 0:
                        self._zoom_in()
                    else:
                        self._zoom_out()
                    return True
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self._clear_response()
                    return True
        return super().eventFilter(obj, event)

    def _do_render_update(self) -> None:
        """Re-render the buffered content at the new font size."""
        if not self._buffer:
            return
        from ui.response_panel import _md_to_html
        raw = "".join(self._buffer)
        sb = self._view.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 40
        self._view.setHtml(self._build_html(_md_to_html(raw)))
        if at_bottom:
            sb.setValue(sb.maximum())

    # ------------------------------------------------------------------ rendering
    def _build_html(self, body: str) -> str:
        return (
            "<div style=\"font-family:'Segoe UI',Arial,sans-serif;"
            f"font-size:{self._font_size}px;line-height:1.75;color:#1a1a2e;padding:6px 4px\">"
            + body
            + "</div>"
        )

    def _submit(self, query: str) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._buffer.clear()
        self._view.setHtml(
            "<p style=\"font-family:'Segoe UI',Arial,sans-serif;"
            "font-size:13px;color:#7a8898;padding:8px\">▶  Thinking…</p>"
        )
        self._status_lbl.setText("● Streaming")
        prompt = f"{query}\n\nContext (selected text):\n{self._selected_text}"
        self._worker = _ExplainWorker(prompt)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_chunk(self, text: str) -> None:
        from ui.response_panel import _md_to_html

        self._buffer.append(text)
        raw = "".join(self._buffer)
        self._view.setHtml(self._build_html(_md_to_html(raw)))
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_done(self) -> None:
        self._status_lbl.setText("")

    def _on_error(self, msg: str) -> None:
        self._status_lbl.setText("")
        self._view.setHtml(
            f'<p style="color:#c0392b;font-family:\'Segoe UI\',Arial,sans-serif;'
            f'font-size:13px;padding:8px">⚠  {_html_lib.escape(msg)}</p>'
        )

    def _on_ask_clicked(self) -> None:
        query = self._query_input.text().strip()
        if query:
            self._submit(query)
            self._query_input.clear()
