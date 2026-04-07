# ──────────────────────────────────────────────
#           Burbuja de transferencia
# ──────────────────────────────────────────────

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QProgressBar, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, Signal

from models.file_transfer import FileTransfer, TransferStatus
from ui.styles import COLORS


class TransferBubble(QFrame):
    """
    Burbuja que se inserta en el chat para mostrar el progreso
    de una transferencia (enviando o recibiendo).
    """
    cancel_requested = Signal(str)   # file_id

    STATUS_LABELS = {
        TransferStatus.OFFERING:   ("⏳", "Esperando respuesta…",  COLORS["connecting"]),
        TransferStatus.ACCEPTED:   ("📤", "Enviando…",             COLORS["connecting"]),
        TransferStatus.RECEIVING:  ("📥", "Recibiendo…",           COLORS["connecting"]),
        TransferStatus.COMPLETED:  ("✅", "Completado",            COLORS["connected"]),
        TransferStatus.REJECTED:   ("🚫", "Rechazado",             COLORS["error"]),
        TransferStatus.CANCELLED:  ("✗",  "Cancelado",             COLORS["error"]),
        TransferStatus.ERROR:      ("⚠️", "Error",                  COLORS["error"]),
    }

    def __init__(self, ft: FileTransfer):
        super().__init__()
        self.file_id = ft.id
        self._setup_ui(ft)

    def _setup_ui(self, ft: FileTransfer):
        self.setStyleSheet(
            f"background-color: #1A2A3A; border-radius: 10px; "
            f"border: 1px solid #1E3A5A;"
        )
        self.setMaximumWidth(360)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        if ft.is_sender:
            outer.addStretch()

        inner = QVBoxLayout()
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(6)

        # ── Fila icono + nombre ───────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        file_icon = QLabel("📄")
        file_icon.setStyleSheet("font-size: 16pt; background: transparent;")
        top_row.addWidget(file_icon)

        info = QVBoxLayout()
        info.setSpacing(1)

        self.name_label = QLabel(ft.filename)
        self.name_label.setStyleSheet(
            "color: #FFFFFF; font-weight: 600; font-size: 9pt; background: transparent;"
        )
        self.name_label.setMaximumWidth(200)
        self.name_label.setWordWrap(True)
        info.addWidget(self.name_label)

        self.size_label = QLabel(ft.size_str)
        self.size_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 8pt; background: transparent;"
        )
        info.addWidget(self.size_label)

        top_row.addLayout(info)
        top_row.addStretch()

        # Botón cancelar
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(22, 22)
        self.cancel_btn.setStyleSheet(
            "background-color: #2A2A2A; color: #888888; "
            "border-radius: 11px; font-size: 9pt; border: none;"
            "QPushButton:hover { background-color: #FF6B6B; color: #FFFFFF; }"
        )
        self.cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self.file_id))
        top_row.addWidget(self.cancel_btn)

        inner.addLayout(top_row)

        # ── Barra de progreso ─────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1E1E;
                border-radius: 3px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #00FF88;
                border-radius: 3px;
            }
        """)
        inner.addWidget(self.progress_bar)

        # ── Estado ────────────────────────────────────────────
        self.status_label = QLabel()
        self.status_label.setStyleSheet(
            f"color: {COLORS['connecting']}; font-size: 8pt; background: transparent;"
        )
        inner.addWidget(self.status_label)

        outer.addLayout(inner)

        if not ft.is_sender:
            outer.addStretch()

        self.update_transfer(ft)

    def update_transfer(self, ft: FileTransfer):
        icon, text, color = self.STATUS_LABELS.get(
            ft.status, ("?", ft.status.value, COLORS["text_muted"])
        )

        finished = ft.status in (
            TransferStatus.COMPLETED,
            TransferStatus.CANCELLED,
            TransferStatus.REJECTED,
            TransferStatus.ERROR,
        )

        self.progress_bar.setValue(ft.progress_pct)
        self.status_label.setText(
            f"{icon}  {text}"
            + (f"  {ft.progress_pct}%" if not finished else "")
            + (f" → {ft.save_path}" if ft.status == TransferStatus.COMPLETED and not ft.is_sender else "")
        )
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 8pt; background: transparent;"
        )

        if finished:
            self.cancel_btn.setVisible(False)
            if ft.status == TransferStatus.COMPLETED:
                self.progress_bar.setStyleSheet("""
                    QProgressBar { background-color: #1E1E1E; border-radius: 3px; border: none; }
                    QProgressBar::chunk { background-color: #00FF88; border-radius: 3px; }
                """)
            elif ft.status == TransferStatus.ERROR:
                self.progress_bar.setStyleSheet("""
                    QProgressBar { background-color: #1E1E1E; border-radius: 3px; border: none; }
                    QProgressBar::chunk { background-color: #FF6B6B; border-radius: 3px; }
                """)

        if ft.error_msg:
            self.status_label.setText(f"⚠️  {ft.error_msg}")
