
"""
ECHOES — Sidebar
━━━━━━━━━━━━━━━━
• Fully custom-painted entry cards (smooth hover lerp, no stylesheet thrash)
• Staggered fade + slide-in entrance animation for each card
• Persistent selection highlight with animated accent bar
• Debounced real-time search (180 ms) to avoid hammering SQLite
• Easter egg: typing "meow" in the search bar emits `meow_easter_egg`
"""

from PySide6.QtCore import Qt, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QFont, QPainter, QColor, QBrush, QPen, QFontMetrics, QTextDocument
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QComboBox, QFrame, QSizePolicy
)

from ui.components import (
    MinimalInput,
    COLOR_SURFACE, COLOR_SURFACE_HOVER, COLOR_BORDER,
    COLOR_ACCENT, COLOR_MUTED, COLOR_TEXT
)
from utils.icons import get_svg_pixmap


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _html_to_plain(html: str) -> str:
    """Convert stored rich-text HTML into a clean single-line snippet."""
    if not html:
        return ""
    if "<" not in html:                      # already plain text
        return " ".join(html.split())
    doc = QTextDocument()
    doc.setHtml(html)
    return " ".join(doc.toPlainText().split())


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(_lerp(c1.red(),   c2.red(),   t)),
        int(_lerp(c1.green(), c2.green(), t)),
        int(_lerp(c1.blue(),  c2.blue(),  t)),
    )


# ══════════════════════════════════════════════
# ENTRY CARD  (custom painted)
# ══════════════════════════════════════════════

class EntryCard(QFrame):
    """
    A single journal entry preview.

    Everything is drawn in `paintEvent`, which means the entrance
    animation (opacity + slide) works reliably without attaching a
    QGraphicsOpacityEffect to every row.
    """

    clicked = Signal(int)

    CARD_HEIGHT = 82

    def __init__(self, entry: dict, index: int = 0, parent=None):
        super().__init__(parent)
        self.entry_id = entry["id"]

        # ── Cached display data ──
        self.date_text = (entry.get("created_at") or "")[:10]
        self.category = entry.get("category", "Personal")
        self.mood = entry.get("mood", "happy")
        self.title_text = entry.get("title") or "Untitled Echo"
        self.snippet_text = _html_to_plain(entry.get("content", "")) or "No content yet…"
        self.mood_pixmap = get_svg_pixmap(self.mood, color=COLOR_ACCENT, size=14)

        # ── Animation state ──
        self._hover = 0.0        # 0 → 1 hover blend
        self._hover_target = 0.0
        self._selected = False
        self._select = 0.0       # 0 → 1 selection blend
        self._appear = 0.0       # 0 → 1 entrance blend

        self.setFixedHeight(self.CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        # ── Fonts ──
        self._f_meta = QFont("Inter", 8)
        self._f_title = QFont("Inter", 10, QFont.Weight.DemiBold)
        self._f_snip = QFont("Inter", 8)
        self._f_cat = QFont("Inter", 8, QFont.Weight.Bold)

        # ── Animation driver ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        # Staggered entrance
        QTimer.singleShot(index * 32, self._begin_appear)

    # ── Animation ─────────────────────────────

    def _begin_appear(self):
        self._appear = 0.001     # kick the easing loop
        self.update()

    def _tick(self):
        dirty = False

        # Hover easing
        if abs(self._hover_target - self._hover) > 0.003:
            self._hover += (self._hover_target - self._hover) * 0.22
            dirty = True
        elif self._hover != self._hover_target:
            self._hover = self._hover_target
            dirty = True

        # Selection easing
        sel_target = 1.0 if self._selected else 0.0
        if abs(sel_target - self._select) > 0.003:
            self._select += (sel_target - self._select) * 0.22
            dirty = True
        elif self._select != sel_target:
            self._select = sel_target
            dirty = True

        # Entrance easing
        if 0.0 < self._appear < 1.0:
            self._appear = min(1.0, self._appear + (1.0 - self._appear) * 0.16 + 0.012)
            dirty = True

        if dirty:
            self.update()

    # ── State ─────────────────────────────────

    def set_selected(self, state: bool):
        self._selected = state

    # ── Events ────────────────────────────────

    def enterEvent(self, event):
        self._hover_target = 1.0
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_target = 0.0
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry_id)
        super().mousePressEvent(event)

    # ── Painting ──────────────────────────────

    def paintEvent(self, event):
        if self._appear <= 0.0:
            return   # not yet revealed

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Entrance: fade + slide up
        p.setOpacity(self._appear)
        p.translate(0, (1.0 - self._appear) * 12.0)

        # Combined highlight strength
        glow = max(self._hover, self._select)

        rect = QRectF(0, 0, self.width(), self.height() - 2)

        # ── Background ──
        base = QColor(COLOR_SURFACE)
        hot = QColor(COLOR_SURFACE_HOVER)
        bg = _lerp_color(base, hot, glow)
        if self._select > 0:
            bg = _lerp_color(bg, QColor(45, 35, 72), self._select * 0.55)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(rect, 10, 10)

        # ── Border ──
        border = _lerp_color(QColor(COLOR_BORDER), QColor(COLOR_ACCENT), glow * 0.85)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(border, 1.0 + glow * 0.4))
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)

        # ── Left accent bar (grows on hover/select) ──
        if glow > 0.01:
            bar_h = rect.height() * 0.62 * glow
            bar_y = rect.center().y() - bar_h / 2
            accent = QColor(COLOR_ACCENT)
            accent.setAlphaF(min(1.0, glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(accent))
            p.drawRoundedRect(QRectF(0, bar_y, 3.0, bar_h), 1.5, 1.5)

        pad_l = 13 + glow * 3     # subtle slide-right on hover
        pad_r = 12
        inner_w = self.width() - pad_l - pad_r

        # ── Row 1: date (left) · mood icon + category (right) ──
        p.setFont(self._f_meta)
        p.setPen(QColor(COLOR_MUTED))
        p.drawText(QRectF(pad_l, 9, inner_w * 0.5, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   self.date_text)

        fm_cat = QFontMetrics(self._f_cat)
        cat_w = fm_cat.horizontalAdvance(self.category)
        cat_x = self.width() - pad_r - cat_w

        p.setFont(self._f_cat)
        p.setPen(QColor(COLOR_ACCENT))
        p.drawText(QRectF(cat_x, 9, cat_w, 14),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                   self.category)

        if not self.mood_pixmap.isNull():
            p.drawPixmap(int(cat_x - 19), 9, self.mood_pixmap)

        # ── Row 2: title ──
        fm_title = QFontMetrics(self._f_title)
        title = fm_title.elidedText(self.title_text, Qt.TextElideMode.ElideRight, int(inner_w))
        p.setFont(self._f_title)
        p.setPen(QColor(COLOR_TEXT))
        p.drawText(QRectF(pad_l, 30, inner_w, 18),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        # ── Row 3: snippet ──
        fm_snip = QFontMetrics(self._f_snip)
        snippet = fm_snip.elidedText(self.snippet_text, Qt.TextElideMode.ElideRight, int(inner_w))
        snip_col = QColor(COLOR_MUTED)
        snip_col.setAlpha(int(_lerp(175, 225, glow)))
        p.setFont(self._f_snip)
        p.setPen(snip_col)
        p.drawText(QRectF(pad_l, 51, inner_w, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, snippet)

        p.end()


# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════

class SidebarView(QWidget):
    """Search + filter + chronological entry list."""

    entry_selected = Signal(int)
    meow_easter_egg = Signal()          # typing "meow" in search

    MAGIC_WORD = "meow"
    SEARCH_DEBOUNCE_MS = 180

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setFixedWidth(300)

        self._cards: list[EntryCard] = []
        self._active_id: int | None = None
        self._meow_armed = True

        # Debounce timer for search
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.refresh_entries)

        self._init_ui()
        self.refresh_entries()

    # ── UI ────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(10)

        # ── Search ──
        self.search_input = MinimalInput("Search entries...", icon_name="search")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # ── Filter row ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        cat_lbl = QLabel("Filter:")
        cat_lbl.setFont(QFont("Inter", 8))
        cat_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")

        self.category_combo = QComboBox()
        self.category_combo.addItems(
            ["All", "Personal", "Work", "Ideas", "Reflections"]
        )
        self.category_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 1px solid {COLOR_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 7px;
                padding: 4px;
                outline: none;
                selection-background-color: {COLOR_ACCENT};
                selection-color: #FFFFFF;
            }}
        """)
        self.category_combo.currentTextChanged.connect(self.refresh_entries)

        filter_row.addWidget(cat_lbl)
        filter_row.addWidget(self.category_combo, 1)
        layout.addLayout(filter_row)

        # ── Result count ──
        self.count_lbl = QLabel("")
        self.count_lbl.setFont(QFont("Inter", 7))
        self.count_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")
        layout.addWidget(self.count_lbl)

        # ── Scrollable list ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                border-radius: 3px;
                min-height: 26px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLOR_ACCENT};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 6)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area, 1)

    # ── Search handling ───────────────────────

    def _on_search_changed(self, text: str):
        """Debounce the query and watch for the secret word."""
        probe = text.lower().strip()

        # ── Easter egg ──
        if probe == self.MAGIC_WORD:
            if self._meow_armed:
                self._meow_armed = False
                self.meow_easter_egg.emit()
        else:
            self._meow_armed = True

        self._search_timer.start(self.SEARCH_DEBOUNCE_MS)

    # ── List rendering ────────────────────────

    def _clear_list(self):
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def refresh_entries(self):
        """Reload entries from the database and rebuild the list."""
        self._clear_list()

        entries = self.db.get_all_entries(
            search=self.search_input.text().strip(),
            category=self.category_combo.currentText()
        )

        # ── Empty state ──
        if not entries:
            self.count_lbl.setText("")

            empty = QLabel("No entries found.\nStart writing your first echo.")
            empty.setFont(QFont("Inter", 9))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {COLOR_MUTED}; border: none; "
                f"background: transparent; margin-top: 28px;"
            )
            self.scroll_layout.addWidget(empty)
            return

        # ── Count label ──
        n = len(entries)
        self.count_lbl.setText(f"{n} {'entry' if n == 1 else 'entries'}")

        # ── Build cards ──
        for i, entry in enumerate(entries):
            card = EntryCard(entry, index=i)
            card.clicked.connect(self._on_card_clicked)
            if entry["id"] == self._active_id:
                card.set_selected(True)
            self._cards.append(card)
            self.scroll_layout.addWidget(card)

    # ── Selection ─────────────────────────────

    def _on_card_clicked(self, entry_id: int):
        self.set_active_entry(entry_id)
        self.entry_selected.emit(entry_id)

    def set_active_entry(self, entry_id: int | None):
        """Highlight the currently-open entry."""
        self._active_id = entry_id
        for card in self._cards:
            card.set_selected(card.entry_id == entry_id)

    def clear_selection(self):
        self.set_active_entry(None)