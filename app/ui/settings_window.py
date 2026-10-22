"""
ChatGPT Desktop Neutral Dark Settings Window for Nomi Windows.
Clean monochrome vector styling without emojis, matching ChatGPT Desktop Settings.
"""

import os
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QScrollArea,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QListWidget,
    QHeaderView,
    QProgressBar,
    QMessageBox,
    QFrame,
    QButtonGroup,
)
import pyperclip

from app.config import app_config
from app.audio.recorder import AudioRecorder
from app.postprocessing.ollama_client import OllamaPostProcessor
from app.ui.styles import DARK_THEME_QSS
from app.ui.tray_icon import create_tray_pixmap
from app.ui.glass import apply_acrylic_blur
from app.ui.components import (
    SwitchToggle,
    SettingsCard,
    SettingsRow,
    NavItemButton,
)

_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets")).replace("\\", "/")
ICON_GEAR = f"{_ASSETS_DIR}/gear.svg"
ICON_MIC = f"{_ASSETS_DIR}/mic.svg"
ICON_SPARKLE = f"{_ASSETS_DIR}/sparkle.svg"
ICON_BOOK = f"{_ASSETS_DIR}/book.svg"
ICON_EDIT = f"{_ASSETS_DIR}/edit.svg"
ICON_CLOCK = f"{_ASSETS_DIR}/clock.svg"
ICON_CHECKLIST = f"{_ASSETS_DIR}/checklist.svg"
ICON_BRAIN = f"{_ASSETS_DIR}/brain.svg"

from app.ui.smart_studio_pages import SmartStudioPagesMixin


class SettingsWindow(QMainWindow, SmartStudioPagesMixin):
    """ChatGPT Desktop Styled Settings, Studio, and Autonomous Assistant Window."""

    settings_changed = pyqtSignal()
    reset_position_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nomi — Personal Context Assistant & Smart Notes")
        self.resize(980, 700)
        self.setMinimumSize(880, 600)
        self.setWindowIcon(QIcon(create_tray_pixmap(True)))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(DARK_THEME_QSS)

        # Initialize studio state (lecture recording, timers, etc.)
        self._init_studio_state()

        # Test recorder for mic meter
        self._test_recorder: Optional[AudioRecorder] = None
        self._history_items: List[Dict[str, Any]] = []

        self._init_ui()
        self.tabs = self
        self._load_values()

    def showEvent(self, event):
        super().showEvent(event)
        # Apply neutral dark Acrylic blur behind window
        apply_acrylic_blur(self, dark_mode=True, tint_abgr=0xEE1E1E1E)

    def switch_page(self, index: int):
        """Public method to change active page."""
        self._switch_page(index)

    def setCurrentIndex(self, index: int):
        """Backward compatibility for tab widget index switching."""
        self._switch_page(index)

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        # Main horizontal split: Sidebar on Left, Content on Right
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ------------------ Left Sidebar ------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(240)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(16, 20, 16, 20)
        s_layout.setSpacing(10)

        # App title / Header
        brand_label = QLabel("Settings")
        brand_label.setStyleSheet("font-size: 19px; font-weight: 600; color: #FFFFFF; padding-left: 4px;")
        s_layout.addWidget(brand_label)

        # Search Bar matching ChatGPT desktop
        self.txt_search = QLineEdit()
        self.txt_search.setObjectName("searchBar")
        self.txt_search.setPlaceholderText("Search")
        self.txt_search.textChanged.connect(self._on_search_changed)
        s_layout.addWidget(self.txt_search)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        # Category 1: Assistant & Studio (Research Paper capabilities)
        cat_assist = QLabel("Assistant & Notes")
        cat_assist.setStyleSheet("color: #8E8E8E; font-size: 11.5px; font-weight: 600; padding-left: 6px; margin-top: 6px;")
        s_layout.addWidget(cat_assist)

        self.btn_nav_general = NavItemButton("General", icon_path=ICON_GEAR)
        self.btn_nav_notes = NavItemButton("Smart Notes", icon_path=ICON_BOOK)
        self.btn_nav_tasks = NavItemButton("Tasks & Actions", icon_path=ICON_CHECKLIST)
        self.btn_nav_memory = NavItemButton("Ask Memory", icon_path=ICON_BRAIN)

        s_layout.addWidget(self.btn_nav_general)
        s_layout.addWidget(self.btn_nav_notes)
        s_layout.addWidget(self.btn_nav_tasks)
        s_layout.addWidget(self.btn_nav_memory)

        # Category 2: System & Models
        cat_sys = QLabel("System & AI")
        cat_sys.setStyleSheet("color: #8E8E8E; font-size: 11.5px; font-weight: 600; padding-left: 6px; margin-top: 10px;")
        s_layout.addWidget(cat_sys)

        self.btn_nav_voice = NavItemButton("Voice & Audio", icon_path=ICON_MIC)
        self.btn_nav_models = NavItemButton("AI Models", icon_path=ICON_SPARKLE)
        self.btn_nav_vocab = NavItemButton("Vocabulary", icon_path=ICON_BOOK)
        self.btn_nav_edit = NavItemButton("Edit Mode", icon_path=ICON_EDIT)
        self.btn_nav_history = NavItemButton("History", icon_path=ICON_CLOCK)

        s_layout.addWidget(self.btn_nav_voice)
        s_layout.addWidget(self.btn_nav_models)
        s_layout.addWidget(self.btn_nav_vocab)
        s_layout.addWidget(self.btn_nav_edit)
        s_layout.addWidget(self.btn_nav_history)

        self.nav_buttons = [
            self.btn_nav_general,   # 0
            self.btn_nav_notes,     # 1
            self.btn_nav_tasks,     # 2
            self.btn_nav_memory,    # 3
            self.btn_nav_voice,     # 4
            self.btn_nav_models,    # 5
            self.btn_nav_vocab,     # 6
            self.btn_nav_edit,      # 7
            self.btn_nav_history,   # 8
        ]

        for idx, btn in enumerate(self.nav_buttons):
            self.nav_group.addButton(btn, idx)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))

        self.btn_nav_general.setChecked(True)

        s_layout.addStretch()

        # Bottom info card (clean neutral)
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            background-color: #1E1E1E;
            border: 1px solid #2C2C2C;
            border-radius: 8px;
            padding: 8px;
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(3)

        nomi_ver = QLabel("Nomi Assistant v2.0")
        nomi_ver.setStyleSheet("color: #E2E8F0; font-size: 11.5px; font-weight: 500;")
        info_layout.addWidget(nomi_ver)

        status_text = QLabel("Context Engine & Smart Notes Active")
        status_text.setStyleSheet("color: #8E8E8E; font-size: 11px;")
        info_layout.addWidget(status_text)

        s_layout.addWidget(info_frame)

        main_layout.addWidget(sidebar)

        # ------------------ Right Content Area ------------------
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(36, 24, 36, 24)
        content_layout.setSpacing(16)

        # Top Bar: Page Title + Save Button
        top_bar = QHBoxLayout()
        self.lbl_page_title = QLabel("General")
        self.lbl_page_title.setObjectName("pageTitle")
        top_bar.addWidget(self.lbl_page_title)
        top_bar.addStretch()

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setObjectName("saveBtn")
        self.btn_save.clicked.connect(self._save_values)
        top_bar.addWidget(self.btn_save)

        content_layout.addLayout(top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_general_page())  # 0
        self.stack.addWidget(self._build_notes_page())    # 1
        self.stack.addWidget(self._build_tasks_page())    # 2
        self.stack.addWidget(self._build_memory_page())   # 3
        self.stack.addWidget(self._build_voice_page())    # 4
        self.stack.addWidget(self._build_models_page())   # 5
        self.stack.addWidget(self._build_vocab_page())    # 6
        self.stack.addWidget(self._build_edit_page())     # 7
        self.stack.addWidget(self._build_history_page())  # 8

        content_layout.addWidget(self.stack)

        main_layout.addWidget(content_container, stretch=1)

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        titles = [
            "General",
            "Smart Notes (Lecture Mode)",
            "Tasks & Actions",
            "Searchable AI Memory",
            "Voice & Audio",
            "AI Models",
            "Vocabulary",
            "Edit Mode",
            "History",
        ]
        if index < len(titles):
            self.lbl_page_title.setText(titles[index])
        if index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)

    def _on_search_changed(self, text: str):
        query = text.strip().lower()
        if not query:
            return
        keywords = {
            0: ["general", "hotkey", "shortcut", "paste", "clipboard", "pill", "command"],
            1: ["notes", "lecture", "meeting", "summary", "formula", "study", "smart"],
            2: ["tasks", "actions", "deadline", "calendar", "todo", "schedule", "ics"],
            3: ["memory", "ask", "search", "query", "question", "retrieval", "recall"],
            4: ["voice", "audio", "mic", "microphone", "input", "device", "meter", "level"],
            5: ["ai", "model", "whisper", "ollama", "groq", "openai", "token", "compute"],
            6: ["vocab", "vocabulary", "word", "jargon", "acronym", "dictionary"],
            7: ["edit", "mode", "instruction", "rewrite", "transform"],
            8: ["history", "log", "speech", "transcription", "recent"],
        }
        for page_idx, words in keywords.items():
            if any(query in w for w in words):
                self._switch_page(page_idx)
                break

    # ------------------ Page 0: General ------------------
    def _build_general_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("scrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(14)

        # Section 1: Dictation Shortcuts
        lbl_sec1 = QLabel("Dictation Shortcuts")
        lbl_sec1.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec1)

        card1 = SettingsCard()

        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "Both Enabled (Hold key or tap toggle)",
            "Hold-to-Talk (Hold key while speaking)",
            "Press-to-Toggle (Tap key to start/stop)"
        ])
        self.combo_mode.setFixedWidth(280)
        card1.add_row(SettingsRow(
            "Dictation Trigger Mode",
            "Choose between holding down the key while speaking, tapping once to start and tap again to finish, or both.",
            self.combo_mode
        ))

        self.combo_hold_key = QComboBox()
        self.combo_hold_key.addItems(["alt_r", "alt_l", "f8", "f9", "f10", "f11", "f12", "ctrl_l", "ctrl_r", "space", "caps_lock"])
        self.combo_hold_key.setFixedWidth(130)
        card1.add_row(SettingsRow(
            "Hold Shortcut Key",
            "Physical key to hold down while speaking (e.g. Right Alt). Releasing triggers instant transcription.",
            self.combo_hold_key
        ))

        self.combo_toggle_key = QComboBox()
        self.combo_toggle_key.addItems(["f8", "f9", "f10", "f11", "f12", "alt_r", "alt_l", "caps_lock"])
        self.combo_toggle_key.setFixedWidth(130)
        card1.add_row(SettingsRow(
            "Toggle Shortcut Key",
            "Alternative hands-free key to start and stop dictation sessions.",
            self.combo_toggle_key
        ))
        layout.addWidget(card1)

        # Section 2: Clipboard & Pasting
        lbl_sec2 = QLabel("Pasting & Clipboard")
        lbl_sec2.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec2)

        card2 = SettingsCard()

        self.sw_auto_paste = SwitchToggle()
        card2.add_row(SettingsRow(
            "Auto-paste text",
            "Simulates Ctrl+V into the currently active window immediately after transcription finishes.",
            self.sw_auto_paste
        ))

        self.sw_restore_clip = SwitchToggle()
        card2.add_row(SettingsRow(
            "Restore previous clipboard content",
            "Preserves your existing clipboard history and restores previous text after auto-pasting completes.",
            self.sw_restore_clip
        ))

        self.sw_context_aware = SwitchToggle()
        card2.add_row(SettingsRow(
            "Context-aware dictation",
            "Inspects the active window title to adapt formatting (e.g. email, IDE code comment, or chat).",
            self.sw_context_aware
        ))

        self.sw_command_mode = SwitchToggle()
        card2.add_row(SettingsRow(
            "Autonomous Command Mode",
            "Automatically recognizes calendar scheduling ('Schedule meeting at 4 PM') and task creation ('Remind me to submit assignment') instead of plain dictation.",
            self.sw_command_mode
        ))
        layout.addWidget(card2)

        # Section 3: Overlay Notch
        lbl_sec3 = QLabel("Floating Notch Visualizer")
        lbl_sec3.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec3)

        card3 = SettingsCard()

        self.btn_reset_pos = QPushButton("Reset Position")
        self.btn_reset_pos.setObjectName("secondaryBtn")
        self.btn_reset_pos.clicked.connect(self._reset_overlay_pos)

        card3.add_row(SettingsRow(
            "Overlay Position",
            "You can drag the top notch pill anywhere on your screen. Tap to restore default top center docking.",
            self.btn_reset_pos
        ))
        layout.addWidget(card3)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------ Page 1: Voice & Audio ------------------
    def _build_voice_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("scrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(14)

        lbl_sec = QLabel("Microphone & Audio Input")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        card = SettingsCard()

        # Device selection row with Refresh
        dev_widget = QWidget()
        dev_layout = QHBoxLayout(dev_widget)
        dev_layout.setContentsMargins(0, 0, 0, 0)
        dev_layout.setSpacing(8)

        self.combo_mic = QComboBox()
        self.combo_mic.setFixedWidth(240)
        self._populate_mic_devices()
        dev_layout.addWidget(self.combo_mic)

        self.btn_refresh_mics = QPushButton("Refresh")
        self.btn_refresh_mics.setObjectName("secondaryBtn")
        self.btn_refresh_mics.clicked.connect(self._populate_mic_devices)
        dev_layout.addWidget(self.btn_refresh_mics)

        card.add_row(SettingsRow(
            "Recording Device",
            "Select the microphone input device used to capture your speech.",
            dev_widget
        ))

        # Mic Test Row
        test_widget = QWidget()
        test_layout = QHBoxLayout(test_widget)
        test_layout.setContentsMargins(0, 0, 0, 0)
        test_layout.setSpacing(12)

        self.mic_level_bar = QProgressBar()
        self.mic_level_bar.setRange(0, 100)
        self.mic_level_bar.setValue(0)
        self.mic_level_bar.setFixedWidth(180)
        test_layout.addWidget(self.mic_level_bar)

        self.btn_test_mic = QPushButton("Test Mic")
        self.btn_test_mic.setObjectName("secondaryBtn")
        self.btn_test_mic.setCheckable(True)
        self.btn_test_mic.toggled.connect(self._toggle_mic_test)
        test_layout.addWidget(self.btn_test_mic)

        card.add_row(SettingsRow(
            "Microphone Test & Meter",
            "Check audio sensitivity and ensure your voice input is detected properly.",
            test_widget
        ))
        layout.addWidget(card)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------ Page 2: AI Models ------------------
    def _build_models_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("scrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(14)

        # Section 1: Local Whisper & Ollama
        lbl_sec1 = QLabel("Local Offline Inference (Private & Fast)")
        lbl_sec1.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec1)

        card1 = SettingsCard()

        self.combo_whisper_model = QComboBox()
        self.combo_whisper_model.addItems(["tiny.en", "base.en", "small.en", "small", "medium"])
        self.combo_whisper_model.setFixedWidth(130)
        card1.add_row(SettingsRow(
            "Faster-Whisper Model",
            "Speech-to-text model running 100% locally and privately on your computer CPU.",
            self.combo_whisper_model
        ))

        self.combo_compute_type = QComboBox()
        self.combo_compute_type.addItems(["int8", "float32"])
        self.combo_compute_type.setFixedWidth(130)
        card1.add_row(SettingsRow(
            "Whisper Compute Type",
            "Quantization precision (int8 offers optimal speed and low memory usage).",
            self.combo_compute_type
        ))

        ollama_widget = QWidget()
        o_layout = QHBoxLayout(ollama_widget)
        o_layout.setContentsMargins(0, 0, 0, 0)
        o_layout.setSpacing(8)

        self.combo_ollama_model = QComboBox()
        self.combo_ollama_model.setFixedWidth(180)
        self._populate_ollama_models()
        o_layout.addWidget(self.combo_ollama_model)

        self.btn_test_ollama = QPushButton("Test Ollama")
        self.btn_test_ollama.setObjectName("secondaryBtn")
        self.btn_test_ollama.clicked.connect(self._test_ollama_connection)
        o_layout.addWidget(self.btn_test_ollama)

        card1.add_row(SettingsRow(
            "Local Ollama Model",
            "LLM used for intelligent speech cleanup, punctuation, and grammar correction.",
            ollama_widget
        ))

        self.sw_postprocessing = SwitchToggle()
        card1.add_row(SettingsRow(
            "Enable LLM Post-Processing",
            "Automatically removes filler words ('um', 'uh', 'you know'), corrects slips of the tongue, and formats text.",
            self.sw_postprocessing
        ))
        layout.addWidget(card1)

        # Section 2: Cloud Fallbacks
        lbl_sec2 = QLabel("Cloud API Providers (Optional)")
        lbl_sec2.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec2)

        card2 = SettingsCard()

        self.txt_groq_key = QLineEdit()
        self.txt_groq_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_groq_key.setPlaceholderText("gsk_...")
        self.txt_groq_key.setFixedWidth(240)
        card2.add_row(SettingsRow(
            "Groq API Key",
            "Optional ultra-fast cloud LLM fallback for instant processing without local Ollama.",
            self.txt_groq_key
        ))

        self.txt_openai_key = QLineEdit()
        self.txt_openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_openai_key.setPlaceholderText("sk-...")
        self.txt_openai_key.setFixedWidth(240)
        card2.add_row(SettingsRow(
            "OpenAI API Key",
            "Optional OpenAI API key for cloud Whisper and GPT-4o-mini processing.",
            self.txt_openai_key
        ))
        layout.addWidget(card2)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------ Page 3: Vocabulary ------------------
    def _build_vocab_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("scrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(14)

        lbl_sec = QLabel("Custom Vocabulary & Technical Terms")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        card = SettingsCard()

        add_widget = QWidget()
        a_layout = QHBoxLayout(add_widget)
        a_layout.setContentsMargins(0, 0, 0, 0)
        a_layout.setSpacing(8)

        self.txt_new_vocab = QLineEdit()
        self.txt_new_vocab.setPlaceholderText("Enter word or acronym...")
        self.txt_new_vocab.setFixedWidth(220)
        self.txt_new_vocab.returnPressed.connect(self._add_vocabulary)
        a_layout.addWidget(self.txt_new_vocab)

        self.btn_add_vocab = QPushButton("Add Word")
        self.btn_add_vocab.setObjectName("secondaryBtn")
        self.btn_add_vocab.clicked.connect(self._add_vocabulary)
        a_layout.addWidget(self.btn_add_vocab)

        card.add_row(SettingsRow(
            "Add New Word",
            "Nomi will preserve exact spelling for names, brand names, technical jargon, or acronyms.",
            add_widget
        ))
        layout.addWidget(card)

        lbl_list = QLabel("Preserved Words")
        lbl_list.setObjectName("sectionHeader")
        layout.addWidget(lbl_list)

        self.list_vocab = QListWidget()
        self.list_vocab.setFixedHeight(220)
        layout.addWidget(self.list_vocab)

        self.btn_delete_vocab = QPushButton("Remove Selected Word")
        self.btn_delete_vocab.setObjectName("dangerBtn")
        self.btn_delete_vocab.setFixedWidth(180)
        self.btn_delete_vocab.clicked.connect(self._remove_vocabulary)
        layout.addWidget(self.btn_delete_vocab)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------ Page 4: Edit Mode ------------------
    def _build_edit_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        container.setObjectName("scrollContent")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(14)

        lbl_sec = QLabel("Voice-Driven Text Transformation")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        card1 = SettingsCard()

        self.sw_edit_mode = SwitchToggle()
        card1.add_row(SettingsRow(
            "Enable Edit Mode",
            "Allows you to highlight existing text in any application and speak instructions to rewrite or transform it.",
            self.sw_edit_mode
        ))
        layout.addWidget(card1)

        lbl_how = QLabel("How Edit Mode Works")
        lbl_how.setObjectName("sectionHeader")
        layout.addWidget(lbl_how)

        card2 = SettingsCard()
        guide_widget = QWidget()
        g_layout = QVBoxLayout(guide_widget)
        g_layout.setContentsMargins(18, 16, 18, 16)
        g_layout.setSpacing(10)

        steps = [
            ("1. Highlight Any Text", "Select any paragraph, email draft, or code in your active application."),
            ("2. Hold Dictation Key", "Press and hold your hotkey, then speak an instruction (e.g. 'Make this more professional', 'Turn into bullet points', 'Fix grammar')."),
            ("3. Release to Replace", "Nomi analyzes your highlighted text and instruction, then automatically pastes the transformed version in place.")
        ]

        for num_title, desc in steps:
            t = QLabel(num_title)
            t.setStyleSheet("font-size: 13.5px; font-weight: 500; color: #ECECEC;")
            d = QLabel(desc)
            d.setStyleSheet("font-size: 12px; color: #9B9B9B; margin-bottom: 4px;")
            g_layout.addWidget(t)
            g_layout.addWidget(d)

        card2.add_row(guide_widget)
        layout.addWidget(card2)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------ Page 5: History ------------------
    def _build_history_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 18, 24)
        layout.setSpacing(12)

        lbl_sec = QLabel("Recent Dictation History")
        lbl_sec.setObjectName("sectionHeader")
        layout.addWidget(lbl_sec)

        self.table_history = QTableWidget(0, 4)
        self.table_history.setHorizontalHeaderLabels(["App", "Raw Speech", "Cleaned Result", "Time"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_history.itemDoubleClicked.connect(lambda _: self._copy_selected_history())
        layout.addWidget(self.table_history)

        btn_row = QHBoxLayout()
        self.btn_copy_history = QPushButton("Copy Selected Text")
        self.btn_copy_history.setObjectName("secondaryBtn")
        self.btn_copy_history.clicked.connect(self._copy_selected_history)
        btn_row.addWidget(self.btn_copy_history)

        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.setObjectName("dangerBtn")
        self.btn_clear_history.clicked.connect(self._clear_history)
        btn_row.addWidget(self.btn_clear_history)
        btn_row.addStretch()

        layout.addLayout(btn_row)
        return container

    # ------------------ Logic & Storage ------------------
    def _populate_mic_devices(self):
        saved_idx = None
        if hasattr(self, 'combo_mic') and self.combo_mic.count() > 0:
            saved_idx = self.combo_mic.currentData()
        if saved_idx is None:
            saved_idx = app_config.get("input_device_index", None)

        self.combo_mic.clear()
        self.combo_mic.addItem("Default Microphone", None)
        devices = AudioRecorder.get_input_devices()
        for dev in devices:
            self.combo_mic.addItem(f"{dev['name']} [ID: {dev['index']}]", dev['index'])

        if saved_idx is not None:
            idx = self.combo_mic.findData(saved_idx)
            if idx >= 0:
                self.combo_mic.setCurrentIndex(idx)
            else:
                self.combo_mic.setCurrentIndex(0)
        else:
            self.combo_mic.setCurrentIndex(0)

    def _populate_ollama_models(self):
        saved = app_config.get("ollama_model", "llama3.2:latest")
        self.combo_ollama_model.clear()
        models = OllamaPostProcessor.get_installed_models()
        if models:
            self.combo_ollama_model.addItems(models)
        else:
            self.combo_ollama_model.addItem("llama3.2:latest")

        idx = self.combo_ollama_model.findText(saved)
        if idx >= 0:
            self.combo_ollama_model.setCurrentIndex(idx)
        elif saved:
            self.combo_ollama_model.addItem(saved)
            self.combo_ollama_model.setCurrentIndex(self.combo_ollama_model.count() - 1)

    def _load_values(self):
        # 1. Hotkeys & Mode
        mode = app_config.get("hotkey_mode", "both")
        if mode == "both":
            self.combo_mode.setCurrentIndex(0)
        elif mode == "hold":
            self.combo_mode.setCurrentIndex(1)
        elif mode == "toggle":
            self.combo_mode.setCurrentIndex(2)
        else:
            self.combo_mode.setCurrentIndex(0)

        hold_k = app_config.get("hold_hotkey", "alt_r")
        idx_hold = self.combo_hold_key.findText(hold_k)
        if idx_hold >= 0:
            self.combo_hold_key.setCurrentIndex(idx_hold)
        else:
            self.combo_hold_key.addItem(hold_k)
            self.combo_hold_key.setCurrentIndex(self.combo_hold_key.count() - 1)

        toggle_k = app_config.get("toggle_hotkey", "f8")
        idx_toggle = self.combo_toggle_key.findText(toggle_k)
        if idx_toggle >= 0:
            self.combo_toggle_key.setCurrentIndex(idx_toggle)
        else:
            self.combo_toggle_key.addItem(toggle_k)
            self.combo_toggle_key.setCurrentIndex(self.combo_toggle_key.count() - 1)

        # 2. Paste & Context Switches
        self.sw_auto_paste.setChecked(bool(app_config.get("auto_paste", True)))
        self.sw_restore_clip.setChecked(bool(app_config.get("restore_clipboard", True)))
        self.sw_context_aware.setChecked(bool(app_config.get("context_aware", True)))
        self.sw_command_mode.setChecked(bool(app_config.get("command_mode", True)))

        # 3. Audio & Mic Selection
        saved_dev = app_config.get("input_device_index", None)
        if saved_dev is not None:
            idx_dev = self.combo_mic.findData(saved_dev)
            if idx_dev >= 0:
                self.combo_mic.setCurrentIndex(idx_dev)
            else:
                self.combo_mic.setCurrentIndex(0)
        else:
            self.combo_mic.setCurrentIndex(0)

        # 4. AI & Whisper Models
        wm = app_config.get("whisper_model", "tiny.en")
        idx_wm = self.combo_whisper_model.findText(wm)
        if idx_wm >= 0:
            self.combo_whisper_model.setCurrentIndex(idx_wm)
        else:
            self.combo_whisper_model.addItem(wm)
            self.combo_whisper_model.setCurrentIndex(self.combo_whisper_model.count() - 1)

        ct = app_config.get("whisper_compute_type", "int8")
        idx_ct = self.combo_compute_type.findText(ct)
        if idx_ct >= 0:
            self.combo_compute_type.setCurrentIndex(idx_ct)
        else:
            self.combo_compute_type.addItem(ct)
            self.combo_compute_type.setCurrentIndex(self.combo_compute_type.count() - 1)

        om = app_config.get("ollama_model", "llama3.2:latest")
        idx_om = self.combo_ollama_model.findText(om)
        if idx_om >= 0:
            self.combo_ollama_model.setCurrentIndex(idx_om)
        elif om:
            self.combo_ollama_model.addItem(om)
            self.combo_ollama_model.setCurrentIndex(self.combo_ollama_model.count() - 1)

        self.sw_postprocessing.setChecked(bool(app_config.get("postprocessing_enabled", True)))
        self.sw_edit_mode.setChecked(bool(app_config.get("edit_mode_enabled", False)))

        # 5. Cloud API Keys
        self.txt_groq_key.setText(app_config.get("groq_api_key", ""))
        self.txt_openai_key.setText(app_config.get("openai_api_key", ""))

        # 6. Vocabulary
        self._refresh_vocabulary_list()

        # 7. Persistent History
        self._load_history()

    def _save_values(self, silent: bool = False):
        idx = self.combo_mode.currentIndex()
        if idx == 0:
            mode = "both"
        elif idx == 1:
            mode = "hold"
        else:
            mode = "toggle"
        app_config.set("hotkey_mode", mode)
        app_config.set("hold_hotkey", self.combo_hold_key.currentText().strip())
        app_config.set("toggle_hotkey", self.combo_toggle_key.currentText().strip())

        app_config.set("auto_paste", self.sw_auto_paste.isChecked())
        app_config.set("restore_clipboard", self.sw_restore_clip.isChecked())
        app_config.set("context_aware", self.sw_context_aware.isChecked())
        app_config.set("command_mode", self.sw_command_mode.isChecked())

        app_config.set("whisper_model", self.combo_whisper_model.currentText().strip())
        app_config.set("whisper_compute_type", self.combo_compute_type.currentText().strip())
        app_config.set("ollama_model", self.combo_ollama_model.currentText().strip())
        app_config.set("postprocessing_enabled", self.sw_postprocessing.isChecked())
        app_config.set("edit_mode_enabled", self.sw_edit_mode.isChecked())

        app_config.set("groq_api_key", self.txt_groq_key.text().strip())
        app_config.set("openai_api_key", self.txt_openai_key.text().strip())

        dev_idx = self.combo_mic.currentData()
        app_config.set("input_device_index", dev_idx)

        self.settings_changed.emit()

        if not silent:
            QMessageBox.information(self, "Settings Saved", "All settings and preferences have been saved.")

    def _refresh_vocabulary_list(self):
        self.list_vocab.clear()
        vocab: List[str] = app_config.get("custom_vocabulary", [])
        for w in vocab:
            self.list_vocab.addItem(w)

    def _add_vocabulary(self):
        word = self.txt_new_vocab.text().strip()
        if not word:
            return
        if app_config.add_vocabulary(word):
            self._refresh_vocabulary_list()
            self.txt_new_vocab.clear()
        else:
            QMessageBox.information(self, "Vocabulary", f"'{word}' is already in your vocabulary list.")

    def _remove_vocabulary(self):
        current_item = self.list_vocab.currentItem()
        if current_item:
            word = current_item.text()
            app_config.remove_vocabulary(word)
            self._refresh_vocabulary_list()
        else:
            QMessageBox.information(self, "Vocabulary", "Please select a word from the list to remove.")

    def _toggle_mic_test(self, checked: bool):
        if checked:
            dev_idx = self.combo_mic.currentData()
            self._test_recorder = AudioRecorder(device_index=dev_idx)
            self._test_recorder.audio_level_updated.connect(self._on_test_mic_level)
            self._test_recorder.start()
            self.btn_test_mic.setText("Stop Test")
        else:
            if self._test_recorder:
                self._test_recorder.stop()
                self._test_recorder = None
            self.btn_test_mic.setText("Test Mic")
            self.mic_level_bar.setValue(0)

    def _on_test_mic_level(self, rms: float, preview):
        level = min(100, int(rms * 400))
        self.mic_level_bar.setValue(level)

    def _test_ollama_connection(self):
        models = OllamaPostProcessor.get_installed_models()
        if models:
            self.combo_ollama_model.clear()
            self.combo_ollama_model.addItems(models)
            saved = app_config.get("ollama_model", "llama3.2:latest")
            idx = self.combo_ollama_model.findText(saved)
            if idx >= 0:
                self.combo_ollama_model.setCurrentIndex(idx)
            QMessageBox.information(
                self,
                "Ollama Connected",
                f"Successfully connected to Ollama.\nInstalled models:\n• " + "\n• ".join(models)
            )
        else:
            QMessageBox.warning(
                self,
                "Ollama Not Found",
                "Could not connect to local Ollama on http://localhost:11434.\n\n"
                "Please make sure the Ollama desktop service is running."
            )

    def _load_history(self):
        self.table_history.setRowCount(0)
        entries = app_config.load_history()
        for item in entries:
            self._insert_history_row(
                item.get("app", "Unknown"),
                item.get("raw", ""),
                item.get("cleaned", ""),
                item.get("time", "")
            )

    def _insert_history_row(self, app_name: str, raw_speech: str, cleaned_result: str, timestamp_str: str):
        row = self.table_history.rowCount()
        self.table_history.insertRow(row)
        self.table_history.setItem(row, 0, QTableWidgetItem(app_name or "Unknown"))
        self.table_history.setItem(row, 1, QTableWidgetItem(raw_speech))
        self.table_history.setItem(row, 2, QTableWidgetItem(cleaned_result))
        self.table_history.setItem(row, 3, QTableWidgetItem(timestamp_str))

    def add_history_entry(self, app_name: str, raw_speech: str, cleaned_result: str, timestamp_str: str):
        self._insert_history_row(app_name, raw_speech, cleaned_result, timestamp_str)
        history = app_config.load_history()
        history.append({
            "app": app_name or "Unknown",
            "raw": raw_speech,
            "cleaned": cleaned_result,
            "time": timestamp_str
        })
        app_config.save_history(history)

    def _copy_selected_history(self):
        row = self.table_history.currentRow()
        if row >= 0:
            cleaned_item = self.table_history.item(row, 2)
            raw_item = self.table_history.item(row, 1)
            text_to_copy = cleaned_item.text() if cleaned_item and cleaned_item.text() else (raw_item.text() if raw_item else "")
            if text_to_copy:
                pyperclip.copy(text_to_copy)
                preview = text_to_copy[:60] + "..." if len(text_to_copy) > 60 else text_to_copy
                QMessageBox.information(self, "Copied", f"Copied to clipboard:\n\n\"{preview}\"")
            else:
                QMessageBox.information(self, "Empty", "The selected entry contains no text.")
        else:
            QMessageBox.information(self, "Selection Required", "Please click or select a row in the table first.")

    def _clear_history(self):
        self.table_history.setRowCount(0)
        app_config.save_history([])
        QMessageBox.information(self, "History Cleared", "Dictation history has been cleared.")

    def _reset_overlay_pos(self):
        self.reset_position_requested.emit()
        QMessageBox.information(
            self,
            "Position Reset",
            "The overlay pill has been reset to the default top-notch position."
        )

    def closeEvent(self, event):
        if self._test_recorder:
            self._test_recorder.stop()
            self._test_recorder = None
        self._save_values(silent=True)
        event.accept()
