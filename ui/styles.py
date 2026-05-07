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

QLabel#AppTitle {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    padding: 8px 4px;
    letter-spacing: 2px;
}

QLabel#PanelTitle {
    font-size: 13px;
    font-weight: 600;
    color: #9aa4b2;
    padding: 6px 10px;
    background-color: #161a22;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

QLabel#StatusLabel {
    color: #7c8896;
    padding: 0 8px;
}

QPlainTextEdit, QTextEdit {
    background-color: #0b0d12;
    border: 1px solid #1f2530;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #2b6cb0;
    color: #e6e6e6;
}

QTextEdit#PromptInput {
    background-color: #11151c;
    border: 1px solid #232a36;
    border-radius: 10px;
    padding: 10px;
    font-size: 15px;
}

QPlainTextEdit#ResponseView {
    background-color: #0b0d12;
    border: 1px solid #1f2530;
    border-top-left-radius: 0;
    border-top-right-radius: 0;
    border-bottom-left-radius: 8px;
    border-bottom-right-radius: 8px;
}

QPushButton {
    background-color: #1f6feb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover    { background-color: #2f7cf1; }
QPushButton:pressed  { background-color: #1858c2; }
QPushButton:disabled { background-color: #2a3140; color: #7c8896; }

QPushButton#SecondaryButton {
    background-color: #232a36;
    color: #e6e6e6;
}
QPushButton#SecondaryButton:hover   { background-color: #2c3441; }
QPushButton#SecondaryButton:pressed { background-color: #1c222c; }

QSplitter::handle {
    background-color: #1a1f2a;
    width: 4px;
}
QSplitter::handle:hover { background-color: #2b6cb0; }

QScrollBar:vertical {
    background: #0f1115;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a3140;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover { background: #38445a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
