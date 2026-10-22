"""
AI-Powered Lecture & Smart Notes Processor.
Transforms raw spoken transcripts into structured educational & meeting notes:
- Title
- Topic Summary
- Key Concepts
- Definitions & Formulas
- Important Points
- Revision Questions
- Action Items & Deadlines
"""

import json
import re
from typing import Dict, Any, List
from app.config import app_config
from app.postprocessing.ollama_client import OllamaPostProcessor


LECTURE_NOTES_SYSTEM_PROMPT = """You are Nomi AI, an advanced context-aware assistant specializing in academic and professional speech structuring.
The user just finished recording a lecture, class, or meeting.
Analyze the transcribed speech carefully and output a structured JSON object with the following EXACT fields:

{
  "title": "A concise, descriptive title for the session",
  "topic_summary": "A coherent, well-written overview summarizing the core ideas discussed",
  "key_concepts": [
    "Core concept 1 with brief explanation",
    "Core concept 2 with brief explanation"
  ],
  "definitions_and_formulas": [
    "Term: Definition or Formula discussed (if none mentioned, provide an empty list)"
  ],
  "important_points": [
    "Key takeaway 1",
    "Key takeaway 2",
    "Key takeaway 3"
  ],
  "revision_questions": [
    "Thought-provoking study or review question 1",
    "Thought-provoking study or review question 2"
  ],
  "extracted_tasks": [
    "Any explicit assignment, deadline, exam reminder, or action item mentioned (if none, empty list)"
  ]
}

CRITICAL RULES:
1. Return ONLY the raw JSON object. Do not include markdown code blocks like ```json ... ``` or commentary.
2. If the speech is casual, adapt appropriately into a clear meeting/discussion note.
3. Fix speech inaccuracies, homophone errors, and slips of the tongue.
"""


class LectureProcessor:
    """Processes long-form transcripts into structured notes using local or cloud LLMs."""

    def __init__(self):
        self.ollama = OllamaPostProcessor(
            base_url=app_config.get("ollama_url", "http://localhost:11434"),
            model=app_config.get("ollama_model", "llama3.2:latest")
        )

    def process_transcript(self, raw_transcript: str) -> Dict[str, Any]:
        """Convert transcript into structured note dictionary."""
        if not raw_transcript or not raw_transcript.strip():
            return {
                "title": "Empty Note",
                "topic_summary": "No speech detected in this recording.",
                "key_concepts": [],
                "definitions_and_formulas": [],
                "important_points": [],
                "revision_questions": [],
                "extracted_tasks": []
            }

        prompt = f"Session Transcript:\n\"\"\"\n{raw_transcript}\n\"\"\""

        # Try Ollama local first, fallback to cloud if configured
        raw_output = ""
        provider = app_config.get("postprocessing_provider", "ollama")

        try:
            if provider == "ollama" and hasattr(self.ollama, "is_available") and self.ollama.is_available():
                try:
                    raw_output = self._query_ollama(prompt)
                except Exception as e:
                    print(f"[LectureProcessor] Ollama failed: {e}. Trying cloud fallback.")
        except Exception as e:
            print(f"[LectureProcessor] Ollama check error: {e}")

        has_cloud_keys = bool(app_config.get("groq_api_key", "").strip() or app_config.get("openai_api_key", "").strip())
        if not raw_output and has_cloud_keys:
            try:
                raw_output = self._query_cloud(prompt)
            except Exception as e:
                print(f"[LectureProcessor] Cloud failed: {e}")

        # Fallback if no LLM responded: heuristic extraction
        if not raw_output:
            return self._heuristic_fallback(raw_transcript)

        return self._parse_json_response(raw_output, raw_transcript)

    def _query_ollama(self, prompt: str) -> str:
        import urllib.request
        model = app_config.get("ollama_model", "llama3.2:latest")
        url = f"{app_config.get('ollama_url', 'http://localhost:11434')}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": LECTURE_NOTES_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2}
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("message", {}).get("content", "")

    def _query_cloud(self, prompt: str) -> str:
        groq_key = app_config.get("groq_api_key", "").strip()
        openai_key = app_config.get("openai_api_key", "").strip()

        if groq_key:
            import urllib.request
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": LECTURE_NOTES_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]

        elif openai_key:
            import urllib.request
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": LECTURE_NOTES_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]

        return ""

    def _parse_json_response(self, text: str, fallback_transcript: str) -> Dict[str, Any]:
        """Safely parse LLM output JSON."""
        # Strip codeblock fences if present
        clean = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
        try:
            parsed = json.loads(clean)
            return {
                "title": parsed.get("title", "Lecture Notes"),
                "topic_summary": parsed.get("topic_summary", ""),
                "key_concepts": parsed.get("key_concepts", []),
                "definitions_and_formulas": parsed.get("definitions_and_formulas", []),
                "important_points": parsed.get("important_points", []),
                "revision_questions": parsed.get("revision_questions", []),
                "extracted_tasks": parsed.get("extracted_tasks", [])
            }
        except Exception:
            return self._heuristic_fallback(fallback_transcript)

    def _heuristic_fallback(self, transcript: str) -> Dict[str, Any]:
        """Fallback when no LLM is running."""
        first_sentence = transcript.split(".")[0] if "." in transcript else transcript[:50]
        return {
            "title": f"Notes: {first_sentence.strip()[:40]}...",
            "topic_summary": transcript.strip(),
            "key_concepts": ["Spoken lecture content recorded locally"],
            "definitions_and_formulas": [],
            "important_points": [s.strip() for s in transcript.split(".") if len(s.strip()) > 10][:5],
            "revision_questions": ["What were the key topics discussed in this session?"],
            "extracted_tasks": []
        }
