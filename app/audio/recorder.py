"""
Audio recording module using sounddevice.
Captures microphone audio at 16kHz mono with live volume/waveform streaming.
"""

import threading
import numpy as np
import sounddevice as sd
from typing import Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal


class AudioRecorder(QObject):
    """
    Asynchronous microphone recorder emitting live volume levels
    and returning normalized audio buffers for speech-to-text.
    """
    # Signal emitted with (rms_level, raw_waveform_chunk)
    audio_level_updated = pyqtSignal(float, list)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, sample_rate: int = 16000, device_index: Optional[int] = None, gain: float = 1.0):
        super().__init__()
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.gain = gain
        self._is_recording = False
        self._stream: Optional[sd.InputStream] = None
        self._frames: List[np.ndarray] = []
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def set_device(self, device_index: Optional[int]) -> None:
        """Update active input device."""
        self.device_index = device_index

    def set_gain(self, gain: float) -> None:
        """Update microphone software gain / pickup range (0.2x to 4.0x)."""
        self.gain = max(0.1, min(4.0, float(gain)))

    def start(self) -> bool:
        """Start recording from the microphone."""
        if self._is_recording:
            return False

        with self._lock:
            self._frames.clear()
            self._is_recording = True

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device_index,
                blocksize=1024,
                callback=self._audio_callback
            )
            self._stream.start()
            self.recording_started.emit()
            return True
        except Exception as e:
            print(f"[AudioRecorder] Error starting stream: {e}")
            self._is_recording = False
            return False

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return the complete audio as a 1D float32 numpy array."""
        if not self._is_recording:
            return None

        self._is_recording = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"[AudioRecorder] Error stopping stream: {e}")
            finally:
                self._stream = None

        self.recording_stopped.emit()

        with self._lock:
            if not self._frames:
                return None
            audio_data = np.concatenate(self._frames, axis=0).flatten()
            self._frames.clear()

        # Check if duration is too short (< 0.25 seconds)
        duration = len(audio_data) / self.sample_rate
        if duration < 0.25:
            return None

        return audio_data

    def get_current_audio(self) -> Optional[np.ndarray]:
        """Return a snapshot of recorded audio so far without stopping the recording."""
        if not self._is_recording:
            return None
        with self._lock:
            if not self._frames:
                return None
            return np.concatenate(self._frames, axis=0).flatten()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Callback invoked by sounddevice when audio is received."""
        if not self._is_recording:
            return

        chunk = indata.copy()
        if self.gain != 1.0:
            chunk = np.clip(chunk * self.gain, -1.0, 1.0)

        with self._lock:
            self._frames.append(chunk)

        # Calculate Root Mean Square (RMS) energy level
        rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0

        # Downsample waveform to 16 points for UI visualization
        sub_samples = chunk.flatten()
        if len(sub_samples) >= 16:
            indices = np.linspace(0, len(sub_samples) - 1, 16, dtype=int)
            waveform_preview = [float(abs(sub_samples[i])) for i in indices]
        else:
            waveform_preview = [0.0] * 16

        self.audio_level_updated.emit(rms, waveform_preview)

    @staticmethod
    def get_input_devices() -> List[dict]:
        """List all available audio input devices."""
        devices = []
        try:
            device_list = sd.query_devices()
            for idx, dev in enumerate(device_list):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": dev.get("name", f"Device {idx}"),
                        "channels": dev.get("max_input_channels", 1),
                        "default_samplerate": dev.get("default_samplerate", 16000),
                        "hostapi": dev.get("hostapi", 0)
                    })
        except Exception as e:
            print(f"[AudioRecorder] Error querying devices: {e}")
        return devices
