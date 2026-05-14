"""A single AI response panel with rich-text rendering, zoom controls, and README export."""
from __future__ import annotations

import datetime
import html as _html
import pathlib
import re

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QFont, QTextCursor
from workers.voice_input_worker import VoiceInputWorker
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# ── Markdown → HTML helpers ───────────────────────────────────────────────────

def _inline(text: str) -> str:
    """Convert inline markdown to HTML.  Call AFTER html.escape()."""
    # Bold + italic  ***text***
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
    # Bold  **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Italic  *text*  (not ** boundary)
    text = re.sub(r"\*([^*\n]+?)\*", r"<i>\1</i>", text)
    # Bold  __text__
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Italic  _text_
    text = re.sub(r"_([^_\n]+?)_", r"<i>\1</i>", text)
    # Inline code  `text`
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#eef0f4;border-radius:3px;padding:1px 5px;'
        r'font-family:Consolas,monospace;font-size:0.9em;color:#333">\1</code>',
        text,
    )
    return text


def _md_to_html(raw: str) -> str:
    """Convert a full Markdown string to clean HTML for QTextEdit."""
    lines = raw.split("\n")
    out: list[str] = []
    in_ul = False
    in_ol = False
    in_code = False
    code_buf: list[str] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for line in lines:
        stripped = line.strip()

        # ── fenced code block ───────────────────────────────────────
        if stripped.startswith("```"):
            if not in_code:
                in_code = True
                code_buf = []
                close_lists()
            else:
                in_code = False
                escaped = _html.escape("\n".join(code_buf))
                out.append(
                    '<pre style="background:#f6f8fa;border:1px solid #d8dde6;'
                    "border-radius:6px;padding:10px 14px;font-family:Consolas,"
                    "monospace;font-size:14px;color:#24292e;white-space:pre-wrap;"
                    f'margin:6px 0"><code>{escaped}</code></pre>'
                )
            continue

        if in_code:
            code_buf.append(line)
            continue

        # ── detect list type for this line ──────────────────────────
        is_bullet = stripped.startswith("- ") or stripped.startswith("* ")
        is_numbered = bool(re.match(r"^\d+\.\s", stripped))

        if not is_bullet and in_ul:
            out.append("</ul>")
            in_ul = False
        if not is_numbered and in_ol:
            out.append("</ol>")
            in_ol = False

        # ── headings ────────────────────────────────────────────────
        if stripped.startswith("### "):
            close_lists()
            out.append(
                '<p style="font-size:13px;font-weight:700;margin:8px 0 2px;color:#1a1a2e">'
                + _inline(_html.escape(stripped[4:])) + "</p>"
            )
        elif stripped.startswith("## "):
            close_lists()
            out.append(
                '<p style="font-size:15px;font-weight:700;margin:10px 0 3px;color:#1a1a2e;'
                'border-bottom:1px solid #e8eaed;padding-bottom:3px">'
                + _inline(_html.escape(stripped[3:])) + "</p>"
            )
        elif stripped.startswith("# "):
            close_lists()
            out.append(
                '<p style="font-size:17px;font-weight:700;margin:12px 0 4px;color:#1a1a2e">'
                + _inline(_html.escape(stripped[2:])) + "</p>"
            )

        # ── bullet list ─────────────────────────────────────────────
        elif is_bullet:
            if not in_ul:
                out.append('<ul style="margin:4px 0;padding-left:22px;list-style-type:disc">')
                in_ul = True
            out.append(
                '<li style="margin:2px 0;line-height:1.6">'
                + _inline(_html.escape(stripped[2:])) + "</li>"
            )

        # ── numbered list ───────────────────────────────────────────
        elif is_numbered:
            if not in_ol:
                out.append('<ol style="margin:4px 0;padding-left:22px">')
                in_ol = True
            content = re.sub(r"^\d+\.\s+", "", stripped)
            out.append(
                '<li style="margin:2px 0;line-height:1.6">'
                + _inline(_html.escape(content)) + "</li>"
            )

        # ── blockquote ──────────────────────────────────────────────
        elif stripped.startswith("> "):
            close_lists()
            out.append(
                '<div style="border-left:3px solid #aab4c8;margin:5px 0;padding:4px 12px;'
                'color:#555;font-style:italic;background:#f8f9fb;border-radius:0 4px 4px 0">'
                + _inline(_html.escape(stripped[2:])) + "</div>"
            )

        # ── horizontal rule ─────────────────────────────────────────
        elif stripped in ("---", "***", "___"):
            close_lists()
            out.append('<hr style="border:none;border-top:1px solid #e0e4ea;margin:8px 0">')

        # ── empty line ──────────────────────────────────────────────
        elif not stripped:
            close_lists()
            out.append('<div style="margin:5px 0"></div>')

        # ── normal paragraph ────────────────────────────────────────
        else:
            out.append(
                '<p style="margin:2px 0;line-height:1.65;color:#1a1a2e">'
                + _inline(_html.escape(stripped)) + "</p>"
            )

    close_lists()
    return "\n".join(out)


# ── SelectionPopup ────────────────────────────────────────────────────────────

class _SelectionPopup(QWidget):
    """Compact frameless overlay: Explain + custom Ask on selected text."""

    explain_clicked = Signal()
    ask_clicked = Signal(str)

    def __init__(self, stylesheet: str) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet(stylesheet)
        self._build()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(5)

        explain_btn = QPushButton("\u2726 Explain")
        explain_btn.setObjectName("SelectionPopupButton")
        explain_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        explain_btn.setFixedHeight(26)
        explain_btn.clicked.connect(self.explain_clicked.emit)

        self._input = QLineEdit()
        self._input.setObjectName("SelectionPopupInput")
        self._input.setPlaceholderText("Ask about selection\u2026")
        self._input.setFixedHeight(26)
        self._input.setMinimumWidth(170)
        self._input.returnPressed.connect(self._on_ask)

        self._mic_btn = QPushButton("\U0001f3a4")
        self._mic_btn.setObjectName("SelectionPopupButton")
        self._mic_btn.setFixedSize(26, 26)
        self._mic_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._mic_btn.setToolTip("Voice input into the ask box")
        self._mic_btn.clicked.connect(self._toggle_mic)

        ask_btn = QPushButton("Ask \u2192")
        ask_btn.setObjectName("SelectionPopupButton")
        ask_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ask_btn.setFixedHeight(26)
        ask_btn.clicked.connect(self._on_ask)

        layout.addWidget(explain_btn)
        layout.addWidget(self._input)
        layout.addWidget(self._mic_btn)
        layout.addWidget(ask_btn)
        self.adjustSize()

        # Voice worker for this popup
        self._voice_active = False
        self._voice_base_text = ""
        self._voice_worker = VoiceInputWorker(self)
        self._voice_worker.text_ready.connect(self._on_voice_text)
        self._voice_worker.partial_text.connect(self._on_voice_partial)

    def _toggle_mic(self) -> None:
        if self._voice_active:
            self._voice_worker.stop_voice()
            self._voice_active = False
            self._mic_btn.setStyleSheet("")
        else:
            self._voice_base_text = self._input.text()
            if self._voice_base_text and not self._voice_base_text.endswith(" "):
                self._voice_base_text += " "
            self._voice_worker.start_voice()
            self._voice_active = True
            self._mic_btn.setStyleSheet(
                "background:#1a3a1a;color:#4ecb71;"
                "border:2px solid #4ecb71;border-radius:3px;"
            )

    def _on_voice_text(self, text: str) -> None:
        self._voice_base_text += text
        self._input.setText(self._voice_base_text.rstrip())

    def _on_voice_partial(self, text: str) -> None:
        self._input.setText((self._voice_base_text + text).rstrip())

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        if self._voice_active:
            self._voice_worker.stop_voice()
            self._voice_active = False
            self._mic_btn.setStyleSheet("")
            self._voice_base_text = ""

    def _on_ask(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self._voice_base_text = ""
            self.ask_clicked.emit(text)


# ── ResponsePanel ─────────────────────────────────────────────────────────────

class ResponsePanel(QWidget):
    """Title bar + rich-text response view that streams AI output.

    Every panel has Clear, Zoom Out and Zoom In controls.
    When *show_tools* is True, an Export-as-README button is also shown.
    After streaming completes, call ``finalize_render()`` to convert the
    accumulated Markdown buffer to styled HTML.
    """

    detach_requested = Signal()
    fullscreen_requested = Signal()
    explain_requested = Signal(str, str)  # (selected_text, query)

    _BASE_FONT_SIZE = 16
    _MIN_FONT_SIZE = 8
    _MAX_FONT_SIZE = 72

    def __init__(
        self,
        title: str,
        show_tools: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._font_size = self._BASE_FONT_SIZE
        self._title_text = title
        self._raw_buffer: list[str] = []

        # ---- title bar -----------------------------------------------
        self._title_label = QLabel(title)
        self._title_label.setObjectName("PanelTitle")

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 0, 6, 0)
        header_layout.setSpacing(4)
        header_layout.addWidget(self._title_label, 1)

        # Always-present: Clear, A−, A+
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("PanelToolButton")
        self._clear_btn.setToolTip("Clear this response")
        self._clear_btn.setFixedHeight(26)
        self._clear_btn.clicked.connect(self.clear)

        self._zoom_out_btn = QPushButton("A−")
        self._zoom_out_btn.setObjectName("PanelToolButton")
        self._zoom_out_btn.setToolTip("Zoom Out  (Ctrl+Scroll\u2193)")
        self._zoom_out_btn.setFixedSize(34, 26)
        self._zoom_out_btn.clicked.connect(self._zoom_out)

        self._zoom_reset_btn = QPushButton("A\u21ba")
        self._zoom_reset_btn.setObjectName("PanelToolButton")
        self._zoom_reset_btn.setToolTip("Reset font size to default")
        self._zoom_reset_btn.setFixedSize(34, 26)
        self._zoom_reset_btn.clicked.connect(self._zoom_reset)

        self._zoom_in_btn = QPushButton("A+")
        self._zoom_in_btn.setObjectName("PanelToolButton")
        self._zoom_in_btn.setToolTip("Zoom In  (Ctrl+Scroll\u2191)")
        self._zoom_in_btn.setFixedSize(34, 26)
        self._zoom_in_btn.clicked.connect(self._zoom_in)

        header_layout.addWidget(self._clear_btn)
        header_layout.addSpacing(4)
        header_layout.addWidget(self._zoom_out_btn)
        header_layout.addWidget(self._zoom_reset_btn)
        header_layout.addWidget(self._zoom_in_btn)

        if show_tools:
            self._readme_btn = QPushButton("↓ README")
            self._readme_btn.setObjectName("PanelToolButton")
            self._readme_btn.setToolTip("Export response as README.md")
            self._readme_btn.setFixedHeight(26)
            self._readme_btn.clicked.connect(self._export_readme)
            header_layout.addSpacing(4)
            header_layout.addWidget(self._readme_btn)
        self._detach_btn = QPushButton("Detach")
        self._detach_btn.setObjectName("PanelToolButton")
        self._detach_btn.setToolTip("Pop out to a floating window")
        self._detach_btn.setFixedHeight(26)
        self._detach_btn.clicked.connect(self.detach_requested.emit)
        self._fullscreen_panel_btn = QPushButton("\u26f6")
        self._fullscreen_panel_btn.setObjectName("PanelToolButton")
        self._fullscreen_panel_btn.setToolTip("Open fullscreen in floating window")
        self._fullscreen_panel_btn.setFixedSize(34, 26)
        self._fullscreen_panel_btn.clicked.connect(self.fullscreen_requested.emit)
        header_layout.addSpacing(4)
        header_layout.addWidget(self._detach_btn)
        header_layout.addWidget(self._fullscreen_panel_btn)
        header_layout.addSpacing(2)

        header_widget = QWidget()
        header_widget.setObjectName("PanelTitleBar")
        header_widget.setLayout(header_layout)

        # ---- response view (rich text) -------------------------------
        self._view = QTextEdit()
        self._view.setObjectName("ResponseView")
        self._view.setReadOnly(True)
        self._view.setAcceptRichText(True)
        self._view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self._apply_font()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header_widget)
        layout.addWidget(self._view, 1)

        # Debounce timer: renders HTML at most every 100 ms during streaming
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(100)
        self._render_timer.timeout.connect(self._do_render_update)

        # Ctrl+scroll zoom
        self._view.installEventFilter(self)

        # Selection popup for Explain / Ask
        self._current_selection: str = ""
        self._selection_popup: _SelectionPopup | None = None
        self._view.selectionChanged.connect(self._on_selection_changed)

    # ---------------------------------------------------------------- streaming
    def append_chunk(self, text: str) -> None:
        """Buffer chunk and schedule HTML re-render."""
        if not text:
            return
        self._raw_buffer.append(text)
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _do_render_update(self) -> None:
        """Render current buffer as HTML; stay at bottom if already there."""
        raw = "".join(self._raw_buffer)
        if not raw.strip():
            return
        body = _md_to_html(raw)
        full_html = self._build_html(body)
        sb = self._view.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 40
        self._view.setHtml(full_html)
        if at_bottom:
            sb.setValue(sb.maximum())

    def finalize_render(self) -> None:
        """Final render after streaming ends — scroll to top."""
        self._render_timer.stop()
        raw = "".join(self._raw_buffer)
        if not raw.strip():
            return
        body = _md_to_html(raw)
        self._view.setHtml(self._build_html(body))
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._view.setTextCursor(cursor)

    def _build_html(self, body: str) -> str:
        return (
            '<div style="font-family:\'Segoe UI\',Arial,sans-serif;'
            f'font-size:{self._font_size}px;line-height:1.65;color:#1a1a2e;padding:2px">'
            + body + "</div>"
        )

    def append_line(self, text: str) -> None:
        prefix = "\n" if self._view.toPlainText() else ""
        self.append_chunk(prefix + text)

    def show_error(self, message: str) -> None:
        self._view.setHtml(
            f'<p style="color:#c0392b;font-family:Segoe UI,Arial;'
            f'font-size:{self._font_size}px;padding:8px">'
            f'⚠ {_html.escape(message)}</p>'
        )

    def clear(self) -> None:
        self._render_timer.stop()
        self._raw_buffer.clear()
        self._view.clear()

    # ---------------------------------------------------- float mode (detach)
    def enter_float_mode(self, float_win) -> None:
        """Called when panel moves into a slim _FloatWindow — merge into one row."""
        self._detach_btn.setText("\u229f Dock")
        self._detach_btn.setToolTip("Dock back to main window")
        self._detach_btn.clicked.disconnect()
        self._detach_btn.clicked.connect(float_win._request_dock)
        self._fullscreen_panel_btn.clicked.disconnect()
        self._fullscreen_panel_btn.clicked.connect(float_win._toggle_fs)

    def exit_float_mode(self) -> None:
        """Called when panel is docked back — restore original button wiring."""
        self._detach_btn.setText("Detach")
        self._detach_btn.setToolTip("Pop out to a floating window")
        self._detach_btn.clicked.disconnect()
        self._detach_btn.clicked.connect(self.detach_requested.emit)
        self._fullscreen_panel_btn.clicked.disconnect()
        self._fullscreen_panel_btn.clicked.connect(self.fullscreen_requested.emit)

    # -------------------------------------------- selection popup (explain)
    def _on_selection_changed(self) -> None:
        text = (
            self._view.textCursor()
            .selectedText()
            .replace("\u2029", "\n")
            .strip()
        )
        if not text:
            # Use a short delay before hiding so a click inside the popup
            # (which clears the view's selection) doesn't immediately close it.
            QTimer.singleShot(200, self._maybe_hide_popup)
            return
        self._current_selection = text
        if self._selection_popup is None:
            self._selection_popup = _SelectionPopup(self.styleSheet())
            self._selection_popup.explain_clicked.connect(self._on_popup_explain)
            self._selection_popup.ask_clicked.connect(self._on_popup_ask)
        # Position near cursor, clamped to screen
        from PySide6.QtGui import QGuiApplication
        cr = self._view.cursorRect()
        gp = self._view.viewport().mapToGlobal(cr.bottomRight())
        popup_w = self._selection_popup.sizeHint().width()
        screen = QGuiApplication.screenAt(gp)
        if screen:
            sr = screen.availableGeometry()
            x = min(gp.x(), sr.right() - popup_w - 10)
            y = min(gp.y() + 4, sr.bottom() - 50)
            self._selection_popup.move(x, y)
        else:
            self._selection_popup.move(gp.x(), gp.y() + 4)
        self._selection_popup.show()
        self._selection_popup.raise_()

    def _maybe_hide_popup(self) -> None:
        """Hide the popup unless the user is currently interacting with it."""
        if self._selection_popup is None or not self._selection_popup.isVisible():
            return
        from PySide6.QtWidgets import QApplication
        fw = QApplication.focusWidget()
        # Keep visible if focus is inside the popup (user is typing in the input)
        if fw is not None and (
            fw is self._selection_popup or self._selection_popup.isAncestorOf(fw)
        ):
            return
        self._selection_popup.hide()

    def _on_popup_explain(self) -> None:
        if self._current_selection:
            self.explain_requested.emit(
                self._current_selection, "Explain this in detail:"
            )
        if self._selection_popup:
            self._selection_popup.hide()

    def _on_popup_ask(self, query: str) -> None:
        if self._current_selection and query:
            self.explain_requested.emit(self._current_selection, query)
        if self._selection_popup:
            self._selection_popup.hide()

    # --------------------------------------------------------------------- zoom
    def _apply_font(self) -> None:
        font = QFont("Segoe UI")
        font.setPointSize(self._font_size)
        self._view.setFont(font)

    def _zoom_in(self) -> None:
        if self._font_size < self._MAX_FONT_SIZE:
            self._font_size += 2
            self._apply_font()
            self._do_render_update()

    def _zoom_out(self) -> None:
        if self._font_size > self._MIN_FONT_SIZE:
            self._font_size -= 2
            self._apply_font()
            self._do_render_update()

    def _zoom_reset(self) -> None:
        self._font_size = self._BASE_FONT_SIZE
        self._apply_font()
        self._do_render_update()

    # ---------------------------------------------------------- Ctrl+scroll zoom
    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if obj is self._view and event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if event.angleDelta().y() > 0:
                    self._zoom_in()
                else:
                    self._zoom_out()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------ README export
    def _export_readme(self) -> None:
        content = "".join(self._raw_buffer).strip()
        if not content:
            QMessageBox.information(self, "Export README", "Nothing to export yet.")
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save as README", f"README_{timestamp}.md",
            "Markdown Files (*.md);;All Files (*)",
        )
        if not path:
            return
        ts_label = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        readme_text = f"# CortexHub — OpenAI GPT Response\n\n*Generated on {ts_label}*\n\n---\n\n{content}\n"
        pathlib.Path(path).write_text(readme_text, encoding="utf-8")
        QMessageBox.information(self, "Exported", f"Saved to:\n{path}")
