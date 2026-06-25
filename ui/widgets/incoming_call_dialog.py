# ──────────────────────────────────────────────
#  Diálogo de llamada entrante
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from ui.styles import COLORS


class IncomingCallDialog(QDialog):
    """
    Diálogo que se muestra cuando llega una videollamada.
    Permite aceptar o rechazar.
    """
    
    accepted_signal = Signal()  # Emitido cuando se acepta
    rejected_signal = Signal()  # Emitido cuando se rechaza

    def __init__(self, peer_name: str, parent=None):
        super().__init__(parent)
        self.peer_name = peer_name
        self._setup_ui()
        self.setWindowTitle("Videollamada entrante")
        self.setFixedSize(350, 200)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1A1A1A;
                border: 2px solid {COLORS['accent']};
            }}
        """)
        # Mostrar siempre al frente
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ── Mensaje ────────────────────────────────────────────
        title = QLabel("Llamada entrante")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title)

        msg = QLabel(f"<b>{self.peer_name}</b> quiere hacer videollamada")
        msg_font = QFont()
        msg_font.setPointSize(11)
        msg.setFont(msg_font)
        msg.setStyleSheet("color: #E0E0E0;")
        msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(msg)

        layout.addStretch()

        # ── Botones ────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.accept_btn = QPushButton("Aceptar")
        self.accept_btn.setFixedHeight(40)
        self.accept_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2E7D32;
                color: #FFFFFF;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #388E3C;
            }}
            QPushButton:pressed {{
                background-color: #1B5E20;
            }}
        """)
        self.accept_btn.clicked.connect(self._on_accept)
        btn_layout.addWidget(self.accept_btn)

        self.reject_btn = QPushButton("Rechazar")
        self.reject_btn.setFixedHeight(40)
        self.reject_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #C62828;
                color: #FFFFFF;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #D32F2F;
            }}
            QPushButton:pressed {{
                background-color: #B71C1C;
            }}
        """)
        self.reject_btn.clicked.connect(self._on_reject)
        btn_layout.addWidget(self.reject_btn)

        layout.addLayout(btn_layout)

    def _on_accept(self):
        """Usuario aceptó la llamada."""
        self.accepted_signal.emit()
        self.accept()

    def _on_reject(self):
        """Usuario rechazó la llamada."""
        self.rejected_signal.emit()
        self.reject()
