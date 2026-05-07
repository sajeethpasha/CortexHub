"""A single AI response panel with title and auto-scrolling streaming view."""
from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class ResponsePanel(QWidget):
    """Title bar + read-only text area that streams AI output line by line."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("PanelTitle")

        self._view = QPlainTextEdit()
        self._view.setObjectName("ResponseView")
        self._view.setReadOnly(True)
        self._view.setUndoRedoEnabled(False)
        self._view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._title_label)
        layout.addWidget(self._view, 1)

    # ---------------------------------------------------------------- streaming
    def append_chunk(self, text: str) -> None:
        """Append a streamed chunk and keep the view auto-scrolled."""
        if not text:
            return
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self._view.setTextCursor(cursor)
        self._view.ensureCursorVisible()

    def append_line(self, text: str) -> None:
        self.append_chunk(("\n" if self._view.toPlainText() else "") + text)

    def show_error(self, message: str) -> None:
        self.append_line(f"[Error] {message}")

    def clear(self) -> None:
        self._view.clear()
