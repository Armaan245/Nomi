"""
Personal AI Memory & Semantic Retrieval Service.
Allows students and users to query their past notes and transcripts:
e.g. "What was explained about operating systems last week?"
"""

import json
import re
from typing import Dict, Any, List
from app.config import app_config
from app.services.notes_service import SmartNotesService


MEMORY_QA_SYSTEM_PROMPT = """You are Nomi's Personal AI Memory Engine.
The user is asking a question about their past lectures, classes, meetings, or thoughts.
Below is the relevant context retrieved from their saved notes and transcripts.

Retrieved Context:
\"\"\"
{context_text}
\"\"\"

Answer the user's question accurately, concisely, and contextually based ONLY on the provided notes and transcripts.
- If the answer is found in the notes, cite the note title and date.
- If the information is not in the notes, explain politely that it wasn't mentioned in any of their recorded sessions.
"""


class MemoryService:
    """Manages search and question-answering over user's personal context and lecture archives."""

    @classmethod
    def query_memory(cls, question: str) -> Dict[str, Any]:
        """Search memory and generate context-aware answer."""
        if not question or not question.strip():
            return {
                "answer": "Please ask a question about your saved notes or lectures.",
                "sources": []
            }

        # 1. Retrieve notes
        notes = SmartNotesService.load_all_notes()
        history = app_config.load_history()

        if not notes and not history:
            return {
                "answer": "No notes or recordings found in your memory yet. Record a lecture or session first!",
                "sources": []
            }

        # 2. Score and rank relevant notes
        scored_sources = cls._rank_sources(question, notes, history)
        if not scored_sources:
            # Fallback to recent 3 notes
            scored_sources = [(n, 1) for n in notes[:3]]

        # 3. Build context block
        context_chunks = []
        source_names = []
        for item, _ in scored_sources[:4]:
            if "key_concepts" in item:
                # It's a structured smart note
                chunk = (
                    f"Note Title: {item.get('title')} ({item.get('created_at')})\n"
                    f"Summary: {item.get('topic_summary')}\n"
                    f"Key Concepts: {', '.join(item.get('key_concepts', []))}\n"
                    f"Important Points: {'; '.join(item.get('important_points', []))}\n"
                )
                source_names.append(f"{item.get('title')} ({item.get('created_at')})")
            else:
                # History entry
                chunk = f"Recorded on {item.get('time')}: {item.get('cleaned')}\n"
                source_names.append(f"Speech Log ({item.get('time')})")
            context_chunks.append(chunk)

        context_text = "\n---\n".join(context_chunks)
        sys_prompt = MEMORY_QA_SYSTEM_PROMPT.format(context_text=context_text)

        # 4. Synthesize with LLM
        answer = cls._query_llm(sys_prompt, question)
        if not answer:
            # Fallback simple extraction
            answer = f"Found relevant information in: {', '.join(source_names[:2])}.\n\n" + context_chunks[0]

        return {
            "answer": answer,
            "sources": source_names[:3]
        }

    @classmethod
    def _rank_sources(cls, query: str, notes: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> List[tuple]:
        words = set(re.findall(r'\w+', query.lower()))
        # Remove common stop words
        stops = {"what", "was", "did", "the", "about", "last", "week", "yesterday", "how", "when", "why", "who", "where", "is", "a", "an", "in", "on", "at", "to", "for"}
        keywords = words - stops

        scored = []
        for n in notes:
            text = f"{n.get('title', '')} {n.get('topic_summary', '')} {' '.join(n.get('key_concepts', []))} {n.get('raw_transcript', '')}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((n, score))

        for h in history:
            text = f"{h.get('cleaned', '')} {h.get('raw', '')}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((h, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    @classmethod
    def _query_llm(cls, system_prompt: str, user_prompt: str) -> str:
        # 1. Ollama
        try:
            import urllib.request
            model = app_config.get("ollama_model", "llama3.2:latest")
            url = f"{app_config.get('ollama_url', 'http://localhost:11434')}/api/chat"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.2}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except Exception:
            pass

        # 2. Cloud (Groq / OpenAI)
        groq_key = app_config.get("groq_api_key", "").strip()
        openai_key = app_config.get("openai_api_key", "").strip()

        if groq_key:
            try:
                import urllib.request
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except Exception:
                pass

        return ""
