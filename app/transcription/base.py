"""
Base interface for transcription providers.
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseTranscriptionService(ABC):
    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000, language: Optional[str] = "en") -> str:
        """
        Transcribe a 1D float32 numpy audio array.
        Returns transcribed text.
        """
        pass
