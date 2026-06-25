# ──────────────────────────────────────────────
#  Panel de conexión
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, Signal

from ui.styles import COLORS


class ConnectionPanel(QWidget):
    connect_requested = Signal(str, int)   # ip, puerto
    cancel_requested  = Signal()           # cancelar intento en curso

    def __init__(self):
        super().__init__()
        self._connecting = False
        self._listening_text = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Conectar a peer")
        title.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt; "
            "font-weight: 600; letter-spacing: 1px;"
        )
        layout.addWidget(title)

        # ── IP : Puerto ───────────────────────────
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

        # ── Botones ───────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.setFixedWidth(90)
        self.btn_connect.clicked.connect(self._on_connect)
        btn_row.addWidget(self.btn_connect)

        # Botón cancelar — solo visible mientras conecta
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.setStyleSheet(
            "background-color: #2A2A2A; color: #AAAAAA; "
            "border: 1px solid #444444; border-radius: 4px; padding: 6px;"
            "QPushButton:hover { background-color: #FF6B6B; color: #FFFFFF; border-color: #FF6B6B; }"
        )
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.hide()
        btn_row.addWidget(self.btn_cancel)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Estado ────────────────────────────────
        self.status_label = QLabel("Esperando...")
        self.status_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt;"
        )
        layout.addWidget(self.status_label)

        # ── Error ─────────────────────────────────
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
        self._listening_text = f"Escuchando en {ip}:{port}"
        if not self._connecting:
            self.set_status(self._listening_text, COLORS["connected"])

    def set_connecting(self, ip: str = "", port: int = 0):
        self._connecting = True
        label = f"⟳  Conectando a {ip}:{port}…" if ip else "⟳  Conectando…"
        self.set_status(label, COLORS["connecting"])
        self.error_label.setText("")
        self.btn_connect.setEnabled(False)
        self.ip_input.setEnabled(False)
        self.port_input.setEnabled(False)
        self.btn_cancel.show()

    def set_idle(self):
        """Vuelve al estado normal — siempre re-habilita el formulario."""
        self._connecting = False
        self.btn_connect.setEnabled(True)
        self.ip_input.setEnabled(True)
        self.port_input.setEnabled(True)
        self.btn_cancel.hide()
        # Restaurar el texto de "escuchando" si lo teníamos
        if self._listening_text:
            self.set_status(self._listening_text, COLORS["connected"])
        else:
            self.set_status("Esperando...", COLORS["text_muted"])

    def set_connect_error(self, msg: str):
        self.set_error(msg)
        self.set_idle()

    # ── Internos ──────────────────────────────────────────────────────────────

    def _on_connect(self):
        if self._connecting:
            return
        ip       = self.ip_input.text().strip()
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

        self.set_connecting(ip, port)
        self.connect_requested.emit(ip, port)

    def _on_cancel(self):
        self.cancel_requested.emit()
        self.set_idle()
        self.set_error("Conexión cancelada.")
