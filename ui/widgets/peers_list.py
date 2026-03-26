# ──────────────────────────────────────────────
#  ui/widgets/peers_list.py  –  Lista de peers
# ──────────────────────────────────────────────

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from models.connection_state import ConnectionState
from models.peer import Peer
from ui.styles import COLORS


# ── Item personalizado ────────────────────────────────────────────────────────

class PeerItem(QListWidgetItem):
    INDICATORS = {
        ConnectionState.READY:         ("●", COLORS["connected"]),
        ConnectionState.CONNECTING:    ("⟳", COLORS["connecting"]),
        ConnectionState.ERROR:         ("✗", COLORS["error"]),
        ConnectionState.DISCONNECTING: ("○", COLORS["disconnected"]),
    }

    def __init__(self, peer: Peer):
        super().__init__()
        self.peer = peer
        self.refresh()

    def refresh(self):
        icon, color = self.INDICATORS.get(
            self.peer.state, ("○", COLORS["disconnected"])
        )
        self.setText(f"  {icon}  {self.peer.username}   {self.peer.address}")
        self.setForeground(QColor(color))


# ── Widget ────────────────────────────────────────────────────────────────────

class PeersList(QWidget):
    peer_selected = Signal(object)   # emite un Peer

    def __init__(self):
        super().__init__()
        self._items: dict[str, PeerItem] = {}   # peer_id → item
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("  Peers")
        header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 9pt; "
            "padding: 8px 10px 4px 10px; font-weight: 600; letter-spacing: 1px;"
        )
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget { padding-top: 0; }")
        self.list_widget.itemClicked.connect(self._on_click)
        layout.addWidget(self.list_widget)

    def add_or_update_peer(self, peer: Peer):
        if peer.id in self._items:
            item = self._items[peer.id]
            item.peer = peer
            item.refresh()
        else:
            item = PeerItem(peer)
            self._items[peer.id] = item
            self.list_widget.addItem(item)

    def _on_click(self, item: PeerItem):
        self.peer_selected.emit(item.peer)
