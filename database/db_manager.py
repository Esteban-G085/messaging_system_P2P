# ──────────────────────────────────────────────
#           Gestor SQLite
# ──────────────────────────────────────────────

import sqlite3
import os
from datetime import datetime
from typing import List, Optional

from config.settings import DB_PATH
from models.message import Message, MessageStatus
from models.peer import Peer
from models.connection_state import ConnectionState
from utils.logger import logger


class DBManager:
    """
    Gestiona toda la persistencia del historial y peers.
    Usa sqlite3 en modo thread-safe (check_same_thread=False
    porque qasync corre en el mismo hilo que Qt).
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def connect(self):
        """Abre la conexión y crea las tablas si no existen."""
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._apply_schema()
        logger.info(f"[DB] Conectado a {self.db_path}")

    def close(self):
        if self._conn:
            self._conn.close()
            logger.info("[DB] Conexión cerrada")

    def _apply_schema(self):
        schema_path = os.path.join(
            os.path.dirname(__file__), "schema.sql"
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            self._conn.executescript(f.read())
        self._conn.commit()

    # ── Peers ────────────────────────────────────────────────────────────────

    def upsert_peer(self, peer: Peer):
        """Inserta o actualiza un peer."""
        sql = """
            INSERT INTO peers (id, username, ip, port, last_connected, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username       = excluded.username,
                ip             = excluded.ip,
                port           = excluded.port,
                last_connected = excluded.last_connected
        """
        self._conn.execute(sql, (
            peer.id,
            peer.username,
            peer.ip,
            peer.port,
            datetime.now().isoformat(),
            int(peer.is_favorite),
        ))
        self._conn.commit()

    def get_all_peers(self) -> List[Peer]:
        """Obtiene la lista de todos los peers registrados en la base de datos."""
        rows = self._conn.execute("SELECT * FROM peers").fetchall()
        return [self._row_to_peer(r) for r in rows]

    def get_peer(self, peer_id: str) -> Optional[Peer]:
        """
        Busca un peer por su identificador único.
        Retorna el objeto Peer si lo encuentra, de lo contrario None.
        """
        row = self._conn.execute(
            "SELECT * FROM peers WHERE id = ?", (peer_id,)
        ).fetchone()
        return self._row_to_peer(row) if row else None

    def set_favorite(self, peer_id: str, value: bool):
        """Marca o desmarca un peer como favorito."""
        self._conn.execute(
            "UPDATE peers SET is_favorite = ? WHERE id = ?",
            (int(value), peer_id),
        )
        self._conn.commit()

    def _row_to_peer(self, row: sqlite3.Row) -> Peer:
        return Peer(
            id=row["id"],
            username=row["username"],
            ip=row["ip"] or "",
            port=row["port"] or 0,
            state=ConnectionState.IDLE,
            is_favorite=bool(row["is_favorite"]),
        )

    # ── Mensajes ─────────────────────────────────────────────────────────────

    def save_message(self, msg: Message):
        """
        Inserta un nuevo mensaje en el historial. 
        Si el identificador del mensaje ya existe, la operación se ignora para evitar duplicados.
        """
        sql = """
            INSERT OR IGNORE INTO messages
                (id, sender_id, receiver_id, content, timestamp, is_delivered, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        self._conn.execute(sql, (
            msg.id,
            msg.sender_id,
            msg.receiver_id,
            msg.content,
            msg.timestamp.isoformat(),
            int(msg.status in (MessageStatus.DELIVERED, MessageStatus.READ)),
            int(msg.status == MessageStatus.READ),
        ))
        self._conn.commit()

    def get_messages_for_peer(
        self,
        peer_id: str,
        local_id: str,
        limit: int = 200,
    ) -> List[Message]:
        """
        Devuelve los últimos `limit` mensajes de la conversación
        entre el nodo local y el peer indicado.
        """
        sql = """
            SELECT * FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
            LIMIT ?
        """
        rows = self._conn.execute(
            sql, (local_id, peer_id, peer_id, local_id, limit)
        ).fetchall()
        return [self._row_to_message(r, local_id) for r in rows]

    def mark_delivered(self, msg_id: str):
        """Marca un mensaje como entregado exitosamente."""
        self._conn.execute(
            "UPDATE messages SET is_delivered = 1 WHERE id = ?", (msg_id,)
        )
        self._conn.commit()

    def mark_read(self, msg_id: str):
        """Marca un mensaje como leído por el usuario."""
        self._conn.execute(
            "UPDATE messages SET is_read = 1 WHERE id = ?", (msg_id,)
        )
        self._conn.commit()

    def _row_to_message(self, row: sqlite3.Row, local_id: str) -> Message:
        is_mine = row["sender_id"] == local_id
        if row["is_read"]:
            status = MessageStatus.READ
        elif row["is_delivered"]:
            status = MessageStatus.DELIVERED
        else:
            status = MessageStatus.SENT

        ts_raw = row["timestamp"]
        try:
            ts = datetime.fromisoformat(ts_raw)
        except Exception:
            ts = datetime.now()

        return Message(
            id=row["id"],
            sender_id=row["sender_id"],
            sender_name="",          # se rellena desde el Peer en memoria
            content=row["content"],
            timestamp=ts,
            receiver_id=row["receiver_id"],
            status=status,
            is_mine=is_mine,
        )

    # ── Log de conexiones ─────────────────────────────────────────────────────

    def log_connection(self, peer_id: str, action: str):
        """
        Registra un evento de conexión/desconexión.
        action: 'connected' | 'disconnected' | 'error'
        """
        self._conn.execute(
            "INSERT INTO connection_log (peer_id, action) VALUES (?, ?)",
            (peer_id, action),
        )
        self._conn.commit()

    def get_connection_log(self, peer_id: str, limit: int = 50) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM connection_log WHERE peer_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (peer_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
