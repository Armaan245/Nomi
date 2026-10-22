"""
Voice Activity Detection (VAD) and silence trimming utilities.
Prevents Whisper hallucinations on empty microphone background noise.
"""

import numpy as np


def trim_silence(
    audio: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.002,
    padding_seconds: float = 0.2
) -> np.ndarray:
    """
    Trim leading and trailing silence from audio based on amplitude energy.
    Keeps generous padding to avoid clipping the start or end of words.
    """
    if len(audio) == 0:
        return audio

    frame_len = int(sample_rate * 0.02)
    num_frames = len(audio) // frame_len

    if num_frames == 0:
        return audio

    energy = np.array([
        np.sqrt(np.mean(audio[i * frame_len : (i + 1) * frame_len] ** 2))
        for i in range(num_frames)
    ])

    active_indices = np.where(energy > threshold)[0]
    if len(active_indices) == 0:
        # If below threshold, still return original rather than discarding
        return audio

    start_frame = active_indices[0]
    end_frame = active_indices[-1]

    pad_frames = int(padding_seconds / 0.02)
    start_frame = max(0, start_frame - pad_frames)
    end_frame = min(num_frames - 1, end_frame + pad_frames)

    start_sample = start_frame * frame_len
    end_sample = min(len(audio), (end_frame + 1) * frame_len)

    trimmed = audio[start_sample:end_sample]
    return trimmed if len(trimmed) > 0 else audio


def has_speech(audio: np.ndarray, threshold: float = 0.0005, min_duration_sec: float = 0.2) -> bool:
    """Check if audio has minimum required length and non-zero sound."""
    if len(audio) < 16000 * min_duration_sec:
        return False
    rms = float(np.sqrt(np.mean(audio**2)))
    return rms >= threshold
