# ──────────────────────────────────────────────
#  utils/validators.py  –  Validación de entrada
# ──────────────────────────────────────────────

import re
from typing import Tuple


def validate_ip(ip: str) -> bool:
    """Valida que la cadena sea una IPv4 bien formada."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip.strip()):
        return False
    return all(0 <= int(p) <= 255 for p in ip.split("."))


def validate_port(port: int) -> bool:
    """Puerto válido para la app: 1024-65535."""
    return 1024 <= port <= 65535


def validate_username(username: str) -> bool:
    """Username entre 2 y 32 caracteres."""
    return bool(username and 2 <= len(username.strip()) <= 32)


def validate_connection(ip: str, port: int) -> Tuple[bool, str]:
    """
    Valida ip+puerto antes de intentar conectar.
    Retorna (ok, mensaje_error).
    """
    if not validate_ip(ip):
        return False, f"Dirección IP inválida: '{ip}'"
    if not validate_port(port):
        return False, f"Puerto fuera de rango (1024-65535): {port}"
    return True, ""
