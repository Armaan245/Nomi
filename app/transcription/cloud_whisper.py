"""
Cloud Speech-to-Text service supporting Groq and OpenAI Whisper endpoints.
"""

import io
import wave
from typing import Optional
import numpy as np
import requests
from app.transcription.base import BaseTranscriptionService


class CloudWhisperService(BaseTranscriptionService):
    """Cloud API Whisper transcription (Groq / OpenAI)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        model: str = "whisper-large-v3-turbo"
    ):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()

    def _audio_to_wav_bytes(self, audio: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Convert float32 [-1.0, 1.0] numpy array into 16-bit PCM WAV bytes in memory."""
        # Scale to 16-bit signed integer
        scaled = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(scaled.tobytes())

        return buffer.getvalue()

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = "en"
    ) -> str:
        if len(audio) == 0:
            return ""

        if not self.api_key:
            raise ValueError("Cloud transcription API key is empty.")

        wav_bytes = self._audio_to_wav_bytes(audio, sample_rate)
        url = f"{self.base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        files = {
            "file": ("dictation.wav", wav_bytes, "audio/wav")
        }
        data = {
            "model": self.model,
            "response_format": "json"
        }
        if language:
            data["language"] = language

        resp = requests.post(url, headers=headers, files=files, data=data, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"Transcription API failed ({resp.status_code}): {resp.text}")

        res_json = resp.json()
        return res_json.get("text", "").strip()
