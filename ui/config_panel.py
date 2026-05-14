"""Interview configuration dialog for CORTEXHUB."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from workers.voice_input_worker import VoiceInputWorker

_INTERVIEW_TYPES = [
    "Mixed / All topics",
    "Technical Coding",
    "System Design",
    "Behavioral (STAR)",
    "Data Structures & Algorithms",
    "General Q&A",
]

_CODE_LANGUAGES = [
    "Any language (AI decides)",
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "JavaScript / TypeScript",
    "C",
    "C++",
    "C#",
    "Go",
    "Rust",
    "Swift",
    "Kotlin",
    "Ruby",
    "PHP",
    "Scala",
    "R",
    "MATLAB",
    "Dart / Flutter",
    "Shell / Bash",
    "HTML / CSS",
    "SQL",
    "Haskell",
    "Elixir",
    "Perl",
    "Lua",
]

_STYLE_PRESETS = [
    "Concise & direct (short punchy answers)",
    "STAR method (Situation -> Task -> Action -> Result)",
    "Detailed with code examples",
    "Natural & conversational",
    "Custom...",
]

# ── Mic button stylesheets ─────────────────────────────────────────────────────
_MIC_ON_STYLE = (
    "QPushButton{background:#0d2240;color:#1f9cf0;"
    "border:1.5px solid #1f9cf0;border-radius:5px;"
    "font-size:13px;padding:2px 8px;font-weight:700;}"
    "QPushButton:hover{background:#0e2e55;}"
)
_MIC_OFF_STYLE = (
    "QPushButton{background:#2a0d0d;color:#e05252;"
    "border:1.5px solid #e05252;border-radius:5px;"
    "font-size:13px;padding:2px 8px;font-weight:700;}"
    "QPushButton:hover{background:#380f0f;}"
)

# Inline QSS for the floating popup (top-level widget, can't inherit parent sheet)
_POPUP_QSS = """
QFrame {
    background-color: #141820;
    border: 1.5px solid #273045;
    border-radius: 8px;
}
QLineEdit {
    background-color: #0d1018;
    border: 1px solid #273045;
    border-radius: 5px;
    padding: 6px 10px;
    color: #dce4f0;
    font-size: 13px;
}
QLineEdit:focus { border-color: #1f6feb; }
QCheckBox {
    color: #c0c8d8;
    font-size: 13px;
    padding: 3px 6px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1.5px solid #3a4a6a;
    border-radius: 3px;
    background-color: #0d1018;
}
QCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #1f6feb;
}
QCheckBox::indicator:hover { border-color: #1f9cf0; }
QScrollArea, QWidget { background-color: transparent; }
QScrollBar:vertical { background: #141820; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #252d3e; min-height: 20px; border-radius: 3px; }
QScrollBar::handle:vertical:hover { background: #324060; }
"""


# ─────────────────────────────────────────────────────────────────────────────
class MultiSelectDropdown(QWidget):
    """Editable multi-select dropdown with live search/filter and custom entry."""

    changed = Signal(list)

    def __init__(
        self,
        options: list,
        placeholder: str = "Select...",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._options: list = list(options)
        self._selected: list = []
        self._checkboxes: dict = {}
        self._checks_layout = None
        self._build_widget(placeholder)
        self._build_popup()

    # ── inline widget ─────────────────────────────────────────────────────────
    def _build_widget(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._display = QLineEdit()
        self._display.setObjectName("MultiSelectDisplay")
        self._display.setPlaceholderText(placeholder)
        self._display.setReadOnly(True)
        self._display.setCursor(Qt.CursorShape.PointingHandCursor)
        self._display.mousePressEvent = lambda _e: self._show_popup()

        self._drop_btn = QPushButton("v")
        self._drop_btn.setObjectName("MultiSelectDropBtn")
        self._drop_btn.setFixedWidth(30)
        self._drop_btn.clicked.connect(self._show_popup)

        layout.addWidget(self._display, 1)
        layout.addWidget(self._drop_btn)

    # ── floating popup ─────────────────────────────────────────────────────────
    def _build_popup(self) -> None:
        self._popup = QFrame(None, Qt.WindowType.Popup)
        self._popup.setObjectName("MultiSelectPopupFrame")
        self._popup.setStyleSheet(_POPUP_QSS)

        pop_l = QVBoxLayout(self._popup)
        pop_l.setContentsMargins(6, 6, 6, 6)
        pop_l.setSpacing(4)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search or type to add custom...")
        self._search_input.textChanged.connect(self._filter_visible)
        self._search_input.returnPressed.connect(self._add_custom_from_input)
        pop_l.addWidget(self._search_input)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(210)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        checks_container = QWidget()
        self._checks_layout = QVBoxLayout(checks_container)
        self._checks_layout.setContentsMargins(2, 2, 2, 2)
        self._checks_layout.setSpacing(2)

        for opt in self._options:
            self._add_option(opt, checked=False, emit=False)

        scroll.setWidget(checks_container)
        pop_l.addWidget(scroll)
        self._popup.setFixedWidth(320)

    # ── helpers ────────────────────────────────────────────────────────────────
    def _add_option(self, name: str, checked: bool = False, emit: bool = True) -> None:
        if name in self._checkboxes:
            if checked:
                self._checkboxes[name].setChecked(True)
            return
        cb = QCheckBox(name)
        cb.setChecked(checked)
        cb.stateChanged.connect(self._on_state_changed)
        self._checkboxes[name] = cb
        self._checks_layout.addWidget(cb)
        if emit:
            self._on_state_changed()

    def _show_popup(self) -> None:
        self._search_input.clear()
        self._filter_visible("")
        pos = self.mapToGlobal(QPoint(0, self.height()))
        self._popup.move(pos)
        self._popup.show()
        self._search_input.setFocus()

    def _filter_visible(self, text: str) -> None:
        t = text.lower()
        for name, cb in self._checkboxes.items():
            cb.setVisible(not t or t in name.lower())

    def _add_custom_from_input(self) -> None:
        text = self._search_input.text().strip()
        if not text:
            return
        if text in self._checkboxes:
            self._checkboxes[text].setChecked(True)
        else:
            self._add_option(text, checked=True)
        self._search_input.clear()
        self._filter_visible("")

    def _on_state_changed(self) -> None:
        self._selected = [n for n, cb in self._checkboxes.items() if cb.isChecked()]
        self._display.setText(", ".join(self._selected))
        self.changed.emit(list(self._selected))

    # ── public API ────────────────────────────────────────────────────────────
    @property
    def selected(self) -> list:
        return list(self._selected)

    def set_selected(self, items: list) -> None:
        for item in items:
            if item and item not in self._checkboxes:
                self._add_option(item, checked=False, emit=False)
        for name, cb in self._checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(name in items)
            cb.blockSignals(False)
        self._on_state_changed()


# ─────────────────────────────────────────────────────────────────────────────
class ConfigDialog(QDialog):
    """Modal dialog for setting up interview context before a session."""

    session_started = Signal(dict)
    config_updated = Signal(dict)

    def __init__(self, current_config=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Interview Configuration - CORTEXHUB")
        self.setModal(True)
        self.resize(740, 580)
        self.setMinimumSize(560, 440)

        # Fit to available screen height
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            h = min(580, avail.height() - 100)
            w = min(740, avail.width() - 80)
            self.resize(w, h)

        config = current_config or {}

        # ── Voice workers ──────────────────────────────────────────────────────
        self._role_voice_active = False
        self._role_voice_partial_base = ""
        self._role_voice_worker = VoiceInputWorker(self)
        self._role_voice_worker.text_ready.connect(self._on_role_voice_text)
        self._role_voice_worker.partial_text.connect(self._on_role_voice_partial)
        self._role_voice_worker.status_changed.connect(self._on_role_voice_status)

        self._tech_voice_active = False
        self._tech_voice_partial_anchor = -1
        self._tech_voice_worker = VoiceInputWorker(self)
        self._tech_voice_worker.text_ready.connect(self._on_tech_voice_text)
        self._tech_voice_worker.partial_text.connect(self._on_tech_voice_partial)
        self._tech_voice_worker.status_changed.connect(self._on_tech_voice_status)

        self._build_ui(config)
        _sc = QShortcut(QKeySequence("Ctrl+M"), self)
        _sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        _sc.activated.connect(self._on_ctrl_m)

    # ------------------------------------------------------------------ build
    def _build_ui(self, config: dict) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(6)

        # ── Fixed header (above scroll) ────────────────────────────────────────
        hdr = QLabel("Interview Setup")
        hdr.setObjectName("ConfigHeader")
        root.addWidget(hdr)

        sub = QLabel(
            "Configure your profile so responses are tailored to your background. "
            "All fields are optional."
        )
        sub.setObjectName("ConfigSubHeader")
        sub.setWordWrap(True)
        root.addWidget(sub)

        root.addWidget(self._divider())

        # ── Scrollable form body ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea>QWidget>QWidget{background:transparent;}"
        )

        form = QWidget()
        f = QVBoxLayout(form)
        f.setContentsMargins(0, 4, 6, 4)
        f.setSpacing(8)

        # ── Role ───────────────────────────────────────────────────────────────
        role_hdr_row = QHBoxLayout()
        role_hdr_row.setSpacing(8)
        role_hdr_row.addWidget(self._section_label("Role & Interview Type"))
        role_hdr_row.addStretch(1)
        self._role_mic_btn = self._make_mic_btn()
        self._role_mic_btn.clicked.connect(self._toggle_role_mic)
        role_hdr_row.addWidget(self._role_mic_btn)
        f.addLayout(role_hdr_row)

        self._role_input = QLineEdit()
        self._role_input.setObjectName("ConfigLineEdit")
        self._role_input.setPlaceholderText(
            "e.g. Senior Backend Engineer, ML Engineer, Frontend Lead..."
        )
        self._role_input.setText(config.get("role", ""))
        f.addWidget(self._role_input)

        # Interview Type
        type_lbl = QLabel("Interview Type:")
        type_lbl.setObjectName("ConfigInlineLabel")
        f.addWidget(type_lbl)

        saved_type = config.get("interview_type", _INTERVIEW_TYPES[0])
        saved_types = [t.strip() for t in saved_type.split(",") if t.strip()]
        if not saved_types:
            saved_types = [_INTERVIEW_TYPES[0]]

        self._interview_type_widget = MultiSelectDropdown(
            _INTERVIEW_TYPES,
            placeholder="Select interview type(s)...",
        )
        self._interview_type_widget.set_selected(saved_types)
        f.addWidget(self._interview_type_widget)

        # Code Language
        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        lang_lbl = QLabel("Code Language:")
        lang_lbl.setObjectName("ConfigInlineLabel")

        saved_lang = config.get("language", _CODE_LANGUAGES[0])
        saved_langs = [s.strip() for s in saved_lang.split(",") if s.strip()]
        if not saved_langs:
            saved_langs = [_CODE_LANGUAGES[0]]

        self._lang_widget = MultiSelectDropdown(
            _CODE_LANGUAGES,
            placeholder="Select language(s) or type custom...",
        )
        self._lang_widget.set_selected(saved_langs)
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self._lang_widget, 1)
        f.addLayout(lang_row)

        f.addWidget(self._divider())

        # ── Resume ─────────────────────────────────────────────────────────────
        f.addWidget(self._section_label("Resume"))

        self._resume_tabs = QTabWidget()
        self._resume_tabs.setObjectName("ConfigTabs")
        self._resume_tabs.setFixedHeight(155)

        paste_widget = QWidget()
        paste_layout = QVBoxLayout(paste_widget)
        paste_layout.setContentsMargins(4, 6, 4, 4)
        self._resume_text = QTextEdit()
        self._resume_text.setObjectName("ConfigTextArea")
        self._resume_text.setPlaceholderText(
            "Paste your resume text here...\n\n"
            "Include: job titles, companies, tech stack, responsibilities."
        )
        self._resume_text.setPlainText(config.get("resume", ""))
        paste_layout.addWidget(self._resume_text)
        self._resume_tabs.addTab(paste_widget, "  Paste Text  ")

        upload_widget = QWidget()
        upload_layout = QVBoxLayout(upload_widget)
        upload_layout.setContentsMargins(4, 8, 4, 4)
        upload_layout.setSpacing(8)
        self._upload_status = QLabel("No file selected")
        self._upload_status.setObjectName("ConfigUploadStatus")
        self._upload_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_btn = QPushButton("Choose .txt File")
        upload_btn.setObjectName("ConfigUploadButton")
        upload_btn.clicked.connect(self._pick_file)
        upload_layout.addStretch(1)
        upload_layout.addWidget(self._upload_status)
        upload_layout.addWidget(upload_btn, 0, Qt.AlignmentFlag.AlignCenter)
        upload_layout.addStretch(1)
        self._resume_tabs.addTab(upload_widget, "  Upload File  ")

        f.addWidget(self._resume_tabs)

        # ── Technical Stack ────────────────────────────────────────────────────
        tech_hdr_row = QHBoxLayout()
        tech_hdr_row.setSpacing(8)
        tech_hdr_row.addWidget(self._section_label("Technical Stack"))
        tech_hdr_row.addStretch(1)
        self._tech_mic_btn = self._make_mic_btn()
        self._tech_mic_btn.clicked.connect(self._toggle_tech_mic)
        tech_hdr_row.addWidget(self._tech_mic_btn)
        f.addLayout(tech_hdr_row)

        self._tech_stack = QTextEdit()
        self._tech_stack.setObjectName("ConfigTextArea")
        self._tech_stack.setFixedHeight(64)
        self._tech_stack.setPlaceholderText(
            "e.g. Python, FastAPI, PostgreSQL, Kafka, Kubernetes, React, AWS..."
        )
        self._tech_stack.setPlainText(config.get("tech_stack", ""))
        f.addWidget(self._tech_stack)

        # ── Response style ─────────────────────────────────────────────────────
        f.addWidget(self._section_label("Preferred Response Style"))

        self._style_combo = QComboBox()
        self._style_combo.setObjectName("ConfigCombo")
        for preset in _STYLE_PRESETS:
            self._style_combo.addItem(preset)
        saved_style = config.get("style", "")
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)

        self._custom_style = QTextEdit()
        self._custom_style.setObjectName("ConfigTextArea")
        self._custom_style.setFixedHeight(48)
        self._custom_style.setPlaceholderText("Describe how you want answers formatted...")

        self._style_upload_btn = QPushButton("Upload .txt Style File")
        self._style_upload_btn.setObjectName("ConfigUploadButton")
        self._style_upload_btn.setToolTip("Load style instructions from a text file")
        self._style_upload_btn.clicked.connect(self._pick_style_file)

        self._custom_style_widget = QWidget()
        cs_layout = QVBoxLayout(self._custom_style_widget)
        cs_layout.setContentsMargins(0, 2, 0, 0)
        cs_layout.setSpacing(4)
        cs_layout.addWidget(self._custom_style)
        cs_layout.addWidget(self._style_upload_btn, 0, Qt.AlignmentFlag.AlignRight)
        self._custom_style_widget.setVisible(False)

        preset_idx = None
        for i, p in enumerate(_STYLE_PRESETS[:-1]):
            if saved_style == p:
                preset_idx = i
                break
        if preset_idx is not None:
            self._style_combo.setCurrentIndex(preset_idx)
        elif saved_style:
            self._style_combo.setCurrentIndex(len(_STYLE_PRESETS) - 1)
            self._custom_style.setPlainText(saved_style)
            self._custom_style_widget.setVisible(True)
        else:
            self._style_combo.setCurrentIndex(0)

        f.addWidget(self._style_combo)
        f.addWidget(self._custom_style_widget)

        scroll.setWidget(form)
        root.addWidget(scroll, 1)

        # ── Fixed bottom: divider + buttons ───────────────────────────────────
        root.addWidget(self._divider())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("ConfigCancelButton")
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)

        update_btn = QPushButton("Update Profile")
        update_btn.setObjectName("ConfigUpdateButton")
        update_btn.setFixedWidth(140)
        update_btn.setToolTip("Apply changes without resetting current conversation")
        update_btn.clicked.connect(self._on_update)

        start_btn = QPushButton("Start New Session")
        start_btn.setObjectName("ConfigStartButton")
        start_btn.setFixedWidth(170)
        start_btn.setToolTip("Save profile and start a fresh conversation")
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(update_btn)
        btn_row.addWidget(start_btn)
        root.addLayout(btn_row)

    # ---------------------------------------------------------------- helpers
    def _make_mic_btn(self) -> QPushButton:
        btn = QPushButton("\U0001f3a4\\")
        btn.setFixedSize(46, 28)
        btn.setToolTip("Toggle microphone  (Ctrl+M)")
        btn.setStyleSheet(_MIC_OFF_STYLE)
        return btn

    def _set_mic_on(self, btn: QPushButton) -> None:
        btn.setText("\U0001f3a4")
        btn.setStyleSheet(_MIC_ON_STYLE)

    def _set_mic_off(self, btn: QPushButton) -> None:
        btn.setText("\U0001f3a4\\")
        btn.setStyleSheet(_MIC_OFF_STYLE)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("ConfigSectionLabel")
        return lbl

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("ConfigDivider")
        return line

    # ---------------------------------------------------------------- mic
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if (
            event.key() == Qt.Key.Key_M
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._on_ctrl_m()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _on_ctrl_m(self) -> None:
        # Stop whichever is currently active, or start based on focus
        if self._tech_voice_active:
            self._toggle_tech_mic()
        elif self._role_voice_active:
            self._toggle_role_mic()
        else:
            focused = self.focusWidget()
            if focused is self._tech_stack or focused is self._tech_mic_btn:
                self._toggle_tech_mic()
            else:
                self._toggle_role_mic()

    def _toggle_role_mic(self) -> None:
        if self._role_voice_active:
            self._role_voice_worker.stop_voice()
            self._role_voice_active = False
            self._set_mic_off(self._role_mic_btn)
            self._role_voice_partial_base = ""
        else:
            self._role_voice_partial_base = self._role_input.text()
            if self._role_voice_partial_base and not self._role_voice_partial_base.endswith(" "):
                self._role_voice_partial_base += " "
            self._role_voice_worker.start_voice()
            self._role_voice_active = True
            self._set_mic_on(self._role_mic_btn)

    def _toggle_tech_mic(self) -> None:
        if self._tech_voice_active:
            self._tech_voice_worker.stop_voice()
            self._tech_voice_active = False
            self._set_mic_off(self._tech_mic_btn)
            self._tech_voice_partial_anchor = -1
        else:
            self._tech_voice_worker.start_voice()
            self._tech_voice_active = True
            self._set_mic_on(self._tech_mic_btn)
            self._tech_voice_partial_anchor = -1

    # ---------------------------------------------------------------- voice — role
    def _on_role_voice_text(self, text: str) -> None:
        self._role_voice_partial_base += text + " "
        self._role_input.setText(self._role_voice_partial_base.rstrip())

    def _on_role_voice_partial(self, text: str) -> None:
        self._role_input.setText((self._role_voice_partial_base + text).rstrip())

    def _on_role_voice_status(self, status: str) -> None:
        if status.startswith("Error"):
            self._role_voice_active = False
            self._set_mic_off(self._role_mic_btn)
            self._role_voice_partial_base = ""

    # ---------------------------------------------------------------- voice — tech
    def _on_tech_voice_text(self, text: str) -> None:
        from PySide6.QtGui import QTextCursor
        cursor = self._tech_stack.textCursor()
        if self._tech_voice_partial_anchor >= 0:
            cursor.setPosition(self._tech_voice_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        else:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text + " ")
        self._tech_stack.setTextCursor(cursor)
        self._tech_voice_partial_anchor = -1

    def _on_tech_voice_partial(self, text: str) -> None:
        from PySide6.QtGui import QTextCursor
        if not text:
            return
        cursor = self._tech_stack.textCursor()
        if self._tech_voice_partial_anchor < 0:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self._tech_voice_partial_anchor = cursor.position()
        else:
            cursor.setPosition(self._tech_voice_partial_anchor)
            cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        cursor.insertText(text)
        self._tech_stack.setTextCursor(cursor)

    def _on_tech_voice_status(self, status: str) -> None:
        if status.startswith("Error"):
            self._tech_voice_active = False
            self._set_mic_off(self._tech_mic_btn)
            self._tech_voice_partial_anchor = -1

    # ---------------------------------------------------------------- slots
    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Resume File", "", "Text files (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._resume_text.setPlainText(content)
            self._upload_status.setText(
                "Loaded: " + path.split("/")[-1].split("\\")[-1]
            )
            self._resume_tabs.setCurrentIndex(0)
        except Exception as exc:  # noqa: BLE001
            self._upload_status.setText(f"Error reading file: {exc}")

    def _pick_style_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Style File", "", "Text files (*.txt);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self._custom_style.setPlainText(content)
        except Exception as exc:  # noqa: BLE001
            self._custom_style.setPlainText(f"Error reading file: {exc}")

    def _on_style_changed(self, idx: int) -> None:
        self._custom_style_widget.setVisible(idx == len(_STYLE_PRESETS) - 1)

    def _collect(self) -> dict:
        resume = self._resume_text.toPlainText().strip()
        tech_stack = self._tech_stack.toPlainText().strip()

        idx = self._style_combo.currentIndex()
        style = (
            self._custom_style.toPlainText().strip()
            if idx == len(_STYLE_PRESETS) - 1
            else _STYLE_PRESETS[idx]
        )

        selected_types = self._interview_type_widget.selected
        interview_type = ", ".join(selected_types) if selected_types else _INTERVIEW_TYPES[0]

        selected_langs = self._lang_widget.selected
        language = ", ".join(selected_langs) if selected_langs else _CODE_LANGUAGES[0]

        return {
            "resume": resume,
            "tech_stack": tech_stack,
            "style": style,
            "role": self._role_input.text().strip(),
            "interview_type": interview_type,
            "language": language,
        }

    def _on_update(self) -> None:
        self.config_updated.emit(self._collect())
        self.accept()

    def _on_start(self) -> None:
        self.session_started.emit(self._collect())
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._role_voice_worker.stop_voice()
        self._tech_voice_worker.stop_voice()
        self._role_voice_worker.wait(2000)
        self._tech_voice_worker.wait(2000)
        super().closeEvent(event)
