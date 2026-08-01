"""
ECHOES — Editor
━━━━━━━━━━━━━━━
• Emits `confetti_requested` so main.py can fire the save celebration
• Unsaved-changes indicator (pulsing amber dot)
• Live word / character / reading-time counter
• Keyboard shortcuts: Ctrl+S, Ctrl+B, Ctrl+I, Ctrl+U
• Dark-themed confirmation dialog (no more white system popup)
• Format buttons stay in sync with the cursor position
"""

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QMessageBox, QFrame, QSizePolicy
)

from ui.components import (
    MinimalCard, MinimalInput, MinimalTextEdit, AnimatedButton,
    ToastNotification,
    COLOR_SURFACE, COLOR_BORDER, COLOR_ACCENT,
    COLOR_TEXT, COLOR_MUTED, COLOR_DANGER
)


# ──────────────────────────────────────────────
# Pulsing "unsaved changes" indicator
# ──────────────────────────────────────────────

class DirtyDot(QLabel):
    """Small amber dot that gently pulses while there are unsaved edits."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._on = False
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._render(0.0)

    def set_active(self, state: bool):
        if state == self._on:
            return
        self._on = state
        if state:
            self._phase = 0.0
            self._timer.start(40)
        else:
            self._timer.stop()
            self._render(0.0)

    def _tick(self):
        self._phase += 0.13
        # Oscillate opacity between ~0.45 and 1.0
        import math
        alpha = 0.72 + math.sin(self._phase) * 0.28
        self._render(alpha)

    def _render(self, alpha: float):
        if alpha <= 0.0:
            self.setStyleSheet("background: transparent; border: none;")
            return
        a = int(max(0, min(255, alpha * 255)))
        self.setStyleSheet(
            f"background-color: rgba(245, 158, 11, {a});"
            f"border-radius: 5px; border: none;"
        )


# ══════════════════════════════════════════════
# EDITOR VIEW
# ══════════════════════════════════════════════

class EditorView(QWidget):
    """Rich-text journal editor with metadata controls."""

    # ── Signals consumed by main.py ──
    entry_saved = Signal()          # sidebar should refresh
    entry_deleted = Signal()        # sidebar should refresh
    confetti_requested = Signal()   # fire the celebration overlay

    # (icon key, tooltip)
    MOODS = [
        ("happy",     "Happy"),
        ("neutral",   "Neutral"),
        ("sad",       "Down"),
        ("energetic", "Energised"),
    ]

    CATEGORIES = ["Personal", "Work", "Ideas", "Reflections"]

    WORDS_PER_MINUTE = 220

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db

        self.current_entry_id: int | None = None
        self.selected_mood = "happy"

        self._loading = False    # suppress dirty-flag while populating
        self._dirty = False

        self._init_ui()
        self._setup_shortcuts()
        self._update_counts()

    # ══════════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════════

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        card = MinimalCard(self, corner_radius=12)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addLayout(self._build_title_row())
        layout.addLayout(self._build_meta_row())
        layout.addWidget(self._divider())
        layout.addLayout(self._build_format_row())

        # ── Main writing surface ──
        self.editor = MinimalTextEdit()
        self.editor.setPlaceholderText(
            "What echoed through your day?\n\n"
            "Write freely — nobody else is reading this."
        )
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._sync_format_buttons)
        self.editor.selectionChanged.connect(self._sync_format_buttons)
        layout.addWidget(self.editor, 1)

        layout.addLayout(self._build_footer())
        root.addWidget(card)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {COLOR_BORDER}; border: none;")
        return line

    # ── Row 1: title + dirty dot ──────────────

    def _build_title_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.title_input = MinimalInput("Entry Title…")
        self.title_input.setFont(QFont("Inter", 11, QFont.Weight.DemiBold))
        self.title_input.textChanged.connect(self._mark_dirty)

        self.dirty_dot = DirtyDot()
        self.dirty_dot.setToolTip("You have unsaved changes")

        row.addWidget(self.title_input, 1)
        row.addWidget(self.dirty_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        return row

    # ── Row 2: category + mood ────────────────

    def _build_meta_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        cat_lbl = QLabel("Category")
        cat_lbl.setFont(QFont("Inter", 8))
        cat_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")

        self.category_combo = QComboBox()
        self.category_combo.addItems(self.CATEGORIES)
        self.category_combo.setFixedHeight(32)
        self.category_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.category_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 7px;
                padding: 4px 10px;
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
        self.category_combo.currentTextChanged.connect(self._mark_dirty)

        mood_lbl = QLabel("Mood")
        mood_lbl.setFont(QFont("Inter", 8))
        mood_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")

        row.addWidget(cat_lbl)
        row.addWidget(self.category_combo)
        row.addSpacing(14)
        row.addWidget(mood_lbl)

        # ── Mood toggle group ──
        self.mood_btns: dict[str, AnimatedButton] = {}
        for key, tip in self.MOODS:
            btn = AnimatedButton(icon_name=key, icon_color="#FAFAFA", corner_radius=7)
            btn.setCheckable(True)
            btn.setFixedSize(36, 32)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda _=False, k=key: self._on_mood_clicked(k))
            self.mood_btns[key] = btn
            row.addWidget(btn)

        self.mood_btns["happy"].setChecked(True)
        row.addStretch(1)
        return row

    # ── Row 3: formatting toolbar ─────────────

    def _build_format_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        self.bold_btn = self._fmt_button("bold", "Bold  (Ctrl+B)", self._toggle_bold)
        self.italic_btn = self._fmt_button("italic", "Italic  (Ctrl+I)", self._toggle_italic)
        self.underline_btn = self._fmt_button("underline", "Underline  (Ctrl+U)", self._toggle_underline)

        row.addWidget(self.bold_btn)
        row.addWidget(self.italic_btn)
        row.addWidget(self.underline_btn)
        row.addStretch(1)

        # Live status chip (right side of toolbar)
        self.mode_lbl = QLabel("New entry")
        self.mode_lbl.setFont(QFont("Inter", 8))
        self.mode_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")
        row.addWidget(self.mode_lbl)

        return row

    def _fmt_button(self, icon: str, tip: str, slot) -> AnimatedButton:
        btn = AnimatedButton(icon_name=icon, icon_color="#FAFAFA", corner_radius=7)
        btn.setCheckable(True)
        btn.setFixedSize(34, 32)
        btn.setToolTip(tip)
        btn.clicked.connect(slot)
        return btn

    # ── Row 4: footer ─────────────────────────

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        self.status_lbl = QLabel()
        self.status_lbl.setFont(QFont("Inter", 8))
        self.status_lbl.setStyleSheet(f"color: {COLOR_MUTED}; border: none;")

        self.delete_btn = AnimatedButton(
            " Delete", icon_name="trash", icon_color=COLOR_DANGER, corner_radius=8
        )
        self.delete_btn.setToolTip("Delete this entry")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLOR_DANGER};
                border: 1px solid #3F2727;
                border-radius: 8px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.14);
                border: 1px solid {COLOR_DANGER};
            }}
            QPushButton:pressed {{
                background-color: rgba(239, 68, 68, 0.24);
            }}
        """)
        self.delete_btn.clicked.connect(self.delete_current_entry)

        self.save_btn = AnimatedButton(
            " Save Entry", primary=True, icon_name="save",
            icon_color="#FFFFFF", corner_radius=8
        )
        self.save_btn.setToolTip("Save  (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_current_entry)

        row.addWidget(self.status_lbl)
        row.addStretch(1)
        row.addWidget(self.delete_btn)
        row.addWidget(self.save_btn)
        return row

    # ══════════════════════════════════════════
    # SHORTCUTS
    # ══════════════════════════════════════════

    def _setup_shortcuts(self):
        """Editor-scoped shortcuts (won't clash with global window keys)."""
        ctx = Qt.ShortcutContext.WidgetWithChildrenShortcut

        for seq, slot in (
            ("Ctrl+S", self.save_current_entry),
            ("Ctrl+B", self._toggle_bold),
            ("Ctrl+I", self._toggle_italic),
            ("Ctrl+U", self._toggle_underline),
        ):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(ctx)
            sc.activated.connect(slot)

    # ══════════════════════════════════════════
    # DIRTY TRACKING
    # ══════════════════════════════════════════

    def _mark_dirty(self, *_):
        if self._loading:
            return
        if not self._dirty:
            self._dirty = True
            self.dirty_dot.set_active(True)

    def _mark_clean(self):
        self._dirty = False
        self.dirty_dot.set_active(False)

    def has_unsaved_changes(self) -> bool:
        return self._dirty

    # ══════════════════════════════════════════
    # TEXT / COUNTS
    # ══════════════════════════════════════════

    def _on_text_changed(self):
        self._mark_dirty()
        self._update_counts()

    def _update_counts(self):
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        minutes = max(1, round(words / self.WORDS_PER_MINUTE)) if words else 0

        parts = [f"{words} words", f"{chars} characters"]
        if minutes:
            parts.append(f"~{minutes} min read")
        self.status_lbl.setText("   ·   ".join(parts))

    # ══════════════════════════════════════════
    # MOOD
    # ══════════════════════════════════════════

    def _on_mood_clicked(self, key: str):
        self._set_mood(key)
        self._mark_dirty()

    def _set_mood(self, key: str):
        if key not in self.mood_btns:
            key = "happy"
        self.selected_mood = key
        for k, btn in self.mood_btns.items():
            btn.setChecked(k == key)

    # ══════════════════════════════════════════
    # FORMATTING
    # ══════════════════════════════════════════

    def _apply_format(self, fmt: QTextCharFormat):
        """Apply to the selection, or to subsequent typing if nothing is selected."""
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def _toggle_bold(self):
        current = int(self.editor.currentCharFormat().fontWeight()) >= 700
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if current else QFont.Weight.Bold)
        self._apply_format(fmt)
        self._sync_format_buttons()

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.editor.currentCharFormat().fontItalic())
        self._apply_format(fmt)
        self._sync_format_buttons()

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.editor.currentCharFormat().fontUnderline())
        self._apply_format(fmt)
        self._sync_format_buttons()

    def _sync_format_buttons(self):
        """Keep the toolbar toggles matching the text under the cursor."""
        fmt = self.editor.currentCharFormat()
        self.bold_btn.setChecked(int(fmt.fontWeight()) >= 700)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.underline_btn.setChecked(fmt.fontUnderline())

    # ══════════════════════════════════════════
    # LOAD / CLEAR
    # ══════════════════════════════════════════

    def load_entry(self, entry_id: int):
        entry = self.db.get_entry_by_id(entry_id)
        if not entry:
            return

        self._loading = True
        try:
            self.current_entry_id = entry["id"]
            self.title_input.setText(entry.get("title", ""))
            self.editor.setHtml(entry.get("content", ""))
            self.category_combo.setCurrentText(entry.get("category", "Personal"))
            self._set_mood(entry.get("mood", "happy"))
            self.mode_lbl.setText(f"Editing · {entry.get('created_at', '')[:10]}")
        finally:
            self._loading = False

        self._mark_clean()
        self._update_counts()
        self._sync_format_buttons()

    def clear_editor(self):
        self._loading = True
        try:
            self.current_entry_id = None
            self.title_input.clear()
            self.editor.clear()
            self.category_combo.setCurrentIndex(0)
            self._set_mood("happy")
            self.mode_lbl.setText("New entry")
        finally:
            self._loading = False

        self._mark_clean()
        self._update_counts()
        self.title_input.setFocus()

    # ══════════════════════════════════════════
    # SAVE / DELETE
    # ══════════════════════════════════════════

    def save_current_entry(self):
        title = self.title_input.text().strip() or "Untitled Echo"
        content = self.editor.toHtml()
        category = self.category_combo.currentText()

        is_new = self.current_entry_id is None

        if is_new:
            self.current_entry_id = self.db.create_entry(
                title, content, category, self.selected_mood
            )
        else:
            self.db.update_entry(
                self.current_entry_id, title, content,
                category, self.selected_mood
            )

        self._mark_clean()
        self.mode_lbl.setText("Saved" if not is_new else "Saved · new entry")

        self._show_toast("Entry saved")

        # ── The celebration hook main.py listens for ──
        self.confetti_requested.emit()
        self.entry_saved.emit()

    def delete_current_entry(self):
        # Nothing persisted yet → just wipe the form
        if self.current_entry_id is None:
            self.clear_editor()
            self._show_toast("Draft cleared")
            return

        if not self._confirm("Delete entry",
                             "This echo will be permanently removed.\n"
                             "This action cannot be undone."):
            return

        self.db.delete_entry(self.current_entry_id)
        self.clear_editor()
        self._show_toast("Entry deleted")
        self.entry_deleted.emit()

    # ══════════════════════════════════════════
    # DIALOGS / TOASTS
    # ══════════════════════════════════════════

    def _confirm(self, title: str, text: str) -> bool:
        """Dark-themed yes/no dialog."""
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.NoIcon)
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        box.setDefaultButton(QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Delete")
        box.button(QMessageBox.StandardButton.No).setText("Cancel")

        box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLOR_SURFACE};
            }}
            QLabel {{
                color: {COLOR_TEXT};
                font-size: 12px;
                min-width: 300px;
            }}
            QPushButton {{
                background-color: {COLOR_SURFACE};
                color: {COLOR_TEXT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 7px;
                padding: 7px 18px;
                min-width: 74px;
            }}
            QPushButton:hover {{
                border: 1px solid {COLOR_ACCENT};
            }}
            QPushButton:default {{
                background-color: {COLOR_ACCENT};
                border: none;
                color: #FFFFFF;
            }}
        """)
        return box.exec() == QMessageBox.StandardButton.Yes

    def _show_toast(self, message: str):
        toast = ToastNotification(message, self)
        toast.move(max(10, self.width() - 280), 16)
        toast.show()
        toast.raise_()
        toast.animate_show()