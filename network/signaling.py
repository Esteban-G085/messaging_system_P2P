# network/signaling.py
import json
from utils.crypto import CryptoSession

class Signaling:
    def __init__(self, peer_connection, crypto_session: CryptoSession):
        self.pc = peer_connection
        self.crypto = crypto_session   # instancia de CryptoSession

    def send_offer(self, node, peer, offer):
        message = {
            "type": "videocall_offer",
            "sdp": offer.sdp,
            "type_sdp": offer.type
        }
        encrypted = self.crypto.encrypt_message(json.dumps(message))
        node.send(peer, encrypted)

    def send_answer(self, node, peer, answer):
        message = {
            "type": "videocall_answer",
            "sdp": answer.sdp,
            "type_sdp": answer.type
        }
        encrypted = self.crypto.encrypt_message(json.dumps(message))
        node.send(peer, encrypted)

    def send_candidate(self, node, peer, candidate):
        message = {
            "type": "ice_candidate",
            "candidate": candidate.to_json()
        }
        encrypted = self.crypto.encrypt_message(json.dumps(message))
        node.send(peer, encrypted)

    def handle_message(self, raw_message):
        decrypted = self.crypto.decrypt_message(raw_message)
        data = json.loads(decrypted)
        return data
