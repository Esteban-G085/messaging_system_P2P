# ──────────────────────────────────────────────
#  Ventana de Videollamada
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor
from PySide6.QtGui import QImage, QPixmap
from ui.styles import COLORS


class VideoWindow(QMainWindow):
    """
    Ventana para mostrar el stream de videollamada.
    Muestra video del peer remoto y controles para colgar.
    """

    def __init__(self, peer_name: str, parent=None):
        super().__init__(parent)
        self.peer_name = peer_name
        self.setWindowTitle(f"Videollamada - {peer_name}")
        self.setFixedSize(800, 600)
        self.setStyleSheet(f"background-color: #000000;")

        self._setup_ui()

    def _setup_ui(self):
        """Crea la interfaz de la ventana de video."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Área de video (por ahora placeholder) ────────────────────────
        video_area = QFrame()
        video_area.setStyleSheet("background-color: #1A1A1A; border: 2px solid #333;")
        video_layout = QVBoxLayout(video_area)
        video_layout.setContentsMargins(0, 0, 0, 0)

        # Label placeholder para video
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)

        # 🔥 fondo negro real tipo videollamada
        self.video_label.setStyleSheet("background-color: black;")

        # 🔥 importante para que escale el video
        self.video_label.setMinimumSize(640, 480)

        # 🔥 permite que el contenido se adapte
        self.video_label.setScaledContents(False)

        video_layout.addWidget(self.video_label)
        layout.addWidget(video_area, stretch=1)

        # ── Barra de estado ────────────────────────────────────────────
        status_bar = QFrame()
        status_bar.setFixedHeight(30)
        status_bar.setStyleSheet(f"background-color: {COLORS['bg_panel']};")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.status_label = QLabel("⏱️ Conectando...")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9pt;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        layout.addWidget(status_bar)

        # ── Barra de controles ──────────────────────────────────────────
        controls = QFrame()
        controls.setStyleSheet(f"background-color: {COLORS['bg_panel']};")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(10)

        controls_layout.addStretch()

        # Botón de micrófono (mute)
        self.mute_btn = QPushButton("🎤")
        self.mute_btn.setFixedSize(50, 50)
        self.mute_btn.setToolTip("Mutearse")
        self.mute_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A2A;
                color: #FFFFFF;
                border-radius: 25px;
                font-size: 18pt;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3A3A3A;
            }}
        """)
        controls_layout.addWidget(self.mute_btn)

        # Botón de cámara
        self.camera_btn = QPushButton("📷")
        self.camera_btn.setFixedSize(50, 50)
        self.camera_btn.setToolTip("Apagar cámara")
        self.camera_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2A2A2A;
                color: #FFFFFF;
                border-radius: 25px;
                font-size: 18pt;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #3A3A3A;
            }}
        """)
        controls_layout.addWidget(self.camera_btn)

        # Botón de colgar
        self.hangup_btn = QPushButton("📞 Colgar")
        self.hangup_btn.setFixedSize(120, 50)
        self.hangup_btn.setToolTip("Terminar videollamada")
        self.hangup_btn.setStyleSheet(f"""
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
        controls_layout.addWidget(self.hangup_btn)

        controls_layout.addStretch()

        layout.addWidget(controls)

    def set_video_label(self, text: str):
        """Actualiza el label de video."""
        self.video_label.setText(text)
    
    def set_status(self, text: str):
        """Actualiza el label de estado."""
        self.status_label.setText(text)

    def closeEvent(self, event):
        """Al cerrar la ventana, emitir señal de colgar."""
        # Puede extenderse para emitir señal
        event.accept()

    # video_window.py — en update_frame:
    def update_frame(self, frame):
        try:
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            image   = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap  = QPixmap.fromImage(image)
            scaled  = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
        except Exception as e:
            print("Error mostrando frame:", e)
