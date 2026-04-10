# network/signaling.py
import json
import asyncio
from utils.crypto import CryptoSession
from network.protocol import Protocol
from utils.logger import logger


class Signaling:
    def __init__(self, peer_connection, crypto_session: CryptoSession):
        self.pc = peer_connection
        self.crypto = crypto_session   # instancia de CryptoSession

    async def send_offer(self, node, peer, offer):
        """Envía una oferta SDP cifrada al peer remoto."""
        try:
            message = {
                "type": "videocall_offer",
                "sdp": offer.sdp,
                "type_sdp": offer.type
            }
            content = json.dumps(message)
            encrypted = self.crypto.encrypt(content)
            
            msg_id, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
            logger.info(f"[SIGNALING] Oferta SDP enviada a {peer.username}")
        except Exception as e:
            logger.error(f"[SIGNALING] Error enviando oferta: {e}")

    async def send_answer(self, node, peer, answer):
        """Envía una respuesta SDP cifrada al peer remoto."""
        try:
            message = {
                "type": "videocall_answer",
                "sdp": answer.sdp,
                "type_sdp": answer.type
            }
            content = json.dumps(message)
            encrypted = self.crypto.encrypt(content)
            
            msg_id, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
            logger.info(f"[SIGNALING] Respuesta SDP enviada a {peer.username}")
        except Exception as e:
            logger.error(f"[SIGNALING] Error enviando respuesta: {e}")

    async def send_candidate(self, node, peer, candidate):
        """Envía un candidato ICE cifrado al peer remoto."""
        try:
            # Serializar el candidato ICE
            candidate_data = {
                "candidate": candidate.candidate,
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex
            }
            
            message = {
                "type": "ice_candidate",
                "candidate": candidate_data
            }
            content = json.dumps(message)
            encrypted = self.crypto.encrypt(content)
            
            msg_id, payload = Protocol.message(node.username, node.peer_id, encrypted)
            await peer.connection.send(payload)
            logger.info(f"[SIGNALING] Candidato ICE enviado a {peer.username}")
        except Exception as e:
            logger.error(f"[SIGNALING] Error enviando candidato: {e}")

    def handle_message(self, raw_message):
        """Descifra un mensaje de videollamada."""
        decrypted = self.crypto.decrypt_message(raw_message)
        data = json.loads(decrypted)
        return data
