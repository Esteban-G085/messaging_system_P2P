# ──────────────────────────────────────────────
#           Configuración global
# ──────────────────────────────────────────────

APP_NAME    = "P2P Chat"
APP_VERSION = "1.2.2"

# Red
DEFAULT_PORT = 5000
DEFAULT_HOST = "0.0.0.0"

# Timeouts y reintentos
CONNECTION_TIMEOUT  = 5   # segundos para conexión inicial
HEARTBEAT_INTERVAL  = 30  # segundos entre heartbeats
HEARTBEAT_TIMEOUT   = 10  # segundos de espera antes de considerar caído al peer
MAX_RETRIES         = 3
RETRY_DELAYS        = [2, 5, 10]  # segundos de espera entre reintentos (1º, 2º, 3º)

# Persistencia
DB_PATH = "p2p_chat.db"
