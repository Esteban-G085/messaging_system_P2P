from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from models.connection_state import ConnectionState


@dataclass
class Peer:
    id:         str
    username:   str
    ip:         str
    port:       int
    state:      ConnectionState    = ConnectionState.IDLE
    last_seen:  Optional[datetime] = None
    connection: Optional[object]   = None

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"

    @property
    def is_ready(self) -> bool:
        return self.state == ConnectionState.READY

    def to_dict(self) -> dict:
        return {
            "id":        self.id,
            "username":  self.username,
            "ip":        self.ip,
            "port":      self.port,
            "state":     self.state.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }
        