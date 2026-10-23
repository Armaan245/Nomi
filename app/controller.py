"""
Central Controller for Nomi Windows.
Orchestrates Hotkeys, Audio Recording, Context Detection,
Speech Transcription, LLM Post-Processing, and Auto-Pasting.
"""

import time
import threading
from datetime import datetime
from typing import Optional
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from app.config import app_config
from app.audio.recorder import AudioRecorder
from app.audio.vad import trim_silence, has_speech
from app.transcription.local_whisper import LocalWhisperService
from app.transcription.cloud_whisper import CloudWhisperService
from app.postprocessing.ollama_client import OllamaPostProcessor
from app.postprocessing.cloud_client import CloudPostProcessor
from app.system.context import SystemContextService
from app.system.paster import TextPaster
from app.system.hotkey import GlobalHotkeyManager
from app.ui.pill_overlay import PillOverlay
from app.ui.tray_icon import SystemTrayManager
from app.ui.settings_window import SettingsWindow


class AppController(QObject):
    """Coordinates all subsystems of the Nomi application."""

    # Thread-safe GUI signals
    signal_set_state_listening = pyqtSignal()
    signal_update_live_text = pyqtSignal(str)
    signal_set_state_transcribing = pyqtSignal()
    signal_set_state_polishing = pyqtSignal()
    signal_set_state_pasted = pyqtSignal(str)
    signal_set_state_cancelled = pyqtSignal(str)
    signal_add_history = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # UI Components
        self.pill = PillOverlay()
        self.tray = SystemTrayManager()
        self.settings_window = SettingsWindow()

        # Connect thread-safe signals to Pill UI
        self.signal_set_state_listening.connect(self.pill.set_state_listening)
        self.signal_update_live_text.connect(self.pill.update_live_text)
        self.signal_set_state_transcribing.connect(self.pill.set_state_transcribing)
        self.signal_set_state_polishing.connect(self.pill.set_state_polishing)
        self.signal_set_state_pasted.connect(self.pill.set_state_pasted)
        self.signal_set_state_cancelled.connect(self.pill.set_state_cancelled)
        self.signal_add_history.connect(self.settings_window.add_history_entry)

        # Live speech streaming timer
        from PyQt6.QtCore import QTimer
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(480)
        self._live_timer.timeout.connect(self._on_live_stream_tick)
        self._live_worker_busy = False
        self._last_stream_samples = 0
        self._latest_live_text = ""

        # Audio Recorder
        dev_idx = app_config.get("input_device_index")
        gain = app_config.get("mic_gain", 1.0)
        self.recorder = AudioRecorder(device_index=dev_idx, gain=gain)
        self.recorder.audio_level_updated.connect(self.pill.update_volume)

        # Global Hotkey Manager
        mode = app_config.get("hotkey_mode", "both")
        hold_k = app_config.get("hold_hotkey", "alt_r")
        toggle_k = app_config.get("toggle_hotkey", "f8")
        self.hotkey_mgr = GlobalHotkeyManager(mode=mode, hold_key_name=hold_k, toggle_key_name=toggle_k)

        self.hotkey_mgr.hold_start_signal.connect(self.start_dictation)
        self.hotkey_mgr.hold_stop_signal.connect(self.stop_dictation)
        self.hotkey_mgr.toggle_signal.connect(self.toggle_dictation)
        self.hotkey_mgr.cancel_signal.connect(self.cancel_dictation)

        # Tray connections
        self.tray.open_settings_requested.connect(self._show_settings)
        self.tray.open_notes_requested.connect(self._show_notes)
        self.tray.open_tasks_requested.connect(self._show_tasks)
        self.tray.open_history_requested.connect(self._show_history)
        self.tray.toggle_hotkeys_requested.connect(self.hotkey_mgr.set_enabled)
        self.tray.quit_requested.connect(self.quit_app)

        # Settings connections
        self.settings_window.settings_changed.connect(self._apply_settings_update)
        self.settings_window.reset_position_requested.connect(self.pill.reset_position)

        # Services
        self._local_whisper = LocalWhisperService(
            model_name=app_config.get("whisper_model", "tiny.en"),
            device=app_config.get("whisper_device", "cpu"),
            compute_type=app_config.get("whisper_compute_type", "int8")
        )
        self._local_whisper.preload()

        self._ollama_processor = OllamaPostProcessor(
            base_url=app_config.get("ollama_url", "http://localhost:11434"),
            model=app_config.get("ollama_model", "llama3.2:latest")
        )

        # Session State
        self._is_active = False
        self._active_app_name = ""
        self._active_window_title = ""
        self._target_hwnd = 0

        # Start hotkey listener
        self.hotkey_mgr.start()
        print("[Controller] Nomi initialized and ready.")

    def _show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _show_notes(self):
        self.settings_window.switch_page(1)  # Smart Notes Studio
        self._show_settings()

    def _show_tasks(self):
        self.settings_window.switch_page(2)  # Tasks & Calendar
        self._show_settings()

    def _show_history(self):
        self.settings_window.switch_page(8)  # History page in sidebar
        self._show_settings()

    def _open_memory_query(self, query: str):
        self.settings_window.switch_page(3)  # Ask Memory
        self._show_settings()
        if hasattr(self.settings_window, 'txt_memory_query'):
            self.settings_window.txt_memory_query.setText(query)
            self.settings_window._ask_memory()

    def _apply_settings_update(self):
        """Update runtime components with fresh settings."""
        mode = app_config.get("hotkey_mode", "both")
        hold_k = app_config.get("hold_hotkey", "alt_r")
        toggle_k = app_config.get("toggle_hotkey", "f8")
        self.hotkey_mgr.set_config(mode=mode, hold_key=hold_k, toggle_key=toggle_k)

        dev_idx = app_config.get("input_device_index")
        self.recorder.set_device(dev_idx)
        self.recorder.set_gain(app_config.get("mic_gain", 1.0))

        # Update whisper model
        self._local_whisper = LocalWhisperService(
            model_name=app_config.get("whisper_model", "tiny.en"),
            device=app_config.get("whisper_device", "cpu"),
            compute_type=app_config.get("whisper_compute_type", "int8")
        )
        self._ollama_processor = OllamaPostProcessor(
            base_url=app_config.get("ollama_url", "http://localhost:11434"),
            model=app_config.get("ollama_model", "llama3.2:latest")
        )
        print("[Controller] Settings applied.")

    # ------------------ Dictation Lifecycle ------------------

    @pyqtSlot()
    def start_dictation(self):
        """Triggered when the user initiates dictation."""
        if self._is_active:
            return

        self._is_active = True

        # Capture context of foreground application
        title, proc_name, hwnd = SystemContextService.get_active_window_info()
        self._active_window_title = title
        self._active_app_name = proc_name
        self._target_hwnd = hwnd

        print(f"[Controller] Dictation started! Target App: '{proc_name}', Window: '{title}' (HWND: {hwnd})")

        # Show Notch / Pill Visualizer
        self.signal_set_state_listening.emit()

        # Reset streaming state
        self._last_stream_samples = 0
        self._latest_live_text = ""
        self._live_worker_busy = False

        # Start microphone recording
        started = self.recorder.start()
        if not started:
            print("[Controller] Failed to start audio recorder!")
            self.signal_set_state_cancelled.emit("Mic Error")
            self._is_active = False
            return

        # Start live transcription timer if enabled
        if app_config.get("live_transcription_enabled", True):
            self._live_timer.start()

    @pyqtSlot()
    def stop_dictation(self):
        """Triggered when user releases the hold key or completes toggle."""
        if not self._is_active:
            return

        self._is_active = False
        self._live_timer.stop()

        # Stop microphone
        audio_data = self.recorder.stop()
        if audio_data is None or len(audio_data) == 0:
            print("[Controller] Audio buffer is empty.")
            self.signal_set_state_cancelled.emit("No audio")
            return

        duration_sec = round(len(audio_data) / 16000.0, 2)
        print(f"[Controller] Dictation stopped. Recorded {len(audio_data)} samples ({duration_sec}s).")

        # Check if audio has minimum duration and speech energy
        threshold = float(app_config.get("audio_energy_threshold", 0.005)) * 0.1
        if not has_speech(audio_data, threshold=threshold):
            print("[Controller] Audio was too quiet or too short (< 0.2s).")
            self.signal_set_state_cancelled.emit("Too quiet")
            return

        # Advance pill state to transcribing
        self.signal_set_state_transcribing.emit()

        # Run pipeline in background worker thread
        threading.Thread(
            target=self._process_pipeline_worker,
            args=(audio_data, self._active_app_name, self._active_window_title, self._target_hwnd),
            daemon=True
        ).start()

    @pyqtSlot()
    def toggle_dictation(self):
        """Toggle dictation on/off."""
        if self._is_active:
            self.stop_dictation()
        else:
            self.start_dictation()

    @pyqtSlot()
    def cancel_dictation(self):
        """Cancel current session immediately without processing or pasting."""
        if not self._is_active:
            return
        print("[Controller] Session cancelled by user.")
        self._is_active = False
        self._live_timer.stop()
        self.recorder.stop()
        self.signal_set_state_cancelled.emit("Cancelled")

    def _on_live_stream_tick(self):
        """Periodic tick to transcribe accumulating microphone audio and stream live text to the notch."""
        if not self._is_active or self._live_worker_busy:
            return

        audio = self.recorder.get_current_audio()
        if audio is None or len(audio) < 16000 * 0.45:
            return

        # Check if meaningful new audio arrived (> 0.25s)
        if (len(audio) - self._last_stream_samples) < 16000 * 0.25:
            return

        self._last_stream_samples = len(audio)
        self._live_worker_busy = True

        def _worker(audio_chunk: np.ndarray):
            try:
                partial = self._local_whisper.transcribe(audio_chunk)
                if self._is_active and partial:
                    self._latest_live_text = partial
                    self.signal_update_live_text.emit(partial)
            except Exception as e:
                print(f"[Controller] Live streaming preview tick error: {e}")
            finally:
                self._live_worker_busy = False

        threading.Thread(target=_worker, args=(audio,), daemon=True).start()

    def _process_pipeline_worker(
        self,
        audio_data: np.ndarray,
        active_app: str,
        active_title: str,
        target_hwnd: int
    ):
        """Worker thread executing STT, LLM post-processing, and auto-pasting."""
        try:
            # 1. Silence trimming
            energy_th = float(app_config.get("audio_energy_threshold", 0.005)) * 0.4
            trimmed_audio = trim_silence(audio_data, threshold=energy_th)
            if len(trimmed_audio) == 0:
                trimmed_audio = audio_data

            # 2. Transcription (STT)
            print(f"[Pipeline] Running Faster-Whisper on {len(trimmed_audio)} audio samples...")
            raw_transcript = ""
            groq_key = app_config.get("groq_api_key", "").strip()

            if groq_key and app_config.get("transcription_provider") == "groq":
                try:
                    cloud_stt = CloudWhisperService(
                        api_key=groq_key,
                        base_url="https://api.groq.com/openai/v1",
                        model=app_config.get("groq_whisper_model", "whisper-large-v3-turbo")
                    )
                    raw_transcript = cloud_stt.transcribe(trimmed_audio)
                except Exception as e:
                    print(f"[Pipeline] Cloud STT failed ({e}), falling back to local Whisper...")
                    raw_transcript = self._local_whisper.transcribe(trimmed_audio)
            else:
                raw_transcript = self._local_whisper.transcribe(trimmed_audio)

            raw_transcript = raw_transcript.strip()
            if not raw_transcript:
                print("[Pipeline] Speech recognition returned empty text.")
                self.signal_set_state_cancelled.emit("Empty transcript")
                return

            print(f"[Pipeline] Whisper recognized: '{raw_transcript}'")

            # 3. Post-Processing (LLM Cleanup & Context-Aware Formatting)
            final_text = raw_transcript
            if app_config.get("postprocessing_enabled", True):
                self.signal_set_state_polishing.emit()
                print(f"[Pipeline] Polishing with Ollama model '{self._ollama_processor.model}'...")

                vocab = app_config.get("custom_vocabulary", [])

                if groq_key and app_config.get("postprocessing_provider") == "groq":
                    cloud_llm = CloudPostProcessor(
                        api_key=groq_key,
                        base_url="https://api.groq.com/openai/v1",
                        model=app_config.get("groq_model", "llama-3.3-70b-versatile")
                    )
                    final_text = cloud_llm.clean_dictation(
                        transcript=raw_transcript,
                        active_app=active_app,
                        active_window_title=active_title,
                        vocabulary=vocab
                    )
                else:
                    final_text = self._ollama_processor.clean_dictation(
                        transcript=raw_transcript,
                        active_app=active_app,
                        active_window_title=active_title,
                        vocabulary=vocab
                    )

            final_text = final_text.strip()
            print(f"[Pipeline] Final Cleaned Text: '{final_text}'")

            if not final_text:
                self.signal_set_state_cancelled.emit("Empty output")
                return

            # 4. Autonomous Command Mode Check (Calendar, Tasks, Reminders, Q&A)
            if app_config.get("command_mode", True):
                from app.services.intent_agent import IntentAgent
                intent_data = IntentAgent.analyze_intent(final_text)
                intent_type = intent_data.get("intent")

                if intent_type in ("SCHEDULE_EVENT", "CREATE_TASK"):
                    action_result = IntentAgent.execute_action(intent_data)
                    self.signal_set_state_pasted.emit(action_result)
                    timestamp_str = datetime.now().strftime("%H:%M:%S")
                    self.signal_add_history.emit(
                        active_app,
                        raw_transcript,
                        f"[{intent_type}] {action_result}",
                        timestamp_str
                    )
                    # Refresh studio tasks table if settings window is active
                    if hasattr(self.settings_window, '_refresh_tasks_table'):
                        self.settings_window._refresh_tasks_table()
                    return

                elif intent_type == "QUERY_MEMORY":
                    self.signal_set_state_pasted.emit("Memory Q&A")
                    timestamp_str = datetime.now().strftime("%H:%M:%S")
                    self.signal_add_history.emit(
                        active_app,
                        raw_transcript,
                        f"[Memory Query] {intent_data.get('query', final_text)}",
                        timestamp_str
                    )
                    query = intent_data.get("query", final_text)
                    QTimer.singleShot(100, lambda: self._open_memory_query(query))
                    return

            # 5. Direct Cursor Injection with Bliss (SendInput Unicode)
            if app_config.get("auto_paste", True):
                self.signal_set_state_pasted.emit(final_text)
                mode = app_config.get("typing_mode", "direct")
                speed_ms = app_config.get("typing_speed_ms", 0)
                restore_clip = app_config.get("restore_clipboard", True)
                delay_ms = app_config.get("paste_delay_ms", 70)
                print(f"[Pipeline] Typing text directly at cursor (HWND: {target_hwnd}, mode: '{mode}', speed: {speed_ms}ms)...")
                injected = TextPaster.inject_text(
                    final_text,
                    target_hwnd=target_hwnd,
                    mode=mode,
                    speed_ms=speed_ms,
                    restore_clipboard=restore_clip,
                    delay_ms=delay_ms
                )
                print(f"[Pipeline] Cursor injection completed: {injected}")
            else:
                self.signal_set_state_pasted.emit("Copied!")
                import pyperclip
                pyperclip.copy(final_text)

            # 5. Log to History
            timestamp_str = datetime.now().strftime("%H:%M:%S")
            self.signal_add_history.emit(
                active_app,
                raw_transcript,
                final_text,
                timestamp_str
            )

        except Exception as e:
            print(f"[Pipeline] Error in processing worker: {e}")
            import traceback
            traceback.print_exc()
            self.signal_set_state_cancelled.emit("Error")

    def quit_app(self):
        """Clean shutdown of background threads and application."""
        print("[Nomi] Shutting down...")
        self.hotkey_mgr.stop()
        if self.recorder.is_recording:
            self.recorder.stop()
        self.pill.close()
        self.settings_window.close()
        self.tray.tray_icon.hide()
        import sys
        sys.exit(0)
