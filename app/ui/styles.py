"""
ChatGPT Desktop Neutral Dark Theme for Nomi Windows.
Clean monochrome aesthetic with no blue tint, matching ChatGPT desktop settings.
"""

import os

_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets")).replace("\\", "/")
CHEVRON_SVG = f"{_ASSETS_DIR}/chevron.svg"
SEARCH_SVG = f"{_ASSETS_DIR}/search.svg"

DARK_THEME_QSS = f"""
/* Global typography and base defaults */
QWidget {{
    font-family: 'Segoe UI Variable Display', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #ECECEC;
    font-size: 13px;
    selection-background-color: #2F2F2F;
    selection-color: #FFFFFF;
}}

/* Translucent Main Window for Acrylic blur */
QMainWindow, QDialog {{
    background: transparent;
}}

/* Central ChatGPT Canvas */
QWidget#centralWidget {{
    background-color: #212121;
    border: 1px solid #2E2E2E;
    border-radius: 10px;
}}

/* Left Sidebar Panel */
QFrame#sidebarFrame {{
    background-color: #171717;
    border-right: 1px solid #2B2B2B;
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
}}

/* Search Bar in Sidebar */
QLineEdit#searchBar {{
    background-color: #212121;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 7px 12px;
    color: #ECECEC;
    font-size: 13px;
}}

QLineEdit#searchBar:hover {{
    border-color: #444444;
    background-color: #262626;
}}

QLineEdit#searchBar:focus {{
    border-color: #666666;
    background-color: #262626;
}}

/* Right Content Area */
QScrollArea {{
    background: transparent;
    border: none;
}}

QWidget#scrollContent {{
    background: transparent;
}}

/* Page and Section Titles */
QLabel#pageTitle {{
    font-size: 26px;
    font-weight: 600;
    color: #FFFFFF;
    letter-spacing: -0.2px;
}}

QLabel#sectionHeader {{
    font-size: 14px;
    font-weight: 600;
    color: #E5E5E5;
    margin-top: 14px;
    margin-bottom: 4px;
}}

/* Inputs & Dropdowns */
QLineEdit, QComboBox, QSpinBox {{
    background-color: #2F2F2F;
    border: 1px solid #404040;
    border-radius: 8px;
    padding: 7px 12px;
    color: #ECECEC;
    font-size: 13px;
}}

QLineEdit:hover, QComboBox:hover {{
    border-color: #555555;
    background-color: #363636;
}}

QLineEdit:focus, QComboBox:focus {{
    border-color: #777777;
    background-color: #363636;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
}}

QComboBox::down-arrow {{
    image: url('{CHEVRON_SVG}');
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: #242424;
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    padding: 4px;
    color: #ECECEC;
    selection-background-color: #333333;
    selection-color: #FFFFFF;
    outline: none;
}}

/* Buttons */
QPushButton#saveBtn {{
    background-color: #FFFFFF;
    color: #171717;
    border: none;
    border-radius: 8px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#saveBtn:hover {{
    background-color: #E5E5E5;
}}

QPushButton#saveBtn:pressed {{
    background-color: #CCCCCC;
}}

QPushButton#secondaryBtn {{
    background-color: #2F2F2F;
    color: #ECECEC;
    border: 1px solid #404040;
    border-radius: 8px;
    padding: 7px 15px;
    font-weight: 500;
}}

QPushButton#secondaryBtn:hover {{
    background-color: #383838;
    border-color: #505050;
    color: #FFFFFF;
}}

QPushButton#secondaryBtn:checked {{
    background-color: #3D3D3D;
    border-color: #666666;
    color: #FFFFFF;
}}

QPushButton#dangerBtn {{
    background-color: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.30);
    border-radius: 8px;
    padding: 7px 15px;
    font-weight: 500;
}}

QPushButton#dangerBtn:hover {{
    background-color: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.50);
    color: #FFFFFF;
}}

/* Tables & Lists */
QTableWidget, QListWidget {{
    background-color: #1C1C1C;
    border: 1px solid #2E2E2E;
    border-radius: 8px;
    gridline-color: #2A2A2A;
    color: #ECECEC;
    padding: 4px;
}}

QTableWidget::item, QListWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    color: #ECECEC;
}}

QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: #2F2F2F;
    color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: #282828;
    color: #9E9E9E;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #333333;
    font-weight: 600;
    font-size: 12px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: #2F2F2F;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: transparent;
    height: 8px;
}}

QProgressBar::chunk {{
    background-color: #2563EB;
    border-radius: 4px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 4px 2px 4px 0;
}}

QScrollBar::handle:vertical {{
    background: #383838;
    min-height: 28px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: #4E4E4E;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* Tooltips */
QToolTip {{
    background-color: #1F1F1F;
    border: 1px solid #3E3E3E;
    color: #ECECEC;
    padding: 5px 9px;
    border-radius: 6px;
    font-size: 12px;
}}

/* Text Browser & Markdown Notes */
QTextBrowser, QTextEdit {{
    background-color: #1A1A1A;
    color: #ECECEC;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 12px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13.5px;
    line-height: 1.5;
}}

QPushButton#primaryBtn {{
    background-color: #10A37F;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}}

QPushButton#primaryBtn:hover {{
    background-color: #1A7F64;
}}

QPushButton#primaryBtn:pressed {{
    background-color: #0E6850;
}}
"""
