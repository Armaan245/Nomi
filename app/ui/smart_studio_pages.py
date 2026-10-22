"""
Studio pages for Nomi Research Paper capabilities:
1. Smart Notes Studio (Section 4: Lecture and Smart Notes Mode)
2. Tasks & Actions Dashboard (Section 3 & 6: Action extraction & calendar integration)
3. Ask Memory (Section 5: Personal AI semantic memory Q&A)
"""

import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextBrowser,
    QListWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QMessageBox,
    QFileDialog,
    QFrame,
    QSplitter,
)
import pyperclip

from app.config import app_config
from app.audio.recorder import AudioRecorder
from app.transcription.local_whisper import LocalWhisperService
from app.services.notes_service import SmartNotesService, TasksService
from app.services.lecture_processor import LectureProcessor
from app.services.memory_service import MemoryService
from app.services.intent_agent import IntentAgent
from app.ui.components import SettingsCard, SettingsRow


class SmartStudioPagesMixin:
    """Provides Smart Notes, Tasks, and Memory Q&A pages for the SettingsWindow."""

    def _init_studio_state(self):
        self._lecture_recorder: Optional[AudioRecorder] = None
        self._lecture_timer = QTimer(self)
        self._lecture_timer.timeout.connect(self._on_lecture_timer_tick)
        self._lecture_seconds = 0
        self._current_selected_note: Optional[Dict[str, Any]] = None

    # =========================================================================
    # Page: Smart Notes Studio (Lecture Mode)
    # =========================================================================

    def _build_notes_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 20)
        layout.setSpacing(14)

        # Top Control Card: Live Lecture Recording
        rec_card = SettingsCard()
        rec_widget = QWidget()
        r_layout = QHBoxLayout(rec_widget)
        r_layout.setContentsMargins(18, 14, 18, 14)
        r_layout.setSpacing(14)

        self.btn_record_lecture = QPushButton("Start Lecture Recording")
        self.btn_record_lecture.setObjectName("primaryBtn")
        self.btn_record_lecture.setFixedWidth(200)
        self.btn_record_lecture.clicked.connect(self._toggle_lecture_recording)
        r_layout.addWidget(self.btn_record_lecture)

        self.lbl_lecture_timer = QLabel("00:00")
        self.lbl_lecture_timer.setStyleSheet("font-size: 16px; font-weight: 700; color: #10A37F; font-family: 'Consolas', monospace;")
        r_layout.addWidget(self.lbl_lecture_timer)

        self.lbl_lecture_status = QLabel("Ready to capture classroom lecture, discussion, or meeting audio.")
        self.lbl_lecture_status.setStyleSheet("color: #9B9B9B; font-size: 12.5px;")
        r_layout.addWidget(self.lbl_lecture_status, stretch=1)

        self.btn_sample_note = QPushButton("Generate Demo Note")
        self.btn_sample_note.setObjectName("secondaryBtn")
        self.btn_sample_note.clicked.connect(self._generate_demo_lecture_note)
        r_layout.addWidget(self.btn_sample_note)

        rec_card.add_row(rec_widget)
        layout.addWidget(rec_card)

        # Splitter: Saved Notes List on Left, Formatted Viewer on Right
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #2E2E2E; width: 1px; }")

        # Left Column: Saved Sessions List
        left_widget = QWidget()
        l_layout = QVBoxLayout(left_widget)
        l_layout.setContentsMargins(0, 0, 8, 0)
        l_layout.setSpacing(8)

        lbl_sessions = QLabel("Saved Lecture Notes")
        lbl_sessions.setObjectName("sectionHeader")
        l_layout.addWidget(lbl_sessions)

        self.list_notes = QListWidget()
        self.list_notes.itemClicked.connect(self._on_note_clicked)
        l_layout.addWidget(self.list_notes, stretch=1)

        splitter.addWidget(left_widget)

        # Right Column: Note Viewer & Actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        self.lbl_note_title = QLabel("Select a session to view structured notes")
        self.lbl_note_title.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF;")
        header_row.addWidget(self.lbl_note_title, stretch=1)

        self.btn_copy_note = QPushButton("Copy Markdown")
        self.btn_copy_note.setObjectName("secondaryBtn")
        self.btn_copy_note.clicked.connect(self._copy_current_note_markdown)
        header_row.addWidget(self.btn_copy_note)

        self.btn_export_note = QPushButton("Export .md")
        self.btn_export_note.setObjectName("secondaryBtn")
        self.btn_export_note.clicked.connect(self._export_current_note)
        header_row.addWidget(self.btn_export_note)

        self.btn_delete_note = QPushButton("Delete")
        self.btn_delete_note.setObjectName("dangerBtn")
        self.btn_delete_note.clicked.connect(self._delete_current_note)
        header_row.addWidget(self.btn_delete_note)

        right_layout.addLayout(header_row)

        self.txt_note_view = QTextBrowser()
        self.txt_note_view.setOpenExternalLinks(True)
        right_layout.addWidget(self.txt_note_view, stretch=1)

        splitter.addWidget(right_widget)
        splitter.setSizes([260, 520])

        layout.addWidget(splitter, stretch=1)

        self._refresh_notes_list()
        return container

    def _on_lecture_timer_tick(self):
        self._lecture_seconds += 1
        m = self._lecture_seconds // 60
        s = self._lecture_seconds % 60
        self.lbl_lecture_timer.setText(f"{m:02d}:{s:02d}")

    def _toggle_lecture_recording(self):
        if self._lecture_recorder is None:
            # Start Recording
            dev_idx = app_config.get("input_device_index", None)
            try:
                self._lecture_recorder = AudioRecorder(device_index=dev_idx)
                self._lecture_recorder.start()
                self._lecture_seconds = 0
                self._lecture_timer.start(1000)
                self.btn_record_lecture.setText("Finish & Generate Notes")
                self.btn_record_lecture.setStyleSheet("background-color: #EF4444; color: #FFFFFF; font-weight: 600;")
                self.lbl_lecture_status.setText("Recording classroom lecture in progress... (Listening with VAD)")
            except Exception as e:
                QMessageBox.warning(self, "Audio Error", f"Could not start microphone: {e}")
        else:
            # Stop Recording & Process
            self._lecture_timer.stop()
            self.lbl_lecture_status.setText("Transcribing audio and structuring notes with AI...")
            self.btn_record_lecture.setEnabled(False)
            self.btn_record_lecture.setText("Processing...")

            raw_audio = self._lecture_recorder.stop()
            self._lecture_recorder = None

            QTimer.singleShot(100, lambda: self._process_lecture_audio(raw_audio))

    def _process_lecture_audio(self, raw_audio):
        try:
            if raw_audio is None or len(raw_audio) < 16000:
                QMessageBox.information(self, "No Audio", "Recording was too short to generate notes.")
                self._reset_lecture_btn()
                return

            # Transcribe with Local Whisper
            whisper = LocalWhisperService(
                model_name=app_config.get("whisper_model", "tiny.en"),
                device=app_config.get("whisper_device", "cpu"),
                compute_type=app_config.get("whisper_compute_type", "int8")
            )
            transcript = whisper.transcribe(raw_audio)

            if not transcript or not transcript.strip():
                QMessageBox.information(self, "No Speech Detected", "Whisper did not detect any spoken words.")
                self._reset_lecture_btn()
                return

            # Structure with LectureProcessor
            processor = LectureProcessor()
            note_data = processor.process_transcript(transcript)

            saved_note = SmartNotesService.add_note(
                title=note_data.get("title", "Lecture Session"),
                topic_summary=note_data.get("topic_summary", ""),
                key_concepts=note_data.get("key_concepts", []),
                definitions_and_formulas=note_data.get("definitions_and_formulas", []),
                important_points=note_data.get("important_points", []),
                revision_questions=note_data.get("revision_questions", []),
                extracted_tasks=note_data.get("extracted_tasks", []),
                raw_transcript=transcript
            )

            self._refresh_notes_list()
            self._display_note(saved_note)
            self._refresh_tasks_table()
            QMessageBox.information(self, "Notes Ready", f"Successfully generated Smart Notes:\n\"{saved_note['title']}\"")
        except Exception as e:
            QMessageBox.warning(self, "Processing Error", f"Failed to generate notes: {e}")
        finally:
            self._reset_lecture_btn()

    def _reset_lecture_btn(self):
        self.btn_record_lecture.setEnabled(True)
        self.btn_record_lecture.setText("Start Lecture Recording")
        self.btn_record_lecture.setStyleSheet("")
        self.lbl_lecture_status.setText("Ready to capture classroom lecture, discussion, or meeting audio.")
        self.lbl_lecture_timer.setText("00:00")

    def _generate_demo_lecture_note(self):
        """Generate a realistic sample lecture note demonstrating the full schema from the paper."""
        sample_transcript = (
            "Welcome everyone to Computer Science 301. Today we are covering Operating System Process Scheduling. "
            "A process is a program in execution, consisting of program code, stack, data section, and program counter. "
            "The Operating System uses scheduling algorithms to maximize CPU utilization and throughput. "
            "The turnaround time formula is defined as completion time minus arrival time: Turnaround Time = Completion Time - Arrival Time. "
            "Waiting time is turnaround time minus burst time. "
            "Round Robin scheduling uses a fixed time quantum. If the time quantum is too large, it degrades into First-Come First-Served. "
            "For next Tuesday, make sure to submit Homework 3 on Priority Scheduling algorithms, and remember our midterm exam is on Friday at 10 AM."
        )
        processor = LectureProcessor()
        note_data = processor.process_transcript(sample_transcript)
        saved = SmartNotesService.add_note(
            title=note_data.get("title", "CS 301: OS Process Scheduling"),
            topic_summary=note_data.get("topic_summary", ""),
            key_concepts=note_data.get("key_concepts", []),
            definitions_and_formulas=note_data.get("definitions_and_formulas", []),
            important_points=note_data.get("important_points", []),
            revision_questions=note_data.get("revision_questions", []),
            extracted_tasks=note_data.get("extracted_tasks", []),
            raw_transcript=sample_transcript
        )
        self._refresh_notes_list()
        self._display_note(saved)
        self._refresh_tasks_table()
        QMessageBox.information(self, "Demo Note Created", "Sample Lecture Note with key concepts, formulas, questions, and extracted tasks has been generated.")

    def _refresh_notes_list(self):
        self.list_notes.clear()
        notes = SmartNotesService.load_all_notes()
        for note in notes:
            item_text = f"{note.get('title', 'Untitled')}\n{note.get('created_at', '')}"
            self.list_notes.addItem(item_text)

        if notes:
            self._display_note(notes[0])

    def _on_note_clicked(self, item):
        idx = self.list_notes.row(item)
        notes = SmartNotesService.load_all_notes()
        if 0 <= idx < len(notes):
            self._display_note(notes[idx])

    def _display_note(self, note: Dict[str, Any]):
        self._current_selected_note = note
        self.lbl_note_title.setText(note.get("title", "Lecture Notes"))

        html = f"""
        <html>
        <head>
        <style>
            body {{ color: #ECECEC; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 13.5px; line-height: 1.6; margin: 0; }}
            h2 {{ color: #FFFFFF; font-size: 15px; margin-top: 18px; margin-bottom: 6px; border-bottom: 1px solid #333333; padding-bottom: 4px; }}
            p {{ color: #D1D1D1; margin-top: 4px; margin-bottom: 10px; }}
            ul {{ margin-top: 4px; padding-left: 20px; }}
            li {{ margin-bottom: 4px; color: #D1D1D1; }}
            .badge {{ display: inline-block; background-color: #262626; border: 1px solid #404040; border-radius: 4px; padding: 2px 8px; font-size: 12px; color: #10A37F; font-weight: 600; margin-bottom: 8px; }}
            .formula {{ background-color: #222222; border-left: 3px solid #10A37F; padding: 6px 10px; font-family: 'Consolas', monospace; color: #A7F3D0; margin: 4px 0; }}
            .task-item {{ background-color: rgba(16, 163, 127, 0.12); border: 1px solid rgba(16, 163, 127, 0.3); border-radius: 6px; padding: 6px 10px; color: #ECECEC; margin: 4px 0; }}
        </style>
        </head>
        <body>
        <div class="badge">{note.get('created_at', '')}</div>

        <h2>Topic Summary</h2>
        <p>{note.get('topic_summary', 'No summary generated.')}</p>

        <h2>Key Concepts</h2>
        <ul>
        """
        for c in note.get("key_concepts", []):
            html += f"<li><b>{c}</b></li>"
        html += "</ul>"

        defs = note.get("definitions_and_formulas", [])
        if defs:
            html += "<h2>Definitions & Formulas</h2>"
            for d in defs:
                html += f'<div class="formula">{d}</div>'

        points = note.get("important_points", [])
        if points:
            html += "<h2>Important Points</h2><ul>"
            for p in points:
                html += f"<li>{p}</li>"
            html += "</ul>"

        questions = note.get("revision_questions", [])
        if questions:
            html += "<h2>Revision & Study Questions</h2><ul>"
            for q in questions:
                html += f"<li>{q}</li>"
            html += "</ul>"

        tasks = note.get("extracted_tasks", [])
        if tasks:
            html += "<h2>Extracted Tasks & Deadlines</h2>"
            for t in tasks:
                html += f'<div class="task-item"> {t}</div>'

        if note.get("raw_transcript"):
            html += f"""
            <h2>Raw Spoken Transcript</h2>
            <p style='color: #8E8E8E; font-size: 12px; font-style: italic;'>{note.get('raw_transcript')}</p>
            """

        html += "</body></html>"
        self.txt_note_view.setHtml(html)

    def _copy_current_note_markdown(self):
        if self._current_selected_note:
            md = SmartNotesService.export_as_markdown(self._current_selected_note)
            pyperclip.copy(md)
            QMessageBox.information(self, "Copied", "Full structured note copied to clipboard as Markdown.")

    def _export_current_note(self):
        if not self._current_selected_note:
            return
        md = SmartNotesService.export_as_markdown(self._current_selected_note)
        default_name = f"{self._current_selected_note.get('title', 'Lecture_Note')}.md"
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Smart Note", default_name, "Markdown (*.md);;Text (*.txt)")
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)
            QMessageBox.information(self, "Exported", f"Saved note to:\n{filepath}")

    def _delete_current_note(self):
        if not self._current_selected_note:
            return
        nid = self._current_selected_note.get("id")
        if nid:
            SmartNotesService.delete_note(nid)
            self._refresh_notes_list()

    # =========================================================================
    # Page: Tasks & Actions Dashboard
    # =========================================================================

    def _build_tasks_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 20)
        layout.setSpacing(14)

        # Header card with quick add
        card = SettingsCard()
        add_widget = QWidget()
        a_layout = QHBoxLayout(add_widget)
        a_layout.setContentsMargins(18, 14, 18, 14)
        a_layout.setSpacing(10)

        self.txt_task_title = QLineEdit()
        self.txt_task_title.setPlaceholderText("Enter new action item or deadline...")
        self.txt_task_title.returnPressed.connect(self._add_task_manual)
        a_layout.addWidget(self.txt_task_title, stretch=2)

        self.txt_task_due = QLineEdit()
        self.txt_task_due.setPlaceholderText("Due date (e.g. Tomorrow 4 PM)")
        self.txt_task_due.setFixedWidth(200)
        self.txt_task_due.returnPressed.connect(self._add_task_manual)
        a_layout.addWidget(self.txt_task_due)

        self.btn_add_task = QPushButton("Add Task")
        self.btn_add_task.setObjectName("secondaryBtn")
        self.btn_add_task.clicked.connect(self._add_task_manual)
        a_layout.addWidget(self.btn_add_task)

        card.add_row(add_widget)
        layout.addWidget(card)

        # Table of Tasks
        self.table_tasks = QTableWidget(0, 4)
        self.table_tasks.setHorizontalHeaderLabels(["Done", "Task / Action Item", "Due Date", "Source"])
        self.table_tasks.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tasks.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_tasks.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tasks.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tasks.cellChanged.connect(self._on_task_cell_changed)
        layout.addWidget(self.table_tasks, stretch=1)

        # Bottom Actions Row
        btn_row = QHBoxLayout()
        self.btn_schedule_ics = QPushButton("Schedule in Calendar (.ics)")
        self.btn_schedule_ics.setObjectName("primaryBtn")
        self.btn_schedule_ics.clicked.connect(self._schedule_selected_task)
        btn_row.addWidget(self.btn_schedule_ics)

        self.btn_delete_task = QPushButton("Delete Task")
        self.btn_delete_task.setObjectName("dangerBtn")
        self.btn_delete_task.clicked.connect(self._delete_selected_task)
        btn_row.addWidget(self.btn_delete_task)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        self._refresh_tasks_table()
        return container

    def _refresh_tasks_table(self):
        self.table_tasks.blockSignals(True)
        self.table_tasks.setRowCount(0)
        tasks = TasksService.load_all_tasks()
        for row, t in enumerate(tasks):
            self.table_tasks.insertRow(row)

            # Checkbox item
            item_done = QTableWidgetItem()
            item_done.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item_done.setCheckState(Qt.CheckState.Checked if t.get("completed") else Qt.CheckState.Unchecked)
            item_done.setData(Qt.ItemDataRole.UserRole, t.get("id"))
            self.table_tasks.setItem(row, 0, item_done)

            item_title = QTableWidgetItem(t.get("title", ""))
            self.table_tasks.setItem(row, 1, item_title)

            item_due = QTableWidgetItem(t.get("due_date", "No deadline"))
            self.table_tasks.setItem(row, 2, item_due)

            item_src = QTableWidgetItem(t.get("source", "Voice"))
            self.table_tasks.setItem(row, 3, item_src)

        self.table_tasks.blockSignals(False)

    def _on_task_cell_changed(self, row: int, col: int):
        if col == 0:
            item = self.table_tasks.item(row, 0)
            if item:
                tid = item.data(Qt.ItemDataRole.UserRole)
                if tid:
                    TasksService.toggle_task(tid)

    def _add_task_manual(self):
        title = self.txt_task_title.text().strip()
        due = self.txt_task_due.text().strip()
        if title:
            TasksService.add_task(title=title, due_date=due, source="Manual")
            self.txt_task_title.clear()
            self.txt_task_due.clear()
            self._refresh_tasks_table()

    def _delete_selected_task(self):
        row = self.table_tasks.currentRow()
        if row >= 0:
            item = self.table_tasks.item(row, 0)
            if item:
                tid = item.data(Qt.ItemDataRole.UserRole)
                if tid:
                    TasksService.delete_task(tid)
                    self._refresh_tasks_table()

    def _schedule_selected_task(self):
        row = self.table_tasks.currentRow()
        if row >= 0:
            title_item = self.table_tasks.item(row, 1)
            due_item = self.table_tasks.item(row, 2)
            title = title_item.text() if title_item else "Nomi Task"
            due_text = due_item.text() if due_item else ""

            ics_path = IntentAgent.generate_ics(
                title=title,
                start_time_str=datetime.now().strftime("%Y-%m-%d 10:00"),
                end_time_str=datetime.now().strftime("%Y-%m-%d 11:00"),
                description=f"Action item extracted by Nomi AI (Due: {due_text})"
            )
            if ics_path and os.path.exists(ics_path):
                os.startfile(ics_path)
                QMessageBox.information(self, "Calendar Event Created", f"Opened '{title}' in your system calendar application.")
        else:
            QMessageBox.information(self, "Select Task", "Please select a task from the list to schedule.")

    # =========================================================================
    # Page: Ask Memory (Searchable AI Knowledge Base)
    # =========================================================================

    def _build_memory_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 20)
        layout.setSpacing(14)

        # Search Query Card
        card = SettingsCard()
        q_widget = QWidget()
        q_layout = QVBoxLayout(q_widget)
        q_layout.setContentsMargins(18, 16, 18, 16)
        q_layout.setSpacing(10)

        lbl_desc = QLabel("Ask any natural language question across all your recorded lectures, meetings, and speech history.")
        lbl_desc.setStyleSheet("color: #9B9B9B; font-size: 13px;")
        q_layout.addWidget(lbl_desc)

        input_row = QHBoxLayout()
        self.txt_memory_query = QLineEdit()
        self.txt_memory_query.setPlaceholderText("e.g., What was explained about process scheduling algorithms?")
        self.txt_memory_query.returnPressed.connect(self._ask_memory)
        input_row.addWidget(self.txt_memory_query, stretch=1)

        self.btn_memory_ask = QPushButton("Ask Nomi")
        self.btn_memory_ask.setObjectName("primaryBtn")
        self.btn_memory_ask.clicked.connect(self._ask_memory)
        input_row.addWidget(self.btn_memory_ask)
        q_layout.addLayout(input_row)

        # Quick Suggestion Chips
        chips_row = QHBoxLayout()
        chips = [
            "What was covered in operating systems?",
            "What homework assignments were given?",
            "Summarize the formulas discussed"
        ]
        for chip_text in chips:
            btn_chip = QPushButton(chip_text)
            btn_chip.setObjectName("secondaryBtn")
            btn_chip.setStyleSheet("font-size: 11.5px; padding: 4px 10px; border-radius: 6px;")
            btn_chip.clicked.connect(lambda _, t=chip_text: self._set_query_and_ask(t))
            chips_row.addWidget(btn_chip)
        chips_row.addStretch()
        q_layout.addLayout(chips_row)

        card.add_row(q_widget)
        layout.addWidget(card)

        # Answer Result Area
        lbl_ans = QLabel("AI Synthesized Answer")
        lbl_ans.setObjectName("sectionHeader")
        layout.addWidget(lbl_ans)

        self.txt_memory_answer = QTextBrowser()
        self.txt_memory_answer.setPlaceholderText("Your answer synthesized from saved lectures and notes will appear here...")
        layout.addWidget(self.txt_memory_answer, stretch=1)

        self.lbl_memory_sources = QLabel("")
        self.lbl_memory_sources.setStyleSheet("color: #8E8E8E; font-size: 12px; font-style: italic;")
        layout.addWidget(self.lbl_memory_sources)

        return container

    def _set_query_and_ask(self, query_text: str):
        self.txt_memory_query.setText(query_text)
        self._ask_memory()

    def _ask_memory(self):
        query = self.txt_memory_query.text().strip()
        if not query:
            return
        self.btn_memory_ask.setEnabled(False)
        self.btn_memory_ask.setText("Searching...")
        self.txt_memory_answer.setHtml("<p style='color: #8E8E8E;'><i>Searching saved notes and synthesizing answer...</i></p>")

        QTimer.singleShot(50, lambda: self._execute_memory_query(query))

    def _execute_memory_query(self, query: str):
        try:
            res = MemoryService.query_memory(query)
            ans = res.get("answer", "No answer found.")
            sources = res.get("sources", [])

            html = f"""
            <html><body style="color: #ECECEC; font-family: 'Segoe UI', -apple-system, sans-serif; font-size: 14px; line-height: 1.6;">
            {ans.replace(chr(10), '<br>')}
            </body></html>
            """
            self.txt_note_view.setHtml(html)
            self.txt_memory_answer.setHtml(html)

            if sources:
                self.lbl_memory_sources.setText(f"Sources cited: {', '.join(sources)}")
            else:
                self.lbl_memory_sources.setText("")
        except Exception as e:
            self.txt_memory_answer.setText(f"Error querying memory: {e}")
        finally:
            self.btn_memory_ask.setEnabled(True)
            self.btn_memory_ask.setText("Ask Nomi")
