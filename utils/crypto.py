# ──────────────────────────────────────────────────────────
#  utils/crypto.py  –  Criptografía híbrida ECC + AES-GCM
#
#  Flujo por sesión:
#    1. Cada nodo genera par de claves ECC (SECP256R1)
#    2. Se intercambian claves públicas en el HELLO
#    3. ECDH  →  secreto compartido
#    4. HKDF  →  clave simétrica AES-256
#    5. AES-GCM  →  cifrado/descifrado de cada mensaje
# ──────────────────────────────────────────────────────────

import base64
import hashlib
import os

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDH,
    SECP256R1,
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
    generate_private_key,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from utils.logger import logger


# ── Constantes ────────────────────────────────────────────

CURVE      = SECP256R1()
AES_KEY_LEN = 32   # AES-256
IV_LEN      = 12   # 96 bits recomendado para GCM


# ─────────────────────────────────────────────────────────
#  CryptoSession  –  una instancia por par de peers
# ─────────────────────────────────────────────────────────

class CryptoSession:
    """
    Encapsula todo el estado criptográfico de una sesión P2P.

    Uso:
        session = CryptoSession()
        pub_pem = session.public_key_pem()   # enviar al peer

        session.establish(peer_pub_pem)      # recibir del peer
        ciphertext = session.encrypt("hola")
        plaintext  = session.decrypt(ciphertext)
    """

    def __init__(self):
        # Par de claves ECC de este nodo para esta sesión
        self._private_key: EllipticCurvePrivateKey = generate_private_key(CURVE)
        self._aes_key: bytes | None = None   # se establece tras el intercambio
        self._peer_public_key_pem: str = ""   # clave pública del peer para fingerprint

    # ── Clave pública ─────────────────────────────────────

    def public_key_pem(self) -> str:
        """Retorna la clave pública en formato PEM (para enviar por red)."""
        pem_bytes = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem_bytes.decode("utf-8")

    # ── Establecer sesión ─────────────────────────────────

    def establish(self, peer_public_pem: str) -> bool:
        """
        Recibe la clave pública del peer (PEM), ejecuta ECDH
        y deriva la clave AES-256 con HKDF.
        Retorna True si todo fue correcto.
        """
        try:
            self._peer_public_key_pem = peer_public_pem
            peer_pub: EllipticCurvePublicKey = serialization.load_pem_public_key(
                peer_public_pem.encode("utf-8")
            )
            # ECDH → secreto compartido
            shared_secret: bytes = self._private_key.exchange(ECDH(), peer_pub)

            # HKDF → clave AES-256
            self._aes_key = HKDF(
                algorithm=hashes.SHA256(),
                length=AES_KEY_LEN,
                salt=None,
                info=b"p2p-chat-session",
            ).derive(shared_secret)

            logger.info("[CRYPTO] Sesión establecida correctamente")
            return True

        except Exception as e:
            logger.error(f"[CRYPTO] Error estableciendo sesión: {e}")
            return False

    @property
    def peer_fingerprint(self) -> str:
        """SHA-256 de la clave pública del peer, formateado como fingerprint."""
        if not self._peer_public_key_pem:
            return ""
        raw = hashlib.sha256(self._peer_public_key_pem.encode("utf-8")).hexdigest()
        # Formato: grupos de 4 caracteres separados por espacio
        return " ".join(raw[i:i+4] for i in range(0, len(raw), 4))

    @property
    def is_ready(self) -> bool:
        return self._aes_key is not None

    # ── Cifrado / Descifrado ──────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """
        Cifra un mensaje con AES-256-GCM.
        Retorna base64(iv + ciphertext_con_tag) como string.
        """
        if not self.is_ready:
            raise RuntimeError("La sesión aún no está establecida")

        iv = os.urandom(IV_LEN)          # IV aleatorio, NUNCA reutilizar
        aesgcm = AESGCM(self._aes_key)
        ciphertext = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
        # Empaquetamos: iv (12 bytes) || ciphertext+tag
        packed = iv + ciphertext
        return base64.b64encode(packed).decode("utf-8")

    def decrypt(self, payload_b64: str) -> str:
        """
        Descifra un payload generado por encrypt().
        Lanza ValueError si el tag de autenticación falla (mensaje alterado).
        """
        if not self.is_ready:
            raise RuntimeError("La sesión aún no está establecida")

        packed = base64.b64decode(payload_b64.encode("utf-8"))
        iv         = packed[:IV_LEN]
        ciphertext = packed[IV_LEN:]

        aesgcm = AESGCM(self._aes_key)
        plaintext = aesgcm.decrypt(iv, ciphertext, None)
        return plaintext.decode("utf-8")
