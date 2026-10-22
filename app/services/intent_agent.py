"""
Autonomous Agent & Intent Classification Service for Nomi Command Mode.
Classifies spoken commands into:
1. SCHEDULE_EVENT: Calendar scheduling & .ics invitation generation
2. CREATE_TASK: Action item / reminder creation
3. QUERY_MEMORY: Natural language memory retrieval
4. GENERAL_DICTATION: Text pasting fallback
"""

import json
import re
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.config import app_config
from app.services.notes_service import TasksService

INTENT_SYSTEM_PROMPT = """You are Nomi's Autonomous Action Agent.
The user spoke a command or message.
Today's Date and Time is: {current_time}.

Analyze the user's spoken audio and classify their intent into one of:
1. "SCHEDULE_EVENT" (e.g., "Schedule a meeting with Sarah tomorrow at 3 PM", "Add math exam next Monday at 10 AM to my calendar")
2. "CREATE_TASK" (e.g., "Remind me to submit the assignment by Friday", "Add task buy groceries", "Todo finish paper")
3. "QUERY_MEMORY" (e.g., "What was explained about operating systems last week?", "What did the teacher say about the final project?")
4. "DICTATION" (General speech or typing)

Output ONLY a JSON object formatted as follows:

For SCHEDULE_EVENT:
{{
  "intent": "SCHEDULE_EVENT",
  "title": "Meeting with Sarah",
  "start_time": "YYYY-MM-DD HH:MM",
  "end_time": "YYYY-MM-DD HH:MM",
  "description": "Optional notes or details",
  "confirmation_message": "Schedule 'Meeting with Sarah' on Oct 24 at 3:00 PM?"
}}

For CREATE_TASK:
{{
  "intent": "CREATE_TASK",
  "title": "Submit assignment",
  "due_date": "YYYY-MM-DD or descriptive deadline",
  "priority": "High / Medium / Low",
  "confirmation_message": "Add task 'Submit assignment' due Friday?"
}}

For QUERY_MEMORY:
{{
  "intent": "QUERY_MEMORY",
  "query": "operating systems lecture concepts"
}}

For DICTATION:
{{
  "intent": "DICTATION",
  "text": "Exact polished speech"
}}
"""


class IntentAgent:
    """Classifies user speech intents and coordinates tool execution."""

    @classmethod
    def analyze_intent(cls, spoken_text: str) -> Dict[str, Any]:
        """Classify spoken text into an actionable intent structure."""
        if not spoken_text or not spoken_text.strip():
            return {"intent": "DICTATION", "text": ""}

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        sys_prompt = INTENT_SYSTEM_PROMPT.format(current_time=now_str)

        # Quick heuristic check for obvious dictation vs command
        lower = spoken_text.lower().strip()
        command_triggers = ["schedule", "meeting", "calendar", "remind me", "add task", "todo", "what was", "what did"]
        if not any(t in lower for t in command_triggers) and len(spoken_text.split()) > 20:
            # Long speech without command words is regular dictation
            return {"intent": "DICTATION", "text": spoken_text}

        raw_output = cls._query_llm(sys_prompt, spoken_text)
        if not raw_output:
            return cls._heuristic_intent(spoken_text)

        try:
            clean = re.sub(r"^```(?:json)?", "", raw_output.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(clean)
            if "intent" in parsed:
                return parsed
        except Exception:
            pass

        return cls._heuristic_intent(spoken_text)

    @classmethod
    def _heuristic_intent(cls, text: str) -> Dict[str, Any]:
        lower = text.lower()
        if "schedule" in lower or "meeting" in lower or "calendar" in lower:
            return {
                "intent": "SCHEDULE_EVENT",
                "title": text.replace("schedule", "").replace("a meeting", "").strip().capitalize() or "Scheduled Event",
                "start_time": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:00"),
                "end_time": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:00"),
                "description": f"Created via Nomi Voice Command: \"{text}\"",
                "confirmation_message": f"Schedule event from your command: '{text}'?"
            }
        elif "remind" in lower or "task" in lower or "todo" in lower:
            clean_title = re.sub(r"^(remind me to|add task|create task|todo)\s*", "", text, flags=re.IGNORECASE).strip()
            return {
                "intent": "CREATE_TASK",
                "title": clean_title.capitalize(),
                "due_date": "Upcoming",
                "priority": "Medium",
                "confirmation_message": f"Create task: '{clean_title.capitalize()}'?"
            }
        elif lower.startswith("what was") or lower.startswith("what did") or "remember" in lower:
            return {
                "intent": "QUERY_MEMORY",
                "query": text
            }
        return {"intent": "DICTATION", "text": text}

    @classmethod
    def _query_llm(cls, system_prompt: str, user_prompt: str) -> str:
        # Check Ollama
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
                "format": "json",
                "options": {"temperature": 0.1}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {}).get("content", "")
        except Exception:
            pass

        # Check Groq
        groq_key = app_config.get("groq_api_key", "").strip()
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
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data["choices"][0]["message"]["content"]
            except Exception:
                pass

        return ""

    @classmethod
    def execute_action(cls, intent_data: Dict[str, Any]) -> str:
        """Execute the authorized action."""
        intent = intent_data.get("intent")

        if intent == "CREATE_TASK":
            title = intent_data.get("title", "Voice Task")
            due = intent_data.get("due_date", "")
            priority = intent_data.get("priority", "Medium")
            TasksService.add_task(title=title, due_date=due, priority=priority, source="Voice Command")
            return f"Task created: \"{title}\""

        elif intent == "SCHEDULE_EVENT":
            title = intent_data.get("title", "Nomi Event")
            start = intent_data.get("start_time", "")
            end = intent_data.get("end_time", "")
            desc = intent_data.get("description", "")
            ics_path = cls.generate_ics(title, start, end, desc)
            if ics_path and os.path.exists(ics_path):
                # Launch default Windows Calendar or Outlook to confirm and save
                try:
                    os.startfile(ics_path)
                except Exception:
                    pass
            return f"Calendar event created: \"{title}\""

        return "Action completed."

    @classmethod
    def generate_ics(cls, title: str, start_time_str: str, end_time_str: str, description: str) -> Optional[str]:
        """Generate standard iCalendar (.ics) file."""
        try:
            # Parse start time
            try:
                dt_start = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
            except Exception:
                dt_start = datetime.now() + timedelta(hours=1)

            try:
                dt_end = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
            except Exception:
                dt_end = dt_start + timedelta(hours=1)

            stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            t_start = dt_start.strftime("%Y%m%dT%H%M%S")
            t_end = dt_end.strftime("%Y%m%dT%H%M%S")

            ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Nomi AI//Personal Assistant//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{stamp}-nomi@ai
DTSTAMP:{stamp}
DTSTART:{t_start}
DTEND:{t_end}
SUMMARY:{title}
DESCRIPTION:{description}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""
            nomi_dir = os.path.expanduser("~/.nomi/calendar")
            os.makedirs(nomi_dir, exist_ok=True)
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:25]
            filepath = os.path.join(nomi_dir, f"{safe_name}.ics")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(ics_content)
            return filepath
        except Exception as e:
            print(f"[IntentAgent] Error generating .ics: {e}")
            return None
