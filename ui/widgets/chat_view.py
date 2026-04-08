# ──────────────────────────────────────────────
#  Multi-chat con tabs
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QFrame, QSizePolicy,
    QTabWidget, QTabBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

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

        if not self.msg.is_mine:
            name = QLabel(self.msg.sender_name)
            name.setStyleSheet(
                f"color: {COLORS['accent']}; font-size: 8pt; font-weight: 600;"
            )
            inner.addWidget(name)

        content = QLabel(self.msg.content)
        content.setWordWrap(True)
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content.setStyleSheet("color: #FFFFFF; font-size: 10pt;")
        inner.addWidget(content)

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


# ── Panel de chat para un solo peer ───────────────────────────────────────────

class ChatPanel(QWidget):
    """Un panel de mensajes independiente por peer."""

    def __init__(self, peer_id: str, peer_name: str):
        super().__init__()
        self.peer_id   = peer_id
        self.peer_name = peer_name
        self._bubbles: dict[str, QWidget] = {}
        self._unread   = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background-color: #121212; border: none;")

        self.container = QWidget()
        self.msg_layout = QVBoxLayout(self.container)
        self.msg_layout.setContentsMargins(4, 8, 4, 8)
        self.msg_layout.setSpacing(1)
        self.msg_layout.addStretch()

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def append_message(self, msg: Message):
        bubble = MessageBubble(msg)
        self._bubbles[msg.id] = bubble
        idx = self.msg_layout.count() - 1
        self.msg_layout.insertWidget(idx, bubble)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def append_widget(self, widget: QWidget):
        """Inserta cualquier widget (ej: TransferBubble) en el panel."""
        idx = self.msg_layout.count() - 1
        self.msg_layout.insertWidget(idx, widget)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def load_history(self, messages: list[Message]):
        # Limpiar primero
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._bubbles.clear()
        for msg in messages:
            self.append_message(msg)

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )


# ── ChatView con tabs ─────────────────────────────────────────────────────────

class ChatView(QWidget):
    """
    Contenedor multi-tab: una pestaña por conversación activa.
    Los mensajes se enrutan al panel correcto aunque no sea el tab activo.
    """

    def __init__(self):
        super().__init__()
        # peer_id → ChatPanel
        self._panels: dict[str, ChatPanel] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Placeholder cuando no hay ninguna conversación abierta
        self._placeholder = QLabel("  Selecciona un peer para chatear")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11pt;"
        )

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close)
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background-color: #121212;
            }}
            QTabBar::tab {{
                background-color: #1A1A1A;
                color: {COLORS['text_muted']};
                padding: 7px 14px;
                border: none;
                border-right: 1px solid #2A2A2A;
                font-size: 9pt;
                min-width: 100px;
            }}
            QTabBar::tab:selected {{
                background-color: #121212;
                color: #FFFFFF;
                border-bottom: 2px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #222222;
                color: #CCCCCC;
            }}
            QTabBar::close-button {{
                subcontrol-position: right;
            }}
        """)
        self._tabs.hide()

        layout.addWidget(self._placeholder, stretch=1)
        layout.addWidget(self._tabs, stretch=1)

    # ── API pública ───────────────────────────────────────────────────────────

    def open_chat(self, peer_id: str, peer_name: str, messages: list[Message]):
        """
        Abre o enfoca la pestaña de un peer.
        Si ya existe, solo la trae al frente.
        """
        if peer_id in self._panels:
            # Traer al frente
            panel = self._panels[peer_id]
            idx   = self._tabs.indexOf(panel)
            self._tabs.setCurrentIndex(idx)
            self._clear_badge(peer_id)
            return

        # Crear nuevo panel
        panel = ChatPanel(peer_id, peer_name)
        panel.load_history(messages)
        self._panels[peer_id] = panel

        self._tabs.addTab(panel, f"  {peer_name}  ")
        self._tabs.setCurrentWidget(panel)

        self._placeholder.hide()
        self._tabs.show()

    def add_message(self, peer_id: str, msg: Message):
        """Enruta el mensaje al panel correcto; añade badge si no es el tab activo."""
        panel = self._panels.get(peer_id)
        if not panel:
            return

        panel.append_message(msg)

        # Badge de no leídos si el tab no está activo
        if self._tabs.currentWidget() is not panel:
            panel._unread += 1
            idx = self._tabs.indexOf(panel)
            self._tabs.setTabText(
                idx, f"  {panel.peer_name}  🔴"
            )

    def add_transfer_bubble(self, peer_id: str, widget: QWidget):
        panel = self._panels.get(peer_id)
        if panel:
            panel.append_widget(widget)

    def update_peer_name(self, peer_id: str, new_name: str):
        panel = self._panels.get(peer_id)
        if panel:
            panel.peer_name = new_name
            idx = self._tabs.indexOf(panel)
            self._tabs.setTabText(idx, f"  {new_name}  ")

    # ── Internos ──────────────────────────────────────────────────────────────

    def _on_tab_close(self, index: int):
        panel = self._tabs.widget(index)
        # Buscar y eliminar de _panels
        pid = next((k for k, v in self._panels.items() if v is panel), None)
        if pid:
            del self._panels[pid]
        self._tabs.removeTab(index)

        if self._tabs.count() == 0:
            self._tabs.hide()
            self._placeholder.show()

    def _clear_badge(self, peer_id: str):
        panel = self._panels.get(peer_id)
        if panel and panel._unread > 0:
            panel._unread = 0
            idx = self._tabs.indexOf(panel)
            self._tabs.setTabText(idx, f"  {panel.peer_name}  ")
