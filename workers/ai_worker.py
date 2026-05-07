"""Background worker that runs AI streams on its own asyncio event loop."""
from __future__ import annotations

import asyncio
import threading

from PySide6.QtCore import QThread, Signal

from ai.ai_manager import AIManager
from sessions.session_manager import MODEL_CLAUDE, MODEL_OPENAI


class AIWorker(QThread):
    """A QThread that owns an asyncio event loop.

    The UI thread submits prompts via :meth:`submit`. The worker streams from
    both AI models concurrently and emits Qt signals as chunks arrive, so the
    UI never blocks.
    """

    # model_name, chunk_text
    chunk_received = Signal(str, str)
    # model_name
    response_finished = Signal(str)
    # model_name, error_message
    error_occurred = Signal(str, str)
    # emitted once both models have finished (success or error)
    all_done = Signal()

    def __init__(self, ai_manager: AIManager, parent=None) -> None:
        super().__init__(parent)
        self._ai_manager = ai_manager
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = threading.Event()

    # --------------------------------------------------------------- lifecycle
    def run(self) -> None:  # runs in the worker thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        try:
            self._loop.run_forever()
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    def stop(self) -> None:
        """Stop the event loop and wait for the thread to exit."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait()

    # ------------------------------------------------------------------ submit
    def submit(self, prompt: str) -> None:
        """Schedule a new prompt to be streamed to both models."""
        self._ready.wait()
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(self._handle(prompt), self._loop)

    # ---------------------------------------------------------------- internal
    async def _handle(self, prompt: str) -> None:
        await asyncio.gather(
            self._stream_one(MODEL_OPENAI, prompt),
            self._stream_one(MODEL_CLAUDE, prompt),
        )
        self.all_done.emit()

    async def _stream_one(self, model_name: str, prompt: str) -> None:
        collected: list[str] = []
        try:
            async for chunk in self._ai_manager.stream(model_name, prompt):
                collected.append(chunk)
                self.chunk_received.emit(model_name, chunk)
            self._ai_manager.commit_assistant(model_name, "".join(collected))
            self.response_finished.emit(model_name)
        except Exception as exc:  # noqa: BLE001 - surface any provider error
            # Still persist whatever we managed to collect so context is kept.
            if collected:
                self._ai_manager.commit_assistant(model_name, "".join(collected))
            self.error_occurred.emit(model_name, str(exc))
