import sqlite3
import os
from datetime import datetime, timezone
from typing import List, Optional

from config.settings import DB_PATH
from models.message import Message, MessageStatus
from models.peer import Peer
from models.connection_state import ConnectionState
from utils.logger import logger


class DBManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._apply_schema()
        logger.info(f"[DB] Conectado a {self.db_path}")

    def _apply_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            self._conn.executescript(f.read())
        self._conn.commit()

    # ── Peers ─────────────────────────────────────────────────────────────────

    def upsert_peer(self, peer: Peer):
        sql = """
            INSERT INTO peers (id, username, ip, port, last_connected)
            VALUES (?, ?, ?, ?, ?)
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
        ))
        self._conn.commit()

    def _row_to_peer(self, row: sqlite3.Row) -> Peer:
        return Peer(
            id=row["id"],
            username=row["username"],
            ip=row["ip"] or "",
            port=row["port"] or 0,
            state=ConnectionState.IDLE,
        )

    # ── Fingerprints ──────────────────────────────────────────────────────────

    def get_fingerprint(self, peer_id: str) -> Optional[str]:
        """Retorna el fingerprint almacenado para un peer, o None."""
        row = self._conn.execute(
            "SELECT fingerprint FROM peer_fingerprints WHERE peer_id = ?", (peer_id,)
        ).fetchone()
        return row["fingerprint"] if row else None

    def save_fingerprint(self, peer_id: str, fingerprint: str):
        """Guarda o actualiza el fingerprint de un peer."""
        self._conn.execute("""
            INSERT INTO peer_fingerprints (peer_id, fingerprint, trusted)
            VALUES (?, ?, 1)
            ON CONFLICT(peer_id) DO UPDATE SET fingerprint = excluded.fingerprint
        """, (peer_id, fingerprint))
        self._conn.commit()

    def is_fingerprint_trusted(self, peer_id: str) -> bool:
        """Retorna True si el fingerprint está marcado como confiable."""
        row = self._conn.execute(
            "SELECT trusted FROM peer_fingerprints WHERE peer_id = ?", (peer_id,)
        ).fetchone()
        return bool(row and row["trusted"])

    # ── Mensajes ──────────────────────────────────────────────────────────────

    def save_message(self, msg: Message):
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

    def get_messages_for_peer(self, peer_id: str, local_id: str, limit: int = 200) -> List[Message]:
        sql = """
            SELECT * FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
            LIMIT ?
        """
        rows = self._conn.execute(sql, (local_id, peer_id, peer_id, local_id, limit)).fetchall()
        return [self._row_to_message(r, local_id) for r in rows]

    def mark_delivered(self, msg_id: str):
        self._conn.execute(
            "UPDATE messages SET is_delivered = 1 WHERE id = ?", (msg_id,)
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

        try:
            ts_str = row["timestamp"]
            # Compatibilidad con Python < 3.11 (no soporta sufijo Z)
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            ts = datetime.fromisoformat(ts_str)
        except Exception:
            ts = datetime.now(timezone.utc)

        return Message(
            id=row["id"],
            sender_id=row["sender_id"],
            sender_name="",
            content=row["content"],
            timestamp=ts,
            receiver_id=row["receiver_id"],
            status=status,
            is_mine=is_mine,
        )