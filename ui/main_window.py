"""CORTEXHUB main window."""
from __future__ import annotations

import base64
import logging
import os

from PySide6.QtCore import QBuffer, Qt, QPoint, QThread, Signal, QTimer
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QApplication,
    QLineEdit,
)

log = logging.getLogger(__name__)


class _PromptTextEdit(QTextEdit):
    """QTextEdit that intercepts clipboard-pasted images and emits a signal."""

    image_pasted = Signal(str, str)  # media_type, base64_data

    def insertFromMimeData(self, source) -> None:  # noqa: N802
        if source.hasImage():
            qimage: QImage = source.imageData()
            buf = QBuffer()
            buf.open(QBuffer.OpenModeFlag.ReadWrite)
            qimage.save(buf, "PNG")
            b64 = base64.b64encode(bytes(buf.data())).decode()
            buf.close()
            self.image_pasted.emit("image/png", b64)
            return
        super().insertFromMimeData(source)


class _ResponseSplitter(QSplitter):
    """Thin divider splitter between the two response panels."""
    pass


class _FloatWindow(QWidget):
    """Standalone floating window for a detached panel. Docks back on request or close."""

    dock_requested = Signal(object)

    def __init__(
        self,
        content: QWidget,
        title: str,
        stylesheet: str,
        extra_bar_widgets: list | None = None,
        slim: bool = False,
    ) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle(f"CORTEXHUB  —  {title}")
        self.setStyleSheet(stylesheet)
        self.resize(800, 560)
        self._content = content
        self._docked = False
        self._fs_btn = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if not slim:
            lbl = QLabel(title)
            lbl.setObjectName("ContextLabel")

            self._fs_btn = QPushButton("⛶  Fullscreen")
            self._fs_btn.setObjectName("TopBarButtonSecondary")
            self._fs_btn.clicked.connect(self._toggle_fs)

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
            if extra_bar_widgets:
                for w in extra_bar_widgets:
                    bl.addWidget(w)
                bl.addSpacing(6)
            bl.addWidget(self._fs_btn)
            bl.addWidget(dock_btn)
            outer.addWidget(bar)

        outer.addWidget(content, 1)

    def _toggle_fs(self) -> None:
        if self.isFullScreen() or self.isMaximized():
            self.showNormal()
            if self._fs_btn:
                self._fs_btn.setText("⛶  Fullscreen")
        else:
            self.showFullScreen()
            if self._fs_btn:
                self._fs_btn.setText("⊞  Restore")

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
from workers.voice_input_worker import VoiceInputWorker


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
        self._worker.setPriority(QThread.Priority.HighPriority)

        # ---- ui -----------------------------------------------------------
        self._busy_models: set[str] = set()
        self._openai_float: _FloatWindow | None = None
        self._openai_placeholder: QWidget | None = None
        self._claude_float: _FloatWindow | None = None
        self._claude_placeholder: QWidget | None = None
        self._prompt_float: _FloatWindow | None = None
        self._prompt_placeholder: QWidget | None = None
        self._explain_windows: list = []  # keep refs so GC won't destroy running threads
        self._caption_active = False
        self._caption_worker = CaptionWorker(self)
        self._caption_worker.text_ready.connect(self._on_caption_text)
        self._caption_worker.partial_text.connect(self._on_partial_caption)
        self._caption_worker.status_changed.connect(self._on_caption_status)
        self._caption_partial_anchor = -1

        self._voice_active = False
        self._voice_worker = VoiceInputWorker(self)
        self._voice_worker.text_ready.connect(self._on_voice_text)
        self._voice_worker.partial_text.connect(self._on_voice_partial)
        self._voice_worker.status_changed.connect(self._on_voice_status)
        self._voice_partial_anchor = -1
        self._pending_images: list[dict] = []  # {"media_type", "data", "widget"}
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

        self._redock_btn = QPushButton("\u21ba  Redock All")
        self._redock_btn.setObjectName("TopBarButtonSecondary")
        self._redock_btn.setToolTip("Dock all floating panels back to main window")
        self._redock_btn.clicked.connect(self._redock_all)

        self._fullscreen_btn = QPushButton("Fullscreen")
        self._fullscreen_btn.setObjectName("TopBarButtonSecondary")
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        self._shortcuts_popup = None
        self._shortcuts_btn = QPushButton("\u2328")
        self._shortcuts_btn.setObjectName("ShortcutsBtn")
        self._shortcuts_btn.setToolTip("Keyboard shortcuts reference  (F1)")
        self._shortcuts_btn.setFixedSize(32, 28)
        self._shortcuts_btn.clicked.connect(self._show_shortcuts_panel)

        self._session_badge = QLabel("○  No Profile")
        self._session_badge.setObjectName("SessionBadge")

        self._configure_btn = QPushButton("⚙  Configure")
        self._configure_btn.setObjectName("ConfigureButton")
        self._configure_btn.setToolTip("Set up your resume and tech stack for interview mode")
        self._configure_btn.clicked.connect(self._on_configure_clicked)

        self._new_session_btn = QPushButton("↺  New Session")
        self._new_session_btn.setObjectName("NewSessionButton")
        self._new_session_btn.setToolTip("Clear conversation history and start a fresh session")
        self._new_session_btn.clicked.connect(self._on_new_session_clicked)

        top_bar = QWidget()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 0, 14, 0)
        top_layout.setSpacing(8)
        top_layout.addWidget(self._shortcuts_btn)
        top_layout.addSpacing(6)
        top_layout.addWidget(context_label)
        top_layout.addSpacing(10)
        top_layout.addWidget(self._session_badge)
        top_layout.addStretch(1)
        top_layout.addWidget(self._configure_btn)
        top_layout.addWidget(self._new_session_btn)
        top_layout.addSpacing(6)
        top_layout.addWidget(self._status)
        top_layout.addSpacing(12)
        top_layout.addWidget(self._send_btn)
        top_layout.addWidget(self._clear_btn)
        top_layout.addWidget(self._redock_btn)
        top_layout.addWidget(self._fullscreen_btn)

        # ---- prompt input ------------------------------------------------
        self._prompt = _PromptTextEdit()
        self._prompt.setObjectName("PromptInput")
        self._prompt.setPlaceholderText(
            "Ask anything…   (Ctrl+Enter to send  |  📎 paste or attach images)"
        )
        self._prompt.setFixedHeight(116)
        self._prompt.image_pasted.connect(self._add_image)

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

        self._mic_btn = QPushButton("🎤\\")
        self._mic_btn.setObjectName("PanelToolButton")
        self._mic_btn.setToolTip(
            "Start / stop voice input from your microphone into the question box  (Ctrl+M)"
        )
        self._mic_btn.setFixedSize(38, 26)
        self._mic_btn.setStyleSheet(
            "QPushButton{background:#2a0d0d;color:#e05252;"
            "border:1.5px solid #e05252;border-radius:5px;}"
            "QPushButton:hover{background:#380f0f;}"
        )
        self._mic_btn.clicked.connect(self._toggle_voice_input)
        ph_layout.addWidget(self._mic_btn)

        self._attach_btn = QPushButton("📎")
        self._attach_btn.setObjectName("PanelToolButton")
        self._attach_btn.setToolTip(
            "Attach images (PNG, JPG, GIF, WEBP) — you can also paste images with Ctrl+V"
        )
        self._attach_btn.setFixedSize(34, 26)
        self._attach_btn.clicked.connect(self._on_attach_image)
        ph_layout.addWidget(self._attach_btn)

        # ---- image preview strip (hidden when empty) --------------------
        self._image_strip_inner = QWidget()
        self._image_strip_inner.setObjectName("ImageStripInner")
        self._image_strip_layout = QHBoxLayout(self._image_strip_inner)
        self._image_strip_layout.setContentsMargins(6, 4, 6, 4)
        self._image_strip_layout.setSpacing(6)
        self._image_strip_layout.addStretch(1)

        self._image_strip = QScrollArea()
        self._image_strip.setObjectName("ImageStrip")
        self._image_strip.setWidget(self._image_strip_inner)
        self._image_strip.setWidgetResizable(True)
        self._image_strip.setFixedHeight(88)
        self._image_strip.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._image_strip.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._image_strip.setVisible(False)

        self._prompt_container = QWidget()
        self._prompt_container.setObjectName("PromptContainer")
        prompt_inner = QVBoxLayout(self._prompt_container)
        prompt_inner.setContentsMargins(0, 0, 0, 0)
        prompt_inner.setSpacing(0)
        prompt_inner.addWidget(prompt_hdr)
        prompt_inner.addWidget(self._image_strip)
        prompt_inner.addWidget(self._prompt)

        # ---- response panels in a horizontal splitter --------------------
        self._openai_panel = ResponsePanel("OpenAI GPT Response", show_tools=True)
        self._claude_panel = ResponsePanel("Claude Response", show_tools=True)
        self._openai_panel.detach_requested.connect(self._detach_openai)
        self._openai_panel.fullscreen_requested.connect(self._fullscreen_openai)
        self._openai_panel.explain_requested.connect(self._on_explain_requested)
        self._claude_panel.detach_requested.connect(self._detach_claude)
        self._claude_panel.fullscreen_requested.connect(self._fullscreen_claude)
        self._claude_panel.explain_requested.connect(self._on_explain_requested)

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
        self._inner_layout.setContentsMargins(12, 8, 12, 8)
        self._inner_layout.setSpacing(6)
        self._inner_layout.addWidget(self._prompt_container)
        self._inner_layout.addWidget(self._splitter, 1)

        layout.addWidget(inner, 1)
        self.setCentralWidget(central)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_send_clicked)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_send_clicked)
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self._toggle_voice_input)
        QShortcut(QKeySequence("F1"), self, activated=self._show_shortcuts_panel)

        # Zoom shortcuts (Ctrl + + / Ctrl + -)
        # Register both Ctrl++ and the common Ctrl+= mapping for keyboards where + is Shift+=
        QShortcut(QKeySequence("Ctrl++"), self, activated=self._zoom_in_all)
        QShortcut(QKeySequence("Ctrl+="), self, activated=self._zoom_in_all)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self._zoom_out_all)

        # Line-spacing prefix mode: press `L` then `+` or `-` within 1.5s
        self._line_prefix_active = False
        self._line_prefix_timer = QTimer(self)
        self._line_prefix_timer.setSingleShot(True)
        self._line_prefix_timer.setInterval(1500)
        self._line_prefix_timer.timeout.connect(self._clear_line_prefix)

        sc_L = QShortcut(QKeySequence("L"), self)
        sc_L.setContext(Qt.ApplicationShortcut)
        sc_L.activated.connect(self._activate_line_prefix)

        sc_plus = QShortcut(QKeySequence(Qt.Key_Plus), self)
        sc_plus.setContext(Qt.ApplicationShortcut)
        sc_plus.activated.connect(lambda: self._handle_prefix_plus_minus(True))

        sc_minus = QShortcut(QKeySequence(Qt.Key_Minus), self)
        sc_minus.setContext(Qt.ApplicationShortcut)
        sc_minus.activated.connect(lambda: self._handle_prefix_plus_minus(False))

    # ---------------------------------------------------------------- custom shortcuts handlers
    def _zoom_in_all(self) -> None:
        """Zoom in both response panels."""
        for p in (getattr(self, "_openai_panel", None), getattr(self, "_claude_panel", None)):
            if p is None:
                continue
            try:
                if hasattr(p, "zoom_in"):
                    p.zoom_in()
                else:
                    p._zoom_in()
            except Exception:
                pass

    def _zoom_out_all(self) -> None:
        """Zoom out both response panels."""
        for p in (getattr(self, "_openai_panel", None), getattr(self, "_claude_panel", None)):
            if p is None:
                continue
            try:
                if hasattr(p, "zoom_out"):
                    p.zoom_out()
                else:
                    p._zoom_out()
            except Exception:
                pass

    def _activate_line_prefix(self) -> None:
        """Activate the `L` prefix for a short window to accept + or - for line spacing.

        Ignore when focus is inside text-editing widgets so typing isn't interrupted.
        """
        fw = QApplication.focusWidget()
        if isinstance(fw, (QTextEdit, QLineEdit)):
            return
        self._line_prefix_active = True
        self._line_prefix_timer.start()
        try:
            self._status.setText("● Line spacing: waiting for + or -")
        except Exception:
            pass

    def _clear_line_prefix(self) -> None:
        self._line_prefix_active = False
        try:
            self._status.setText("● Ready")
        except Exception:
            pass

    def _handle_prefix_plus_minus(self, plus: bool) -> None:
        """Handle + or - pressed while L-prefix is active: adjust line spacing."""
        if not getattr(self, "_line_prefix_active", False):
            return
        for p in (getattr(self, "_openai_panel", None), getattr(self, "_claude_panel", None)):
            if p is None:
                continue
            try:
                if plus:
                    p.increase_line_spacing()
                else:
                    p.decrease_line_spacing()
            except Exception:
                pass
        self._clear_line_prefix()

    # ----------------------------------------------------------------- shortcuts panel
    def _show_shortcuts_panel(self) -> None:
        """Toggle the floating keyboard shortcuts reference panel."""
        if self._shortcuts_popup and self._shortcuts_popup.isVisible():
            self._shortcuts_popup.hide()
            return
        if not self._shortcuts_popup:
            self._shortcuts_popup = self._build_shortcuts_popup()
        # Position popup below and left-aligned to the button
        pos = self._shortcuts_btn.mapToGlobal(
            QPoint(0, self._shortcuts_btn.height() + 6)
        )
        self._shortcuts_popup.move(pos)
        self._shortcuts_popup.show()
        self._shortcuts_popup.raise_()

    def _build_shortcuts_popup(self) -> QFrame:
        """Build the shortcuts reference panel (created once, cached on self)."""
        popup = QFrame(self, Qt.WindowType.Popup)
        popup.setObjectName("ShortcutsPanelFrame")
        popup.setFixedWidth(360)

        outer = QVBoxLayout(popup)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(0)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_icon = QLabel("\u2328")
        title_icon.setObjectName("ShortcutsPanelIcon")
        title_lbl = QLabel("Keyboard Shortcuts")
        title_lbl.setObjectName("ShortcutsPanelTitle")
        title_row.addWidget(title_icon)
        title_row.addWidget(title_lbl, 1)
        outer.addLayout(title_row)
        outer.addSpacing(10)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("ShortcutsPanelDivider")
        outer.addWidget(divider)
        outer.addSpacing(12)

        _categories = [
            ("Core Actions", [
                ("Ctrl+Enter",  "Send question to AI"),
                ("Ctrl+M",      "Toggle microphone on / off"),
                ("F11",         "Toggle fullscreen"),
                ("F1",          "Show this shortcuts panel"),
            ]),
            ("Text Editing", [
                ("Ctrl+Z",      "Undo"),
                ("Ctrl+Y",      "Redo"),
                ("Ctrl+A",      "Select all"),
                ("Ctrl+C",      "Copy"),
                ("Ctrl+V",      "Paste"),
                ("Ctrl+X",      "Cut"),
            ]),
            ("Panels & View", [
                ("Ctrl+Scroll", "Zoom response text"),
                ("Ctrl++ / Ctrl+-", "Zoom response text"),
                ("L + / L -", "Adjust line spacing"),
                ("Esc",         "Close popups / dismiss"),
            ]),
        ]

        for cat_name, shortcuts in _categories:
            cat_lbl = QLabel(cat_name.upper())
            cat_lbl.setObjectName("ShortcutsCategoryLabel")
            outer.addWidget(cat_lbl)
            outer.addSpacing(6)

            for key, desc in shortcuts:
                row = QHBoxLayout()
                row.setContentsMargins(0, 1, 0, 1)
                row.setSpacing(0)

                key_badge = QLabel(key)
                key_badge.setObjectName("ShortcutsKeyBadge")
                key_badge.setFixedWidth(108)
                key_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

                arr = QLabel("\u2192")
                arr.setObjectName("ShortcutsArrow")

                desc_lbl = QLabel(desc)
                desc_lbl.setObjectName("ShortcutsDesc")

                row.addWidget(key_badge)
                row.addSpacing(10)
                row.addWidget(arr)
                row.addSpacing(8)
                row.addWidget(desc_lbl, 1)
                outer.addLayout(row)
                outer.addSpacing(3)

            outer.addSpacing(10)

        return popup

    # ----------------------------------------------------------------- actions
    def _on_send_clicked(self) -> None:
        prompt = self._prompt.toPlainText().strip()
        images = [(e["media_type"], e["data"]) for e in self._pending_images]
        if (not prompt and not images) or self._busy_models:
            return

        # Clear visible panels for the new question (history is kept in DB).
        self._openai_panel.clear()
        self._claude_panel.clear()

        self._busy_models = {MODEL_OPENAI, MODEL_CLAUDE}
        self._send_btn.setEnabled(False)

        self._status.setText("● Streaming…")

        self._worker.submit(prompt, images)
        self._clear_images()
        # Keep the question visible — do not clear the prompt

    def _on_clear_clicked(self) -> None:
        self._openai_panel.clear()
        self._claude_panel.clear()

    def _clear_prompt(self) -> None:
        """Clear prompt AND both response panels, unlock for new input."""
        self._prompt.clear()
        self._clear_images()
        self._caption_partial_anchor = -1
        self._openai_panel.clear()
        self._claude_panel.clear()
        self._send_btn.setEnabled(True)
        self._status.setText("● Ready")


    def _on_attach_image(self) -> None:
        """Open file dialog and add selected images to the pending list."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Attach Images", "",
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"
        )
        for path in paths:
            result = self._load_image_from_path(path)
            if result:
                self._add_image(*result)

    def _load_image_from_path(self, path: str) -> tuple[str, str] | None:
        """Load any image file, normalise to PNG, return (media_type, base64)."""
        qimage = QImage(path)
        if qimage.isNull():
            log.warning("Could not load image: %s", path)
            return None
        # Resize if larger than 1568px (Claude/OpenAI recommendation)
        if qimage.width() > 1568 or qimage.height() > 1568:
            qimage = qimage.scaled(
                1568, 1568,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.ReadWrite)
        qimage.save(buf, "PNG")
        b64 = base64.b64encode(bytes(buf.data())).decode()
        buf.close()
        return "image/png", b64

    def _add_image(self, media_type: str, b64_data: str) -> None:
        """Add an image to the pending list and render its thumbnail in the strip."""
        # Build thumbnail pixmap
        img_bytes = base64.b64decode(b64_data)
        pixmap = QPixmap()
        pixmap.loadFromData(img_bytes)
        thumb = pixmap.scaled(
            64, 64,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Build thumbnail cell
        cell = QFrame()
        cell.setObjectName("ImageThumbFrame")
        cell.setFixedSize(76, 76)

        thumb_lbl = QLabel()
        thumb_lbl.setPixmap(thumb)
        thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb_lbl.setObjectName("ImageThumbLabel")

        del_btn = QPushButton("✕")
        del_btn.setObjectName("ImageDeleteBtn")
        del_btn.setFixedSize(18, 18)

        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(3, 3, 3, 3)
        cell_layout.setSpacing(2)
        cell_layout.addWidget(thumb_lbl, 1, Qt.AlignmentFlag.AlignCenter)
        cell_layout.addWidget(del_btn, 0, Qt.AlignmentFlag.AlignRight)

        entry: dict = {"media_type": media_type, "data": b64_data, "widget": cell}
        del_btn.clicked.connect(lambda _checked, e=entry: self._remove_image(e))

        # Insert before the trailing stretch (last item)
        insert_pos = self._image_strip_layout.count() - 1
        self._image_strip_layout.insertWidget(insert_pos, cell)

        self._pending_images.append(entry)
        self._image_strip.setVisible(True)
        self._update_attach_btn_label()

    def _remove_image(self, entry: dict) -> None:
        """Remove one image thumbnail and its data entry."""
        if entry in self._pending_images:
            self._pending_images.remove(entry)
        widget = entry.get("widget")
        if widget:
            self._image_strip_layout.removeWidget(widget)
            widget.deleteLater()
        if not self._pending_images:
            self._image_strip.setVisible(False)
        self._update_attach_btn_label()

    def _clear_images(self) -> None:
        """Remove all pending images and hide the strip."""
        for entry in list(self._pending_images):
            widget = entry.get("widget")
            if widget:
                self._image_strip_layout.removeWidget(widget)
                widget.deleteLater()
        self._pending_images.clear()
        self._image_strip.setVisible(False)
        self._update_attach_btn_label()

    def _update_attach_btn_label(self) -> None:
        n = len(self._pending_images)
        self._attach_btn.setText(f"📎 {n}" if n else "📎")

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
        self._send_btn.setEnabled(True)
        self._status.setText("● Done")

    # ── Configure / Session ──────────────────────────────────────────────────────────
    def _on_configure_clicked(self) -> None:
        from ui.config_panel import ConfigDialog
        dlg = ConfigDialog(self._session.interview_config, parent=self)
        dlg.setStyleSheet(self.styleSheet())
        dlg.session_started.connect(self._start_session_with_config)
        dlg.config_updated.connect(self._apply_config)
        dlg.exec()

    def _start_session_with_config(self, config: dict) -> None:
        self._session.set_config(config)
        self._session.new_session(keep_config=True)
        self._openai_panel.clear()
        self._claude_panel.clear()
        self._clear_prompt()
        self._update_session_badge()
        self._status.setText("● New session started")

    def _apply_config(self, config: dict) -> None:
        self._session.set_config(config)
        self._update_session_badge()
        self._status.setText("● Profile updated")

    def _on_new_session_clicked(self) -> None:
        self._session.new_session(keep_config=True)
        self._openai_panel.clear()
        self._claude_panel.clear()
        self._clear_prompt()
        self._update_session_badge()
        self._status.setText("● New session started")

    def _update_session_badge(self) -> None:
        if self._session.has_context:
            self._session_badge.setText("● Profile Active")
            self._session_badge.setObjectName("SessionBadgeActive")
        else:
            self._session_badge.setText("○  No Profile")
            self._session_badge.setObjectName("SessionBadge")
        self._session_badge.style().unpolish(self._session_badge)
        self._session_badge.style().polish(self._session_badge)

    # ─── Detach / Dock ─────────────────────────────────────────────────────────────────────────
    def _detach_openai(self) -> None:
        if self._openai_float:
            self._openai_float.raise_()
            return
        self._openai_placeholder = QWidget()
        self._splitter.replaceWidget(0, self._openai_placeholder)
        self._openai_float = _FloatWindow(
            self._openai_panel, "OpenAI GPT Response", self.styleSheet(), slim=True
        )
        self._openai_panel.enter_float_mode(self._openai_float)
        self._openai_float.dock_requested.connect(self._dock_openai)
        self._openai_float.show()

    def _dock_openai(self, _=None) -> None:
        self._openai_panel.exit_float_mode()
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
            self._claude_panel, "Claude Response", self.styleSheet(), slim=True
        )
        self._claude_panel.enter_float_mode(self._claude_float)
        self._claude_float.dock_requested.connect(self._dock_claude)
        self._claude_float.show()

    def _dock_claude(self, _=None) -> None:
        self._claude_panel.exit_float_mode()
        self._splitter.replaceWidget(1, self._claude_panel)
        self._claude_placeholder.deleteLater()
        self._claude_placeholder = None
        win, self._claude_float = self._claude_float, None
        win.hide()
        win.deleteLater()

    def _fullscreen_openai(self) -> None:
        self._detach_openai()
        if self._openai_float:
            self._openai_float.showFullScreen()

    def _fullscreen_claude(self) -> None:
        self._detach_claude()
        if self._claude_float:
            self._claude_float.showFullScreen()

    def _redock_all(self) -> None:
        """Dock all floating panels back into the main window."""
        if self._openai_float:
            self._dock_openai()
        if self._claude_float:
            self._dock_claude()
        if self._prompt_float:
            self._dock_prompt()

    def _on_explain_requested(self, selected_text: str, query: str) -> None:
        from ui.explain_window import ExplainWindow
        win = ExplainWindow(selected_text, query, self.styleSheet())
        self._explain_windows.append(win)
        win.closed.connect(lambda w=win: self._explain_windows.remove(w) if w in self._explain_windows else None)
        win.show()
        win.raise_()

    def _detach_prompt(self) -> None:
        if self._prompt_float:
            self._prompt_float.raise_()
            return
        # Allow the text area to expand freely in the float window
        self._prompt.setMinimumHeight(60)
        self._prompt.setMaximumHeight(16_777_215)
        self._prompt_placeholder = QWidget()
        self._prompt_placeholder.setFixedHeight(10)
        idx = self._inner_layout.indexOf(self._prompt_container)
        self._inner_layout.removeWidget(self._prompt_container)
        self._inner_layout.insertWidget(idx, self._prompt_placeholder)

        # Toolbar buttons for the float window
        _send = QPushButton("Send")
        _send.setObjectName("TopBarButton")
        _send.clicked.connect(self._on_send_clicked)

        _clr_q = QPushButton("Clear Q")
        _clr_q.setObjectName("TopBarButtonSecondary")
        _clr_q.setToolTip("Clear question text only")
        _clr_q.clicked.connect(self._prompt.clear)

        _clr_all = QPushButton("Clear All")
        _clr_all.setObjectName("TopBarButtonSecondary")
        _clr_all.setToolTip("Clear question and both responses")
        _clr_all.clicked.connect(self._clear_prompt)

        self._prompt_float = _FloatWindow(
            self._prompt_container, "Question Box", self.styleSheet(),
            extra_bar_widgets=[_send, _clr_q, _clr_all],
        )
        self._prompt_float.resize(960, 560)
        self._prompt_float.dock_requested.connect(self._dock_prompt)
        # Ctrl+Enter submits from the float window
        QShortcut(QKeySequence("Ctrl+Return"), self._prompt_float,
                  activated=self._on_send_clicked)
        QShortcut(QKeySequence("Ctrl+Enter"), self._prompt_float,
                  activated=self._on_send_clicked)
        self._prompt_float.show()

    def _dock_prompt(self, _=None) -> None:
        self._prompt.setFixedHeight(116)
        idx = self._inner_layout.indexOf(self._prompt_placeholder)
        self._inner_layout.removeWidget(self._prompt_placeholder)
        self._inner_layout.insertWidget(idx, self._prompt_container)
        self._prompt_placeholder.deleteLater()
        self._prompt_placeholder = None
        win, self._prompt_float = self._prompt_float, None
        win.hide()
        win.deleteLater()

    def _toggle_live_caption(self) -> None:
        if self._caption_active:
            self._caption_worker.stop_caption()
            self._caption_active = False
            self._caption_btn.setText("⏺ Live Caption")
            self._caption_btn.setObjectName("PanelToolButton")
            self._caption_btn.setStyleSheet("")
            self._caption_partial_anchor = -1
        else:
            self._caption_worker.start_caption()
            self._caption_active = True
            self._caption_btn.setText("⏸ Stop Caption")
            self._caption_btn.setObjectName("CaptionButtonActive")
            self._caption_btn.setStyleSheet(
                "QPushButton{background:#1a3a1a;color:#4ecb71;"
                "border:1px solid #2a6a2a;border-radius:5px;}"
                "QPushButton:hover{background:#204a20;}"
            )
            self._caption_partial_anchor = -1

    def _toggle_voice_input(self) -> None:
        if self._voice_active:
            self._voice_worker.stop_voice()
            self._voice_active = False
            self._mic_btn.setText("🎤\\")
            self._mic_btn.setStyleSheet(
                "QPushButton{background:#2a0d0d;color:#e05252;"
                "border:1.5px solid #e05252;border-radius:5px;}"
                "QPushButton:hover{background:#380f0f;}"
            )
            self._voice_partial_anchor = -1
        else:
            self._voice_worker.start_voice()
            self._voice_active = True
            self._mic_btn.setText("🎤")
            # Blue border when recording
            self._mic_btn.setStyleSheet(
                "QPushButton{background:#0d2240;color:#1f9cf0;"
                "border:1.5px solid #1f9cf0;border-radius:5px;}"
                "QPushButton:hover{background:#0e2e55;}"
            )
            self._voice_partial_anchor = -1

    def _on_caption_text(self, text: str) -> None:
        """Commit final recognised sentence; replace any in-progress partial."""
        cursor = self._prompt.textCursor()
        if self._caption_partial_anchor >= 0:
            cursor.setPosition(self._caption_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + " ")
        self._prompt.setTextCursor(cursor)
        self._caption_partial_anchor = -1

    def _on_partial_caption(self, text: str) -> None:
        """Replace the current in-progress partial with the latest Vosk partial."""
        if not text:
            return
        cursor = self._prompt.textCursor()
        if self._caption_partial_anchor < 0:
            # First partial — record anchor at current end
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._caption_partial_anchor = cursor.position()
        else:
            # Remove previous partial text back to anchor
            cursor.setPosition(self._caption_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        cursor.insertText(text)
        self._prompt.setTextCursor(cursor)

    def _on_caption_status(self, status: str) -> None:
        """Update status label with caption worker status."""
        self._status.setText(f"● {status}")
        if status.startswith("Error"):
            self._caption_active = False
            self._caption_btn.setText("⏺ Live Caption")
            self._caption_btn.setObjectName("PanelToolButton")
            self._caption_btn.setStyleSheet("")

    # -------------------------------------------------------- voice input events
    def _on_voice_text(self, text: str) -> None:
        """Commit final voice sentence; replace any in-progress partial."""
        cursor = self._prompt.textCursor()
        if self._voice_partial_anchor >= 0:
            cursor.setPosition(self._voice_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + " ")
        self._prompt.setTextCursor(cursor)
        self._voice_partial_anchor = -1

    def _on_voice_partial(self, text: str) -> None:
        """Show live partial voice transcription in the prompt box."""
        if not text:
            return
        cursor = self._prompt.textCursor()
        if self._voice_partial_anchor < 0:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._voice_partial_anchor = cursor.position()
        else:
            cursor.setPosition(self._voice_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        cursor.insertText(text)
        self._prompt.setTextCursor(cursor)

    def _on_voice_status(self, status: str) -> None:
        """Update status label; reset mic button on error."""
        self._status.setText(f"● {status}")
        if status.startswith("Error"):
            self._voice_active = False
            self._mic_btn.setText("🎤\\")
            self._mic_btn.setStyleSheet(
                "QPushButton{background:#2a0d0d;color:#e05252;"
                "border:1.5px solid #e05252;border-radius:5px;}"
                "QPushButton:hover{background:#380f0f;}"
            )
            self._voice_partial_anchor = -1

    # ---------------------------------------------------------------- shutdown
    def closeEvent(self, event) -> None:  # noqa: N802 - Qt signature
        for win in (self._openai_float, self._claude_float, self._prompt_float):
            if win:
                win._docked = True  # suppress dock signal
                win.close()
        self._caption_worker.stop_caption()
        self._caption_worker.wait(3000)
        self._voice_worker.stop_voice()
        self._voice_worker.wait(3000)
        try:
            self._worker.stop()
        finally:
            self._db.close()
        super().closeEvent(event)
