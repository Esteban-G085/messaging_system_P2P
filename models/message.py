# ──────────────────────────────────────────────
#           Modelo de mensaje
# ──────────────────────────────────────────────

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageStatus(Enum):
    SENDING   = "sending"
    SENT      = "sent"
    DELIVERED = "delivered"
    READ      = "read"
    ERROR     = "error"


@dataclass
class Message:
    id:          str
    sender_id:   str
    sender_name: str
    content:     str
    timestamp:   datetime              = field(default_factory=datetime.now)
    receiver_id: Optional[str]         = None
    status:      MessageStatus         = MessageStatus.SENDING
    is_mine:     bool                  = False

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "sender_id":   self.sender_id,
            "sender_name": self.sender_name,
            "content":     self.content,
            "timestamp":   self.timestamp.isoformat(),
            "receiver_id": self.receiver_id,
            "status":      self.status.value,
        }
