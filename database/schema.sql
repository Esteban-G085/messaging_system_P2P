-- ──────────────────────────────────────────────
--  database/schema.sql  –  Esquema SQLite P2P
-- ──────────────────────────────────────────────

-- Peers conocidos
CREATE TABLE IF NOT EXISTS peers (
    id             TEXT PRIMARY KEY,
    username       TEXT NOT NULL,
    ip             TEXT,
    port           INTEGER,
    last_connected DATETIME,
    is_favorite    BOOLEAN DEFAULT 0
);

-- Historial de mensajes
CREATE TABLE IF NOT EXISTS messages (
    id           TEXT PRIMARY KEY,
    sender_id    TEXT    NOT NULL,
    receiver_id  TEXT,
    content      TEXT    NOT NULL,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_delivered BOOLEAN DEFAULT 0,
    is_read      BOOLEAN DEFAULT 0,
    FOREIGN KEY (sender_id) REFERENCES peers(id)
);

-- Registro de eventos de conexión
CREATE TABLE IF NOT EXISTS connection_log (
    id        INTEGER  PRIMARY KEY AUTOINCREMENT,
    peer_id   TEXT,
    action    TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peer_id) REFERENCES peers(id)
);
