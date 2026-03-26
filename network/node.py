# ──────────────────────────────────────────────
#  network/node.py  –  Nodo P2P (orquestador)
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
from utils.helpers import generate_peer_id, get_local_ip
from utils.logger import logger


class P2PNode:
    """
    Nodo central del sistema P2P.
    Une el servidor, el cliente y el dispatcher de mensajes.
    Expone callbacks para que el controlador reaccione a eventos de red.
    """

    def __init__(self, username: str, port: int):
        self.username  = username
        self.port      = port
        self.peer_id   = generate_peer_id()
        self.local_ip  = get_local_ip()

        self.peers: Dict[str, Peer] = {}   # peer_id → Peer

        self._server  = WebSocketServer(port=port)
        self._client  = WebSocketClient()
        self._handler = MessageHandler()

        # ── Callbacks para el AppController ────────────────────────────────
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
        Establece conexión saliente, envía HELLO
        y lanza una tarea que escucha mensajes de ese peer.
        """
        ws = await self._client.connect(ip, port)
        await ws.send(Protocol.hello(self.username, self.peer_id, self.port))
        asyncio.create_task(self._listen_outgoing(ws, ip, port))

    async def send_message(self, peer_id: str, content: str) -> Optional[str]:
        peer = self.peers.get(peer_id)
        if not peer or not peer.is_ready:
            logger.warning(f"[NODE] Peer {peer_id[:8]}… no está listo")
            return None

        msg_id, payload = Protocol.message(self.username, self.peer_id, content)
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

    # ── Escucha de mensajes (conexión saliente) ───────────────────────────────

    async def _listen_outgoing(self, ws, ip: str, port: int):
        try:
            async for raw in ws:
                await self._handler.handle(ws, raw)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[NODE] Conexión cerrada con {ip}:{port}")
            self._mark_peer_disconnected_by_ip(ip)

    # ── Handlers de mensajes ─────────────────────────────────────────────────

    async def _on_hello(self, ws, data: dict):
        d    = data["data"]
        peer = Peer(
            id=d["peer_id"],
            username=d["username"],
            ip=ws.remote_address[0],
            port=d["port"],
            state=ConnectionState.READY,
            last_seen=datetime.now(),
            connection=ws,
        )
        self.peers[peer.id] = peer
        await ws.send(Protocol.hello_ack(self.peer_id))
        logger.info(f"[NODE] HELLO de {peer.username} ({peer.address})")
        if self.on_peer_connected:
            self.on_peer_connected(peer)

    async def _on_hello_ack(self, ws, data: dict):
        remote_ip = ws.remote_address[0]
        # El peer puede ya estar en el dict (si envió HELLO al mismo tiempo)
        peer = self._find_peer_by_ip(remote_ip)
        if peer:
            peer.state      = ConnectionState.READY
            peer.connection = ws
            peer.last_seen  = datetime.now()
            logger.info(f"[NODE] HELLO_ACK de {peer.username}")
            if self.on_peer_connected:
                self.on_peer_connected(peer)
        else:
            # Peer aún no registrado (conexión saliente sin HELLO previo)
            remote_id = data["data"].get("peer_id", remote_ip)
            peer = Peer(
                id=remote_id,
                username=remote_ip,   # nombre provisional
                ip=remote_ip,
                port=0,
                state=ConnectionState.READY,
                last_seen=datetime.now(),
                connection=ws,
            )
            self.peers[peer.id] = peer
            if self.on_peer_connected:
                self.on_peer_connected(peer)

    async def _on_message(self, ws, data: dict):
        d      = data["data"]
        msg_id = data["msg_id"]
        await ws.send(Protocol.message_ack(msg_id))    # ACK inmediato
        if self.on_message_received:
            self.on_message_received(
                d["sender_id"], d["sender"], d["content"], data["timestamp"]
            )

    async def _on_message_ack(self, ws, data: dict):
        if self.on_message_ack:
            self.on_message_ack(data["data"]["original_msg_id"])

    async def _on_heartbeat(self, ws, data: dict):
        # Responder el heartbeat para confirmar que seguimos vivos
        await ws.send(Protocol.heartbeat(self.peer_id))
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.last_seen = datetime.now()

    async def _on_disconnect(self, ws, data: dict):
        peer = self._find_peer_by_ip(ws.remote_address[0])
        if peer:
            peer.state      = ConnectionState.IDLE
            peer.connection = None
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
            if self.on_peer_disconnected:
                self.on_peer_disconnected(peer)
