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
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
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
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
