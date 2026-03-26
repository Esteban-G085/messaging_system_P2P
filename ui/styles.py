# ──────────────────────────────────────────────
#  ui/styles.py  –  Estilos Qt (dark theme)
# ──────────────────────────────────────────────

COLORS = {
    "connected":    "#00FF88",
    "disconnected": "#666666",
    "connecting":   "#FFB800",
    "error":        "#FF6B6B",
    "delivered":    "#00FF88",
    "read":         "#4A90E2",
    "bg_main":      "#121212",
    "bg_panel":     "#1E1E1E",
    "bg_bubble_me": "#1A3A2A",
    "bg_bubble_th": "#252525",
    "text":         "#FFFFFF",
    "text_muted":   "#888888",
    "border":       "#333333",
    "accent":       "#00FF88",
}

MAIN_STYLE = """
/* ── Global ───────────────────────── */
QMainWindow, QWidget {
    background-color: #121212;
    color: #FFFFFF;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10pt;
}

/* ── Listas ───────────────────────── */
QListWidget {
    background-color: #1E1E1E;
    border: none;
    border-radius: 4px;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #2C2C2C;
    color: #00FF88;
}
QListWidget::item:hover:!selected {
    background-color: #252525;
}

/* ── Inputs ───────────────────────── */
QLineEdit {
    background-color: #1E1E1E;
    color: #FFFFFF;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 6px 10px;
}
QLineEdit:focus {
    border: 1px solid #00FF88;
}
QLineEdit::placeholder {
    color: #555555;
}

/* ── Botones ──────────────────────── */
QPushButton {
    background-color: #00FF88;
    color: #121212;
    border: none;
    border-radius: 4px;
    padding: 7px 16px;
    font-weight: 600;
}
QPushButton:hover    { background-color: #00CC6A; }
QPushButton:pressed  { background-color: #009950; }
QPushButton:disabled { background-color: #2A2A2A; color: #555555; }

/* ── Scroll ───────────────────────── */
QScrollArea  { background-color: #121212; border: none; }
QScrollBar:vertical {
    background-color: #1E1E1E;
    width: 6px; border-radius: 3px; margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #3A3A3A;
    border-radius: 3px; min-height: 30px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

/* ── Splitter ─────────────────────── */
QSplitter::handle { background-color: #2A2A2A; width: 1px; }

/* ── Dialog ───────────────────────── */
QDialog { background-color: #1A1A1A; }
"""
