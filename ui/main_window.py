# ──────────────────────────────────────────────
#  ui/main_window.py  –  Ventana principal
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QSplitter, QFrame,
    QLineEdit, QPushButton, QLabel,
)
from PySide6.QtCore import Qt
from qasync import asyncSlot

from controller.app_controller import AppController
from models.message import Message
from models.peer import Peer
from ui.styles import COLORS, MAIN_STYLE
from ui.widgets.chat_view import ChatView
from ui.widgets.connection_panel import ConnectionPanel
from ui.widgets.peers_list import PeersList


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController):
        super().__init__()
        self.ctrl = controller
        self._active_peer: Peer | None = None

        self._setup_ui()
        self._connect_signals()
        self._connect_controller()

        info = self.ctrl.get_local_info()
        self.conn_panel.set_listening(info["ip"], info["port"])
        self.setWindowTitle(
            f"P2P Chat  —  {info['username']}  ({info['ip']}:{info['port']})"
        )

    # ── Construcción de la UI ─────────────────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(MAIN_STYLE)
        self.resize(900, 620)

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel izquierdo (peers + conexión) ────────────────────────────────
        left = QFrame()
        left.setFixedWidth(250)
        left.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; "
            "border-right: 1px solid #2A2A2A;"
        )
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.peers_list = PeersList()
        left_layout.addWidget(self.peers_list, stretch=1)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #2A2A2A;")
        left_layout.addWidget(divider)

        self.conn_panel = ConnectionPanel()
        left_layout.addWidget(self.conn_panel)

        root.addWidget(left)

        # ── Panel derecho (chat + input) ──────────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.chat_view = ChatView()
        right_layout.addWidget(self.chat_view, stretch=1)

        # Barra de input
        input_bar = QFrame()
        input_bar.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; "
            "border-top: 1px solid #2A2A2A;"
        )
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(10, 8, 10, 8)
        input_layout.setSpacing(8)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Escribe tu mensaje…")
        self.msg_input.setStyleSheet(
            "background-color: #2A2A2A; border-radius: 18px; "
            "padding: 7px 14px; font-size: 10pt; border: none;"
        )
        self.msg_input.returnPressed.connect(self._on_send)
        input_layout.addWidget(self.msg_input, stretch=1)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setEnabled(False)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(input_bar)
        root.addWidget(right, stretch=1)

    # ── Señales internas ──────────────────────────────────────────────────────

    def _connect_signals(self):
        self.peers_list.peer_selected.connect(self._on_peer_selected)
        self.conn_panel.connect_requested.connect(self._on_connect_requested)

    # ── Callbacks del controlador ─────────────────────────────────────────────

    def _connect_controller(self):
        self.ctrl.ui_on_peer_update  = self._ui_peer_update
        self.ctrl.ui_on_message      = self._ui_message
        self.ctrl.ui_on_error        = self._ui_error

    def _ui_peer_update(self, peer: Peer):
        self.peers_list.add_or_update_peer(peer)
        # Si el peer activo cambia de estado, actualizar el header del chat
        if self._active_peer and self._active_peer.id == peer.id:
            self._active_peer = peer

    def _ui_message(self, peer_id: str, msg: Message):
        self.chat_view.add_message(peer_id, msg)

    def _ui_error(self, error: str):
        self.conn_panel.set_connect_error(error)

    # ── Handlers de eventos de UI ─────────────────────────────────────────────

    def _on_peer_selected(self, peer: Peer):
        self._active_peer = peer
        messages = self.ctrl.get_messages(peer.id)
        self.chat_view.set_peer(peer.username, peer.id, messages)
        self.send_btn.setEnabled(peer.is_ready)
        self.msg_input.setEnabled(peer.is_ready)
        if peer.is_ready:
            self.msg_input.setFocus()

    @asyncSlot()
    async def _on_connect_requested(self, ip: str, port: int):
        await self.ctrl.connect_to_peer(ip, port)
        # Si la conexión fue exitosa el controlador llama a _ui_peer_update
        # que refresca la lista; si falló llama a _ui_error
        self.conn_panel.set_idle()

    @asyncSlot()
    async def _on_send(self):
        if not self._active_peer:
            return
        content = self.msg_input.text().strip()
        if not content:
            return
        self.msg_input.clear()
        await self.ctrl.send_message(self._active_peer.id, content)
