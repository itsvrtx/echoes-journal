"""
ECHOES — Branding / Logo System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Auto-discovers the logo file (any common name / extension / casing)
• Hi-DPI aware rendering with devicePixelRatio
• Native SVG support via QSvgRenderer
• Auto-plates dark logos so they stay visible on a dark UI
• Multi-resolution QIcon for a crisp title bar
• Sets the Windows AppUserModelID so the taskbar uses YOUR icon
• Procedural fallback mark — the app never looks broken
"""

import os
import sys
import ctypes

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (
    QPixmap, QIcon, QPainter, QColor, QBrush, QPen,
    QPainterPath, QLinearGradient, QImage
)
from PySide6.QtWidgets import QApplication, QWidget

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

LOGO_BASENAMES = ("logo", "icon", "echoes", "app", "brand", "appicon")
LOGO_EXTS = (".png", ".svg", ".ico", ".jpg", ".jpeg", ".webp", ".bmp")

_render_cache: dict = {}
_found_logo: str | None = None
_scanned = False


def _base_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def assets_dir() -> str:
    return os.path.join(_base_dir(), "assets")


def find_logo(explicit: str | None = None) -> str | None:
    global _found_logo, _scanned

    if explicit and os.path.isfile(explicit):
        return explicit

    if _scanned:
        return _found_logo

    _scanned = True
    folder = assets_dir()

    if not os.path.isdir(folder):
        _found_logo = None
        return None

    try:
        files = os.listdir(folder)
    except OSError:
        _found_logo = None
        return None

    lower_map = {f.lower(): f for f in files}

    for base in LOGO_BASENAMES:
        for ext in LOGO_EXTS:
            key = base + ext
            if key in lower_map:
                _found_logo = os.path.join(folder, lower_map[key])
                return _found_logo

    for f in sorted(files):
        if os.path.splitext(f)[1].lower() in LOGO_EXTS:
            _found_logo = os.path.join(folder, f)
            return _found_logo

    _found_logo = None
    return None

def _dpr() -> float:
    app = QApplication.instance()
    if app is None:
        return 1.0
    try:
        return float(app.devicePixelRatio())
    except Exception:
        return 1.0


def _load_source(path: str | None, px: int) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None

    if path.lower().endswith(".svg"):
        if not _HAS_SVG:
            return None
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return None
        pm = QPixmap(px, px)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        return pm

    pm = QPixmap(path)
    return None if pm.isNull() else pm


def _mean_luminance(pm: QPixmap) -> float:
    img = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    if w == 0 or h == 0:
        return 1.0

    step = max(1, min(w, h) // 26)
    total, count = 0.0, 0

    for y in range(0, h, step):
        for x in range(0, w, step):
            c = img.pixelColor(x, y)
            if c.alpha() < 40:
                continue
            total += 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()
            count += 1

    return 1.0 if count == 0 else total / count


def _add_plate(pm: QPixmap, px: int) -> QPixmap:
    out = QPixmap(px, px)
    out.fill(Qt.GlobalColor.transparent)

    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = QRectF(0, 0, px, px)
    radius = px * 0.26

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 26))
    p.drawRoundedRect(r, radius, radius)

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 48), max(1.0, px * 0.012)))
    p.drawRoundedRect(r.adjusted(0.6, 0.6, -0.6, -0.6), radius, radius)

    inner = int(px * 0.76)
    scaled = pm.scaled(
        inner, inner,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    p.drawPixmap(
        int((px - scaled.width()) / 2),
        int((px - scaled.height()) / 2),
        scaled
    )
    p.end()
    return out


def generate_fallback(px: int) -> QPixmap:
    pm = QPixmap(px, px)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, px, px)
    grad.setColorAt(0.0, QColor("#A78BFA"))
    grad.setColorAt(1.0, QColor("#6D28D9"))

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, px, px), px * 0.24, px * 0.24)
    p.fillPath(path, QBrush(grad))

    cx, cy = px * 0.34, px * 0.5
    for rad, alpha, width in ((0.17, 240, 0.088),
                              (0.29, 168, 0.076),
                              (0.41, 96, 0.064)):
        p.setPen(QPen(QColor(255, 255, 255, alpha),
                      px * width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(
            QRectF(cx - px * rad, cy - px * rad, px * rad * 2, px * rad * 2),
            -55 * 16, 110 * 16
        )

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 246))
    p.drawEllipse(QPointF(cx, cy), px * 0.056, px * 0.056)
    p.end()
    return pm


def render_logo(size: int = 64,
                path: str | None = None,
                plate: bool | None = None) -> QPixmap:
    resolved = find_logo(path)
    key = (size, resolved, plate, round(_dpr(), 2))
    if key in _render_cache:
        return _render_cache[key]

    dpr = _dpr()
    px = max(8, int(size * dpr))

    src = _load_source(resolved, px)
    is_fallback = src is None or src.isNull()
    if is_fallback:
        src = generate_fallback(px)

    pm = src.scaled(
        px, px,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    use_plate = plate
    if use_plate is None:
        use_plate = (not is_fallback) and _mean_luminance(pm) < 0.32

    if use_plate:
        pm = _add_plate(pm, px)

    pm.setDevicePixelRatio(dpr)
    _render_cache[key] = pm
    return pm


def app_icon(path: str | None = None) -> QIcon:
    resolved = find_logo(path)
    icon = QIcon()

    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        src = _load_source(resolved, s)
        if src is None or src.isNull():
            src = generate_fallback(s)
        pm = src.scaled(
            s, s,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        if resolved and _mean_luminance(pm) < 0.32:
            pm = _add_plate(pm, s)
        icon.addPixmap(pm)

    return icon

def set_app_user_model_id(app_id: str = "Echoes.Journal.Desktop.1") -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def describe() -> None:
    folder = assets_dir()
    print("\n" + "─" * 62)
    print("  ECHOES · Logo diagnostics")
    print("─" * 62)
    print(f"  assets folder : {folder}")
    print(f"  exists        : {os.path.isdir(folder)}")

    if os.path.isdir(folder):
        try:
            files = os.listdir(folder)
            print(f"  contents      : {files if files else '(empty)'}")
        except OSError as e:
            print(f"  contents      : <unreadable: {e}>")

    found = find_logo()
    if found:
        size_kb = os.path.getsize(found) / 1024
        print(f"  LOGO FOUND    : {os.path.basename(found)}  ({size_kb:.1f} KB)")
    else:
        print("  LOGO FOUND    : NONE — using generated fallback mark")
        print(f"                  Drop a file here: {os.path.join(folder, 'logo.svg')}")
    print(f"  SVG support   : {_HAS_SVG}")
    print("─" * 62 + "\n")

class LogoBadge(QWidget):
    clicked = Signal()

    def __init__(self, size: int = 40, breathe: bool = False,
                 path: str | None = None, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._size = size
        self._breathe = breathe
        self._pixmap = render_logo(int(size * 0.84), path=path)

        self._hover = 0.0
        self._hover_target = 0.0
        self._bounce = 0.0
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        dirty = False

        if abs(self._hover_target - self._hover) > 0.004:
            self._hover += (self._hover_target - self._hover) * 0.20
            dirty = True

        if self._bounce > 0.001:
            self._bounce *= 0.86
            dirty = True

        if self._breathe:
            self._phase += 0.026
            dirty = True

        if dirty:
            self.update()

    def enterEvent(self, e):
        self._hover_target = 1.0
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover_target = 0.0
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._bounce = 1.0
            self.clicked.emit()
        super().mousePressEvent(e)

    def paintEvent(self, event):
        import math

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        s = self._size
        cx = cy = s / 2.0

        breath = (math.sin(self._phase) * 0.5 + 0.5) if self._breathe else 0.0
        glow = max(self._hover, breath * 0.55)

        if glow > 0.01:
            p.setPen(Qt.PenStyle.NoPen)
            for i, base_a in enumerate((16, 26, 40)):
                a = int(base_a * glow)
                if a <= 0:
                    continue
                r = s * (0.50 + 0.055 * (3 - i))
                p.setBrush(QColor(139, 92, 246, a))
                p.drawEllipse(QPointF(cx, cy), r, r)

        scale = 1.0 + self._hover * 0.06 - self._bounce * 0.14
        p.translate(cx, cy)
        p.scale(scale, scale)

        dpr = self._pixmap.devicePixelRatio() or 1.0
        lw = self._pixmap.width() / dpr
        lh = self._pixmap.height() / dpr
        p.drawPixmap(QPointF(-lw / 2.0, -lh / 2.0), self._pixmap)
        p.end()