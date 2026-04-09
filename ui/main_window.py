# ──────────────────────────────────────────────
#  Ventana principal
# ──────────────────────────────────────────────

import asyncio
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLineEdit, QPushButton, QLabel,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt
from qasync import asyncSlot

from controller.app_controller import AppController
from models.file_transfer import FileTransfer
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
        self._transfer_bubbles: dict[str, TransferBubble] = {}
        self._connect_task: asyncio.Task | None = None   # tarea de conexión en curso

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
        self.resize(980, 660)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Panel izquierdo
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

        # Panel derecho
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
        self.msg_input.setPlaceholderText("Selecciona un peer para chatear…")
        self.msg_input.setStyleSheet(
            "background-color: #2A2A2A; border-radius: 18px; "
            "padding: 7px 14px; font-size: 10pt; border: none;"
        )
        self.msg_input.setEnabled(False)
        self.msg_input.returnPressed.connect(self._on_send)
        il.addWidget(self.msg_input, stretch=1)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._on_send)
        self.send_btn.setEnabled(False)
        il.addWidget(self.send_btn)

        rl.addWidget(input_bar)
        root.addWidget(right, stretch=1)

        #------------- videollamada -------------
        
        # Botón para iniciar videollamada
        self.btn_start_call = QPushButton("📹 Iniciar videollamada")
        # Botón para aceptar llamada
        self.btn_accept_call = QPushButton("✅ Aceptar llamada")
        # Botón para rechazar llamada
        self.btn_reject_call = QPushButton("❌ Rechazar llamada")

        # Añadirlos al layout principal
        self.layout.addWidget(self.btn_start_call)
        self.layout.addWidget(self.btn_accept_call)
        self.layout.addWidget(self.btn_reject_call)

    # ── Señales ───────────────────────────────────────────────────────────────

    def _connect_signals(self):
        self.peers_list.peer_selected.connect(self._on_peer_selected)
        self.conn_panel.connect_requested.connect(self._on_connect_requested)
        self.conn_panel.cancel_requested.connect(self._on_connect_cancelled)
        self.chat_view._tabs.currentChanged.connect(self._on_tab_changed)

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
        # Si el peer se conectó correctamente → restaurar panel
        if peer.is_ready:
            self.conn_panel.set_idle()
        if self._active_peer and self._active_peer.id == peer.id:
            self._active_peer = peer
            self._update_input_state(peer)

    def _ui_message(self, peer_id: str, msg: Message):
        self.chat_view.add_message(peer_id, msg)

    def _ui_error(self, error: str):
        # El error ya restaura el panel a idle
        self.conn_panel.set_connect_error(error)

    def _ui_file_offer(self, ft: FileTransfer):
        peer        = self.ctrl.node.peers.get(ft.peer_id)
        sender_name = peer.username if peer else ft.peer_id[:8]
        reply = QMessageBox.question(
            self, "Archivo entrante",
            f"<b>{sender_name}</b> quiere enviarte:<br><br>"
            f"📄  <b>{ft.filename}</b>  ({ft.size_str})<br><br>"
            "¿Aceptar la transferencia?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        bubble = TransferBubble(ft)
        bubble.cancel_requested.connect(self._on_cancel_transfer)
        self._transfer_bubbles[ft.id] = bubble
        self.chat_view.add_transfer_bubble(ft.peer_id, bubble)
        if reply == QMessageBox.Yes:
            asyncio.ensure_future(self.ctrl.accept_file(ft.id))
        else:
            asyncio.ensure_future(self.ctrl.reject_file(ft.id))

    def _ui_transfer_update(self, ft: FileTransfer):
        bubble = self._transfer_bubbles.get(ft.id)
        if bubble:
            bubble.update_transfer(ft)
        elif ft.is_sender:
            bubble = TransferBubble(ft)
            bubble.cancel_requested.connect(self._on_cancel_transfer)
            self._transfer_bubbles[ft.id] = bubble
            self.chat_view.add_transfer_bubble(ft.peer_id, bubble)

    def _ui_file_saved(self, ft: FileTransfer):
        save_dir = os.path.dirname(os.path.abspath(ft.save_path))
        QMessageBox.information(
            self, "Archivo recibido",
            f"✅  <b>{ft.filename}</b> guardado correctamente.<br><br>"
            f"📁  {save_dir}",
        )

    # ── Eventos de UI ─────────────────────────────────────────────────────────

    def _on_peer_selected(self, peer: Peer):
        self._active_peer = peer
        messages = self.ctrl.get_messages(peer.id)
        self.chat_view.open_chat(peer.id, peer.username, messages)
        self._update_input_state(peer)

    def _on_tab_changed(self, index: int):
        if index < 0:
            self._active_peer = None
            self._set_input_enabled(False)
            return
        panel = self.chat_view._tabs.widget(index)
        if not panel:
            return
        self.chat_view._clear_badge(panel.peer_id)
        peer = self.ctrl.node.peers.get(panel.peer_id)
        if peer:
            self._active_peer = peer
            self._update_input_state(peer)
        else:
            self._active_peer = None
            self._set_input_enabled(False)

    # ── Conexión en background ────────────────────────────────────────────────

    def _on_connect_requested(self, ip: str, port: int):
        """
        Lanza la conexión como tarea asyncio en background.
        La UI queda libre inmediatamente — el resultado llega
        por _ui_peer_update (éxito) o _ui_error (fallo).
        """
        # Cancelar intento previo si lo hubiera
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()

        self._connect_task = asyncio.ensure_future(
            self.ctrl.connect_to_peer(ip, port)
        )

    def _on_connect_cancelled(self):
        """El usuario pulsó Cancelar — abortar la tarea en curso."""
        if self._connect_task and not self._connect_task.done():
            self._connect_task.cancel()
            self._connect_task = None

    # ── Input bar ─────────────────────────────────────────────────────────────

    def _update_input_state(self, peer: Peer):
        ready = peer.is_ready
        self._set_input_enabled(ready)
        self.msg_input.setPlaceholderText(
            f"Mensaje para {peer.username}…" if ready
            else "El peer está desconectado"
        )
        if ready:
            self.msg_input.setFocus()

    def _set_input_enabled(self, enabled: bool):
        self.send_btn.setEnabled(enabled)
        self.attach_btn.setEnabled(enabled)
        self.msg_input.setEnabled(enabled)

    #--------------videollamada----------------
    def _on_start_call(self):
        peer = self._on_peer_selected()  # reutilizas tu lógica para obtener el peer
        self.controller.start_videocall(peer)

    def _on_accept_call(self):
        peer = self._on_peer_selected()
        offer_sdp = self.get_incoming_offer()  # deberás implementar cómo obtienes el SDP
        self.controller.accept_videocall(peer, offer_sdp)

    def _on_reject_call(self):
        print("Llamada rechazada")
        # Aquí podrías enviar un mensaje de rechazo al peer

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
            self, "Seleccionar archivo", "", "Todos los archivos (*)"
        )
        if not filepath:
            return
        await self.ctrl.send_file(self._active_peer.id, filepath)

    @asyncSlot(str)
    async def _on_cancel_transfer(self, file_id: str):
        await self.ctrl.cancel_file(file_id)
