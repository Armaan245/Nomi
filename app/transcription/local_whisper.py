"""
Local Speech-to-Text service using Faster-Whisper.
Runs completely offline with high CPU/GPU efficiency and int8 quantization.
"""

import threading
from typing import Optional
import numpy as np
from faster_whisper import WhisperModel
from app.transcription.base import BaseTranscriptionService


class LocalWhisperService(BaseTranscriptionService):
    """Offline Faster-Whisper transcription engine."""

    _cached_model: Optional[WhisperModel] = None
    _cached_model_name: Optional[str] = None
    _cached_device: Optional[str] = None
    _cached_compute_type: Optional[str] = None
    _model_lock = threading.Lock()
    _inference_lock = threading.Lock()

    def __init__(
        self,
        model_name: str = "tiny.en",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type

    def _get_model(self) -> WhisperModel:
        with self._model_lock:
            if (
                LocalWhisperService._cached_model is None
                or LocalWhisperService._cached_model_name != self.model_name
                or LocalWhisperService._cached_device != self.device
                or LocalWhisperService._cached_compute_type != self.compute_type
            ):
                print(f"[Whisper] Loading local model '{self.model_name}' on {self.device} ({self.compute_type})...")
                LocalWhisperService._cached_model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
                LocalWhisperService._cached_model_name = self.model_name
                LocalWhisperService._cached_device = self.device
                LocalWhisperService._cached_compute_type = self.compute_type
                print("[Whisper] Model loaded successfully.")

            return LocalWhisperService._cached_model

    def preload(self) -> None:
        """Preload the model in background thread so the first dictation is instant."""
        threading.Thread(target=self._get_model, daemon=True).start()

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = "en"
    ) -> str:
        """
        Transcribe audio array using Faster-Whisper.
        audio: 1D float32 numpy array normalized to [-1.0, 1.0].
        """
        if len(audio) == 0:
            return ""

        model = self._get_model()
        with self._inference_lock:
            # faster-whisper expects 16kHz float32 audio
            segments, info = model.transcribe(
                audio,
                beam_size=1,            # 1 for maximum speed, 3 for higher accuracy
                language=language,
                temperature=0.0,
                vad_filter=True,        # Built-in Silero VAD to eliminate silence
                vad_parameters=dict(min_silence_duration_ms=400)
            )

            text_pieces = []
            for segment in segments:
                t = segment.text.strip()
                if t:
                    text_pieces.append(t)

            return " ".join(text_pieces).strip()
