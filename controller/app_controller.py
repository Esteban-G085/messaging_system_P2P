# ──────────────────────────────────────────────
#           Controlador
# ──────────────────────────────────────────────

from datetime import datetime
from typing import Callable, Dict, List, Optional

from database.db_manager import DBManager
from models.file_transfer import FileTransfer
from models.message import Message, MessageStatus
from models.peer import Peer
from network.node import P2PNode
from utils.helpers import generate_msg_id
from utils.logger import logger
from utils.validators import validate_connection

##videollamada
from network.videocall import VideoCall
from network.signaling import Signaling


class AppController:
    """
    Controlador principal de la aplicación.
    Sirve como puente entre la interfaz de usuario (UI), el nodo P2P (red) y la base de datos (persistencia).
    Gestiona el ciclo de vida de la conexión, los mensajes y las transferencias de archivos.
    """
    def __init__(self, username: str, port: int):
        self.node = P2PNode(username, port)

        self.db = DBManager()
        self.db.connect()

        self._messages: Dict[str, List[Message]] = {}

        # Conectar callbacks del nodo
        self.node.on_peer_connected    = self._on_peer_connected
        self.node.on_peer_disconnected = self._on_peer_disconnected
        self.node.on_message_received  = self._on_message_received
        self.node.on_message_ack       = self._on_message_ack
        self.node.on_file_offer        = self._on_file_offer
        self.node.on_transfer_update   = self._on_transfer_update
        self.node.on_file_saved        = self._on_file_saved

        # Callbacks para la UI
        self.ui_on_peer_update:    Optional[Callable[[Peer], None]]         = None
        self.ui_on_message:        Optional[Callable[[str, Message], None]] = None
        self.ui_on_message_ack:    Optional[Callable[[Message], None]]      = None
        self.ui_on_error:          Optional[Callable[[str], None]]          = None
        self.ui_on_file_offer:     Optional[Callable[[FileTransfer], None]] = None
        self.ui_on_transfer_update:Optional[Callable[[FileTransfer], None]] = None
        self.ui_on_file_saved:     Optional[Callable[[FileTransfer], None]] = None

        #videollamada
        self.videocall = None
        self.signaling = None

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def start(self):
        """
        Inicia el nodo P2P (servidor WebSocket local) e inicializa la escucha de conexiones entrantes.
        """
        await self.node.start()

    # ── API para la UI ────────────────────────────────────────────────────────

    async def connect_to_peer(self, ip: str, port: int):
        """
        Intenta establecer una conexión con un peer remoto dadas su dirección IP y puerto.
        
        Args:
            ip (str): Dirección IP del peer remoto.
            port (int): Puerto de escucha del peer remoto.
        """
        ok, err = validate_connection(ip, port)
        if not ok:
            if self.ui_on_error:
                self.ui_on_error(err)
            return
        try:
            await self.node.connect_to_peer(ip, port)
        except ConnectionError as e:
            if self.ui_on_error:
                self.ui_on_error(str(e))

    async def send_message(self, peer_id: str, content: str):
        """
        Envía un mensaje de texto cifrado a un peer específico.
        También guarda el mensaje en la base de datos local y actualiza la lista de mensajes en memoria.

        Args:
            peer_id (str): Identificador único del peer destinatario.
            content (str): Texto del mensaje a enviar.
        """
        if not content.strip():
            return
        msg_id = await self.node.send_message(peer_id, content)
        if not msg_id:
            return
        msg = Message(
            id=msg_id, sender_id=self.node.peer_id,
            sender_name=self.node.username, content=content,
            timestamp=datetime.now(), receiver_id=peer_id,
            status=MessageStatus.SENT, is_mine=True,
        )
        self.db.save_message(msg)
        self._messages.setdefault(peer_id, []).append(msg)
        if self.ui_on_message:
            self.ui_on_message(peer_id, msg)

    async def send_file(self, peer_id: str, filepath: str):
        """Ofrece el envío de un archivo a un peer específico."""
        ft = await self.node.send_file(peer_id, filepath)
        if ft and self.ui_on_transfer_update:
            self.ui_on_transfer_update(ft)

    async def accept_file(self, file_id: str):
        """Acepta una transferencia de archivo entrante."""
        await self.node.accept_file(file_id)

    async def reject_file(self, file_id: str):
        """Rechaza una transferencia de archivo entrante."""
        await self.node.reject_file(file_id)

    async def cancel_file(self, file_id: str):
        """Cancela una transferencia de archivo activa (enviando o recibiendo)."""
        await self.node.cancel_file(file_id)

    # ── Consultas ─────────────────────────────────────────────────────────────

    def get_messages(self, peer_id: str) -> List[Message]:
        """Obtiene el historial de mensajes en memoria con un peer específico."""
        return self._messages.get(peer_id, [])

    def get_peers(self) -> List[Peer]:
        """Obtiene la lista de todos los peers conectados."""
        return list(self.node.peers.values())

    def get_local_info(self) -> dict:
        """Devuelve un diccionario con la información del nodo local (username, ip, puerto y peer id)."""
        return {
            "username": self.node.username,
            "ip":       self.node.local_ip,
            "port":     self.node.port,
            "peer_id":  self.node.peer_id,
        }

    # ── Callbacks del nodo ────────────────────────────────────────────────────

    def _on_peer_connected(self, peer: Peer):
        self.db.upsert_peer(peer)
        self.db.log_connection(peer.id, "connected")
        if peer.id not in self._messages:
            history = self.db.get_messages_for_peer(peer.id, self.node.peer_id)
            for msg in history:
                msg.sender_name = peer.username if not msg.is_mine else self.node.username
            self._messages[peer.id] = history
        if self.ui_on_peer_update:
            self.ui_on_peer_update(peer)

    def _on_peer_disconnected(self, peer: Peer):
        self.db.log_connection(peer.id, "disconnected")
        if self.ui_on_peer_update:
            self.ui_on_peer_update(peer)

    def _on_message_received(self, sender_id, sender_name, content, timestamp):
        msg = Message(
            id=generate_msg_id(), sender_id=sender_id, sender_name=sender_name,
            content=content, timestamp=datetime.now(), receiver_id=self.node.peer_id,
            status=MessageStatus.DELIVERED, is_mine=False,
        )
        self.db.save_message(msg)
        self._messages.setdefault(sender_id, []).append(msg)
        if self.ui_on_message:
            self.ui_on_message(sender_id, msg)

    def _on_message_ack(self, msg_id: str):
        self.db.mark_delivered(msg_id)
        for messages in self._messages.values():
            for msg in messages:
                if msg.id == msg_id:
                    msg.status = MessageStatus.DELIVERED
                    if self.ui_on_message_ack:
                        self.ui_on_message_ack(msg)
                    return

    def _on_file_offer(self, ft: FileTransfer):
        if self.ui_on_file_offer:
            self.ui_on_file_offer(ft)

    def _on_transfer_update(self, ft: FileTransfer):
        if self.ui_on_transfer_update:
            self.ui_on_transfer_update(ft)

    def _on_file_saved(self, ft: FileTransfer):
        if self.ui_on_file_saved:
            self.ui_on_file_saved(ft)

    
    #-------videollamada

    async def start_videocall(self, peer):
        self.videocall = VideoCall()
        self.videocall.add_local_tracks()
        # controller/app_controller.py
        self.signaling = Signaling(self.videocall.pc, self.node.crypto_session)

        # Generar oferta y enviarla al peer usando self.node
        offer = await self.videocall.create_offer()
        self.signaling.send_offer(self.node, peer, offer)

    async def accept_videocall(self, peer, offer_sdp):
        self.videocall = VideoCall()
        self.videocall.add_local_tracks()
        # controller/app_controller.py
        self.signaling = Signaling(self.videocall.pc, self.node.crypto_session)

        await self.videocall.set_remote_description(offer_sdp)
        answer = await self.videocall.create_answer()
        self.signaling.send_answer(self.node, peer, answer)

    async def handle_incoming_message(self, peer, message):
        if message["type"] == "videocall_offer":
            await self.accept_videocall(peer, message["sdp"])
        elif message["type"] == "videocall_answer":
            await self.videocall.set_remote_description(message["sdp"])
        elif message["type"] == "ice_candidate":
            await self.videocall.add_ice_candidate(message["candidate"])

