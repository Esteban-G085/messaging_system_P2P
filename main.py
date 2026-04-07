# ──────────────────────────────────────────────
#           Punto de entrada de la aplicación
# ──────────────────────────────────────────────

import asyncio
import sys

from PySide6.QtWidgets import (
    QApplication, QDialog,
    QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt
from qasync import QEventLoop, asyncSlot

from config.settings import APP_NAME, APP_VERSION, DEFAULT_PORT
from controller.app_controller import AppController
from ui.main_window import MainWindow
from ui.styles import COLORS, MAIN_STYLE
from utils.helpers import get_local_ip
from utils.logger import logger
from utils.validators import validate_username


# ─────────────────────────────────────────────
#  Diálogo de configuración inicial
# ─────────────────────────────────────────────

class SetupDialog(QDialog):
    """
    Pide username y puerto local antes de iniciar la app.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} – Configuración")
        self.setFixedSize(420, 480)
        self.setStyleSheet(MAIN_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Cabecera con color ────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(140)
        header.setStyleSheet(f"background-color: #0D1F15;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 24, 0, 20)
        header_layout.setSpacing(6)

        icon = QLabel("◈")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 28pt; background: transparent;"
        )
        header_layout.addWidget(icon)

        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #FFFFFF; font-size: 16pt; font-weight: 700; "
            "letter-spacing: 2px; background: transparent;"
        )
        header_layout.addWidget(title)

        subtitle = QLabel(f"v{APP_VERSION}  ·  Mensajería P2P")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt; background: transparent;"
        )
        header_layout.addWidget(subtitle)

        root.addWidget(header)

        # ── Cuerpo del formulario ─────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background-color: #161616;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(40, 32, 40, 32)
        body_layout.setSpacing(20)

        # Campo usuario
        user_label = QLabel("Nombre de usuario")
        user_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 8pt; "
            "font-weight: 600; letter-spacing: 1px;"
        )
        body_layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Ej: alice")
        self.username_input.setFixedHeight(42)
        self.username_input.setStyleSheet(
            "background-color: #1E1E1E; color: #FFFFFF; "
            "border: 1px solid #333333; border-radius: 6px; "
            "padding: 0 14px; font-size: 11pt;"
        )
        body_layout.addWidget(self.username_input)

        # Campo puerto
        port_label = QLabel("Puerto local")
        port_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 8pt; "
            "font-weight: 600; letter-spacing: 1px;"
        )
        body_layout.addWidget(port_label)

        port_row = QHBoxLayout()
        port_row.setSpacing(12)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(DEFAULT_PORT)
        self.port_spin.setFixedHeight(42)
        self.port_spin.setStyleSheet(
            "background-color: #1E1E1E; color: #FFFFFF; "
            "border: 1px solid #333333; border-radius: 6px; "
            "padding: 0 10px; font-size: 11pt;"
        )
        port_row.addWidget(self.port_spin, stretch=1)

        ip_badge = QLabel(f"  🌐  {get_local_ip()}")
        ip_badge.setFixedHeight(42)
        ip_badge.setStyleSheet(
            "background-color: #1A1A1A; color: #555555; "
            "border: 1px solid #2A2A2A; border-radius: 6px; "
            "padding: 0 12px; font-size: 9pt;"
        )
        port_row.addWidget(ip_badge, stretch=1)

        body_layout.addLayout(port_row)

        # Espaciador
        body_layout.addSpacing(8)

        # Botón principal
        self.btn_start = QPushButton("Iniciar sesión")
        self.btn_start.setFixedHeight(46)
        self.btn_start.setStyleSheet(
            f"background-color: {COLORS['accent']}; color: #0A1A10; "
            "border: none; border-radius: 6px; "
            "font-size: 11pt; font-weight: 700; letter-spacing: 1px;"
            "QPushButton:hover { background-color: #00CC6A; }"
        )
        self.btn_start.clicked.connect(self._on_accept)
        self.username_input.returnPressed.connect(self._on_accept)
        body_layout.addWidget(self.btn_start)

        # Botón cancelar (discreto)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet(
            "background-color: transparent; color: #555555; "
            "border: 1px solid #2A2A2A; border-radius: 6px; font-size: 9pt;"
            "QPushButton:hover { color: #888888; border-color: #444444; }"
        )
        btn_cancel.clicked.connect(self.reject)
        body_layout.addWidget(btn_cancel)

        # Error
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            f"color: {COLORS['error']}; font-size: 8pt; background: transparent;"
        )
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        body_layout.addWidget(self.error_label)

        root.addWidget(body, stretch=1)

    def _on_accept(self):
        username = self.username_input.text().strip()
        if not validate_username(username):
            self.error_label.setText("El nombre debe tener entre 2 y 32 caracteres.")
            return
        self.accept()

    @property
    def username(self) -> str:
        return self.username_input.text().strip()

    @property
    def port(self) -> int:
        return self.port_spin.value()


# ─────────────────────────────────────────────
#  Arranque de la aplicación
# ─────────────────────────────────────────────

async def main():
    app = QApplication.instance() or QApplication(sys.argv)

    # Diálogo de setup (síncrono, antes del event loop async)
    dialog = SetupDialog()
    if dialog.exec() != QDialog.Accepted:
        sys.exit(0)

    username = dialog.username
    port     = dialog.port

    logger.info(f"Iniciando {APP_NAME} v{APP_VERSION} — {username}:{port}")

    # Controlador + nodo P2P
    ctrl = AppController(username, port)

    # Ventana principal
    window = MainWindow(ctrl)
    window.show()

    # Arrancar el nodo P2P (servidor WebSocket)
    await ctrl.start()

    logger.info("Aplicación lista")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # qasync integra asyncio con el event loop de Qt
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        loop.run_until_complete(main())
        loop.run_forever()
