"""
Configuration management for Nomi Windows.
Handles loading, saving, and defaults stored in ~/.nomi/config.json.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

CONFIG_DIR = Path.home() / ".nomi"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    # Hotkeys
    "hotkey_mode": "both",               # "both", "hold", or "toggle"
    "hold_hotkey": "alt_r",              # Right Alt by default
    "toggle_hotkey": "f8",               # Tap F8 to start/stop
    "cancel_hotkey": "esc",              # Tap Escape to cancel active recording

    # Audio
    "sample_rate": 16000,
    "input_device_index": None,          # None = system default
    "audio_energy_threshold": 0.005,     # Silence / Voice activity threshold
    "mic_gain": 1.0,                     # Microphone pickup range / volume multiplier (0.5x - 3.0x)
    "sound_effects": True,

    # Transcription
    "transcription_provider": "local_whisper",  # "local_whisper", "groq", "openai"
    "whisper_model": "tiny.en",                 # "tiny.en", "base.en", "small.en", "small", "medium"
    "whisper_device": "cpu",                    # "cpu" or "cuda"
    "whisper_compute_type": "int8",             # "int8", "float16", "float32"
    "transcription_language": "en",

    # Post-Processing (Context-aware cleanup & LLM)
    "postprocessing_enabled": True,             # If False, pastes raw whisper transcript instantly
    "postprocessing_provider": "ollama",        # "ollama", "groq", "openai"
    "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.2:latest",

    # Cloud Fallbacks / Providers
    "groq_api_key": "",
    "groq_model": "llama-3.3-70b-versatile",
    "groq_whisper_model": "whisper-large-v3-turbo",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "openai_base_url": "https://api.openai.com/v1",

    # Context, Command & Edit Mode
    "context_aware": True,                      # Read active window title & process name
    "command_mode": True,                       # Autonomous Command Mode (Calendar, Tasks, Reminders)
    "edit_mode_enabled": False,                 # Transform selected text with voice instruction (enable in settings if needed)
    "custom_vocabulary": [
        "Wispr",
        "Nomi",
        "Python",
        "PyQt6",
        "Ollama",
        "API",
        "LLM",
        "JSON",
        "Git",
        "GitHub"
    ],

    # Output, Typing & Pasting
    "auto_paste": True,                         # Auto-insert into active cursor
    "typing_mode": "direct",                    # "direct" (SendInput Unicode cursor typing with bliss), "smooth" (typewriter flow), "clipboard"
    "typing_speed_ms": 0,                       # Typing delay in ms (0 = instant bliss, 4 = smooth typewriter)
    "live_transcription_enabled": True,         # Live real-time preview of spoken text in floating notch
    "restore_clipboard": True,                  # Restore prior clipboard contents if clipboard paste is used
    "paste_delay_ms": 70,                       # Delay before sending Ctrl+V (clipboard mode)

    # UI Preferences
    "overlay_position": "bottom_center",        # "bottom_center", "top_center", "bottom_right"
    "theme": "dark_modern",
    "history_limit": 50,
}


class ConfigManager:
    """Manages application settings with JSON persistence."""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        """Load settings from config file or initialize default."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")
        else:
            self.save()

    def save(self) -> None:
        """Save settings to config file."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save()

    def add_vocabulary(self, term: str) -> bool:
        term = term.strip()
        if not term:
            return False
        vocab: List[str] = self.config.get("custom_vocabulary", [])
        if term not in vocab:
            vocab.append(term)
            self.config["custom_vocabulary"] = vocab
            self.save()
            return True
        return False

    def remove_vocabulary(self, term: str) -> bool:
        vocab: List[str] = self.config.get("custom_vocabulary", [])
        if term in vocab:
            vocab.remove(term)
            self.config["custom_vocabulary"] = vocab
            self.save()
            return True
        return False

    def load_history(self) -> List[Dict[str, Any]]:
        """Load persistent transcription history."""
        history_file = CONFIG_DIR / "history.json"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Config] Error loading history: {e}")
        return []

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        """Save transcription history to disk."""
        history_file = CONFIG_DIR / "history.json"
        try:
            limit = self.get("history_limit", 100)
            trimmed = history[-limit:] if len(history) > limit else history
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(trimmed, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving history: {e}")


# Global singleton instance
app_config = ConfigManager()
