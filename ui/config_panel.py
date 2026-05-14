"""Interview configuration dialog for CORTEXHUB."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QFrame,
)

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
    "JavaScript / TypeScript",
    "C++",
    "Go",
    "Rust",
    "C#",
    "SQL",
]

_STYLE_PRESETS = [
    "Concise & direct (short punchy answers)",
    "STAR method (Situation → Task → Action → Result)",
    "Detailed with code examples",
    "Natural & conversational",
    "Custom…",
]


class ConfigDialog(QDialog):
    """Modal dialog for setting up interview context before a session."""

    # Emitted when the user starts a new session; payload is the config dict
    session_started = Signal(dict)
    # Emitted when the user just updates config without resetting
    config_updated = Signal(dict)

    def __init__(self, current_config: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Interview Configuration — CORTEXHUB")
        self.setModal(True)
        self.resize(720, 620)
        self.setMinimumSize(600, 500)

        config = current_config or {}
        self._build_ui(config)

    # ------------------------------------------------------------------ build
    def _build_ui(self, config: dict) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QLabel("⚙  Interview Setup")
        hdr.setObjectName("ConfigHeader")
        root.addWidget(hdr)

        sub = QLabel(
            "Configure your profile so responses are tailored to your background. "
            "All fields are optional — you can start a session without any data."
        )
        sub.setObjectName("ConfigSubHeader")
        sub.setWordWrap(True)
        root.addWidget(sub)

        root.addWidget(self._divider())
        # ── Session context (role / type / language) ───────────────────────────────
        root.addWidget(self._section_label("🎯  Role & Interview Type"))

        self._role_input = QLineEdit()
        self._role_input.setObjectName("ConfigLineEdit")
        self._role_input.setPlaceholderText(
            "e.g. Senior Backend Engineer at FAANG, ML Engineer, Frontend Lead…"
        )
        self._role_input.setText(config.get("role", ""))
        root.addWidget(self._role_input)

        type_row = QHBoxLayout()
        type_row.setSpacing(10)

        type_lbl = QLabel("Interview Type:")
        type_lbl.setObjectName("ConfigInlineLabel")
        self._interview_type_combo = QComboBox()
        self._interview_type_combo.setObjectName("ConfigCombo")
        for t in _INTERVIEW_TYPES:
            self._interview_type_combo.addItem(t)
        saved_type = config.get("interview_type", _INTERVIEW_TYPES[0])
        idx_t = _INTERVIEW_TYPES.index(saved_type) if saved_type in _INTERVIEW_TYPES else 0
        self._interview_type_combo.setCurrentIndex(idx_t)

        lang_lbl = QLabel("Code Language:")
        lang_lbl.setObjectName("ConfigInlineLabel")
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("ConfigCombo")
        for l in _CODE_LANGUAGES:
            self._lang_combo.addItem(l)
        saved_lang = config.get("language", _CODE_LANGUAGES[0])
        idx_l = _CODE_LANGUAGES.index(saved_lang) if saved_lang in _CODE_LANGUAGES else 0
        self._lang_combo.setCurrentIndex(idx_l)

        type_row.addWidget(type_lbl)
        type_row.addWidget(self._interview_type_combo, 2)
        type_row.addSpacing(12)
        type_row.addWidget(lang_lbl)
        type_row.addWidget(self._lang_combo, 2)
        root.addLayout(type_row)

        root.addWidget(self._divider())
        # ── Resume section ─────────────────────────────────────────────────────
        root.addWidget(self._section_label("📄  Resume"))

        self._resume_tabs = QTabWidget()
        self._resume_tabs.setObjectName("ConfigTabs")
        self._resume_tabs.setFixedHeight(180)

        # Tab 1 — paste text
        paste_widget = QWidget()
        paste_layout = QVBoxLayout(paste_widget)
        paste_layout.setContentsMargins(4, 8, 4, 4)
        self._resume_text = QTextEdit()
        self._resume_text.setObjectName("ConfigTextArea")
        self._resume_text.setPlaceholderText(
            "Paste your resume text here…\n\n"
            "Include: job titles, companies, tech stack, responsibilities, achievements."
        )
        self._resume_text.setPlainText(config.get("resume", ""))
        paste_layout.addWidget(self._resume_text)
        self._resume_tabs.addTab(paste_widget, "  Paste Text  ")

        # Tab 2 — upload file
        upload_widget = QWidget()
        upload_layout = QVBoxLayout(upload_widget)
        upload_layout.setContentsMargins(4, 8, 4, 4)
        upload_layout.setSpacing(8)
        self._upload_status = QLabel("No file selected")
        self._upload_status.setObjectName("ConfigUploadStatus")
        self._upload_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_btn = QPushButton("📁  Choose .txt File")
        upload_btn.setObjectName("ConfigUploadButton")
        upload_btn.clicked.connect(self._pick_file)
        upload_layout.addStretch(1)
        upload_layout.addWidget(self._upload_status)
        upload_layout.addWidget(upload_btn, 0, Qt.AlignmentFlag.AlignCenter)
        upload_layout.addStretch(1)
        self._resume_tabs.addTab(upload_widget, "  Upload File  ")

        root.addWidget(self._resume_tabs)

        # ── Technical stack ────────────────────────────────────────────────────
        root.addWidget(self._section_label("🛠  Technical Stack"))

        self._tech_stack = QTextEdit()
        self._tech_stack.setObjectName("ConfigTextArea")
        self._tech_stack.setFixedHeight(80)
        self._tech_stack.setPlaceholderText(
            "e.g. Python, FastAPI, PostgreSQL, Kafka, Kubernetes, React, AWS (EC2 / S3 / Lambda)…"
        )
        self._tech_stack.setPlainText(config.get("tech_stack", ""))
        root.addWidget(self._tech_stack)

        # ── Response style ─────────────────────────────────────────────────────
        root.addWidget(self._section_label("💬  Preferred Response Style"))

        style_row = QHBoxLayout()
        style_row.setSpacing(10)

        self._style_combo = QComboBox()
        self._style_combo.setObjectName("ConfigCombo")
        for preset in _STYLE_PRESETS:
            self._style_combo.addItem(preset)
        saved_style = config.get("style", "")
        self._style_combo.currentIndexChanged.connect(self._on_style_changed)

        self._custom_style = QTextEdit()
        self._custom_style.setObjectName("ConfigTextArea")
        self._custom_style.setFixedHeight(52)
        self._custom_style.setPlaceholderText("Describe how you want answers formatted…")

        self._style_upload_btn = QPushButton("\U0001f4c1  Upload .txt Style File")
        self._style_upload_btn.setObjectName("ConfigUploadButton")
        self._style_upload_btn.setToolTip("Load style instructions from a text file")
        self._style_upload_btn.clicked.connect(self._pick_style_file)

        self._custom_style_widget = QWidget()
        cs_layout = QVBoxLayout(self._custom_style_widget)
        cs_layout.setContentsMargins(0, 4, 0, 0)
        cs_layout.setSpacing(4)
        cs_layout.addWidget(self._custom_style)
        cs_layout.addWidget(self._style_upload_btn, 0, Qt.AlignmentFlag.AlignRight)
        self._custom_style_widget.setVisible(False)

        # Restore saved style
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

        style_row.addWidget(self._style_combo)
        root.addLayout(style_row)
        root.addWidget(self._custom_style_widget)

        root.addStretch(1)
        root.addWidget(self._divider())

        # ── Buttons ────────────────────────────────────────────────────────────
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

        start_btn = QPushButton("▶  Start New Session")
        start_btn.setObjectName("ConfigStartButton")
        start_btn.setFixedWidth(180)
        start_btn.setToolTip("Save profile and start a fresh conversation")
        start_btn.clicked.connect(self._on_start)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(update_btn)
        btn_row.addWidget(start_btn)
        root.addLayout(btn_row)

    # ---------------------------------------------------------------- helpers
    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("ConfigSectionLabel")
        return lbl

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("ConfigDivider")
        return line

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
            self._upload_status.setText(f"✔  Loaded: {path.split('/')[-1].split(chr(92))[-1]}")
            # Switch to paste tab so user can see the loaded text
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
        if idx == len(_STYLE_PRESETS) - 1:
            style = self._custom_style.toPlainText().strip()
        else:
            style = _STYLE_PRESETS[idx]
        return {
            "resume": resume,
            "tech_stack": tech_stack,
            "style": style,
            "role": self._role_input.text().strip(),
            "interview_type": self._interview_type_combo.currentText(),
            "language": self._lang_combo.currentText(),
        }

    def _on_update(self) -> None:
        self.config_updated.emit(self._collect())
        self.accept()

    def _on_start(self) -> None:
        self.session_started.emit(self._collect())
        self.accept()
