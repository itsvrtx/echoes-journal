from PySide6.QtCore import Qt, QTimer, QDateTime, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from ui.components import MinimalCard, AnimatedButton, COLOR_MUTED, COLOR_ACCENT
from utils.quotes import get_daily_quote
from utils.branding import LogoBadge


class ClickableLabel(QLabel):
    """QLabel emitting click / double-click signals for easter eggs."""
    clicked = Signal()
    double_clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class HeaderView(QWidget):
    """Header: logo badge, brand text, daily quote, live clock, actions."""

    lock_requested = Signal()
    new_entry_requested = Signal()
    cat_requested = Signal()      # double-click the title
    magic_requested = Signal()    # 5 rapid logo clicks

    LOGO_CLICK_TARGET = 5
    CLICK_RESET_MS = 1600

    def __init__(self, logo_path: str = "", parent=None):
        super().__init__(parent)
        self.logo_path = logo_path or None
        self._logo_clicks = 0

        self._click_reset = QTimer(self)
        self._click_reset.setSingleShot(True)
        self._click_reset.timeout.connect(self._reset_clicks)

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        card = MinimalCard(self, corner_radius=12)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 16, 10)
        card_layout.setSpacing(0)

        # ── Brand block ──
        brand_box = QHBoxLayout()
        brand_box.setSpacing(12)

        # Always renders — falls back to a generated mark if no file exists
        self.logo_badge = LogoBadge(size=40, breathe=False, path=self.logo_path)
        self.logo_badge.setToolTip("Psst… click me five times")
        self.logo_badge.clicked.connect(self._on_logo_clicked)
        brand_box.addWidget(self.logo_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)

        title_lbl = ClickableLabel("E C H O E S")
        title_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet(
            "color: #FAFAFA; letter-spacing: 3px; "
            "border: none; background: transparent;"
        )
        title_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        title_lbl.setToolTip("Try double-clicking me…")
        title_lbl.double_clicked.connect(self.cat_requested.emit)

        self.quote_lbl = QLabel(get_daily_quote())
        qf = QFont("Inter", 8)
        qf.setItalic(True)
        self.quote_lbl.setFont(qf)
        self.quote_lbl.setStyleSheet(
            f"color: {COLOR_MUTED}; border: none; background: transparent;"
        )

        text_box.addWidget(title_lbl)
        text_box.addWidget(self.quote_lbl)
        brand_box.addLayout(text_box)

        # ── Live clock ──
        center_box = QVBoxLayout()
        center_box.setSpacing(1)
        center_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.clock_lbl = QLabel()
        self.clock_lbl.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
        self.clock_lbl.setStyleSheet(
            f"color: {COLOR_ACCENT}; border: none; background: transparent;"
        )

        self.date_lbl = QLabel()
        self.date_lbl.setFont(QFont("Inter", 8))
        self.date_lbl.setStyleSheet(
            f"color: {COLOR_MUTED}; border: none; background: transparent;"
        )

        center_box.addWidget(self.clock_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        center_box.addWidget(self.date_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Actions ──
        right_box = QHBoxLayout()
        right_box.setSpacing(8)
        right_box.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        new_btn = AnimatedButton(" New Entry", primary=True,
                                 icon_name="plus", icon_color="#FFFFFF")
        new_btn.clicked.connect(self.new_entry_requested.emit)

        lock_btn = AnimatedButton(" Lock", icon_name="lock", icon_color="#FAFAFA")
        lock_btn.clicked.connect(self.lock_requested.emit)

        right_box.addWidget(new_btn)
        right_box.addWidget(lock_btn)

        card_layout.addLayout(brand_box, 4)
        card_layout.addLayout(center_box, 3)
        card_layout.addLayout(right_box, 3)
        layout.addWidget(card)

        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(1000)
        self._update_clock()

    # ── Easter egg: 5 logo clicks ──

    def _on_logo_clicked(self):
        self._logo_clicks += 1
        self._click_reset.start(self.CLICK_RESET_MS)
        if self._logo_clicks >= self.LOGO_CLICK_TARGET:
            self._logo_clicks = 0
            self._click_reset.stop()
            self.magic_requested.emit()

    def _reset_clicks(self):
        self._logo_clicks = 0

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        self.clock_lbl.setText(now.toString("hh:mm:ss AP"))
        self.date_lbl.setText(now.toString("dddd, MMM d, yyyy"))