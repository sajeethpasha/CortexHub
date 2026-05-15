"""CORTEXHUB entry point."""
from __future__ import annotations

import sys

from dotenv import load_dotenv
load_dotenv()
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    # .env already loaded at module import time.

    app = QApplication(sys.argv)
    app.setApplicationName("CORTEXHUB")

    window = MainWindow()
    window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
