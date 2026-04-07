# ──────────────────────────────────────────────
#           Ventana principal
# ──────────────────────────────────────────────

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLineEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from qasync import asyncSlot

from controller.app_controller import AppController
from models.file_transfer import FileTransfer, TransferStatus
from models.message import Message
from models.peer import Peer
from ui.styles import COLORS, MAIN_STYLE
from ui.widgets.chat_view import ChatView
from ui.widgets.connection_panel import ConnectionPanel
from ui.widgets.peers_list import PeersList
from ui.widgets.transfer_widget import TransferBubble


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController):
        super().__init__()
        self.ctrl = controller
        self._active_peer: Peer | None = None
        # file_id → TransferBubble
        self._transfer_bubbles: dict[str, TransferBubble] = {}

        self._setup_ui()
        self._connect_signals()
        self._connect_controller()

        info = self.ctrl.get_local_info()
        self.conn_panel.set_listening(info["ip"], info["port"])
        self.setWindowTitle(
            f"P2P Chat  —  {info['username']}  ({info['ip']}:{info['port']})"
        )

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(MAIN_STYLE)
        self.resize(920, 640)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Panel izquierdo ───────────────────────────────────────────────────
        left = QFrame()
        left.setFixedWidth(250)
        left.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; border-right: 1px solid #2A2A2A;"
        )
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        self.peers_list = PeersList()
        ll.addWidget(self.peers_list, stretch=1)

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #2A2A2A;")
        ll.addWidget(div)

        self.conn_panel = ConnectionPanel()
        ll.addWidget(self.conn_panel)
        root.addWidget(left)

        # ── Panel derecho ─────────────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self.chat_view = ChatView()
        rl.addWidget(self.chat_view, stretch=1)

        # Barra de input
        input_bar = QFrame()
        input_bar.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; border-top: 1px solid #2A2A2A;"
        )
        il = QHBoxLayout(input_bar)
        il.setContentsMargins(10, 8, 10, 8)
        il.setSpacing(8)

        # Botón adjuntar archivo
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(36, 36)
        self.attach_btn.setToolTip("Enviar archivo")
        self.attach_btn.setStyleSheet(
            "background-color: #2A2A2A; color: #FFFFFF; border-radius: 18px; "
            "font-size: 14pt; border: none;"
            "QPushButton:hover { background-color: #3A3A3A; }"
            "QPushButton:disabled { color: #444444; }"
        )
        self.attach_btn.clicked.connect(self._on_attach)
        self.attach_btn.setEnabled(False)
        il.addWidget(self.attach_btn)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Escribe tu mensaje…")
        self.msg_input.setStyleSheet(
            "background-color: #2A2A2A; border-radius: 18px; "
            "padding: 7px 14px; font-size: 10pt; border: none;"
        )
        self.msg_input.returnPressed.connect(self._on_send)
        il.addWidget(self.msg_input, stretch=1)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setEnabled(False)
        il.addWidget(self.send_btn)

        rl.addWidget(input_bar)
        root.addWidget(right, stretch=1)

    # ── Señales ───────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.peers_list.peer_selected.connect(self._on_peer_selected)
        self.conn_panel.connect_requested.connect(self._on_connect_requested)

    def _connect_controller(self):
        self.ctrl.ui_on_peer_update     = self._ui_peer_update
        self.ctrl.ui_on_message         = self._ui_message
        self.ctrl.ui_on_error           = self._ui_error
        self.ctrl.ui_on_file_offer      = self._ui_file_offer
        self.ctrl.ui_on_transfer_update = self._ui_transfer_update
        self.ctrl.ui_on_file_saved      = self._ui_file_saved

    # ── Callbacks del controlador ─────────────────────────────────────────────

    def _ui_peer_update(self, peer: Peer):
        self.peers_list.add_or_update_peer(peer)
        if self._active_peer and self._active_peer.id == peer.id:
            self._active_peer = peer

    def _ui_message(self, peer_id: str, msg: Message):
        self.chat_view.add_message(peer_id, msg)

    def _ui_error(self, error: str):
        self.conn_panel.set_connect_error(error)

    def _ui_file_offer(self, ft: FileTransfer):
        """Diálogo de aceptar/rechazar archivo entrante."""
        peer = self.ctrl.node.peers.get(ft.peer_id)
        sender_name = peer.username if peer else ft.peer_id[:8]

        reply = QMessageBox.question(
            self,
            "Archivo entrante",
            f"<b>{sender_name}</b> quiere enviarte:<br><br>"
            f"📄  <b>{ft.filename}</b>  ({ft.size_str})<br><br>"
            f"¿Aceptar la transferencia?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        bubble = TransferBubble(ft)
        bubble.cancel_requested.connect(self._on_cancel_transfer)
        self._transfer_bubbles[ft.id] = bubble
        self.chat_view.add_transfer_bubble(ft.peer_id, bubble)

        if reply == QMessageBox.Yes:
            import asyncio
            asyncio.ensure_future(self.ctrl.accept_file(ft.id))
        else:
            import asyncio
            asyncio.ensure_future(self.ctrl.reject_file(ft.id))

    def _ui_transfer_update(self, ft: FileTransfer):
        """Actualiza la burbuja de progreso en el chat."""
        bubble = self._transfer_bubbles.get(ft.id)
        if bubble:
            bubble.update_transfer(ft)
        elif ft.is_sender:
            # Primera actualización del sender → crear burbuja
            bubble = TransferBubble(ft)
            bubble.cancel_requested.connect(self._on_cancel_transfer)
            self._transfer_bubbles[ft.id] = bubble
            self.chat_view.add_transfer_bubble(ft.peer_id, bubble)

    def _ui_file_saved(self, ft: FileTransfer):
        save_dir = os.path.dirname(os.path.abspath(ft.save_path))
        QMessageBox.information(
            self,
            "Archivo recibido",
            f"✅  <b>{ft.filename}</b> guardado correctamente.<br><br>"
            f"📁  {save_dir}",
        )

    # ── Eventos de UI ─────────────────────────────────────────────────────────

    def _on_peer_selected(self, peer: Peer):
        self._active_peer = peer
        messages = self.ctrl.get_messages(peer.id)
        self.chat_view.set_peer(peer.username, peer.id, messages)
        ready = peer.is_ready
        self.send_btn.setEnabled(ready)
        self.attach_btn.setEnabled(ready)
        self.msg_input.setEnabled(ready)
        if ready:
            self.msg_input.setFocus()

    @asyncSlot()
    async def _on_connect_requested(self, ip: str, port: int):
        await self.ctrl.connect_to_peer(ip, port)
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

    @asyncSlot()
    async def _on_attach(self):
        if not self._active_peer:
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo para enviar", "", "Todos los archivos (*)"
        )
        if not filepath:
            return
        await self.ctrl.send_file(self._active_peer.id, filepath)

    @asyncSlot(str)
    async def _on_cancel_transfer(self, file_id: str):
        await self.ctrl.cancel_file(file_id)
