# Nomi

<p align="center">
  <strong>AI-Powered Personal Context Assistant for Voice Understanding, Smart Notes & Autonomous Task Execution</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/GUI-PyQt6-green.svg" alt="PyQt6">
  <img src="https://img.shields.io/badge/STT-Faster--Whisper-orange.svg" alt="Faster-Whisper">
  <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20Llama%203.2-purple.svg" alt="Ollama">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg" alt="Windows">
  <img src="https://img.shields.io/badge/Privacy-100%25%20Local%20%26%20Offline-brightgreen.svg" alt="Local AI">
</p>

<p align="center">
  <em>"Listen → Understand → Remember → Act"</em>
</p>

---

## Overview

**Nomi** is an intelligent context-aware personal AI assistant designed to eliminate repetitive digital interactions and transform real-world spoken information into structured knowledge and automated actions.

Rather than forcing you to open separate note-taking apps, calendar tools, task managers, and search engines, Nomi unifies the entire workflow into a single, elegant desktop companion:

1. **Listen:** High-fidelity speech capture with Voice Activity Detection (VAD) and offline Faster-Whisper speech-to-text.
2. **Understand:** Context-aware LLM reasoning via local Ollama (`llama3.2`) or ultra-fast cloud models (Groq / OpenAI).
3. **Remember:** Automatic generation of structured lecture/meeting notes, action items, and searchable personal AI memory.
4. **Act:** Autonomous agent tool execution—scheduling calendar events (`.ics`), extracting deadlines, and voice-typing directly into active applications.

---

## Key Features

### 🎓 Smart Notes Studio (Lecture & Meeting Mode)
- **Long-Form Audio Capture:** Continuous recording designed for classroom lectures, team meetings, and research sessions.
- **Automated Academic Structuring:** Formats raw spoken transcripts into a comprehensive study schema:
  - 📌 **Topic Summary:** Coherent executive overview.
  - 💡 **Key Concepts:** Core ideas with clear definitions.
  - 📐 **Definitions & Formulas:** Equations and technical terminology highlighted in monospace blocks.
  - 🎯 **Important Points:** Key takeaways and examination highlights.
  - ❓ **Revision Questions:** Active-recall study questions to test understanding.
  - ✅ **Extracted Tasks:** Deadlines, homework, and commitments automatically registered in your task tracker.
- **Export & Sharing:** One-click copy or export to Markdown (`.md`) and plain text.

### ⚡ Autonomous Command Mode & Tool Execution
- **Voice-Driven Actions:** Speak naturally (*"Schedule a meeting with Professor Smith tomorrow at 4 PM"* or *"Remind me to submit the assignment by Friday"*).
- **Intent Classification:** Identifies whether your speech is meant for typing, calendar scheduling, or task creation.
- **Calendar Integration:** Automatically generates standard iCalendar (`.ics`) files and launches your system calendar (Google Calendar, Outlook, Windows Calendar) for instant confirmation.

### 🧠 Searchable AI Memory (Context Retrieval & Q&A)
- **Natural Language Querying:** Ask questions across all your past lectures, classes, meetings, and speech history.
  - *"What was explained about CPU scheduling algorithms last week?"*
  - *"What formulas were discussed in Friday's physics lecture?"*
- **Context Synthesis:** Retrieves matching notes, feeds the context to your local LLM, and provides answers citing the exact note title and date.

### 🎙️ System-Wide Dictation & Voice Typing
- **Type Anywhere:** Dictate at the speed of thought into VS Code, Notion, Slack, Word, Discord, browsers, or terminal windows.
- **Flexible Trigger Modes:**
  - **Hold-to-Talk:** Hold `Right Alt` while speaking; release to instantly transcribe and paste.
  - **Press-to-Toggle:** Tap `F8` to begin hands-free dictation; tap again to finish.
  - **Both Enabled:** Support both hold and toggle triggers simultaneously.
- **Context-Aware Formatting:** Inspects the active window title to adapt formatting (e.g., code comments and snake_case in IDEs vs. formal sentences in email clients).
- **Voice Edit Mode:** Highlight any existing text on screen, hold your hotkey, and speak an instruction (*"make this more professional"*, *"summarize into 3 bullets"*, *"fix grammar"*) to replace it in place.

### 🎨 ChatGPT Desktop Neutral Dark Aesthetic
- **Minimalist Studio:** Neutral dark `#212121` canvas, `#171717` sidebar, `#282828` cards, clean white primary accents, and vector monochrome icons.
- **Floating Notch Pill:** Translucent top-docked notch visualizer with a live liquid soundwave meter that never steals window focus. Drag it anywhere or double-click to reset.
- **100% Offline & Private:** Runs completely locally on your machine CPU/GPU using Faster-Whisper and Ollama. No subscription required, and no data leaves your PC.

---

## System Architecture

Nomi follows a modular 5-layer architecture:

```
Nomi Architecture
├── Layer 1: Client & UI Layer
│   ├── Floating Pill Overlay     # Frameless notch with live waveform visualizer
│   ├── Settings & Studio Hub     # ChatGPT-styled multi-page studio & manager
│   └── System Tray Integration   # Background agent & quick-launch menu
│
├── Layer 2: Audio & Capture Layer
│   ├── Audio Recorder            # 16kHz mono audio stream capture
│   └── Voice Activity Detection  # Silence trimming & speech segment detection
│
├── Layer 3: Speech Processing Layer
│   ├── Faster-Whisper Local      # Offline speech-to-text (int8 quantized)
│   └── Cloud Whisper Fallback    # Optional Groq / OpenAI Whisper endpoints
│
├── Layer 4: AI Context Engine
│   ├── Lecture Processor         # Academic note structuring & question synthesis
│   ├── Intent Agent              # Autonomous command classifier (Calendar / Tasks)
│   ├── Memory Engine             # Semantic retrieval & personal Q&A synthesizer
│   └── Post-Processing LLM       # Ollama Llama 3.2 speech cleanup & grammar polish
│
└── Layer 5: Data & Action Layer
    ├── Notes & Tasks Store       # Persistent JSON store (~/.nomi/notes.json, tasks.json)
    ├── iCalendar Generator       # Standard .ics calendar invitation engine
    └── Win32 Text Paster         # Virtual keystroke injection & clipboard restorer
```

---

## Directory Structure

```
d:/Nomi
├── app/
│   ├── config.py                 # Persistent settings & history manager (~/.nomi/)
│   ├── controller.py             # Central application lifecycle & agent coordinator
│   ├── audio/
│   │   ├── recorder.py           # PyAudio stream recorder & RMS meter
│   │   └── vad.py                # Energy-based Voice Activity Detection
│   ├── transcription/
│   │   ├── base.py               # Abstract speech-to-text provider interface
│   │   ├── local_whisper.py      # Faster-Whisper offline inference runner
│   │   └── cloud_whisper.py      # Cloud Whisper API fallback
│   ├── postprocessing/
│   │   ├── prompt.py             # Context prompts & formatting contracts
│   │   ├── ollama_client.py      # Local Ollama REST client
│   │   └── cloud_client.py       # Cloud LLM completion client (Groq / OpenAI)
│   ├── services/
│   │   ├── notes_service.py      # Smart Notes & Tasks persistence services
│   │   ├── lecture_processor.py  # LLM educational note restructuring engine
│   │   ├── intent_agent.py       # Autonomous command classification & .ics builder
│   │   └── memory_service.py     # Personal memory search & contextual Q&A engine
│   ├── system/
│   │   ├── context.py            # Active window title & process inspection
│   │   ├── hotkey.py             # Global keyboard hook listener (pynput)
│   │   └── paster.py             # Win32 clipboard & text injection
│   └── ui/
│       ├── assets/               # Crisp monochrome vector SVG icons
│       ├── components.py         # Custom PyQt6 SwitchToggle, SettingsCard, NavItem
│       ├── glass.py              # Windows 11 Acrylic blur integration
│       ├── pill_overlay.py       # Floating notch with live soundwave animation
│       ├── settings_window.py    # Main studio hub & configuration window
│       ├── smart_studio_pages.py # Smart Notes, Tasks, and Ask Memory UI pages
│       ├── styles.py             # ChatGPT Desktop dark theme stylesheet
│       └── tray_icon.py          # System tray icon & context actions
├── requirements.txt              # Python package dependencies
└── run.py                        # Application entrypoint
```

---

## Getting Started

### 1. Prerequisites
- **Python:** Version 3.10 or higher.
- **Ollama (Recommended for 100% offline private AI):**
  Install [Ollama](https://ollama.com/) and download the lightweight Llama 3.2 model:
  ```powershell
  ollama run llama3.2:latest
  ```

### 2. Installation
Clone the repository and install dependencies:
```powershell
git clone https://github.com/Armaan245/Nomi.git
cd Nomi
pip install -r requirements.txt
```

### 3. Launching Nomi
Run the application:
```powershell
python run.py
```

---

## Keyboard Shortcuts

| Shortcut | Mode | Description |
|---|---|---|
| **Hold `Right Alt`** | Hold-to-Talk | Hold down while speaking; release to automatically paste cleaned text into your active app. |
| **Tap `F8`** | Press-to-Toggle | Tap once to start dictation; tap again to transcribe and paste. |
| **Tap `Esc`** | Cancel | Immediately aborts the active recording without transcribing or pasting. |
| **Tray Icon** | Double-Click | Opens the Nomi Studio & Settings Hub. |

*All shortcuts, microphones, and trigger modes can be customized in the Settings dialog.*

---

## Roadmap

- [x] Faster-Whisper local offline speech-to-text
- [x] Live Speech-to-Text streaming preview on the floating top notch pill
- [x] Direct Unicode cursor injection ("Typed with bliss" via Windows `SendInput`)
- [x] Real-time soundwave notch pill overlay
- [x] Context-aware text cleanup (window title and app awareness)
- [x] Voice Edit Mode for rewriting highlighted text
- [x] Smart Lecture & Meeting Notes Generator (Summaries, Formulas, Questions)
- [x] Autonomous Command Mode (Task extraction & Calendar scheduling via `.ics`)
- [x] Searchable Personal AI Memory (Context retrieval & Q&A)
- [x] Neutral dark design system
- [ ] Mobile Application Gateway (FastAPI / WebSocket server for Android & iOS)
- [ ] Bluetooth Low Energy (BLE) integration for IoT wearable audio pendants

---

## License

This project is licensed under the MIT License.
