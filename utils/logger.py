# ──────────────────────────────────────────────
#  utils/logger.py  –  Logging centralizado
# ──────────────────────────────────────────────

import logging
import sys
from datetime import datetime


def setup_logger(name: str = "p2p_chat") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # Evita duplicar handlers si se llama varias veces
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s  %(name)s › %(message)s",
        datefmt="%H:%M:%S",
    )

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Archivo diario
    log_file = f"p2p_chat_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# Instancia global – importar desde aquí en todos los módulos
logger = setup_logger()
