# ──────────────────────────────────────────────
#  network/node.py  –  Nodo P2P con ECC + AES
# ──────────────────────────────────────────────

import asyncio
from datetime import datetime
from typing import Callable, Dict, Optional

import websockets

from config.settings import HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT
from models.connection_state import ConnectionState
from models.peer import Peer
from network.client import WebSocketClient
from network.message_handler import MessageHandler
from network.protocol import Protocol
from network.server import WebSocketServer
from utils.crypto import CryptoSession
from utils.helpers import generate_peer_id, get_local_ip
from utils.logger import logger


class P2PNode:
    """
    Nodo central del sistema P2P.
    Cada conexión con un peer tiene su propia CryptoSession (ECDH + AES-GCM).
    """

    def __init__(self, username: str, port: int):
        self.username  = username
        self.port      = port
        self.peer_id   = generate_peer_id()
        self.local_ip  = get_local_ip()

        self.peers: Dict[str, Peer] = {}

        # Una CryptoSession por peer_id: peer_id → CryptoSession
        self._crypto: Dict[str, CryptoSession] = {}

        self._server  = WebSocketServer(port=port)
        self._client  = WebSocketClient()
        self._handler = MessageHandler()

        # Callbacks para el AppController
        self.on_peer_connected:    Optional[Callable[[Peer], None]] = None
        self.on_peer_disconnected: Optional[Callable[[Peer], None]] = None
        self.on_message_received:  Optional[Callable] = None
        self.on_message_ack:       Optional[Callable[[str], None]] = None

        self._setup_handlers()

    # ── Setup ────────────────────────────────────────────────────────────────

    def _setup_handlers(self):
        self._handler.on("HELLO",       self._on_hello)
        self._handler.on("HELLO_ACK",   self._on_hello_ack)
        self._handler.on("MESSAGE",     self._on_message)
        self._handler.on("MESSAGE_ACK", self._on_message_ack)
        self._handler.on("HEARTBEAT",   self._on_heartbeat)
        self._handler.on("DISCONNECT",  self._on_disconnect)

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    async def start(self):
        self._server.set_message_handler(self._handler.handle)
        await self._server.start()
        logger.info(
            f"[NODE] {self.username} iniciado | id={self.peer_id[:8]}… "
            f"| {self.local_ip}:{self.port}"
        )

    async def stop(self):
        for peer_id in list(self.peers):
            await self.disconnect_from_peer(peer_id)
        await self._server.stop()

    # ── API pública ──────────────────────────────────────────────────────────

    async def connect_to_peer(self, ip: str, port: int):
        """
        Conexión saliente: crea una CryptoSession nueva,
        envía HELLO con la clave pública ECC y escucha respuestas.
        """
        session = CryptoSession()
        ws = await self._client.connect(ip, port)

        # Guardamos la sesión temporalmente usando ip:port como clave
        # hasta recibir el HELLO_ACK con el peer_id real
        tmp_key = f"_pending_{ip}:{port}"
        self._crypto[tmp_key] = session

        await ws.send(
            Protocol.hello(
                self.username,
                self.peer_id,
                self.port,
                session.public_key_pem(),
            )
        )
        asyncio.create_task(self._listen_outgoing(ws, ip, port, tmp_key))

    async def send_message(self, peer_id: str, content: str) -> Optional[str]:
        peer    = self.peers.get(peer_id)
        session = self._crypto.get(peer_id)

        if not peer or not peer.is_ready:
            logger.warning(f"[NODE] Peer {peer_id[:8]}… no está listo")
            return None

        if not session or not session.is_ready:
            logger.warning(f"[NODE] Sesión cripto no establecida para {peer_id[:8]}…")
            return None

        # Cifrar antes de enviar
        encrypted = session.encrypt(content)
        msg_id, payload = Protocol.message(self.username, self.peer_id, encrypted)
        await peer.connection.send(payload)
        return msg_id

    async def disconnect_from_peer(self, peer_id: str):
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

    # ── Escucha de mensajes (conexión saliente) ───────────────────────────────

    async def _listen_outgoing(self, ws, ip: str, port: int, tmp_key: str):
        try:
            async for raw in ws:
                await self._handler.handle(ws, raw)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[NODE] Conexión cerrada con {ip}:{port}")
            # Limpiar sesión pendiente si no llegó a establecerse
            self._crypto.pop(tmp_key, None)
            self._mark_peer_disconnected_by_ip(ip)

    # ── Handlers de mensajes ─────────────────────────────────────────────────

    async def _on_hello(self, ws, data: dict):
        """
        Conexión entrante: registrar peer, crear CryptoSession,
        establecerla con la clave pública recibida y responder con HELLO_ACK.
        """
        d = data["data"]

        # Crear y establecer sesión cripto con la clave pública del peer
        session = CryptoSession()
        peer_pub_key = d.get("public_key", "")
        if peer_pub_key:
            ok = session.establish(peer_pub_key)
            if not ok:
                logger.error("[NODE] Fallo al establecer sesión cripto en HELLO")
                return
        else:
            logger.warning("[NODE] HELLO sin clave pública — sesión sin cifrado")

        peer = Peer(
            id=d["peer_id"],
            username=d["username"],
            ip=ws.remote_address[0],
            port=d["port"],
            state=ConnectionState.READY,
            last_seen=datetime.now(),
            connection=ws,
        )
        self.peers[peer.id]  = peer
        self._crypto[peer.id] = session

        # Responder con nuestra clave pública para que el otro nodo
        # también pueda derivar la clave AES
        await ws.send(Protocol.hello_ack(self.peer_id, session.public_key_pem()))

        logger.info(f"[NODE] HELLO de {peer.username} ({peer.address}) — sesión cifrada ✓")
        if self.on_peer_connected:
            self.on_peer_connected(peer)

    async def _on_hello_ack(self, ws, data: dict):
        """
        El peer respondió nuestro HELLO: establecer la sesión cripto
        con su clave pública y marcar el peer como READY.
        """
        d          = data["data"]
        remote_ip  = ws.remote_address[0]
        remote_id  = d.get("peer_id", remote_ip)
        peer_pub_key = d.get("public_key", "")

        # Buscar la sesión pendiente (creada en connect_to_peer)
        tmp_key = next(
            (k for k in self._crypto if k.startswith("_pending_") and remote_ip in k),
            None,
        )
        session = self._crypto.pop(tmp_key, None) if tmp_key else None

        if session and peer_pub_key:
            ok = session.establish(peer_pub_key)
            if ok:
                logger.info(f"[NODE] HELLO_ACK de {remote_ip} — sesión cifrada ✓")
            else:
                logger.error("[NODE] Fallo al establecer sesión cripto en HELLO_ACK")
        else:
            logger.warning("[NODE] HELLO_ACK sin clave pública o sesión perdida")
            session = CryptoSession()   # sesión vacía (sin cifrado)

        # Buscar o crear el peer
        peer = self._find_peer_by_ip(remote_ip)
        if peer:
            peer.state      = ConnectionState.READY
            peer.connection = ws
            peer.last_seen  = datetime.now()
        else:
            peer = Peer(
                id=remote_id,
                username=remote_ip,
                ip=remote_ip,
                port=0,
                state=ConnectionState.READY,
                last_seen=datetime.now(),
                connection=ws,
            )
            self.peers[peer.id] = peer

        self._crypto[peer.id] = session

        if self.on_peer_connected:
            self.on_peer_connected(peer)

    async def _on_message(self, ws, data: dict):
        """Descifra el contenido antes de entregarlo al controlador."""
        d      = data["data"]
        msg_id = data["msg_id"]

        # ACK inmediato (antes de descifrar, para confirmar recepción)
        await ws.send(Protocol.message_ack(msg_id))

        sender_id = d["sender_id"]
        session   = self._crypto.get(sender_id)
        raw_content = d["content"]

        if session and session.is_ready:
            try:
                content = session.decrypt(raw_content)
            except Exception as e:
                logger.error(f"[NODE] Error descifrando mensaje de {sender_id[:8]}…: {e}")
                return
        else:
            # Fallback: mostrar como texto plano (sesión sin cifrado)
            logger.warning(f"[NODE] Mensaje de {sender_id[:8]}… sin sesión cripto")
            content = raw_content

        if self.on_message_received:
            self.on_message_received(
                sender_id, d["sender"], content, data["timestamp"]
            )

    async def _on_message_ack(self, ws, data: dict):
        if self.on_message_ack:
            self.on_message_ack(data["data"]["original_msg_id"])

    async def _on_heartbeat(self, ws, data: dict):
        await ws.send(Protocol.heartbeat(self.peer_id))
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.last_seen = datetime.now()

    async def _on_disconnect(self, ws, data: dict):
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.state      = ConnectionState.IDLE
            peer.connection = None
            self._crypto.pop(peer.id, None)
            logger.info(f"[NODE] Desconexión ordenada de {peer.username}")
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)

    # ── Utilidades internas ───────────────────────────────────────────────────

    def _find_peer_by_ip(self, ip: str) -> Optional[Peer]:
        for peer in self.peers.values():
            if peer.ip == ip:
                return peer
        return None

    def _mark_peer_disconnected_by_ip(self, ip: str):
        peer = self._find_peer_by_ip(ip)
        if peer:
            peer.state      = ConnectionState.IDLE
            peer.connection = None
            self._crypto.pop(peer.id, None)
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)
