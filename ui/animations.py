"""
ECHOES Animation Engine
━━━━━━━━━━━━━━━━━━━━━━━
Overlay stacking order (bottom → top):
    app content  →  AmbientParticles  →  ConfettiOverlay  →  Cats  →  CelebrationBanner

All overlays auto-resize with the host via a single event filter, and are
re-stacked on every spawn so they are never buried under layout widgets.
"""

import random
import math
from PySide6.QtCore import (
    Qt, QTimer, QPointF, QRectF, QEvent, QObject, Signal
)
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QBrush, QFont, QFontMetricsF
)
from PySide6.QtWidgets import QWidget
from ui.cat import PolishedCat as WalkingCat

CAT_PALETTES = [
    ("#FF8C42", "#D4702F"),  
    ("#3D3D3D", "#252525"),   
    ("#A0A0A0", "#787878"),   
    ("#F0E6D0", "#C8B898"),   
    ("#6B4226", "#4A2E1A"),   
    ("#C9B1FF", "#9B7FE6"),   
    ("#FFB6C1", "#E8929E"),   
    ("#87CEEB", "#5FAFD7"),   
]

class _ConfettiPiece:
    __slots__ = ('x', 'y', 'vx', 'vy', 'gravity', 'color',
                 'size', 'life', 'decay', 'rot', 'rot_speed')

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vx = random.uniform(-6, 6)
        self.vy = random.uniform(-11, -4)
        self.gravity = 0.18
        self.color = QColor(random.choice([
            "#8B5CF6", "#EC4899", "#10B981", "#F59E0B",
            "#3B82F6", "#EF4444", "#06B6D4", "#F97316"
        ]))
        self.size = random.uniform(4, 9)
        self.life = 1.0
        self.decay = random.uniform(0.007, 0.018)
        self.rot = random.uniform(0, 360)
        self.rot_speed = random.uniform(-9, 9)


class ConfettiOverlay(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.particles = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if parent:
            self.setGeometry(parent.rect())
        self.hide()

    def burst(self, x, y, count=40):
        for _ in range(count):
            self.particles.append(_ConfettiPiece(x, y))
        self._activate()

    def rain(self, count=55):
        w = max(self.width(), 300)
        for _ in range(count):
            p = _ConfettiPiece(random.uniform(0, w), random.uniform(-60, -5))
            p.vx = random.uniform(-1.6, 1.6)
            p.vy = random.uniform(1.8, 4.5)
            p.gravity = 0.05
            p.decay = random.uniform(0.0035, 0.008)
            self.particles.append(p)
        self._activate()

    def _activate(self):
        self.show()
        self.raise_()
        if not self._timer.isActive():
            self._timer.start(16)

    def _tick(self):
        h = self.height() + 80
        alive = []
        for pt in self.particles:
            pt.x += pt.vx
            pt.y += pt.vy
            pt.vy += pt.gravity
            pt.vx *= 0.99
            pt.life -= pt.decay
            pt.rot += pt.rot_speed
            if pt.life > 0 and pt.y < h:
                alive.append(pt)
        self.particles = alive
        if not self.particles:
            self._timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self.particles:
            p.save()
            p.setOpacity(max(0.0, min(1.0, pt.life)))
            p.translate(pt.x, pt.y)
            p.rotate(pt.rot)
            p.setBrush(QBrush(pt.color))
            p.drawRoundedRect(
                QRectF(-pt.size / 2, -pt.size / 4, pt.size, pt.size * 0.55), 1.5, 1.5
            )
            p.restore()
        p.end()

class CelebrationBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.text = ""
        self.subtitle = ""
        self.duration_ms = 2400
        self.elapsed = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if parent:
            self.setGeometry(parent.rect())
        self.hide()

    def show_message(self, text: str, subtitle: str = ""):
        self.text = text
        self.subtitle = subtitle
        self.elapsed = 0
        if self.parent():
            self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        if not self._timer.isActive():
            self._timer.start(16)

    def _tick(self):
        self.elapsed += 16
        if self.elapsed >= self.duration_ms:
            self._timer.stop()
            self.hide()
        self.update()

    @staticmethod
    def _ease_out_back(k):
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * pow(k - 1, 3) + c1 * pow(k - 1, 2)

    def paintEvent(self, event):
        if not self.text:
            return

        t = min(1.0, self.elapsed / self.duration_ms)

        if t < 0.20:
            k = t / 0.20
            scale = 0.55 + 0.55 * self._ease_out_back(k)
            opacity = min(1.0, k * 1.7)
        elif t < 0.68:
            scale = 1.10 + math.sin((t - 0.20) * 13.0) * 0.018
            opacity = 1.0
        else:
            k = (t - 0.68) / 0.32
            scale = 1.10 + 0.22 * k
            opacity = 1.0 - k

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setOpacity(max(0.0, opacity))

        p.translate(self.width() / 2.0, self.height() / 2.0 - 10)
        p.scale(scale, scale)

        title_font = QFont("Inter", 30, QFont.Weight.Black)
        sub_font = QFont("Inter", 10, QFont.Weight.Medium)
        fm = QFontMetricsF(title_font)
        tw = fm.horizontalAdvance(self.text)
        th = fm.height()

        pill_w = tw + 90
        pill_h = th + 44 + (24 if self.subtitle else 0)
        pill = QRectF(-pill_w / 2, -pill_h / 2, pill_w, pill_h)

        p.setBrush(Qt.BrushStyle.NoBrush)
        for i, a in enumerate((26, 46, 80)):
            p.setPen(QPen(QColor(139, 92, 246, a), 8 - i * 2))
            p.drawRoundedRect(pill.adjusted(-8 + i * 2, -8 + i * 2, 8 - i * 2, 8 - i * 2), 24, 24)

        p.setPen(QPen(QColor("#8B5CF6"), 2))
        p.setBrush(QBrush(QColor(24, 24, 27, 240)))
        p.drawRoundedRect(pill, 18, 18)

        for i in range(10):
            ang = (i / 10.0) * math.pi * 2 + t * 2.4
            rx = pill_w * 0.60 + math.sin(t * 7 + i) * 7
            ry = pill_h * 0.85 + math.cos(t * 7 + i) * 7
            self._star(p, math.cos(ang) * rx, math.sin(ang) * ry,
                       3.5 + math.sin(t * 9 + i) * 1.5)

        p.setPen(QColor("#FAFAFA"))
        p.setFont(title_font)
        ty = -12 if self.subtitle else 0
        p.drawText(QRectF(-pill_w / 2, ty - th / 2, pill_w, th),
                   Qt.AlignmentFlag.AlignCenter, self.text)

        if self.subtitle:
            p.setPen(QColor("#A1A1AA"))
            p.setFont(sub_font)
            p.drawText(QRectF(-pill_w / 2, ty + th / 2 - 2, pill_w, 24),
                       Qt.AlignmentFlag.AlignCenter, self.subtitle)
        p.end()

    def _star(self, p, cx, cy, r):
        path = QPainterPath()
        path.moveTo(cx, cy - r)
        path.quadTo(cx, cy, cx + r, cy)
        path.quadTo(cx, cy, cx, cy + r)
        path.quadTo(cx, cy, cx - r, cy)
        path.quadTo(cx, cy, cx, cy - r)
        p.setPen(Qt.PenStyle.NoPen)
        p.fillPath(path, QColor("#F5C242"))

class AmbientParticles(QWidget):
    def __init__(self, parent=None, count=14):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if parent:
            self.setGeometry(parent.rect())

        self.dots = [{
            'x': random.uniform(0, 1), 'y': random.uniform(0, 1),
            'speed': random.uniform(0.00015, 0.0006),
            'drift': random.uniform(0.3, 1.2),
            'size': random.uniform(1.2, 3.0),
            'opacity': random.uniform(0.05, 0.13),
            'phase': random.uniform(0, math.pi * 2),
        } for _ in range(count)]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)
        self.show()

    def _tick(self):
        if not self.isVisible():
            return                      
        for d in self.dots:
            d['y'] -= d['speed']
            d['phase'] += 0.015
            d['x'] += math.sin(d['phase'] * d['drift']) * 0.0003
            if d['y'] < -0.05:
                d['y'] = 1.05
                d['x'] = random.uniform(0, 1)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        for d in self.dots:
            p.setOpacity(d['opacity'])
            p.setBrush(QBrush(QColor("#8B5CF6")))
            p.drawEllipse(QPointF(d['x'] * w, d['y'] * h), d['size'], d['size'])
        p.end()

class AnimationManager(QObject):

    def __init__(self, host: QWidget):
        super().__init__(host)
        self.host = host
        self.cats = []

        self.ambient = AmbientParticles(host, count=14)
        self.confetti = ConfettiOverlay(host)
        self.banner = CelebrationBanner(host)

        host.installEventFilter(self)
        self._sync_geometry()

        self._spawn_timer = QTimer(self)
        self._spawn_timer.timeout.connect(self.spawn_cat)
        self._spawn_timer.start(random.randint(18000, 45000))

    def eventFilter(self, obj, event):
        if obj is self.host and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._sync_geometry()
        return False

    def _sync_geometry(self):
        r = self.host.rect()
        for w in (self.ambient, self.confetti, self.banner):
            w.setGeometry(r)
        self._restack()

    def _restack(self):
        self.ambient.raise_()
        self.confetti.raise_()
        for c in list(self.cats):
            try:
                c.raise_()
            except RuntimeError:
                self.cats.remove(c)
        self.banner.raise_()

    def spawn_cat(self):
        cat = WalkingCat(self.host)
        cat.finished.connect(lambda c=cat: self._forget_cat(c))
        self.cats.append(cat)
        self._restack()
        self._spawn_timer.setInterval(random.randint(18000, 45000))
        return cat

    def _forget_cat(self, cat):
        if cat in self.cats:
            self.cats.remove(cat)

    def cat_invasion(self, count=10, stagger_ms=230):
        for i in range(count):
            QTimer.singleShot(i * stagger_ms, self.spawn_cat)

    def confetti_burst(self, x, y, count=40):
        self.confetti.burst(x, y, count)
        self._restack()

    def confetti_rain(self, count=55):
        self.confetti.rain(count)
        self._restack()

    def celebrate(self, text, subtitle="", rain=True, cats=0):
        self.banner.show_message(text, subtitle)
        if rain:
            self.confetti.rain(65)
        if cats:
            self.cat_invasion(cats)
        self._restack()
