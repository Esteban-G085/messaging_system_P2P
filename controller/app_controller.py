# ──────────────────────────────────────────────
#           Controlador
# ──────────────────────────────────────────────

from datetime import datetime
from typing import Callable, Dict, List, Optional
import json
import asyncio


from database.db_manager import DBManager
from models import message
from models.file_transfer import FileTransfer
from models.message import Message, MessageStatus
from models.peer import Peer
from network.node import P2PNode
from utils.helpers import generate_msg_id
from utils.logger import logger
from utils.validators import validate_connection


##videollamada
from network.videocall import VideoCallWS


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
        self.node.on_videocall_message = self._on_videocall_message

        # Callbacks para la UI
        self.ui_on_peer_update:    Optional[Callable[[Peer], None]]         = None
        self.ui_on_message:        Optional[Callable[[str, Message], None]] = None
        self.ui_on_message_ack:    Optional[Callable[[Message], None]]      = None
        self.ui_on_error:          Optional[Callable[[str], None]]          = None
        self.ui_on_file_offer:     Optional[Callable[[FileTransfer], None]] = None
        self.ui_on_transfer_update:Optional[Callable[[FileTransfer], None]] = None
        self.ui_on_file_saved:     Optional[Callable[[FileTransfer], None]] = None
        self.ui_on_incoming_call: Optional[Callable[[str, str], None]] = None
        self.ui_on_video_track:   Optional[Callable]                   = None
        self.ui_on_call_ended:    Optional[Callable]                   = None

        # Videollamada
        from network.videocall import VideoCallWS
        self.videocall = VideoCallWS()
        self._pending_videocall_offers: Dict[str, dict] = {}
        

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def start(self):
        """
        Inicia el nodo P2P (servidor WebSocket local) e inicializa la escucha de conexiones entrantes.
        """
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO APLICACIÓN P2P")
        logger.info("=" * 80)
        logger.info(f"[CTRL] Usuario: {self.node.username}")
        logger.info(f"[CTRL] Peer ID: {self.node.peer_id[:16]}...")
        logger.info(f"[CTRL] IP Local: {self.node.local_ip}")
        logger.info(f"[CTRL] Puerto: {self.node.port}")
        logger.info("[CTRL] ⏳ Iniciando servidor WebSocket...")
        
        await self.node.start()
        
        logger.info("[CTRL] ✅ Servidor WebSocket iniciado correctamente")
        logger.info("=" * 80)

    # ── API para la UI ────────────────────────────────────────────────────────

    async def connect_to_peer(self, ip: str, port: int):
        """
        Intenta establecer una conexión con un peer remoto dadas su dirección IP y puerto.
        
        Args:
            ip (str): Dirección IP del peer remoto.
            port (int): Puerto de escucha del peer remoto.
        """
        logger.info("=" * 80)
        logger.info(f"[CTRL] 🔗 INICIANDO CONEXIÓN A PEER")
        logger.info("=" * 80)
        
        ok, err = validate_connection(ip, port)
        if not ok:
            logger.error(f"[CTRL] ❌ Validación fallida: {err}")
            if self.ui_on_error:
                self.ui_on_error(err)
            return
        
        logger.info(f"[CTRL] [FASE 0/3] Validación de parámetros completada ✓")
        logger.info(f"[CTRL]    → Destino: {ip}:{port}")
        
        try:
            logger.info("[CTRL] ⏳ Conectando..." if not self.ui_on_error else "")
            await self.node.connect_to_peer(ip, port)
            logger.info("[CTRL] ✅ Conexión completada")
        except ConnectionError as e:
            logger.error(f"[CTRL] ❌ Error de conexión: {e}")
            if self.ui_on_error:
                self.ui_on_error(str(e))
        except Exception as e:
            logger.error(f"[CTRL] ❌ Error inesperado: {e}")
            if self.ui_on_error:
                self.ui_on_error(f"Error inesperado: {e}")

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
        logger.info("=" * 80)
        logger.info(f"[CTRL] ✅ PEER CONECTADO")
        logger.info("=" * 80)
        logger.info(f"[CTRL] Username: {peer.username}")
        logger.info(f"[CTRL] Peer ID: {peer.id[:16]}...")
        logger.info(f"[CTRL] IP/Puerto: {peer.ip}:{peer.port}")
        logger.info(f"[CTRL] Estado: {peer.state}")
        
        self.db.upsert_peer(peer)
        if peer.id not in self._messages:
            history = self.db.get_messages_for_peer(peer.id, self.node.peer_id)
            for msg in history:
                msg.sender_name = peer.username if not msg.is_mine else self.node.username
            self._messages[peer.id] = history
        
        logger.info("[CTRL] 🏠 Cargado historial messajes")
        logger.info("=" * 80)
        
        if self.ui_on_peer_update:
            self.ui_on_peer_update(peer)

    def _on_peer_disconnected(self, peer: Peer):
        logger.warning("=" * 80)
        logger.warning(f"[CTRL] ❌ PEER DESCONECTADO")
        logger.warning("=" * 80)
        logger.warning(f"[CTRL] Username: {peer.username}")
        logger.warning(f"[CTRL] Peer ID: {peer.id[:16]}...")
        logger.warning("=" * 80)
        
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

    async def _on_videocall_message(self, peer: Peer, message: dict):
        """Callback del nodo para mensajes de videollamada."""
        await self.handle_incoming_videocall_message(peer, message)

    
    # ── Videollamada ──────────────────────────────────────────────────────────

    async def start_videocall(self, peer_id: str):
        """Inicia videollamada: envía señal y arranca captura."""
        peer = self.node.peers.get(peer_id)
        if not peer:
            logger.error(f"[VIDEOCALL] ❌ Peer {peer_id} no encontrado")
            return

        logger.info("=" * 80)
        logger.info(f"[VIDEOCALL] 🎥 INICIANDO VIDEOLLAMADA → {peer.username}")
        logger.info("=" * 80)

        await self._send_videocall_signal(peer_id, "videocall_offer")
        self._start_videocall_session(peer)

    async def accept_videocall(self, peer_id: str):
        """Acepta llamada entrante y arranca captura."""
        peer = self.node.peers.get(peer_id)
        if not peer:
            logger.error(f"[VIDEOCALL] ❌ Peer {peer_id} no encontrado")
            return

        logger.info("=" * 80)
        logger.info(f"[VIDEOCALL] 📞 ACEPTANDO VIDEOLLAMADA de {peer.username}")
        logger.info("=" * 80)

        await self._send_videocall_signal(peer_id, "videocall_answer")
        self._pending_videocall_offers.pop(peer_id, None)
        self._start_videocall_session(peer)

    async def reject_videocall(self, peer_id: str):
        """Rechaza llamada entrante."""
        self._pending_videocall_offers.pop(peer_id, None)
        logger.info(f"[VIDEOCALL] ❌ Videollamada rechazada de {peer_id}")

    async def end_videocall(self, peer_id: str):
        """Cuelga una llamada activa y notifica al peer."""
        logger.info(f"[VIDEOCALL] 📴 Colgando videollamada con {peer_id}")
        self.videocall.stop()
        await self._send_videocall_signal(peer_id, "videocall_end")

    def _start_videocall_session(self, peer):
        """Conecta callbacks y lanza los loops de captura/reproducción."""
        self.videocall.on_frame_received = self.ui_on_video_track
        self.videocall.on_call_ended     = self._on_videocall_ended

        loop = asyncio.get_event_loop()
        loop.create_task(
            self.videocall.start_sending(self.node, peer),
            name=f"videocall_{peer.id[:8]}"
        )
        logger.info(f"[VIDEOCALL] ✅ Sesión iniciada con {peer.username}")

    def _on_videocall_ended(self):
        """Callback interno cuando VideoCallWS termina sus loops."""
        logger.info("[VIDEOCALL] 🔚 Sesión de videollamada terminada")
        self.videocall = VideoCallWS()   # reset para la próxima llamada

    async def _send_videocall_signal(self, peer_id: str, signal_type: str):
        """Envía una señal de control de videollamada cifrada."""
        peer    = self.node.peers.get(peer_id)
        session = self.node._crypto.get(peer_id)
        if not peer or not session:
            logger.error(f"[VIDEOCALL] ❌ No se puede enviar señal '{signal_type}': peer/crypto no disponible")
            return
        try:
            msg        = json.dumps({"type": signal_type})
            encrypted  = session.encrypt(msg)
            from network.protocol import Protocol
            _, payload = Protocol.message(self.node.username, self.node.peer_id, encrypted)
            await peer.connection.send(payload)
            logger.info(f"[VIDEOCALL] 📤 Señal enviada: {signal_type} → {peer.username}")
        except Exception as e:
            logger.error(f"[VIDEOCALL] ❌ Error enviando señal '{signal_type}': {e}")

    async def handle_incoming_videocall_message(self, peer, message):
        """Despacha mensajes entrantes de videollamada."""
        msg_type = message.get("type")

        if msg_type == "videocall_offer":
            self._pending_videocall_offers[peer.id] = {"peer_obj": peer}
            logger.info(f"[VIDEOCALL] 📨 Oferta recibida de {peer.username}")
            if self.ui_on_incoming_call:
                self.ui_on_incoming_call(peer.id, peer.username)

        elif msg_type == "videocall_answer":
            # El receptor aceptó — ya estamos enviando, nada más que hacer
            logger.info(f"[VIDEOCALL] ✅ {peer.username} aceptó la llamada")

        elif msg_type == "videocall_end":
            # El peer colgó
            logger.info(f"[VIDEOCALL] 📴 {peer.username} colgó la llamada")
            self.videocall.stop()
            if self.ui_on_call_ended:
                self.ui_on_call_ended()

        elif msg_type == "video_frame":
            self.videocall.receive_video_frame(message["data"])

        elif msg_type == "audio_frame":
            self.videocall.receive_audio_frame(message["data"])

        else:
            logger.warning(f"[VIDEOCALL] Mensaje desconocido: {msg_type}")