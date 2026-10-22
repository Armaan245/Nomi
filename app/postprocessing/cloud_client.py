"""
Cloud LLM post-processing client supporting Groq and OpenAI chat completions.
"""

import requests
from typing import Optional, List
from app.postprocessing.prompt import (
    DEFAULT_DICTATION_SYSTEM_PROMPT,
    COMMAND_MODE_SYSTEM_PROMPT,
    build_dictation_user_prompt,
    build_command_mode_user_prompt,
)


class CloudPostProcessor:
    """Client for Groq / OpenAI LLM post-processing."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        model: str = "llama-3.3-70b-versatile"
    ):
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()

    def clean_dictation(
        self,
        transcript: str,
        active_app: Optional[str] = None,
        active_window_title: Optional[str] = None,
        vocabulary: Optional[List[str]] = None,
        timeout: float = 10.0
    ) -> str:
        if not transcript or not transcript.strip():
            return ""

        if not self.api_key:
            return transcript

        user_content = build_dictation_user_prompt(
            transcript=transcript,
            active_app=active_app,
            active_window_title=active_window_title,
            vocabulary=vocabulary
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": DEFAULT_DICTATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            if resp.status_code != 200:
                print(f"[CloudLLM] Request failed: {resp.text}")
                return transcript

            data = resp.json()
            cleaned = data["choices"][0]["message"]["content"].strip()
            if cleaned == "EMPTY" or not cleaned:
                return ""
            if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
                cleaned = cleaned[1:-1].strip()
            return cleaned
        except Exception as e:
            print(f"[CloudLLM] Error: {e}")
            return transcript

    def transform_selection(
        self,
        selected_text: str,
        voice_command: str,
        active_app: Optional[str] = None,
        vocabulary: Optional[List[str]] = None,
        timeout: float = 10.0
    ) -> str:
        if not selected_text or not voice_command:
            return selected_text

        if not self.api_key:
            return selected_text

        user_content = build_command_mode_user_prompt(
            selected_text=selected_text,
            voice_command=voice_command,
            active_app=active_app,
            vocabulary=vocabulary
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": COMMAND_MODE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout
            )
            if resp.status_code != 200:
                return selected_text

            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[CloudLLM] Edit mode error: {e}")
            return selected_text
