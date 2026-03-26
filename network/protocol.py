# ──────────────────────────────────────────────
#  network/protocol.py  –  Protocolo de mensajes
# ──────────────────────────────────────────────

import json
from typing import Tuple

from utils.helpers import generate_msg_id, now_iso


class Protocol:
    """
    Fábrica de mensajes JSON del protocolo P2P.
    Todos los métodos retornan strings listos para enviar por WebSocket.
    """

    # ── Handshake ───────────────────────────────────────────────────────────

    @staticmethod
    def hello(username: str, peer_id: str, port: int) -> str:
        return json.dumps({
            "type":      "HELLO",
            "msg_id":    generate_msg_id(),
            "timestamp": now_iso(),
            "data": {
                "username": username,
                "peer_id":  peer_id,
                "port":     port,
            },
        })

    @staticmethod
    def hello_ack(peer_id: str) -> str:
        return json.dumps({
            "type":      "HELLO_ACK",
            "msg_id":    generate_msg_id(),
            "timestamp": now_iso(),
            "data": {
                "status":  "accepted",
                "peer_id": peer_id,
            },
        })

    # ── Mensajería ───────────────────────────────────────────────────────────

    @staticmethod
    def message(sender: str, sender_id: str, content: str) -> Tuple[str, str]:
        """Retorna (msg_id, payload_json) para poder rastrear ACKs."""
        msg_id = generate_msg_id()
        payload = json.dumps({
            "type":      "MESSAGE",
            "msg_id":    msg_id,
            "timestamp": now_iso(),
            "data": {
                "sender":    sender,
                "sender_id": sender_id,
                "content":   content,
            },
        })
        return msg_id, payload

    @staticmethod
    def message_ack(original_msg_id: str) -> str:
        return json.dumps({
            "type":      "MESSAGE_ACK",
            "msg_id":    generate_msg_id(),
            "timestamp": now_iso(),
            "data": {
                "original_msg_id": original_msg_id,
                "status":          "delivered",
            },
        })

    # ── Control de conexión ──────────────────────────────────────────────────

    @staticmethod
    def heartbeat(peer_id: str) -> str:
        return json.dumps({
            "type":      "HEARTBEAT",
            "msg_id":    generate_msg_id(),
            "timestamp": now_iso(),
            "data": {"peer_id": peer_id},
        })

    @staticmethod
    def disconnect(reason: str = "user_logout") -> str:
        return json.dumps({
            "type":      "DISCONNECT",
            "msg_id":    generate_msg_id(),
            "timestamp": now_iso(),
            "data": {"reason": reason},
        })

    # ── Parsing ──────────────────────────────────────────────────────────────

    @staticmethod
    def parse(raw: str) -> dict:
        return json.loads(raw)
