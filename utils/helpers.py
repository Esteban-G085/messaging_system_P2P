# ──────────────────────────────────────────────
#  utils/helpers.py  –  Funciones auxiliares
# ──────────────────────────────────────────────

import socket
import uuid
from datetime import datetime


def get_local_ip() -> str:
    """Detecta la IP LAN del dispositivo (sin enviar tráfico real)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_peer_id() -> str:
    """UUID v4 único para identificar al nodo local de forma persistente."""
    return str(uuid.uuid4())


def generate_msg_id() -> str:
    """UUID v4 único por mensaje (usado para ACKs)."""
    return str(uuid.uuid4())


def format_timestamp(dt: datetime) -> str:
    """Formatea un datetime para mostrar en la UI: HH:MM."""
    return dt.strftime("%H:%M")


def now_iso() -> str:
    """Timestamp UTC en formato ISO-8601 con sufijo Z."""
    return datetime.utcnow().isoformat() + "Z"
