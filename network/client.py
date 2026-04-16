# ──────────────────────────────────────────────
#           Cliente WebSocket
# ──────────────────────────────────────────────

import asyncio
import websockets
from websockets.client import WebSocketClientProtocol
from typing import Dict

from config.settings import CONNECTION_TIMEOUT, MAX_RETRIES, RETRY_DELAYS
from utils.logger import logger


class WebSocketClient:
    """
    Gestiona conexiones salientes a peers remotos.
    Incluye reintentos automáticos con backoff.
    """

    def __init__(self):
        self._connections: Dict[str, WebSocketClientProtocol] = {}

    async def connect(
        self,
        ip: str,
        port: int,
        timeout: float = CONNECTION_TIMEOUT,
    ) -> WebSocketClientProtocol:
        """
        Intenta conectar al peer indicado.
        Lanza ConnectionError si falla tras MAX_RETRIES intentos.
        """
        uri = f"ws://{ip}:{port}"
        logger.info(f"[CLIENT] 🔗 [FASE 1/3] Iniciando conexión WebSocket a {uri}")

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"[CLIENT]    → Intento {attempt + 1}/{MAX_RETRIES}: Resolviendo DNS y conectando...")
                ws = await asyncio.wait_for(
                    websockets.connect(uri),
                    timeout=timeout,
                )
                key = f"{ip}:{port}"
                self._connections[key] = ws
                logger.info(f"[CLIENT] ✅ [FASE 1/3] WebSocket conectado a {uri}")
                return ws

            except asyncio.TimeoutError:
                logger.warning(f"[CLIENT]    ⏱️  Timeout ({timeout}s) conectando a {uri}")
            except Exception as e:
                logger.warning(f"[CLIENT]    ❌ Error: {e}")

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.info(f"[CLIENT] Reintentando en {delay}s…")
                await asyncio.sleep(delay)

        raise ConnectionError(
            f"No se pudo conectar a {ip}:{port} tras {MAX_RETRIES} intentos"
        )

    async def send(self, ws: WebSocketClientProtocol, message: str):
        """Envía un mensaje por el WebSocket dado."""
        try:
            await ws.send(message)
        except Exception as e:
            logger.error(f"[CLIENT] Error al enviar mensaje: {e}")
            raise

    async def disconnect(self, ip: str, port: int):
        """Cierra la conexión con un peer."""
        key = f"{ip}:{port}"
        ws = self._connections.pop(key, None)
        if ws:
            await ws.close()
            logger.info(f"[CLIENT] Desconectado de {key}")
