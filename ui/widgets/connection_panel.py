# ──────────────────────────────────────────────
#           Panel para conectar a un peer nuevo
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal

from ui.styles import COLORS


class ConnectionPanel(QWidget):
    """
    Emite connect_requested(ip, port) cuando el usuario
    pulsa el botón Conectar.
    """
    connect_requested = Signal(str, int)   # ip, puerto

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Título ────────────────────────────────
        title = QLabel("Conectar a peer")
        title.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt; "
            "font-weight: 600; letter-spacing: 1px;"
        )
        layout.addWidget(title)

        # ── Fila IP / Puerto ──────────────────────
        row = QHBoxLayout()
        row.setSpacing(6)

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.10")
        self.ip_input.setMaximumWidth(160)
        row.addWidget(self.ip_input)

        sep = QLabel(":")
        sep.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12pt;")
        row.addWidget(sep)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("5000")
        self.port_input.setMaximumWidth(70)
        self.port_input.returnPressed.connect(self._on_connect)
        row.addWidget(self.port_input)

        row.addStretch()
        layout.addLayout(row)

        # ── Botón + estado ────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.setFixedWidth(100)
        self.btn_connect.clicked.connect(self._on_connect)
        btn_row.addWidget(self.btn_connect)

        self.status_label = QLabel("⚫  Esperando…")
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt;"
        )
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()

        layout.addLayout(btn_row)

        # ── Mensaje de error ──────────────────────
        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            f"color: {COLORS['error']}; font-size: 8pt;"
        )
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_status(self, text: str, color: str = COLORS["text_muted"]):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 9pt;")

    def set_error(self, text: str):
        self.error_label.setText(text)

    def set_listening(self, ip: str, port: int):
        self.set_status(f"●  Escuchando en {ip}:{port}", COLORS["connected"])

    def set_connecting(self):
        self.set_status("⟳  Conectando…", COLORS["connecting"])
        self.btn_connect.setEnabled(False)
        self.error_label.setText("")

    def set_idle(self):
        self.set_status("⚫  Esperando…", COLORS["text_muted"])
        self.btn_connect.setEnabled(True)

    def set_connect_error(self, msg: str):
        self.set_status("✗  Error", COLORS["error"])
        self.set_error(msg)
        self.btn_connect.setEnabled(True)

    # ── Internos ──────────────────────────────────────────────────────────────

    def _on_connect(self):
        ip   = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()

        self.error_label.setText("")

        if not ip:
            self.set_error("Ingresa una dirección IP.")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.set_error("El puerto debe ser un número entero.")
            return

        self.set_connecting()
        self.connect_requested.emit(ip, port)
