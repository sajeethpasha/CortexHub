"""CORTEXHUB entry point."""
from __future__ import annotations

import sys

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    # Load API keys from .env (if present) before any client is constructed.
    load_dotenv()

    app = QApplication(sys.argv)
    app.setApplicationName("CORTEXHUB")

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
