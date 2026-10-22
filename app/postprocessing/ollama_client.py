"""
Local Ollama post-processing client.
Runs 100% offline via the local Ollama daemon (e.g. llama3.2).
"""

import requests
from typing import Optional, List
from app.postprocessing.prompt import (
    DEFAULT_DICTATION_SYSTEM_PROMPT,
    COMMAND_MODE_SYSTEM_PROMPT,
    build_dictation_user_prompt,
    build_command_mode_user_prompt,
)


class OllamaPostProcessor:
    """Client for local Ollama post-processing."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:latest"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def clean_dictation(
        self,
        transcript: str,
        active_app: Optional[str] = None,
        active_window_title: Optional[str] = None,
        vocabulary: Optional[List[str]] = None,
        timeout: float = 15.0
    ) -> str:
        """Process raw speech-to-text transcript through local Ollama."""
        if not transcript or not transcript.strip():
            return ""

        user_content = build_dictation_user_prompt(
            transcript=transcript,
            active_app=active_app,
            active_window_title=active_window_title,
            vocabulary=vocabulary
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": DEFAULT_DICTATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            }
        }

        try:
            url = f"{self.base_url}/api/chat"
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code != 200:
                print(f"[Ollama] Request failed ({resp.status_code}): {resp.text}")
                return transcript

            data = resp.json()
            cleaned = data.get("message", {}).get("content", "").strip()

            if cleaned == "EMPTY" or not cleaned:
                return ""

            # Strip accidental surrounding quotes if present
            if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
                cleaned = cleaned[1:-1].strip()

            return cleaned

        except Exception as e:
            print(f"[Ollama] Fallback to raw transcript due to error: {e}")
            return transcript

    def transform_selection(
        self,
        selected_text: str,
        voice_command: str,
        active_app: Optional[str] = None,
        vocabulary: Optional[List[str]] = None,
        timeout: float = 15.0
    ) -> str:
        """Transform highlighted text according to spoken voice command."""
        if not selected_text or not voice_command:
            return selected_text

        user_content = build_command_mode_user_prompt(
            selected_text=selected_text,
            voice_command=voice_command,
            active_app=active_app,
            vocabulary=vocabulary
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": COMMAND_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            }
        }

        try:
            url = f"{self.base_url}/api/chat"
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code != 200:
                return selected_text

            data = resp.json()
            transformed = data.get("message", {}).get("content", "").strip()
            return transformed if transformed else selected_text

        except Exception as e:
            print(f"[Ollama] Edit mode failed: {e}")
            return selected_text

    @staticmethod
    def get_installed_models(base_url: str = "http://localhost:11434") -> List[str]:
        """Fetch list of models currently pulled in local Ollama."""
        try:
            r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
        return []
