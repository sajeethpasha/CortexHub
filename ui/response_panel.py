"""A single AI response panel with rich-text rendering, zoom controls, and README export."""
from __future__ import annotations

import datetime
import html as _html
import pathlib
import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
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
        r'font-family:Consolas,monospace;font-size:12px;color:#333">\1</code>',
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
                    "monospace;font-size:12px;color:#24292e;white-space:pre-wrap;"
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


# ── ResponsePanel ─────────────────────────────────────────────────────────────

class ResponsePanel(QWidget):
    """Title bar + rich-text response view that streams AI output.

    Every panel has Clear, Zoom Out and Zoom In controls.
    When *show_tools* is True, an Export-as-README button is also shown.
    After streaming completes, call ``finalize_render()`` to convert the
    accumulated Markdown buffer to styled HTML.
    """

    detach_requested = Signal()

    _BASE_FONT_SIZE = 13
    _MIN_FONT_SIZE = 8
    _MAX_FONT_SIZE = 32

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
        self._zoom_out_btn.setToolTip("Zoom Out")
        self._zoom_out_btn.setFixedSize(34, 26)
        self._zoom_out_btn.clicked.connect(self._zoom_out)

        self._zoom_in_btn = QPushButton("A+")
        self._zoom_in_btn.setObjectName("PanelToolButton")
        self._zoom_in_btn.setToolTip("Zoom In")
        self._zoom_in_btn.setFixedSize(34, 26)
        self._zoom_in_btn.clicked.connect(self._zoom_in)

        header_layout.addWidget(self._clear_btn)
        header_layout.addSpacing(4)
        header_layout.addWidget(self._zoom_out_btn)
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
        header_layout.addSpacing(4)
        header_layout.addWidget(self._detach_btn)
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

    # ---------------------------------------------------------------- streaming
    def append_chunk(self, text: str) -> None:
        """Buffer chunk and display plain text while streaming."""
        if not text:
            return
        self._raw_buffer.append(text)
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    def finalize_render(self) -> None:
        """Convert buffered Markdown to styled HTML after streaming finishes."""
        raw = "".join(self._raw_buffer)
        if not raw.strip():
            return
        body = _md_to_html(raw)
        full_html = (
            '<div style="font-family:\'Segoe UI\',Arial,sans-serif;'
            f'font-size:{self._font_size}px;line-height:1.65;color:#1a1a2e;padding:2px">'
            + body
            + "</div>"
        )
        self._view.setHtml(full_html)
        # Scroll to top
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._view.setTextCursor(cursor)

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
        self._raw_buffer.clear()
        self._view.clear()

    # --------------------------------------------------------------------- zoom
    def _apply_font(self) -> None:
        font = QFont("Segoe UI")
        font.setPointSize(self._font_size)
        self._view.setFont(font)

    def _zoom_in(self) -> None:
        if self._font_size < self._MAX_FONT_SIZE:
            self._font_size += 1
            self._apply_font()
            # Re-render HTML with updated size if content is already rendered
            self.finalize_render()

    def _zoom_out(self) -> None:
        if self._font_size > self._MIN_FONT_SIZE:
            self._font_size -= 1
            self._apply_font()
            self.finalize_render()

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
