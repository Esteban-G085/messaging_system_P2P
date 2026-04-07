# ──────────────────────────────────────────────
#           Despachador
# ──────────────────────────────────────────────

import json
from typing import Callable, Dict

from utils.logger import logger


class MessageHandler:
    """
    Parsea mensajes JSON entrantes y despacha al callback
    registrado según el campo "type".
    """

    def __init__(self):
        self._callbacks: Dict[str, Callable] = {}

    def on(self, msg_type: str, callback: Callable):
        """Registra un handler async para un tipo de mensaje."""
        self._callbacks[msg_type] = callback

    async def handle(self, websocket, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"[HANDLER] Mensaje no es JSON válido: {raw[:80]}")
            return

        msg_type = data.get("type")
        if not msg_type:
            logger.warning("[HANDLER] Mensaje sin campo 'type'")
            return

        callback = self._callbacks.get(msg_type)
        if callback:
            try:
                await callback(websocket, data)
            except Exception as e:
                logger.error(f"[HANDLER] Error en callback de '{msg_type}': {e}")
        else:
            logger.warning(f"[HANDLER] Sin handler para tipo: '{msg_type}'")
