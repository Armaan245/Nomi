"""
Data persistence and management for Nomi Smart Notes, Tasks, and Calendar Events.
Stores structured notes and tasks in ~/.nomi/notes.json and ~/.nomi/tasks.json.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

CONFIG_DIR = Path.home() / ".nomi"
NOTES_FILE = CONFIG_DIR / "notes.json"
TASKS_FILE = CONFIG_DIR / "tasks.json"


class SmartNotesService:
    """Manages persistent structured lecture and meeting notes."""

    @staticmethod
    def _ensure_dir():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_all_notes(cls) -> List[Dict[str, Any]]:
        cls._ensure_dir()
        if not NOTES_FILE.exists():
            return []
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[NotesService] Error loading notes: {e}")
            return []

    @classmethod
    def save_all_notes(cls, notes: List[Dict[str, Any]]) -> bool:
        cls._ensure_dir()
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[NotesService] Error saving notes: {e}")
            return False

    @classmethod
    def add_note(
        cls,
        title: str,
        topic_summary: str,
        key_concepts: List[str],
        definitions_and_formulas: List[str],
        important_points: List[str],
        revision_questions: List[str],
        extracted_tasks: List[str],
        raw_transcript: str = ""
    ) -> Dict[str, Any]:
        """Create and persist a new structured smart note."""
        notes = cls.load_all_notes()
        note = {
            "id": str(uuid.uuid4())[:8],
            "title": title or f"Lecture Notes - {datetime.now().strftime('%b %d, %Y')}",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic_summary": topic_summary,
            "key_concepts": key_concepts or [],
            "definitions_and_formulas": definitions_and_formulas or [],
            "important_points": important_points or [],
            "revision_questions": revision_questions or [],
            "extracted_tasks": extracted_tasks or [],
            "raw_transcript": raw_transcript
        }
        # Prepend so newest appears first
        notes.insert(0, note)
        cls.save_all_notes(notes)

        # Also automatically register any extracted tasks into TasksService
        if extracted_tasks:
            for task_text in extracted_tasks:
                if isinstance(task_text, str) and task_text.strip():
                    TasksService.add_task(
                        title=task_text.strip(),
                        source=f"Note: {note['title']}"
                    )

        return note

    @classmethod
    def delete_note(cls, note_id: str) -> bool:
        notes = cls.load_all_notes()
        new_notes = [n for n in notes if n.get("id") != note_id]
        if len(new_notes) != len(notes):
            return cls.save_all_notes(new_notes)
        return False

    @classmethod
    def export_as_markdown(cls, note: Dict[str, Any]) -> str:
        """Format a structured smart note as beautiful Markdown for export."""
        lines = [
            f"# {note.get('title', 'Lecture Notes')}",
            f"*Date: {note.get('created_at', '')}*",
            "",
            "## 📌 Topic Summary",
            note.get('topic_summary', '').strip(),
            "",
            "## 💡 Key Concepts",
        ]
        for c in note.get("key_concepts", []):
            lines.append(f"- **{c}**")
        lines.append("")

        defs = note.get("definitions_and_formulas", [])
        if defs:
            lines.append("## 📐 Definitions & Formulas")
            for d in defs:
                lines.append(f"- {d}")
            lines.append("")

        points = note.get("important_points", [])
        if points:
            lines.append("## 🎯 Important Points")
            for p in points:
                lines.append(f"- {p}")
            lines.append("")

        questions = note.get("revision_questions", [])
        if questions:
            lines.append("## ❓ Revision & Study Questions")
            for q in questions:
                lines.append(f"- {q}")
            lines.append("")

        tasks = note.get("extracted_tasks", [])
        if tasks:
            lines.append("## ✅ Extracted Tasks & Action Items")
            for t in tasks:
                lines.append(f"- [ ] {t}")
            lines.append("")

        if note.get("raw_transcript"):
            lines.append("---")
            lines.append("### Full Raw Transcript")
            lines.append(f"> {note.get('raw_transcript', '').strip()}")

        return "\n".join(lines)


class TasksService:
    """Manages persistent tasks, deadlines, and reminders."""

    @staticmethod
    def _ensure_dir():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_all_tasks(cls) -> List[Dict[str, Any]]:
        cls._ensure_dir()
        if not TASKS_FILE.exists():
            return []
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TasksService] Error loading tasks: {e}")
            return []

    @classmethod
    def save_all_tasks(cls, tasks: List[Dict[str, Any]]) -> bool:
        cls._ensure_dir()
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[TasksService] Error saving tasks: {e}")
            return False

    @classmethod
    def add_task(
        cls,
        title: str,
        due_date: str = "",
        source: str = "Voice Command",
        priority: str = "Medium"
    ) -> Dict[str, Any]:
        tasks = cls.load_all_tasks()
        task = {
            "id": str(uuid.uuid4())[:8],
            "title": title.strip(),
            "due_date": due_date.strip() if due_date else "No deadline",
            "source": source,
            "priority": priority,
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        tasks.insert(0, task)
        cls.save_all_tasks(tasks)
        return task

    @classmethod
    def toggle_task(cls, task_id: str) -> bool:
        tasks = cls.load_all_tasks()
        for t in tasks:
            if t.get("id") == task_id:
                t["completed"] = not t.get("completed", False)
                return cls.save_all_tasks(tasks)
        return False

    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        tasks = cls.load_all_tasks()
        new_tasks = [t for t in tasks if t.get("id") != task_id]
        if len(new_tasks) != len(tasks):
            return cls.save_all_tasks(new_tasks)
        return False
