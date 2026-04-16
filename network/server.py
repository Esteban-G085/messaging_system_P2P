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
        logger.info(f"[SERVER] 🔗 Conexión WebSocket entrante desde {remote[0]}:{remote[1]}")
        try:
            logger.info(f"[SERVER]    Escuchando mensajes de {remote[0]}...")
            async for message in websocket:
                if self._message_handler:
                    logger.debug(f"[SERVER]    ← Mensaje recibido de {remote[0]}")
                    await self._message_handler(websocket, message)
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(f"[SERVER] ✅ Desconexión normal de {remote[0]}")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning(f"[SERVER] ❌ Desconexión con error de {remote[0]}: {e}")
        except (InvalidUpgrade, InvalidHandshake):
            # Petición HTTP plana al puerto WebSocket — ignorar silenciosamente
            pass
        except Exception as e:
            logger.error(f"[SERVER] ❌ Error inesperado con {remote[0]}: {e}")

    async def start(self):
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port,
            # Suprimir logs internos de websockets sobre handshakes fallidos
            logger=None,
        )
        logger.info(f"[SERVER] 🎧 Servidor WebSocket escuchando en ws://{self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[SERVER] Detenido")
