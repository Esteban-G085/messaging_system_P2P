# ──────────────────────────────────────────────
#           Vista de mensajes
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer

from models.message import Message, MessageStatus
from ui.styles import COLORS
from utils.helpers import format_timestamp


# ── Burbuja de mensaje ────────────────────────────────────────────────────────

class MessageBubble(QFrame):
    STATUS_ICONS = {
        MessageStatus.SENDING:   "⚪",
        MessageStatus.SENT:      "✓",
        MessageStatus.DELIVERED: "✓✓",
        MessageStatus.READ:      "✓✓",
        MessageStatus.ERROR:     "✗",
    }

    def __init__(self, msg: Message):
        super().__init__()
        self.msg = msg
        self._setup_ui()

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 3, 6, 3)

        bubble = QWidget()
        bubble.setMaximumWidth(420)
        inner = QVBoxLayout(bubble)
        inner.setContentsMargins(10, 7, 10, 6)
        inner.setSpacing(2)

        # Nombre (sólo mensajes ajenos)
        if not self.msg.is_mine:
            name = QLabel(self.msg.sender_name)
            name.setStyleSheet(
                f"color: {COLORS['accent']}; font-size: 8pt; font-weight: 600;"
            )
            inner.addWidget(name)

        # Texto del mensaje
        content = QLabel(self.msg.content)
        content.setWordWrap(True)
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content.setStyleSheet("color: #FFFFFF; font-size: 10pt;")
        inner.addWidget(content)

        # Pie: hora + estado
        time_str   = format_timestamp(self.msg.timestamp)
        status_str = self.STATUS_ICONS.get(self.msg.status, "") if self.msg.is_mine else ""
        footer = QLabel(f"{time_str}  {status_str}".strip())
        footer.setAlignment(Qt.AlignRight)
        footer.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 7pt; margin-top: 2px;"
        )
        inner.addWidget(footer)

        if self.msg.is_mine:
            bubble.setStyleSheet(
                f"background-color: {COLORS['bg_bubble_me']}; border-radius: 10px;"
            )
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            bubble.setStyleSheet(
                f"background-color: {COLORS['bg_bubble_th']}; border-radius: 10px;"
            )
            outer.addWidget(bubble)
            outer.addStretch()


# ── Vista de chat ─────────────────────────────────────────────────────────────

class ChatView(QWidget):
    def __init__(self):
        super().__init__()
        self._current_peer_id: str | None = None
        self._bubbles: dict[str, MessageBubble] = {}   # msg_id → burbuja
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cabecera
        self.header = QLabel("  Selecciona un peer para chatear")
        self.header.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; "
            f"color: {COLORS['text_muted']}; "
            "padding: 10px 14px; font-size: 10pt; font-weight: 600; "
            "border-bottom: 1px solid #2A2A2A;"
        )
        layout.addWidget(self.header)

        # Área de scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.msg_layout = QVBoxLayout(self.container)
        self.msg_layout.setContentsMargins(4, 8, 4, 8)
        self.msg_layout.setSpacing(1)
        self.msg_layout.addStretch()   # empuja mensajes hacia arriba

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, stretch=1)

    # ── API pública ───────────────────────────────────────────────────────────

    def set_peer(self, peer_name: str, peer_id: str, messages: list[Message]):
        self._current_peer_id = peer_id
        self.header.setText(f"  Chat con  {peer_name}")
        self.header.setStyleSheet(
            f"background-color: {COLORS['bg_panel']}; "
            "color: #FFFFFF; "
            "padding: 10px 14px; font-size: 10pt; font-weight: 600; "
            "border-bottom: 1px solid #2A2A2A;"
        )
        self._clear()
        for msg in messages:
            self._append_bubble(msg)

    def add_message(self, peer_id: str, msg: Message):
        if peer_id == self._current_peer_id:
            self._append_bubble(msg)

    # ── Internos ──────────────────────────────────────────────────────────────

    def _append_bubble(self, msg: Message):
        bubble = MessageBubble(msg)
        self._bubbles[msg.id] = bubble
        # Insertar antes del stretch final
        idx = self.msg_layout.count() - 1
        self.msg_layout.insertWidget(idx, bubble)
        # Scroll al fondo con pequeño delay para que Qt calcule el tamaño
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def _clear(self):
        self._bubbles.clear()
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def add_transfer_bubble(self, peer_id: str, bubble):
        """Inserta una burbuja de transferencia de archivo en el chat activo."""
        if peer_id == self._current_peer_id:
            idx = self.msg_layout.count() - 1
            self.msg_layout.insertWidget(idx, bubble)
            QTimer.singleShot(50, self._scroll_to_bottom)
