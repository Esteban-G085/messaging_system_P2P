# ──────────────────────────────────────────────
#  models/file_transfer.py  –  Transferencia
# ──────────────────────────────────────────────

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TransferStatus(Enum):
    OFFERING     = "offering"      # esperando que el receptor acepte
    ACCEPTED     = "accepted"      # receptor aceptó, enviando chunks
    RECEIVING    = "receiving"     # recibiendo chunks
    COMPLETED    = "completed"     # transferencia exitosa
    REJECTED     = "rejected"      # receptor rechazó
    CANCELLED    = "cancelled"     # cancelado por alguno de los dos
    ERROR        = "error"         # error de red o integridad


@dataclass
class FileTransfer:
    id:           str                        # UUID único de la transferencia
    filename:     str                        # nombre original del archivo
    filesize:     int                        # tamaño en bytes
    total_chunks: int                        # cantidad total de chunks
    peer_id:      str                        # con quién se transfiere
    is_sender:    bool                       # True = yo envío, False = yo recibo
    sha256:       str                        # hash SHA-256 del archivo completo
    status:       TransferStatus = TransferStatus.OFFERING
    chunks_done:  int            = 0         # chunks procesados hasta ahora
    save_path:    Optional[str]  = None      # ruta donde se guarda (receptor)
    started_at:   datetime       = field(default_factory=datetime.now)
    error_msg:    str            = ""

    @property
    def progress(self) -> float:
        """Progreso de 0.0 a 1.0"""
        if self.total_chunks == 0:
            return 0.0
        return min(self.chunks_done / self.total_chunks, 1.0)

    @property
    def progress_pct(self) -> int:
        return int(self.progress * 100)

    @property
    def size_str(self) -> str:
        if self.filesize < 1024:
            return f"{self.filesize} B"
        elif self.filesize < 1024 ** 2:
            return f"{self.filesize / 1024:.1f} KB"
        elif self.filesize < 1024 ** 3:
            return f"{self.filesize / 1024**2:.1f} MB"
        return f"{self.filesize / 1024**3:.1f} GB"
