# ──────────────────────────────────────────────────────────
#           Motor de transferencia
#
#  Flujo emisor:
#    send_file() → FILE_OFFER → espera FILE_OFFER_ACK
#    Si accepted → envía chunks cifrados secuencialmente
#    Al final → FILE_COMPLETE con SHA-256
#
#  Flujo receptor:
#    on_offer()  → callback a UI para aceptar/rechazar
#    on_chunk()  → acumula bytes, reporta progreso
#    on_complete → verifica SHA-256, guarda archivo
# ──────────────────────────────────────────────────────────

import asyncio
import base64
import hashlib
import os
from pathlib import Path
from typing import Callable, Dict, Optional

from models.file_transfer import FileTransfer, TransferStatus
from utils.helpers import generate_msg_id
from utils.logger import logger

CHUNK_SIZE = 65536   # 64 KB por chunk
DOWNLOADS_DIR = Path("downloads")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


class FileTransferManager:
    """
    Gestiona todas las transferencias activas (envío y recepción).
    El nodo lo instancia y lo consulta en cada mensaje de archivo.
    """

    def __init__(self):
        # file_id → FileTransfer
        self.transfers: Dict[str, FileTransfer] = {}
        # file_id → buffer de bytes recibidos (Dict[int, bytes] para reordenamiento)
        self._buffers: Dict[str, Dict[int, bytes]] = {}
        self._chunks_pending: Dict[str, int] = {}

        # Callbacks → asignados por P2PNode
        self.on_transfer_update: Optional[Callable[[FileTransfer], None]] = None
        self.on_file_offer:      Optional[Callable[[FileTransfer], None]] = None
        self.on_file_saved:      Optional[Callable[[FileTransfer], None]] = None

    # ── API de envío ──────────────────────────────────────────────────────────

    def prepare_send(self, filepath: str, peer_id: str) -> FileTransfer:
        """
        Crea el FileTransfer para un archivo a enviar.
        El nodo llama a esto antes de enviar el FILE_OFFER.
        """
        path = Path(filepath)
        size = path.stat().st_size
        total_chunks = max(1, (size + CHUNK_SIZE - 1) // CHUNK_SIZE)
        sha = _sha256(filepath)
        file_id = generate_msg_id()

        ft = FileTransfer(
            id=file_id,
            filename=path.name,
            filesize=size,
            total_chunks=total_chunks,
            peer_id=peer_id,
            is_sender=True,
            sha256=sha,
            status=TransferStatus.OFFERING,
            save_path=filepath,
        )
        self.transfers[file_id] = ft
        return ft

    async def send_chunks(self, ft: FileTransfer, ws, crypto_session) -> bool:
        """
        Envía todos los chunks del archivo cifrados.
        Retorna True si se completó, False si se canceló.
        """
        ft.status = TransferStatus.ACCEPTED
        ft.chunks_done = 0
        self._notify(ft)

        try:
            with open(ft.save_path, "rb") as f:
                chunk_index = 0
                sent_any = False
                while True:
                    raw = f.read(CHUNK_SIZE)
                    if not raw:
                        break

                    if ft.status == TransferStatus.CANCELLED:
                        return False

                    is_last = len(raw) < CHUNK_SIZE or chunk_index == ft.total_chunks - 1

                    # Cifrar chunk con AES-GCM
                    if crypto_session and crypto_session.is_ready:
                        data_b64 = crypto_session.encrypt(base64.b64encode(raw).decode())
                    else:
                        data_b64 = base64.b64encode(raw).decode()

                    import json
                    from utils.helpers import now_iso
                    payload = json.dumps({
                        "type":      "FILE_CHUNK",
                        "msg_id":    generate_msg_id(),
                        "timestamp": now_iso(),
                        "data": {
                            "file_id":     ft.id,
                            "chunk_index": chunk_index,
                            "data":        data_b64,
                            "is_last":     is_last,
                        },
                    })
                    await ws.send(payload)

                    ft.chunks_done = chunk_index + 1
                    self._notify(ft)
                    sent_any = True

                    chunk_index += 1
                    # Pequeña pausa para no saturar el buffer del WebSocket
                    await asyncio.sleep(0.001)

                # Si nunca se envió nada (archivo vacío), igual marcar como completado
                if not sent_any:
                    if ft.status == TransferStatus.CANCELLED:
                        return False
                    # Enviar un chunk final vacío para que el receptor sepa que terminó
                    is_last = True
                    data_b64 = ""
                    import json
                    from utils.helpers import now_iso
                    payload = json.dumps({
                        "type":      "FILE_CHUNK",
                        "msg_id":    generate_msg_id(),
                        "timestamp": now_iso(),
                        "data": {
                            "file_id":     ft.id,
                            "chunk_index": 0,
                            "data":        data_b64,
                            "is_last":     True,
                        },
                    })
                    await ws.send(payload)
                    ft.chunks_done = 1

            ft.status = TransferStatus.COMPLETED
            self._notify(ft)
            return True

        except Exception as e:
            logger.error(f"[FT] Error enviando chunks de {ft.filename}: {e}")
            ft.status = TransferStatus.ERROR
            ft.error_msg = str(e)
            self._notify(ft)
            return False

    # ── API de recepción ──────────────────────────────────────────────────────

    def prepare_receive(
        self,
        file_id: str,
        filename: str,
        filesize: int,
        total_chunks: int,
        sha256: str,
        peer_id: str,
    ) -> FileTransfer:
        """Registra una transferencia entrante pendiente de aceptación."""
        DOWNLOADS_DIR.mkdir(exist_ok=True)
        save_path = str(DOWNLOADS_DIR / filename)

        ft = FileTransfer(
            id=file_id,
            filename=filename,
            filesize=filesize,
            total_chunks=total_chunks,
            peer_id=peer_id,
            is_sender=False,
            sha256=sha256,
            status=TransferStatus.OFFERING,
            save_path=save_path,
        )
        self.transfers[file_id] = ft
        self._buffers[file_id] = {}
        self._chunks_pending[file_id] = total_chunks
        return ft

    def receive_chunk(
        self,
        file_id: str,
        chunk_index: int,
        data_b64: str,
        is_last: bool,
        crypto_session,
    ) -> Optional[FileTransfer]:
        """
        Acumula un chunk recibido (soporta chunks fuera de orden).
        Retorna el FileTransfer actualizado (o None si file_id desconocido).
        """
        ft = self.transfers.get(file_id)
        if not ft:
            logger.warning(f"[FT] Chunk para file_id desconocido: {file_id}")
            return None

        if ft.status == TransferStatus.CANCELLED:
            return ft

        # Descifrar
        try:
            if crypto_session and crypto_session.is_ready:
                raw_b64 = crypto_session.decrypt(data_b64)
                raw = base64.b64decode(raw_b64)
            else:
                raw = base64.b64decode(data_b64)
        except Exception as e:
            logger.error(f"[FT] Error descifrando chunk {chunk_index}: {e}")
            ft.status = TransferStatus.ERROR
            ft.error_msg = f"Error de descifrado en chunk {chunk_index}"
            self._notify(ft)
            return ft

        # Guardar chunk por índice (soporta reordenamiento)
        buf = self._buffers.get(file_id)
        if buf is None:
            logger.warning(f"[FT] Buffer para file_id desconocido: {file_id}")
            return None
        buf[chunk_index] = raw

        ft.chunks_done = len(buf)
        ft.status = TransferStatus.RECEIVING
        self._notify(ft)

        if is_last or ft.chunks_done >= ft.total_chunks:
            self._finalize_receive(ft)

        return ft

    def _finalize_receive(self, ft: FileTransfer):
        """Verifica SHA-256 y guarda el archivo en disco."""
        chunks_dict = self._buffers.pop(ft.id, {})
        self._chunks_pending.pop(ft.id, None)

        # Reconstruir en orden por índice
        data = b"".join(chunks_dict[i] for i in sorted(chunks_dict))

        # Verificar integridad
        received_sha = hashlib.sha256(data).hexdigest()
        if received_sha != ft.sha256:
            logger.error(
                f"[FT] SHA-256 no coincide para {ft.filename}: "
                f"esperado={ft.sha256[:8]}… recibido={received_sha[:8]}…"
            )
            ft.status = TransferStatus.ERROR
            ft.error_msg = "Error de integridad: el archivo puede estar corrupto"
            self._notify(ft)
            return

        # Guardar — si ya existe, agregar sufijo numérico
        save_path = Path(ft.save_path)
        if save_path.exists():
            stem   = save_path.stem
            suffix = save_path.suffix
            parent = save_path.parent
            i = 1
            while save_path.exists():
                save_path = parent / f"{stem}_{i}{suffix}"
                i += 1
            ft.save_path = str(save_path)

        save_path.write_bytes(data)
        ft.status = TransferStatus.COMPLETED
        logger.info(f"[FT] Archivo guardado: {ft.save_path}")
        self._notify(ft)
        if self.on_file_saved:
            self.on_file_saved(ft)

    # ── Cancelar ─────────────────────────────────────────────────────────────

    def cancel(self, file_id: str):
        ft = self.transfers.get(file_id)
        if ft:
            ft.status = TransferStatus.CANCELLED
            self._buffers.pop(file_id, None)
            self._chunks_pending.pop(file_id, None)
            self._notify(ft)

    # ── Interno ───────────────────────────────────────────────────────────────

    def _notify(self, ft: FileTransfer):
        if self.on_transfer_update:
            self.on_transfer_update(ft)
