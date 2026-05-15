"""Dark theme stylesheet for CORTEXHUB."""

DARK_QSS = """
* {
    font-family: "Segoe UI", "Inter", Arial, sans-serif;
    font-size: 14px;
    color: #e6e6e6;
}

QMainWindow, QWidget {
    background-color: #0f1115;
}

/* ── Top header bar ───────────────────────────────────────────── */
QWidget#TopBar {
    background-color: #0a0c10;
    border-bottom: 1px solid #1a1f2a;
    min-height: 42px;
    max-height: 42px;
}

QLabel#ContextLabel {
    font-size: 11px;
    font-weight: 700;
    color: #2e3a4e;
    letter-spacing: 3px;
    padding: 0 2px;
}

QLabel#StatusLabel {
    font-size: 12px;
    color: #4a6a9a;
    padding: 0 4px;
    font-weight: 600;
}

QPushButton#TopBarButton {
    background-color: #1f6feb;
    color: #ffffff;
    border: none;
    border-radius: 7px;
    padding: 6px 20px;
    font-weight: 700;
    font-size: 13px;
    min-width: 64px;
}
QPushButton#TopBarButton:hover    { background-color: #3381f5; }
QPushButton#TopBarButton:pressed  { background-color: #1858c2; }
QPushButton#TopBarButton:disabled { background-color: #1e2a3d; color: #4a5568; }

QPushButton#TopBarButtonSecondary {
    background-color: #1a1f2a;
    color: #c0c8d8;
    border: 1px solid #252d3e;
    border-radius: 7px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 600;
    min-width: 64px;
}
QPushButton#TopBarButtonSecondary:hover   { background-color: #232c3e; color: #ffffff; border-color: #38445a; }
QPushButton#TopBarButtonSecondary:pressed { background-color: #141820; }

/* ── Prompt container ────────────────────────────────────────── */
QWidget#PromptContainer {
    background-color: transparent;
    border: none;
    border-radius: 0;
}

/* ── Image strip ─────────────────────────────────────────────── */
QScrollArea#ImageStrip {
    background: #0d1018;
    border: 1px solid #1e2636;
    border-radius: 6px;
}
QWidget#ImageStripInner {
    background: transparent;
}
QFrame#ImageThumbFrame {
    background: #141820;
    border: 1px solid #252d3e;
    border-radius: 6px;
}
QPushButton#ImageDeleteBtn {
    background: #3a1a1a;
    color: #e05252;
    border: 1px solid #6a2a2a;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    padding: 0px;
}
QPushButton#ImageDeleteBtn:hover {
    background: #5a1a1a;
}

QTextEdit#PromptInput {
    background-color: #0d1018;
    border: 1.5px solid #273045;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    color: #dce4f0;
    selection-background-color: #1f6feb;
}
QTextEdit#PromptInput:focus {
    border: 1.5px solid #3a6bc4;
}
QTextEdit#PromptInput[readOnly="true"] {
    background-color: #0a0d12;
    border: 1.5px solid #1e2636;
    color: #6a7a94;
}

/* ── Clear-both bar ──────────────────────────────────────────── */
QWidget#ClearBar {
    background-color: transparent;
}

/* ── Panel title bar ─────────────────────────────────────────── */
QWidget#PanelTitleBar {
    background-color: #141820;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-height: 38px;
    border: 1px solid #1e2636;
    border-bottom: none;
}

QLabel#PanelTitle {
    font-size: 12px;
    font-weight: 700;
    color: #6a7a94;
    letter-spacing: 1px;
    padding: 6px 4px;
    background-color: transparent;
}

QPushButton#PanelToolButton {
    background-color: #1a2030;
    color: #8899b4;
    border: 1px solid #252d3e;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#PanelToolButton:hover   { background-color: #1e3050; color: #ffffff; border-color: #2a5298; }
QPushButton#PanelToolButton:pressed { background-color: #131928; }

QWidget#PanelZoomGroup {
    background-color: #151d2d;
    border: 1px solid #252d3e;
    border-radius: 5px;
}

QPushButton#ZoomPercentButton {
    background-color: transparent;
    color: #c8d0e0;
    border: none;
    padding: 2px 4px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#ZoomPercentButton:hover   { background-color: #1e3050; color: #ffffff; }
QPushButton#ZoomPercentButton:pressed { background-color: #131928; }

QSlider#PanelZoomSlider {
    min-width: 76px;
    max-width: 130px;
}
QSlider#PanelZoomSlider::groove:horizontal {
    height: 4px;
    background: #252d3e;
    border-radius: 2px;
}
QSlider#PanelZoomSlider::sub-page:horizontal {
    background: #4a7fcb;
    border-radius: 2px;
}
QSlider#PanelZoomSlider::add-page:horizontal {
    background: #252d3e;
    border-radius: 2px;
}
QSlider#PanelZoomSlider::handle:horizontal {
    background: #6fa3ff;
    border: 1px solid #9dbfff;
    width: 11px;
    height: 11px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider#PanelZoomSlider::handle:horizontal:hover {
    background: #8bb6ff;
}

/* ── Response view (white bg, rich text) ─────────────────────── */
QTextEdit#ResponseView {
    background-color: #ffffff;
    color: #1a1a2e;
    border: 1px solid #1e2636;
    border-top: none;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
    padding: 10px 14px;
    selection-background-color: #fff59d;
    selection-color: #1a1a2e;
}

QPushButton#ClearBothButton {
    background-color: #1a2030;
    color: #8899b4;
    border: 1px solid #252d3e;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#ClearBothButton:hover   { background-color: #2a1a1a; color: #e06060; border-color: #6a2a2a; }
QPushButton#ClearBothButton:pressed { background-color: #1a1010; }

/* ── Splitter ────────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #141820;
}
QSplitter::handle:hover { background-color: #1e2636; }

/* ── Scrollbars ──────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f1115;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #252d3e;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background: #324060; }
QLabel#LiveCaptionLabel {
    color: #9aa4b2;
    font-size: 14px;
    padding: 4px 8px;
    background-color: #1a1f2a;
    border-radius: 6px;
    margin: 2px 0;
}

/* ── Session badge ────────────────────────────────────────────── */
QLabel#SessionBadge {
    color: #4a6a9a;
    font-size: 12px;
    font-weight: 600;
    padding: 0 4px;
}
QLabel#SessionBadgeActive {
    color: #4ecb71;
    font-size: 12px;
    font-weight: 700;
    padding: 0 4px;
}

/* ── Top bar interview buttons ────────────────────────────────── */
QPushButton#ConfigureButton {
    background-color: #0e2a2a;
    color: #4ecbcb;
    border: 1px solid #1a4a4a;
    border-radius: 7px;
    padding: 5px 14px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#ConfigureButton:hover { background-color: #143535; color: #7aeaea; }

QPushButton#NewSessionButton {
    background-color: #2a1a08;
    color: #e09050;
    border: 1px solid #4a3018;
    border-radius: 7px;
    padding: 5px 14px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#NewSessionButton:hover { background-color: #3a2210; color: #f0b070; }

/* ── Config Dialog ────────────────────────────────────────────── */
QLabel#ConfigHeader { font-size: 18px; font-weight: 700; color: #c8d8f0; padding: 4px 0; }
QLabel#ConfigSubHeader { font-size: 12px; color: #6a7a94; }
QLabel#ConfigSectionLabel { font-size: 12px; font-weight: 700; color: #8899b4; letter-spacing: 1px; margin-top: 4px; }
QFrame#ConfigDivider { color: #1e2636; }
QTextEdit#ConfigTextArea {
    background-color: #0d1018;
    border: 1.5px solid #273045;
    border-radius: 6px;
    padding: 8px;
    color: #dce4f0;
}
QComboBox#ConfigCombo {
    background-color: #141820;
    border: 1px solid #252d3e;
    border-radius: 6px;
    padding: 6px 12px;
    color: #c0c8d8;
    min-height: 32px;
}
QComboBox#ConfigCombo::drop-down { border: none; width: 20px; }
QComboBox#ConfigCombo QAbstractItemView {
    background-color: #141820;
    border: 1px solid #252d3e;
    color: #c0c8d8;
    selection-background-color: #1f6feb;
}
QPushButton#ConfigStartButton {
    background-color: #1a4a2a;
    color: #4ecb71;
    border: 1px solid #2a6a3a;
    border-radius: 7px;
    padding: 8px 20px;
    font-weight: 700;
    font-size: 14px;
}
QPushButton#ConfigStartButton:hover { background-color: #204a20; color: #7aed9a; }
QPushButton#ConfigUpdateButton {
    background-color: #1a2a3a;
    color: #6a9adc;
    border: 1px solid #253050;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#ConfigUpdateButton:hover { background-color: #1f3252; color: #8ab4f8; }
QPushButton#ConfigCancelButton {
    background-color: #1a1f2a;
    color: #6a7a94;
    border: 1px solid #252d3e;
    border-radius: 7px;
    padding: 8px 16px;
}
QPushButton#ConfigCancelButton:hover { background-color: #232c3e; color: #c0c8d8; }
QPushButton#ConfigUploadButton {
    background-color: #1a2030;
    color: #8899b4;
    border: 1px solid #252d3e;
    border-radius: 6px;
    padding: 6px 16px;
}
QPushButton#ConfigUploadButton:hover { background-color: #1e3050; color: #ffffff; }
QLabel#ConfigUploadStatus { color: #6a7a94; font-size: 12px; }
QTabWidget#ConfigTabs::pane { border: 1px solid #252d3e; background-color: #0d1018; }
QTabWidget#ConfigTabs QTabBar::tab {
    background-color: #141820;
    color: #6a7a94;
    border: 1px solid #252d3e;
    padding: 6px 18px;
}
QTabWidget#ConfigTabs QTabBar::tab:selected {
    background-color: #1a2030;
    color: #c0c8d8;
    border-bottom: 2px solid #1f6feb;
}

/* ── Config Shortcuts Panel ──────────────────────────────────── */
QWidget#ConfigShortcutsPanel {
    background-color: #0a0c10;
    border-right: 1px solid #1a1f2a;
}
QLabel#ConfigShortcutsPanelHeader {
    font-size: 12px;
    font-weight: 700;
    color: #4a6a9a;
    letter-spacing: 2px;
    padding: 2px 0 8px 0;
}
QFrame#ConfigShortcutDivider { color: #1a1f2a; }
QLabel#ConfigShortcutKey {
    font-size: 11px;
    font-weight: 700;
    color: #1f9cf0;
    background-color: #0d1828;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 2px 6px;
}
QLabel#ConfigShortcutDesc {
    font-size: 11px;
    color: #6a7a94;
    padding: 1px 2px 0 2px;
}

/* ── Config Checkboxes ────────────────────────────────────────── */
QWidget#ConfigChecksContainer {
    background-color: #0d1018;
    border: 1.5px solid #273045;
    border-radius: 6px;
}
QCheckBox#ConfigCheckBox {
    color: #c0c8d8;
    font-size: 12px;
    spacing: 6px;
}
QCheckBox#ConfigCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1.5px solid #3a4a6a;
    border-radius: 3px;
    background-color: #0d1018;
}
QCheckBox#ConfigCheckBox::indicator:checked {
    background-color: #1f6feb;
    border-color: #1f6feb;
    image: none;
}
QCheckBox#ConfigCheckBox::indicator:hover {
    border-color: #1f9cf0;
}

/* ── Config Role / Type inline ────────────────────────────────── */
QLabel#ConfigInlineLabel { font-size: 12px; color: #8899b4; }
QLineEdit#ConfigLineEdit {
    background-color: #0d1018;
    border: 1.5px solid #273045;
    border-radius: 6px;
    padding: 7px 10px;
    color: #dce4f0;
    min-height: 28px;
}
QLineEdit#ConfigLineEdit:focus { border-color: #1f6feb; }

/* ── Selection Popup ──────────────────────────────────────────── */
QPushButton#SelectionPopupButton {
    background-color: #1a3050;
    color: #7aaaf0;
    border: 1px solid #2a4a7a;
    border-radius: 5px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 700;
}
QPushButton#SelectionPopupButton:hover { background-color: #1f6feb; color: #ffffff; }
QLineEdit#SelectionPopupInput {
    background-color: #0d1018;
    border: 1px solid #2a4a7a;
    border-radius: 5px;
    padding: 2px 8px;
    color: #c0d0e8;
    font-size: 12px;
}
QLineEdit#SelectionPopupInput:focus { border-color: #4a8adc; }

QLineEdit#ExplainQueryInput {
    background-color: #0d1018;
    border: 1px solid #2a4a7a;
    border-radius: 5px;
    padding: 5px 10px;
    color: #c8d8ee;
    font-size: 13px;
    min-height: 28px;
}
QLineEdit#ExplainQueryInput:focus { border-color: #4a8adc; }

QLabel#StatusLabel {
    color: #5a9a6a;
    font-size: 11px;
}

/* ── Shortcuts Keys Panel ──────────────────────────────────────────────── */
QPushButton#ShortcutsBtn {
    background-color: #111828;
    color: #4a7ab5;
    border: 1px solid #1e3050;
    border-radius: 5px;
    font-size: 16px;
    padding: 0;
}
QPushButton#ShortcutsBtn:hover {
    background-color: #1a2840;
    color: #1f9cf0;
    border-color: #1f6feb;
}
QPushButton#ShortcutsBtn:pressed {
    background-color: #0d1828;
}
QFrame#ShortcutsPanelFrame {
    background-color: #0e1420;
    border: 1.5px solid #1e2d45;
    border-radius: 10px;
}
QLabel#ShortcutsPanelIcon {
    font-size: 16px;
    color: #4a7ab5;
}
QLabel#ShortcutsPanelTitle {
    color: #c0cedf;
    font-size: 13px;
    font-weight: 700;
}
QFrame#ShortcutsPanelDivider {
    background-color: #1a2638;
    max-height: 1px;
    border: none;
}
QLabel#ShortcutsCategoryLabel {
    color: #4a7ab5;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 0 2px 0;
}
QLabel#ShortcutsKeyBadge {
    color: #1f9cf0;
    background-color: #0d1828;
    border: 1px solid #1e3050;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#ShortcutsArrow {
    color: #2a3a55;
    font-size: 11px;
}
QLabel#ShortcutsDesc {
    color: #7890a8;
    font-size: 11px;
}

/* ── MultiSelectDropdown (config panel) ─────────────────────────────────── */
QLineEdit#MultiSelectDisplay {
    background-color: #141820;
    border: 1.5px solid #273045;
    border-radius: 6px 0 0 6px;
    padding: 5px 10px;
    color: #c0c8d8;
    min-height: 26px;
}
QLineEdit#MultiSelectDisplay:hover {
    border-color: #3a4a6a;
}
QPushButton#MultiSelectDropBtn {
    background-color: #1a2030;
    color: #8899b4;
    border: 1.5px solid #273045;
    border-left: none;
    border-radius: 0 6px 6px 0;
    font-size: 14px;
    font-weight: 700;
    padding: 0;
}
QPushButton#MultiSelectDropBtn:hover {
    background-color: #1f3050;
    color: #ffffff;
}
"""
