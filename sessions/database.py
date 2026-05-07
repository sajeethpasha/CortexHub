"""SQLite database layer for CORTEXHUB session storage."""
from __future__ import annotations

import os
import sqlite3
import threading
from typing import Iterable

from utils.helpers import now_iso

DB_FILENAME = "cortexhub.db"


class Database:
    """Tiny thread-safe wrapper around SQLite for storing chat messages."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.path.join(os.getcwd(), DB_FILENAME)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id   TEXT    NOT NULL,
                    model_name   TEXT    NOT NULL,
                    role         TEXT    NOT NULL,
                    message      TEXT    NOT NULL,
                    created_at   TEXT    NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session_model "
                "ON messages (session_id, model_name, id)"
            )
            self._conn.commit()

    def add_message(
        self,
        session_id: str,
        model_name: str,
        role: str,
        message: str,
    ) -> None:
        """Insert a message row. ``role`` is typically 'user' or 'assistant'."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO messages (session_id, model_name, role, message, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (session_id, model_name, role, message, now_iso()),
            )
            self._conn.commit()

    def get_history(
        self, session_id: str, model_name: str
    ) -> list[dict[str, str]]:
        """Return ordered history for a (session, model) pair as role/content dicts."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT role, message FROM messages "
                "WHERE session_id = ? AND model_name = ? "
                "ORDER BY id ASC",
                (session_id, model_name),
            )
            rows: Iterable[sqlite3.Row] = cur.fetchall()
        return [{"role": r["role"], "content": r["message"]} for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
