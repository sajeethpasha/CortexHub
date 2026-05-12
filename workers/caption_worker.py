"""Live-caption worker: captures system audio via WASAPI loopback and
transcribes in real-time using Vosk (fully offline).

On first use the small English model (~50 MB) is downloaded automatically to:
    <repo_root>/models/vosk-model-small-en-us-0.15/

Requirements (install once):
    pip install pyaudiowpatch vosk numpy
"""
from __future__ import annotations

import json
import pathlib
import threading
import urllib.request
import zipfile

import numpy as np
from PySide6.QtCore import QThread, Signal

_MODEL_NAME = "vosk-model-small-en-us-0.15"
_MODEL_URL = f"https://alphacephei.com/vosk/models/{_MODEL_NAME}.zip"
_MODEL_DIR = pathlib.Path(__file__).parent.parent / "models"
_MODEL_PATH = _MODEL_DIR / _MODEL_NAME
_VOSK_RATE = 16_000
_CHUNK = 8192


def _to_mono(data: bytes, channels: int) -> bytes:
    """Mix multichannel PCM int16 down to mono."""
    if channels == 1:
        return data
    audio = np.frombuffer(data, dtype=np.int16).reshape(-1, channels)
    return audio.mean(axis=1).astype(np.int16).tobytes()


def _resample(data: bytes, from_rate: int, to_rate: int) -> bytes:
    """Linear-interpolation resample of mono int16 PCM."""
    if from_rate == to_rate:
        return data
    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    n = int(len(audio) * to_rate / from_rate)
    if n == 0:
        return b""
    resampled = np.interp(
        np.linspace(0, len(audio) - 1, n),
        np.arange(len(audio)),
        audio,
    ).astype(np.int16)
    return resampled.tobytes()


class CaptionWorker(QThread):
    """Background thread that streams live captions from system audio.

    Usage:
        worker.start_caption()   # begin capture & recognition
        worker.stop_caption()    # stop (thread exits cleanly)

    Signals:
        text_ready(str)        – final recognised sentence (append to prompt)
        status_changed(str)    – human-readable status / error message
    """

    text_ready = Signal(str)
    status_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ public

    def start_caption(self) -> None:
        self._stop_event.clear()
        if not self.isRunning():
            self.start()

    def stop_caption(self) -> None:
        self._stop_event.set()

    # ----------------------------------------------------------------- QThread

    def run(self) -> None:
        try:
            self._do_run()
        except Exception as exc:  # noqa: BLE001
            self.status_changed.emit(f"Error: {exc}")

    # ----------------------------------------------------------------- private

    def _do_run(self) -> None:
        # ── check imports ──────────────────────────────────────────────────
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel  # type: ignore
            SetLogLevel(-1)
        except ImportError:
            self.status_changed.emit(
                "Error: vosk not installed — run: pip install vosk"
            )
            return

        try:
            import pyaudiowpatch as pyaudio  # type: ignore
        except ImportError:
            self.status_changed.emit(
                "Error: pyaudiowpatch not installed — run: pip install pyaudiowpatch"
            )
            return

        # ── download / load model ──────────────────────────────────────────
        if not _MODEL_PATH.exists():
            self.status_changed.emit("Downloading speech model (~50 MB)…")
            _MODEL_DIR.mkdir(parents=True, exist_ok=True)
            zip_path = _MODEL_DIR / f"{_MODEL_NAME}.zip"
            try:
                urllib.request.urlretrieve(_MODEL_URL, zip_path)
                self.status_changed.emit("Extracting model…")
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(_MODEL_DIR)
                zip_path.unlink(missing_ok=True)
            except Exception as exc:
                self.status_changed.emit(f"Error downloading model: {exc}")
                return

        self.status_changed.emit("Loading model…")
        try:
            model = Model(str(_MODEL_PATH))
        except Exception as exc:
            self.status_changed.emit(f"Error loading model: {exc}")
            return

        # ── find WASAPI loopback device ────────────────────────────────────
        pa = pyaudio.PyAudio()
        device_info = None
        try:
            wasapi_info = pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out = pa.get_device_info_by_index(
                wasapi_info["defaultOutputDevice"]
            )
            # Prefer loopback that matches the default output device
            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                if d.get("isLoopbackDevice", False) and default_out["name"] in d["name"]:
                    device_info = d
                    break
            # Fall back to any loopback device
            if device_info is None:
                for i in range(pa.get_device_count()):
                    d = pa.get_device_info_by_index(i)
                    if d.get("isLoopbackDevice", False):
                        device_info = d
                        break
        except Exception as exc:
            self.status_changed.emit(f"Error finding audio device: {exc}")
            pa.terminate()
            return

        if device_info is None:
            self.status_changed.emit(
                "Error: No loopback audio device found. "
                "Make sure you are on Windows and audio is playing."
            )
            pa.terminate()
            return

        native_rate = int(device_info["defaultSampleRate"])
        channels = max(1, min(int(device_info.get("maxInputChannels", 2)), 2))
        rec = KaldiRecognizer(model, _VOSK_RATE)
        rec.SetWords(False)

        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=native_rate,
                input=True,
                input_device_index=int(device_info["index"]),
                frames_per_buffer=_CHUNK,
            )
        except Exception as exc:
            self.status_changed.emit(f"Error opening audio stream: {exc}")
            pa.terminate()
            return

        self.status_changed.emit("● Live Caption ON")

        try:
            while not self._stop_event.is_set():
                try:
                    raw = stream.read(_CHUNK, exception_on_overflow=False)
                except Exception:
                    continue

                mono = _to_mono(raw, channels)
                resampled = _resample(mono, native_rate, _VOSK_RATE)
                if not resampled:
                    continue

                if rec.AcceptWaveform(resampled):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        self.text_ready.emit(text + " ")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            self.status_changed.emit("● Live Caption OFF")
