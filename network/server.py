# ──────────────────────────────────────────────
#         Servidor WebSocket
# ──────────────────────────────────────────────

import asyncio
import logging
import websockets
from websockets.exceptions import InvalidUpgrade, InvalidHandshake
from typing import Callable, Optional

from config.settings import DEFAULT_HOST
from utils.logger import logger


# Silenciar los tracebacks de websockets por peticiones HTTP no-WebSocket
# (Windows/antivirus/OS que tocan el puerto con HTTP normal)
logging.getLogger("websockets.server").setLevel(logging.CRITICAL)


class WebSocketServer:
    """
    Escucha conexiones WebSocket entrantes y delega cada mensaje
    al handler registrado.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = 5000):
        self.host = host
        self.port = port
        self._server = None
        self._message_handler: Optional[Callable] = None

    def set_message_handler(self, handler: Callable):
        self._message_handler = handler

    async def _handle_connection(self, websocket):
        remote = websocket.remote_address
        logger.info(f"[SERVER] Conexión entrante desde {remote}")
        try:
            async for message in websocket:
                if self._message_handler:
                    await self._message_handler(websocket, message)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"[SERVER] Conexión cerrada normalmente: {remote}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"[SERVER] Conexión cerrada con error: {remote} – {e}")
        except (InvalidUpgrade, InvalidHandshake):
            # Petición HTTP plana al puerto WebSocket — ignorar silenciosamente
            pass
        except Exception as e:
            logger.error(f"[SERVER] Error inesperado con {remote}: {e}")

    async def start(self):
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            # Suprimir logs internos de websockets sobre handshakes fallidos
            logger=None,
        )
        logger.info(f"[SERVER] Escuchando en {self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[SERVER] Detenido")
