"""
ECHOES — Lock Screen
━━━━━━━━━━━━━━━━━━━━
Logo badge (with breathing glow) · animated PIN dots · shake on error
"""

from PySide6.QtCore import (
    Qt, Signal, QTimer, QPointF, QPoint,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
)
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QGraphicsOpacityEffect
)

from ui.components import (
    MinimalCard, AnimatedButton,
    COLOR_MUTED, COLOR_ACCENT, COLOR_DANGER
)
from utils.branding import LogoBadge


class PinDots(QWidget):
    def __init__(self, count: int = 4, parent=None):
        super().__init__(parent)
        self.count = count
        self.setFixedHeight(34)
        self.setMinimumWidth(count * 30)

        self._progress = [0.0] * count
        self._targets = [0.0] * count
        self._error_flash = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_filled(self, n: int):
        for i in range(self.count):
            self._targets[i] = 1.0 if i < n else 0.0

    def flash_error(self):
        self._error_flash = 1.0

    def _tick(self):
        dirty = False
        for i in range(self.count):
            d = self._targets[i] - self._progress[i]
            if abs(d) > 0.002:
                self._progress[i] += d * 0.28
                dirty = True
            elif self._progress[i] != self._targets[i]:
                self._progress[i] = self._targets[i]
                dirty = True

        if self._error_flash > 0:
            self._error_flash = max(0.0, self._error_flash - 0.02)
            dirty = True

        if dirty:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        spacing = 30
        start_x = (self.width() - (self.count - 1) * spacing) / 2.0
        cy = self.height() / 2.0

        accent = QColor(COLOR_ACCENT)
        danger = QColor(COLOR_DANGER)

        for i in range(self.count):
            cx = start_x + i * spacing
            prog = self._progress[i]

            ring = QColor(COLOR_MUTED)
            ring.setAlpha(110)
            p.setPen(QPen(ring, 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), 6.5, 6.5)

            if prog > 0.01:
                fill = QColor(accent)
                if self._error_flash > 0:
                    f = self._error_flash
                    fill = QColor(
                        int(accent.red() * (1 - f) + danger.red() * f),
                        int(accent.green() * (1 - f) + danger.green() * f),
                        int(accent.blue() * (1 - f) + danger.blue() * f),
                    )

                glow = QColor(fill)
                glow.setAlpha(int(55 * prog))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(glow))
                p.drawEllipse(QPointF(cx, cy), 10.5 * prog, 10.5 * prog)

                p.setBrush(QBrush(fill))
                p.drawEllipse(QPointF(cx, cy), 5.5 * prog, 5.5 * prog)
        p.end()


class LockScreen(QWidget):

    unlocked = Signal()
    PIN_LENGTH = 4

    def __init__(self, db, logo_path: str = "", parent=None):
        super().__init__(parent)
        self.db = db
        self.logo_path = logo_path or None

        self.entered_pin = ""
        self.temp_first_pin = ""
        self.setting_mode = not self.db.has_pin()

        self._init_ui()
        self._animate_in()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = MinimalCard(self, corner_radius=18)
        self.card.setFixedWidth(340)

        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(28, 26, 28, 26)
        cl.setSpacing(13)

        self.logo_badge = LogoBadge(size=78, breathe=True, path=self.logo_path)
        self.logo_badge.setCursor(Qt.CursorShape.ArrowCursor)
        cl.addWidget(self.logo_badge, 0, Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("E C H O E S" if not self.setting_mode else "CREATE PIN")
        self.title_label.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        self.title_label.setStyleSheet(
            "color: #FAFAFA; letter-spacing: 3px; border: none; background: transparent;"
        )
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Enter your 4-digit PIN" if not self.setting_mode
            else "Choose a 4-digit security PIN"
        )
        self.subtitle_label.setFont(QFont("Inter", 9))
        self.subtitle_label.setStyleSheet(
            f"color: {COLOR_MUTED}; border: none; background: transparent;"
        )
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.subtitle_label)

        self.pin_dots = PinDots(self.PIN_LENGTH)
        cl.addWidget(self.pin_dots)

        grid = QGridLayout()
        grid.setSpacing(10)
        keys = [('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
                ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
                ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
                ('C', 3, 0), ('0', 3, 1), ('OK', 3, 2)]

        for text, r, c in keys:
            if text == 'OK':
                btn = AnimatedButton("", icon_name="check", icon_color="#FFFFFF",
                                     primary=True, corner_radius=9)
                btn.setToolTip("Confirm (Enter)")
            else:
                btn = AnimatedButton(text, corner_radius=9)
                if text == 'C':
                    btn.setToolTip("Clear (Backspace)")
            btn.setFixedSize(84, 48)
            btn.setFont(QFont("Inter", 12, QFont.Weight.DemiBold))
            btn.clicked.connect(lambda _=False, t=text: self._on_key(t))
            grid.addWidget(btn, r, c)

        cl.addLayout(grid)

        hint = QLabel("You can also type using your keyboard")
        hint.setFont(QFont("Inter", 7))
        hint.setStyleSheet(f"color: {COLOR_MUTED}; border: none; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(hint)

        outer.addWidget(self.card)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _animate_in(self):
        self._fx = QGraphicsOpacityEffect(self.card)
        self.card.setGraphicsEffect(self._fx)
        self._fade = QPropertyAnimation(self._fx, b"opacity", self)
        self._fade.setDuration(420)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(lambda: self.card.setGraphicsEffect(None))
        self._fade.start()

    def _on_key(self, char: str):
        if char == 'C':
            self.entered_pin = ""
        elif char == 'OK':
            self._submit()
            return
        elif char.isdigit() and len(self.entered_pin) < self.PIN_LENGTH:
            self.entered_pin += char

        self._update_dots()
        if len(self.entered_pin) == self.PIN_LENGTH:
            QTimer.singleShot(140, self._submit)

    def keyPressEvent(self, event):
        key, text = event.key(), event.text()
        if text.isdigit():
            self._on_key(text); event.accept(); return
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.entered_pin = self.entered_pin[:-1]
            self._update_dots(); event.accept(); return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._submit(); event.accept(); return
        super().keyPressEvent(event)

    def _update_dots(self):
        self.pin_dots.set_filled(len(self.entered_pin))

    def reset(self):
        self.entered_pin = ""
        self.temp_first_pin = ""
        self.setting_mode = not self.db.has_pin()
        self._set_subtitle(
            "Enter your 4-digit PIN" if not self.setting_mode
            else "Choose a 4-digit security PIN", error=False
        )
        self._update_dots()
        self.setFocus()

    def _submit(self):
        if len(self.entered_pin) < self.PIN_LENGTH:
            return
        self._handle_setup() if self.setting_mode else self._handle_login()

    def _handle_setup(self):
        if not self.temp_first_pin:
            self.temp_first_pin = self.entered_pin
            self.entered_pin = ""
            self._set_subtitle("Re-enter your PIN to confirm", error=False)
            self._update_dots()
            return

        if self.entered_pin == self.temp_first_pin:
            self.db.set_pin(self.entered_pin)
            self.entered_pin = ""
            self._update_dots()
            self.unlocked.emit()
        else:
            self._reject("PINs did not match — try again")
            self.temp_first_pin = ""
            self._set_subtitle("Choose a 4-digit security PIN", error=True)

    def _handle_login(self):
        if self.db.verify_pin(self.entered_pin):
            self.entered_pin = ""
            self._update_dots()
            self.unlocked.emit()
        else:
            self._reject("Incorrect PIN")

    def _reject(self, message: str):
        self.shake()
        self.pin_dots.flash_error()
        self._set_subtitle(message, error=True)
        self.entered_pin = ""
        QTimer.singleShot(260, self._update_dots)

    def _set_subtitle(self, text: str, error: bool = False):
        self.subtitle_label.setText(text)
        color = COLOR_DANGER if error else COLOR_MUTED
        self.subtitle_label.setStyleSheet(
            f"color: {color}; border: none; background: transparent;"
        )

    def shake(self):
        group = QSequentialAnimationGroup(self)
        origin = self.card.pos()
        for offset in (14, -14, 10, -10, 6, -6, 3, -3, 0):
            step = QPropertyAnimation(self.card, b"pos")
            step.setDuration(38)
            step.setEndValue(QPoint(origin.x() + offset, origin.y()))
            group.addAnimation(step)
        self._shake_group = group
        group.start()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.setFocus)
