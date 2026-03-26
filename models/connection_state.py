# ──────────────────────────────────────────────
#  models/connection_state.py  –  Estados P2P
# ──────────────────────────────────────────────

from enum import Enum


class ConnectionState(Enum):
    IDLE           = "idle"
    CONNECTING     = "connecting"
    CONNECTED      = "connected"
    AUTHENTICATING = "authenticating"
    READY          = "ready"
    ERROR          = "error"
    DISCONNECTING  = "disconnecting"
