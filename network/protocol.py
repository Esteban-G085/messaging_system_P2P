# ──────────────────────────────────────────────
#  network/protocol.py  –  Protocolo de mensajes
# ──────────────────────────────────────────────

import json
from typing import Tuple

from utils.helpers import generate_msg_id, now_iso


class Protocol:

    # ── Handshake ────────────────────────────────────────────────────────────

    @staticmethod
    def hello(username: str, peer_id: str, port: int, public_key_pem: str) -> str:
        return json.dumps({
            "type": "HELLO", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"username": username, "peer_id": peer_id,
                     "port": port, "public_key": public_key_pem},
        })

    @staticmethod
    def hello_ack(peer_id: str, public_key_pem: str) -> str:
        return json.dumps({
            "type": "HELLO_ACK", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"status": "accepted", "peer_id": peer_id, "public_key": public_key_pem},
        })

    # ── Mensajería ───────────────────────────────────────────────────────────

    @staticmethod
    def message(sender: str, sender_id: str, encrypted_content: str) -> Tuple[str, str]:
        msg_id = generate_msg_id()
        payload = json.dumps({
            "type": "MESSAGE", "msg_id": msg_id, "timestamp": now_iso(),
            "data": {"sender": sender, "sender_id": sender_id, "content": encrypted_content},
        })
        return msg_id, payload

    @staticmethod
    def message_ack(original_msg_id: str) -> str:
        return json.dumps({
            "type": "MESSAGE_ACK", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"original_msg_id": original_msg_id, "status": "delivered"},
        })

    # ── Transferencia de archivos ─────────────────────────────────────────────

    @staticmethod
    def file_offer(file_id: str, sender_id: str, filename: str,
                   filesize: int, total_chunks: int, sha256: str) -> str:
        """Propuesta de envío de archivo al receptor."""
        return json.dumps({
            "type": "FILE_OFFER", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {
                "file_id": file_id, "sender_id": sender_id,
                "filename": filename, "filesize": filesize,
                "total_chunks": total_chunks, "sha256": sha256,
            },
        })

    @staticmethod
    def file_offer_ack(file_id: str, accepted: bool) -> str:
        """Respuesta del receptor: acepta o rechaza la transferencia."""
        return json.dumps({
            "type": "FILE_OFFER_ACK", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"file_id": file_id, "accepted": accepted},
        })

    @staticmethod
    def file_cancel(file_id: str, reason: str = "user_cancelled") -> str:
        """Cancela una transferencia en curso."""
        return json.dumps({
            "type": "FILE_CANCEL", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"file_id": file_id, "reason": reason},
        })

    # ── Control de conexión ──────────────────────────────────────────────────

    @staticmethod
    def heartbeat(peer_id: str) -> str:
        return json.dumps({
            "type": "HEARTBEAT", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"peer_id": peer_id},
        })

    @staticmethod
    def disconnect(reason: str = "user_logout") -> str:
        return json.dumps({
            "type": "DISCONNECT", "msg_id": generate_msg_id(), "timestamp": now_iso(),
            "data": {"reason": reason},
        })

    @staticmethod
    def parse(raw: str) -> dict:
        return json.loads(raw)
