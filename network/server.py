# ──────────────────────────────────────────────
#         Servidor WebSocket
# ──────────────────────────────────────────────

import asyncio
import logging
import time
import websockets
from websockets.exceptions import InvalidUpgrade, InvalidHandshake
from typing import Callable, Dict, Optional

from config.settings import DEFAULT_HOST, RATE_LIMIT_MAX_CONNECTIONS, RATE_LIMIT_WINDOW
from utils.logger import logger


# Silenciar los tracebacks de websockets por peticiones HTTP no-WebSocket
# (Windows/antivirus/OS que tocan el puerto con HTTP normal)
logging.getLogger("websockets.server").setLevel(logging.CRITICAL)


class WebSocketServer:
    """
    Escucha conexiones WebSocket entrantes y delega cada mensaje
    al handler registrado. Incluye rate limiting por IP.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = 5000):
        self.host = host
        self.port = port
        self._server = None
        self._message_handler: Optional[Callable] = None
        self._rate_limits: Dict[str, list[float]] = {}   # ip → lista de timestamps

    def set_message_handler(self, handler: Callable):
        self._message_handler = handler

    def _check_rate_limit(self, ip: str) -> bool:
        """Retorna True si la IP excede el límite de conexiones."""
        now = time.time()
        timestamps = self._rate_limits.get(ip, [])
        # Limpiar timestamps viejos
        cutoff = now - RATE_LIMIT_WINDOW
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= RATE_LIMIT_MAX_CONNECTIONS:
            logger.warning(f"[SERVER] [REJECT] Rate limit excedido para {ip} ({len(timestamps)} conexiones en {RATE_LIMIT_WINDOW}s)")
            return True
        timestamps.append(now)
        self._rate_limits[ip] = timestamps
        return False

    async def _handle_connection(self, websocket):
        remote = websocket.remote_address
        ip = remote[0]

        # Rate limiting
        if self._check_rate_limit(ip):
            await websocket.close(code=1013, reason="Demasiadas conexiones")
            return

        logger.info(f"[SERVER] [CONN] Conexión WebSocket entrante desde {ip}:{remote[1]}")
        try:
            logger.info(f"[SERVER]    Escuchando mensajes de {ip}...")
            async for message in websocket:
                if self._message_handler:
                    logger.debug(f"[SERVER]    ← Mensaje recibido de {ip}")
                    await self._message_handler(websocket, message)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"[SERVER] [OK] Desconexión normal de {ip}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"[SERVER] [ERR] Desconexión con error de {ip}: {e}")
        except (InvalidUpgrade, InvalidHandshake):
            # Petición HTTP plana al puerto WebSocket — ignorar silenciosamente
            pass
        except Exception as e:
            logger.error(f"[SERVER] [ERR] Error inesperado con {ip}: {e}")

    async def start(self):
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            # Suprimir logs internos de websockets sobre handshakes fallidos
            logger=None,
        )
        logger.info(f"[SERVER] [OK] Servidor WebSocket escuchando en ws://{self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[SERVER] Detenido")
