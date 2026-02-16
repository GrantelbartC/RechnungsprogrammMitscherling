COLORS = {
    "bg": "#F7F8FA",
    "surface": "#FFFFFF",
    "border": "#E5E7EB",
    "primary": "#4F46E5",
    "primary_hover": "#4338CA",
    "text": "#111827",
    "text_secondary": "#6B7280",
    "danger": "#DC2626",
    "danger_hover": "#B91C1C",
    "success": "#059669",
    "warn": "#D97706",
    "badge_green_bg": "#F0FDF4",
    "badge_green_border": "#BBF7D0",
    "header_bg": "#F3F4F6",
    "line_color": "#D1D5DB",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    font-family: "Segoe UI";
    font-size: 10pt;
    color: {COLORS['text']};
}}

QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg']};
    border-radius: 8px;
}}

QTabBar::tab {{
    padding: 8px 20px;
    margin-right: 2px;
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
    font-size: 10pt;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
    color: white;
    font-weight: bold;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['header_bg']};
}}

QPushButton {{
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    font-size: 10pt;
}}

QPushButton:hover {{
    background-color: {COLORS['header_bg']};
}}

QPushButton[cssClass="primary"] {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
}}

QPushButton[cssClass="primary"]:hover {{
    background-color: {COLORS['primary_hover']};
}}

QPushButton[cssClass="danger"] {{
    background-color: {COLORS['danger']};
    color: white;
    border: none;
}}

QPushButton[cssClass="danger"]:hover {{
    background-color: {COLORS['danger_hover']};
}}

QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
    padding: 6px 10px;
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    background-color: {COLORS['surface']};
    font-size: 10pt;
    color: {COLORS['text']};
}}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus,
QDoubleSpinBox:focus, QDateEdit:focus {{
    border: 2px solid {COLORS['primary']};
}}

QTableWidget {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['surface']};
    gridline-color: {COLORS['border']};
    selection-background-color: #EEF2FF;
    selection-color: {COLORS['text']};
}}

QTableWidget::item {{
    padding: 6px;
}}

QHeaderView::section {{
    background-color: {COLORS['header_bg']};
    padding: 8px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: bold;
    color: {COLORS['text_secondary']};
}}

QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: {COLORS['surface']};
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {COLORS['text']};
}}

QStatusBar {{
    background-color: {COLORS['surface']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_secondary']};
    font-size: 9pt;
}}

QLabel[cssClass="heading"] {{
    font-size: 14pt;
    font-weight: bold;
    color: {COLORS['text']};
}}

QLabel[cssClass="subheading"] {{
    font-size: 11pt;
    font-weight: bold;
    color: {COLORS['text']};
}}

QLabel[cssClass="secondary"] {{
    color: {COLORS['text_secondary']};
    font-size: 9pt;
}}

QLabel[cssClass="badge-success"] {{
    background-color: {COLORS['badge_green_bg']};
    border: 1px solid {COLORS['badge_green_border']};
    border-radius: 4px;
    padding: 2px 8px;
    color: {COLORS['success']};
    font-size: 9pt;
    font-weight: bold;
}}

QLabel[cssClass="badge-warn"] {{
    background-color: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 4px;
    padding: 2px 8px;
    color: {COLORS['warn']};
    font-size: 9pt;
    font-weight: bold;
}}

QLabel[cssClass="badge-primary"] {{
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 4px;
    padding: 2px 8px;
    color: {COLORS['primary']};
    font-size: 9pt;
    font-weight: bold;
}}

QScrollArea {{
    border: none;
    background-color: {COLORS['bg']};
}}

QCheckBox {{
    spacing: 8px;
    font-size: 10pt;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {COLORS['border']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}
"""
