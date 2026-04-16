# ──────────────────────────────────────────────
#           Nodo P2P con ECC + AES + Archivos
# ──────────────────────────────────────────────

import asyncio
from datetime import datetime
import json
from typing import Callable, Dict, Optional

import websockets

from models.connection_state import ConnectionState
from models.peer import Peer
from models.file_transfer import FileTransfer, TransferStatus
from network.client import WebSocketClient
from network.file_transfer import FileTransferManager
from network.message_handler import MessageHandler
from network.protocol import Protocol
from network.server import WebSocketServer
from utils.crypto import CryptoSession
from utils.helpers import generate_peer_id, get_local_ip
from utils.logger import logger


class P2PNode:
    def __init__(self, username: str, port: int):
        self.username = username
        self.port     = port
        self.peer_id  = generate_peer_id()
        self.local_ip = get_local_ip()

        self.peers: Dict[str, Peer] = {}
        self._crypto: Dict[str, CryptoSession] = {}

        self._server   = WebSocketServer(port=port)
        self._client   = WebSocketClient()
        self._handler  = MessageHandler()
        self.ft_manager = FileTransferManager()

        # Callbacks → AppController
        self.on_peer_connected:    Optional[Callable] = None
        self.on_peer_disconnected: Optional[Callable] = None
        self.on_message_received:  Optional[Callable] = None
        self.on_message_ack:       Optional[Callable] = None
        self.on_file_offer:        Optional[Callable] = None   # (FileTransfer)
        self.on_transfer_update:   Optional[Callable] = None   # (FileTransfer)
        self.on_file_saved:        Optional[Callable] = None   # (FileTransfer)
        self.on_videocall_message: Optional[Callable] = None   # (peer, message)

        self._setup_handlers()

    def _setup_handlers(self):
        self._handler.on("HELLO",          self._on_hello)
        self._handler.on("HELLO_ACK",      self._on_hello_ack)
        self._handler.on("MESSAGE",        self._on_message)
        self._handler.on("MESSAGE_ACK",    self._on_message_ack)
        self._handler.on("HEARTBEAT",      self._on_heartbeat)
        self._handler.on("DISCONNECT",     self._on_disconnect)
        self._handler.on("FILE_OFFER",     self._on_file_offer)
        self._handler.on("FILE_OFFER_ACK", self._on_file_offer_ack)
        self._handler.on("FILE_CHUNK",     self._on_file_chunk)
        self._handler.on("FILE_CANCEL",    self._on_file_cancel)

        self.ft_manager.on_transfer_update = self._ft_notify_update
        self.ft_manager.on_file_offer      = self._ft_notify_offer
        self.ft_manager.on_file_saved      = self._ft_notify_saved

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    async def start(self):
        """
        Inicia el servidor WebSocket local para aceptar conexiones entrantes de otros peers.
        Asigna el manejador de mensajes a la instancia del servidor.
        """
        self._server.set_message_handler(self._handler.handle)
        await self._server.start()
        logger.info(f"[NODE] 🚀 Nodo iniciado: {self.username}")
        logger.info(f"[NODE]    • Peer ID: {self.peer_id[:16]}...")
        logger.info(f"[NODE]    • IP Local: {self.local_ip}")
        logger.info(f"[NODE]    • Puerto: {self.port}")

    async def stop(self):
        """Desconecta a todos los peers activos y detiene el servidor de escucha local."""
        for peer_id in list(self.peers):
            await self.disconnect_from_peer(peer_id)
        await self._server.stop()

    # ── API pública ───────────────────────────────────────────────────────────

    async def connect_to_peer(self, ip: str, port: int):
        """
        Establece conexión WebSocket como cliente hacia un peer remoto y envía el handshake (HELLO).
        Mantiene en estado pendiente las credenciales de cifrado hasta que se recibe el ACK.
        
        Args:
            ip (str): Dirección IP a conectar.
            port (int): Puerto remoto.
        """
        logger.info(f"[NODE] 🔗 [FASE 2/3] Iniciando handshake HELLO con {ip}:{port}")
        
        session = CryptoSession()
        logger.info(f"[NODE]    → Generando par de claves ECC (SECP256R1)...")
        
        ws      = await self._client.connect(ip, port)
        tmp_key = f"_pending_{ip}:{port}"
        self._crypto[tmp_key] = session
        
        logger.info(f"[NODE]    → Enviando mensaje HELLO con clave pública...")
        await ws.send(Protocol.hello(
            self.username, self.peer_id, self.port, session.public_key_pem()
        ))
        logger.info(f"[NODE]    → HELLO enviado, esperando HELLO_ACK...")
        
        asyncio.create_task(self._listen_outgoing(ws, ip, port, tmp_key))

    async def send_message(self, peer_id: str, content: str) -> Optional[str]:
        """
        Cifra y envía un mensaje de texto a un peer conectado.
        Retorna el identificador (UUID) único del mensaje enviado, o None si hay problemas de red o cifrado.
        """
        peer    = self.peers.get(peer_id)
        session = self._crypto.get(peer_id)
        if not peer or not peer.is_ready:
            return None
        if not session or not session.is_ready:
            return None
        encrypted        = session.encrypt(content)
        msg_id, payload  = Protocol.message(self.username, self.peer_id, encrypted)
        await peer.connection.send(payload)
        return msg_id

    async def send_file(self, peer_id: str, filepath: str) -> Optional[FileTransfer]:
        """Inicia el envío de un archivo a un peer."""
        peer = self.peers.get(peer_id)
        if not peer or not peer.is_ready:
            logger.warning(f"[NODE] Peer {peer_id[:8]}… no listo para recibir archivo")
            return None

        ft = self.ft_manager.prepare_send(filepath, peer_id)
        offer = Protocol.file_offer(
            ft.id, self.peer_id, ft.filename,
            ft.filesize, ft.total_chunks, ft.sha256,
        )
        await peer.connection.send(offer)
        logger.info(f"[NODE] FILE_OFFER enviado: {ft.filename} ({ft.size_str})")
        return ft

    async def accept_file(self, file_id: str):
        """El usuario aceptó recibir el archivo."""
        ft = self.ft_manager.transfers.get(file_id)
        if not ft:
            return
        peer = self.peers.get(ft.peer_id)
        if not peer or not peer.connection:
            return
        ft.status = TransferStatus.RECEIVING
        await peer.connection.send(Protocol.file_offer_ack(file_id, accepted=True))
        logger.info(f"[NODE] FILE_OFFER_ACK accepted → {ft.filename}")

    async def reject_file(self, file_id: str):
        """El usuario rechazó recibir el archivo."""
        ft = self.ft_manager.transfers.get(file_id)
        if not ft:
            return
        peer = self.peers.get(ft.peer_id)
        if peer and peer.connection:
            await peer.connection.send(Protocol.file_offer_ack(file_id, accepted=False))
        ft.status = TransferStatus.REJECTED
        self._ft_notify_update(ft)

    async def cancel_file(self, file_id: str):
        """Cancela una transferencia en curso."""
        ft = self.ft_manager.transfers.get(file_id)
        if not ft:
            return
        peer = self.peers.get(ft.peer_id)
        if peer and peer.connection:
            await peer.connection.send(Protocol.file_cancel(file_id))
        self.ft_manager.cancel(file_id)

    async def disconnect_from_peer(self, peer_id: str):
        """
        Cierra la conexión WebSocket activa con el peer indicado y limpia las sesiones criptográficas.
        Envía una señal de control de desconexión antes de cerrar.
        """
        peer = self.peers.get(peer_id)
        if peer and peer.connection:
            try:
                await peer.connection.send(Protocol.disconnect())
                await peer.connection.close()
            except Exception:
                pass
            peer.state      = ConnectionState.IDLE
            peer.connection = None
        self._crypto.pop(peer_id, None)

    # ── Escucha saliente ──────────────────────────────────────────────────────

    async def _listen_outgoing(self, ws, ip, port, tmp_key):
        peer_addr = f"{ip}:{port}"
        logger.info(f"[NODE]    Escuchando mensajes desde {peer_addr}...")
        try:
            async for raw in ws:
                logger.debug(f"[NODE]    ← Mensaje recibido de {peer_addr}")
                await self._handler.handle(ws, raw)
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"[NODE] ❌ Conexión de {peer_addr} cerrada")
            self._crypto.pop(tmp_key, None)
            self._mark_peer_disconnected_by_ip(ip)

    # ── Handlers de mensajes ──────────────────────────────────────────────────

    async def _on_hello(self, ws, data):
        d       = data["data"]
        username = d["username"]
        peer_id = d["peer_id"]
        remote_ip = ws.remote_address[0]
        
        logger.info(f"[NODE] 📨 Recibido HELLO de {username} ({remote_ip})")
        
        session = CryptoSession()
        pub_key = d.get("public_key", "")
        
        if pub_key:
            logger.info(f"[NODE]    → Recibida clave pública ECC del peer")
            if not session.establish(pub_key):
                logger.error("[NODE] ❌ Error: Fallo en derivación de secreto compartido (ECDH)")
                return
            logger.info(f"[NODE]    ✅ Secreto compartido derivado exitosamente")
        
        peer = Peer(
            id=peer_id, username=username,
            ip=remote_ip, port=d["port"],
            state=ConnectionState.READY, last_seen=datetime.now(), connection=ws,
        )
        self.peers[peer.id]   = peer
        self._crypto[peer.id] = session
        
        logger.info(f"[NODE]    → Enviando HELLO_ACK con nuestra clave pública...")
        await ws.send(Protocol.hello_ack(self.peer_id, session.public_key_pem()))
        
        logger.info(f"[NODE] ✅ [HANDSHAKE COMPLETADO] Conexión lista con {username}")
        if self.on_peer_connected:
            self.on_peer_connected(peer)

    async def _on_hello_ack(self, ws, data):
        d         = data["data"]
        remote_ip = ws.remote_address[0]
        remote_id = d.get("peer_id", remote_ip)
        pub_key   = d.get("public_key", "")
        
        logger.info(f"[NODE] 📨 Recibido HELLO_ACK de {remote_ip}")
        
        tmp_key   = next(
            (k for k in self._crypto if k.startswith("_pending_") and remote_ip in k), None
        )
        session = self._crypto.pop(tmp_key, None) if tmp_key else CryptoSession()
        
        if session and pub_key:
            logger.info(f"[NODE]    → Recibida clave pública ECC del peer")
            session.establish(pub_key)
            logger.info(f"[NODE]    ✅ Secreto compartido derivado exitosamente")
        else:
            logger.warning(f"[NODE]    ⚠️  No hay clave pública en HELLO_ACK")

        peer = self._find_peer_by_ip(remote_ip)
        if peer:
            logger.info(f"[NODE]    → Actualizando estado de {peer.username} a READY")
            peer.state = ConnectionState.READY
            peer.connection = ws
            peer.last_seen  = datetime.now()
        else:
            logger.info(f"[NODE]    → Creando nuevo peer {remote_id}")
            peer = Peer(id=remote_id, username=remote_ip, ip=remote_ip, port=0,
                        state=ConnectionState.READY, last_seen=datetime.now(), connection=ws)
            self.peers[peer.id] = peer

        self._crypto[peer.id] = session
        logger.info(f"[NODE] ✅ [HANDSHAKE COMPLETADO] {remote_ip} está listo para comunicación")
        if self.on_peer_connected:
            self.on_peer_connected(peer)

    async def _on_message(self, ws, data):
        d         = data["data"]
        msg_id    = data["msg_id"]
        await ws.send(Protocol.message_ack(msg_id))
        sender_id = d["sender_id"]
        session   = self._crypto.get(sender_id)
        content   = d["content"]
        if session and session.is_ready:
            try:
                content = session.decrypt(content)
            except Exception as e:
                logger.error(f"[NODE] Descifrado fallido: {e}")
                return
        
        # Detectar si es un mensaje de videollamada
        try:
            msg_data = json.loads(content)
            if isinstance(msg_data, dict) and msg_data.get("type") in ["videocall_offer", "videocall_answer","video_frame", "audio_frame", "videocall_end"]:
                # Es un mensaje de videollamada
                peer = self.peers.get(sender_id)
                if peer and self.on_videocall_message:
                    await self.on_videocall_message(peer, msg_data)
                return
        except (json.JSONDecodeError, ValueError):
            pass  # No es JSON, tratarlo como mensaje normal
        
        if self.on_message_received:
            self.on_message_received(sender_id, d["sender"], content, data["timestamp"])

    async def _on_message_ack(self, ws, data):
        if self.on_message_ack:
            self.on_message_ack(data["data"]["original_msg_id"])

    async def _on_heartbeat(self, ws, data):
        await ws.send(Protocol.heartbeat(self.peer_id))
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.last_seen = datetime.now()

    async def _on_disconnect(self, ws, data):
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.state = ConnectionState.IDLE
            peer.connection = None
            self._crypto.pop(peer.id, None)
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)

    # ── Handlers de archivos ──────────────────────────────────────────────────

    async def _on_file_offer(self, ws, data):
        d  = data["data"]
        ft = self.ft_manager.prepare_receive(
            file_id=d["file_id"], filename=d["filename"],
            filesize=d["filesize"], total_chunks=d["total_chunks"],
            sha256=d["sha256"], peer_id=d["sender_id"],
        )
        logger.info(f"[NODE] FILE_OFFER recibido: {ft.filename} ({ft.size_str})")
        # Notificar al controlador para que muestre el diálogo
        if self.on_file_offer:
            self.on_file_offer(ft)

    async def _on_file_offer_ack(self, ws, data):
        d       = data["data"]
        file_id = d["file_id"]
        ft      = self.ft_manager.transfers.get(file_id)
        if not ft:
            return

        if d.get("accepted"):
            logger.info(f"[NODE] Receptor aceptó {ft.filename} — enviando chunks…")
            peer    = self.peers.get(ft.peer_id)
            session = self._crypto.get(ft.peer_id)
            if peer and peer.connection:
                asyncio.create_task(
                    self.ft_manager.send_chunks(ft, peer.connection, session)
                )
        else:
            logger.info(f"[NODE] Receptor rechazó {ft.filename}")
            ft.status = TransferStatus.REJECTED
            self._ft_notify_update(ft)

    async def _on_file_chunk(self, ws, data):
        d         = data["data"]
        sender_ip = ws.remote_address[0]
        peer      = self._find_peer_by_ip(sender_ip)
        session   = self._crypto.get(peer.id) if peer else None

        self.ft_manager.receive_chunk(
            file_id=d["file_id"],
            chunk_index=d["chunk_index"],
            data_b64=d["data"],
            is_last=d.get("is_last", False),
            crypto_session=session,
        )

    async def _on_file_cancel(self, ws, data):
        file_id = data["data"]["file_id"]
        self.ft_manager.cancel(file_id)
        logger.info(f"[NODE] Transferencia {file_id[:8]}… cancelada por el peer")

    # ── Callbacks del FileTransferManager ────────────────────────────────────

    def _ft_notify_update(self, ft: FileTransfer):
        if self.on_transfer_update:
            self.on_transfer_update(ft)

    def _ft_notify_offer(self, ft: FileTransfer):
        if self.on_file_offer:
            self.on_file_offer(ft)

    def _ft_notify_saved(self, ft: FileTransfer):
        if self.on_file_saved:
            self.on_file_saved(ft)

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _find_peer_by_ip(self, ip: str) -> Optional[Peer]:
        for peer in self.peers.values():
            if peer.ip == ip:
                return peer
        return None

    def _mark_peer_disconnected_by_ip(self, ip: str):
        peer = self._find_peer_by_ip(ip)
        if peer:
            peer.state = ConnectionState.IDLE
            peer.connection = None
            self._crypto.pop(peer.id, None)
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)





