-- ──────────────────────────────────────────────
--   Esquema SQLite P2P
-- ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS peers (
    id             TEXT PRIMARY KEY,
    username       TEXT NOT NULL,
    ip             TEXT,
    port           INTEGER,
    last_connected DATETIME
    );


CREATE TABLE IF NOT EXISTS peer_fingerprints (
    peer_id    TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    trusted    BOOLEAN DEFAULT 0,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (peer_id) REFERENCES peers(id)
);

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