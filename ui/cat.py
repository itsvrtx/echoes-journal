"""
ECHOES — Procedural Running Cat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A fully procedural, physics-driven cat rendered at 60 FPS.

GAIT: transverse gallop — the real four-beat running gait of a cat.

  • Duty factor 0.30 (vs 0.60 walking) — brief ground contact
  • SUSPENSION PHASE — all four paws leave the ground each cycle
  • Spine flexion/extension — the body gathers then unfurls in flight
  • Paired footfalls: near-rear → far-rear → near-front → far-front
  • Dust puffs kicked up on every paw-strike
  • No-slip cadence solver — paws stay locked to the ground at any speed
  • Verlet tail streams horizontally under aerodynamic drag

States: RUN · SPRINT · SIT · GROOM · STRETCH  (idles are rare and brief)
"""

import math
import random

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QElapsedTimer, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPainterPath, QPen, QBrush,
    QLinearGradient, QRadialGradient, QCursor
)
from PySide6.QtWidgets import QWidget

def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def ease_out_cubic(t):
    return 1.0 - pow(1.0 - clamp(t, 0.0, 1.0), 3)


def mix_color(c1: QColor, c2: QColor, t: float) -> QColor:
    t = clamp(t, 0.0, 1.0)
    return QColor(
        int(lerp(c1.red(), c2.red(), t)),
        int(lerp(c1.green(), c2.green(), t)),
        int(lerp(c1.blue(), c2.blue(), t)),
        int(lerp(c1.alpha(), c2.alpha(), t)),
    )


class Spring:
    __slots__ = ("value", "target", "vel", "k", "d")

    def __init__(self, value=0.0, stiffness=90.0):
        self.value = float(value)
        self.target = float(value)
        self.vel = 0.0
        self.k = stiffness
        self.d = 2.0 * math.sqrt(stiffness)

    def set_stiffness(self, k):
        self.k = k
        self.d = 2.0 * math.sqrt(k)

    def snap(self, v):
        self.value = self.target = float(v)
        self.vel = 0.0

    def update(self, dt):
        dt = min(dt, 0.05)
        accel = self.k * (self.target - self.value) - self.d * self.vel
        self.vel += accel * dt
        self.value += self.vel * dt
        return self.value

class VerletTail:

    def __init__(self, segments=9, seg_len=4.6):
        self.n = segments
        self.seg_len = seg_len
        self.pos = [QPointF(0, 0) for _ in range(segments)]
        self.prev = [QPointF(0, 0) for _ in range(segments)]
        self.stiffness_iters = 6

    def reset(self, anchor: QPointF, direction=1):
        for i in range(self.n):
            p = QPointF(anchor.x() - i * self.seg_len * direction,
                        anchor.y() - i * self.seg_len * 0.30)
            self.pos[i] = p
            self.prev[i] = QPointF(p)

    def update(self, anchor: QPointF, dt: float,
               gravity=42.0, drag=0.986, wind=QPointF(0, 0)):
        dt = min(dt, 0.033)

        for i in range(1, self.n):
            p, pr = self.pos[i], self.prev[i]

            vx = (p.x() - pr.x()) * drag
            vy = (p.y() - pr.y()) * drag

            self.prev[i] = QPointF(p)
            weight = 0.55 + 0.45 * (i / max(1, self.n - 1))

            self.pos[i] = QPointF(
                p.x() + vx + wind.x() * dt * weight,
                p.y() + vy + (gravity + wind.y()) * dt * dt * 60.0 * weight,
            )

        self.pos[0] = QPointF(anchor)
        self.prev[0] = QPointF(anchor)

        for _ in range(self.stiffness_iters):
            for i in range(self.n - 1):
                a, b = self.pos[i], self.pos[i + 1]
                dx, dy = b.x() - a.x(), b.y() - a.y()
                dist = math.hypot(dx, dy)
                if dist < 1e-6:
                    continue
                diff = (dist - self.seg_len) / dist

                if i == 0:
                    self.pos[i + 1] = QPointF(b.x() - dx * diff,
                                              b.y() - dy * diff)
                else:
                    hx, hy = dx * diff * 0.5, dy * diff * 0.5
                    self.pos[i] = QPointF(a.x() + hx, a.y() + hy)
                    self.pos[i + 1] = QPointF(b.x() - hx, b.y() - hy)

    def apply_curl(self, anchor: QPointF, amount: float, direction: int):
        if amount <= 0.001:
            return
        for i in range(self.n):
            t = i / max(1, self.n - 1)
            ang = -0.5 + t * 4.4
            r = 3.0 + t * 13.0
            tx = anchor.x() + math.cos(ang) * r * direction
            ty = anchor.y() + 5.0 + math.sin(ang) * r * 0.62
            self.pos[i] = QPointF(
                lerp(self.pos[i].x(), tx, amount),
                lerp(self.pos[i].y(), ty, amount),
            )

def catmull_rom(points, samples=5):
    n = len(points)
    if n < 3:
        return list(points)

    out = []
    for i in range(n - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(n - 1, i + 2)]

        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1.x()) +
                       (-p0.x() + p2.x()) * t +
                       (2 * p0.x() - 5 * p1.x() + 4 * p2.x() - p3.x()) * t2 +
                       (-p0.x() + 3 * p1.x() - 3 * p2.x() + p3.x()) * t3)
            y = 0.5 * ((2 * p1.y()) +
                       (-p0.y() + p2.y()) * t +
                       (2 * p0.y() - 5 * p1.y() + 4 * p2.y() - p3.y()) * t2 +
                       (-p0.y() + 3 * p1.y() - 3 * p2.y() + p3.y()) * t3)
            out.append(QPointF(x, y))

    out.append(points[-1])
    return out


def tapered_path(points, w_start, w_end) -> QPainterPath:
    n = len(points)
    if n < 2:
        return QPainterPath()

    left, right = [], []
    for i in range(n):
        if i == 0:
            d = points[1] - points[0]
        elif i == n - 1:
            d = points[-1] - points[-2]
        else:
            d = points[i + 1] - points[i - 1]

        length = math.hypot(d.x(), d.y()) or 1.0
        nx, ny = -d.y() / length, d.x() / length

        t = i / (n - 1)
        w = lerp(w_start, w_end, smoothstep(t))

        left.append(QPointF(points[i].x() + nx * w, points[i].y() + ny * w))
        right.append(QPointF(points[i].x() - nx * w, points[i].y() - ny * w))

    path = QPainterPath()
    path.moveTo(left[0])
    for p in left[1:]:
        path.lineTo(p)

    tip = points[-1]
    path.quadTo(
        QPointF(tip.x() + (tip.x() - points[-2].x()) * 0.6,
                tip.y() + (tip.y() - points[-2].y()) * 0.6),
        right[-1]
    )

    for p in reversed(right[:-1]):
        path.lineTo(p)

    path.closeSubpath()
    return path


def solve_ik(hip: QPointF, foot: QPointF, l1: float, l2: float,
             bend: float) -> QPointF:
    dx, dy = foot.x() - hip.x(), foot.y() - hip.y()
    raw = math.hypot(dx, dy) or 1.0
    dist = clamp(raw, abs(l1 - l2) + 0.01, l1 + l2 - 0.01)
    ux, uy = dx / raw, dy / raw

    a = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))

    mx, my = hip.x() + ux * a, hip.y() + uy * a
    return QPointF(mx - uy * h * bend, my + ux * h * bend)

class Palette:
    __slots__ = ("name", "base", "shade", "light", "blush", "eye")

    def __init__(self, name, base, shade, light, blush, eye):
        self.name = name
        self.base = QColor(base)
        self.shade = QColor(shade)
        self.light = QColor(light)
        self.blush = QColor(blush)
        self.eye = QColor(eye)


PALETTES = [
    Palette("Midnight",  "#3C3C48", "#24242E", "#55556A", "#E79FB0", "#7FE3C4"),
    Palette("Ash",       "#8F8FA0", "#6A6A79", "#B2B2C2", "#EFB2BE", "#7CC7F2"),
    Palette("Marmalade", "#E99A5C", "#C0743E", "#F7BC86", "#F2A6B0", "#8CD9A6"),
    Palette("Cream",     "#EADFCA", "#C6B9A0", "#F8F1E4", "#EFA4B0", "#7BBFE8"),
    Palette("Cocoa",     "#7C5843", "#573B2C", "#9A7460", "#E79FB0", "#F2C572"),
    Palette("Lilac",     "#BAA7E9", "#9482CB", "#D6C9F5", "#F2AEC0", "#F6D189"),
    Palette("Rosewater", "#E9B5BF", "#C68E9B", "#F7D3D9", "#E78EA0", "#8CD9C8"),
    Palette("Frost",     "#A9CDE9", "#8099BF", "#CBE4F7", "#EFA6B2", "#F6C878"),
    Palette("Sage",      "#A8C4A8", "#809880", "#CBDFCB", "#EFA6B2", "#F0B06A"),
]

class PolishedCat(QWidget):
    finished = Signal()

    W, H = 118, 88
    GROUND = 56.0                   

    HIP_X, SHO_X = 34.0, 62.0
    BODY_Y = 40.0
    UPPER, LOWER = 10.0, 9.5 

    PHASE = {"near_rear": 0.00, "far_rear": 0.10,
             "near_front": 0.40, "far_front": 0.50}

    DUTY = 0.30                     
    STRIDE = 16.0                   
    LIFT = 8.0                     
    FLIGHT = 7.0                   
    FLIGHT_START = 0.80             

    RUN_SPEED = (150.0, 205.0)     
    SPRINT_MULT = 1.42

    STATES = ("RUN", "SPRINT", "SIT", "GROOM", "STRETCH")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        self.pal = random.choice(PALETTES)
        self.facing = random.choice((-1, 1))
        self.base_speed = random.uniform(*self.RUN_SPEED)

        pw = parent.width() if parent else 900
        ph = parent.height() if parent else 640
        self._x = -self.W - 6.0 if self.facing == 1 else pw + 6.0
        self._y = float(clamp(ph - random.randint(70, 118), 0, max(0, ph - self.H)))
        self.move(int(self._x), int(self._y))

        self.rig = {
            "lift":     Spring(0.0, 110),
            "tilt":     Spring(0.0, 90),
            "head_up":  Spring(0.0, 120),
            "head_fwd": Spring(0.0, 120),
            "head_rot": Spring(0.0, 150),
            "fold_r":   Spring(0.0, 80),
            "fold_f":   Spring(0.0, 80),
            "curl":     Spring(0.0, 55),
            "ear":      Spring(0.0, 200),
            "eye":      Spring(1.0, 260),
            "gait":     Spring(1.0, 70),
            "alpha":    Spring(0.0, 55),
        }

        self.tail = VerletTail(segments=9, seg_len=4.6)
        self.tail.reset(QPointF(self.HIP_X - 6, self.BODY_Y - 4), self.facing)

        self.state = "RUN"
        self.state_time = 0.0
        self._state_duration = 999.0
        self.next_event = random.uniform(2.5, 6.0)
        self._enter("RUN")
        self.phase = random.random()
        self.blink_in = random.uniform(1.2, 3.4)
        self.blink_t = -1.0
        self.breathe = random.random() * math.tau

        self.look = 0.0
        self.groom_t = 0.0
        self.heart = 0.0
        self._exiting = False
        self._dead = False
        self.dust = []
        self._prev_stance = {k: False for k in self.PHASE}

        self.rig["alpha"].target = 1.0

        self._clock = QElapsedTimer()
        self._clock.start()
        self._last_ms = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        self.show()
        self.raise_()

    def _speed(self):
        return self.base_speed * (self.SPRINT_MULT if self.state == "SPRINT" else 1.0)

    def _is_running(self):
        return self.state in ("RUN", "SPRINT")

    def _flight_height(self):
        ph = self.phase
        if ph < self.FLIGHT_START:
            return 0.0
        t = (ph - self.FLIGHT_START) / (1.0 - self.FLIGHT_START)
        return math.sin(math.pi * t) * self.FLIGHT * self.rig["gait"].value

    def _spine_flex(self):
        return math.sin((self.phase - 0.65) * math.tau) * self.rig["gait"].value

    def _tick(self):
        if self._dead:
            return

        now = self._clock.elapsed()
        dt = clamp((now - self._last_ms) / 1000.0, 0.0, 0.05)
        self._last_ms = now
        if dt <= 0.0:
            return

        self._update_state(dt)
        self._update_motion(dt)
        self._update_dust(dt)
        self._update_blink(dt)
        self._update_look()

        for s in self.rig.values():
            s.update(dt)

        self._update_tail(dt)

        if self.heart > 0.0:
            self.heart = max(0.0, self.heart - dt * 0.50)

        self.breathe += dt * 2.4
        self.update()

    def _update_state(self, dt):
        self.state_time += dt
        self.next_event -= dt

        if self.state in ("SIT", "GROOM", "STRETCH"):
            if self.state_time > self._state_duration:
                self._enter("RUN")
            return

        if self.next_event <= 0.0:
            self.next_event = random.uniform(3.0, 7.0)
            roll = random.random()
            if roll < 0.09:
                self._enter("SIT")
            elif roll < 0.16:
                self._enter("GROOM")
            elif roll < 0.22:
                self._enter("STRETCH")
            elif roll < 0.62:
                self._enter("SPRINT")
            else:
                self._enter("RUN")

    def _enter(self, state):
        self.state = state
        self.state_time = 0.0
        r = self.rig

        if state == "RUN":
            self._state_duration = 999.0
            r["lift"].target = 1.5
            r["tilt"].target = -0.05
            r["head_up"].target = 1.4
            r["head_fwd"].target = 2.0
            r["fold_r"].target = 0.0
            r["fold_f"].target = 0.0
            r["curl"].target = 0.0
            r["ear"].target = -0.16      
            r["gait"].target = 1.0

        elif state == "SPRINT":
            self._state_duration = 999.0
            r["lift"].target = 2.4
            r["tilt"].target = -0.10
            r["head_up"].target = 2.2
            r["head_fwd"].target = 3.4
            r["fold_r"].target = 0.0
            r["fold_f"].target = 0.0
            r["curl"].target = 0.0
            r["ear"].target = -0.30      
            r["gait"].target = 1.18

        elif state == "SIT":
            self._state_duration = random.uniform(1.0, 1.8)  
            r["lift"].target = -7.5
            r["tilt"].target = -0.30
            r["head_up"].target = 5.5
            r["head_fwd"].target = -3.5
            r["fold_r"].target = 1.0
            r["fold_f"].target = 0.0
            r["curl"].target = 1.0
            r["ear"].target = 0.08
            r["gait"].target = 0.0

        elif state == "GROOM":
            self._state_duration = random.uniform(1.2, 2.0)
            self.groom_t = 0.0
            r["lift"].target = -7.5
            r["tilt"].target = -0.26
            r["head_up"].target = 3.0
            r["head_fwd"].target = -5.0
            r["fold_r"].target = 1.0
            r["fold_f"].target = 0.0
            r["curl"].target = 0.9
            r["ear"].target = 0.16
            r["gait"].target = 0.0

        elif state == "STRETCH":
            self._state_duration = random.uniform(0.8, 1.3)
            r["lift"].target = -2.5
            r["tilt"].target = 0.24
            r["head_up"].target = -2.6
            r["head_fwd"].target = 2.4
            r["fold_r"].target = 0.0
            r["fold_f"].target = 0.0
            r["curl"].target = 0.0
            r["ear"].target = 0.22
            r["gait"].target = 0.0

    def _update_motion(self, dt):
        parent = self.parent()
        if parent is None:
            self._cleanup()
            return

        speed = self._speed()

        if self._is_running():
            self._x += self.facing * speed * dt
            eff_stride = self.STRIDE * max(0.30, self.rig["gait"].value)
            self.phase = (self.phase + (speed * self.DUTY / eff_stride) * dt) % 1.0

            self._spawn_dust(dt, speed)
        else:
            self.phase = (self.phase + dt * 0.10) % 1.0

        max_y = max(0.0, parent.height() - self.H)
        if self._y > max_y:
            self._y = max_y

        self.move(int(self._x), int(self._y))

        pw = parent.width()
        margin = 40.0
        if self.facing == 1 and self._x > pw - margin:
            self._begin_exit()
        elif self.facing == -1 and self._x < -self.W + margin:
            self._begin_exit()

        if self._exiting and self.rig["alpha"].value < 0.02:
            self._cleanup()

    def _begin_exit(self):
        if not self._exiting:
            self._exiting = True
            self.rig["alpha"].target = 0.0

    def _spawn_dust(self, dt, speed):
        if self.rig["gait"].value < 0.5:
            return

        for key, offset in self.PHASE.items():
            ph = (self.phase + offset) % 1.0
            in_stance = ph < self.DUTY
            was = self._prev_stance[key]
            self._prev_stance[key] = in_stance

            if in_stance and not was:
                hip_x = self.HIP_X if "rear" in key else self.SHO_X
                fx = hip_x + self.STRIDE * 0.5
                for _ in range(2):
                    self.dust.append([
                        fx + random.uniform(-2.0, 2.0),      
                        self.GROUND + random.uniform(-1.0, 1.0),  
                        random.uniform(-26.0, -8.0),         
                        random.uniform(-20.0, -6.0),        
                        1.0,                                 
                        random.uniform(1.6, 3.2),            
                    ])

        if len(self.dust) > 40:
            del self.dust[:-40]

    def _update_dust(self, dt):
        if not self.dust:
            return
        
        recede = self._speed() * dt if self._is_running() else 0.0

        alive = []
        for d in self.dust:
            d[0] += d[2] * dt - recede
            d[1] += d[3] * dt
            d[3] += 34.0 * dt          
            d[2] *= 0.94
            d[4] -= dt * 3.1           
            if d[4] > 0.0 and d[0] > -8.0:
                alive.append(d)
        self.dust = alive

    def _update_blink(self, dt):
        if self.state == "GROOM":
            self.rig["eye"].target = 0.32
            return
        
        base_open = 0.78 if self.state == "SPRINT" else 1.0

        if self.blink_t >= 0.0:
            self.blink_t += dt
            if self.blink_t < 0.06:
                self.rig["eye"].target = 0.0
            elif self.blink_t < 0.14:
                self.rig["eye"].target = base_open
            else:
                self.blink_t = -1.0
                self.blink_in = random.uniform(1.4, 4.0)
        else:
            self.rig["eye"].target = base_open
            self.blink_in -= dt
            if self.blink_in <= 0.0:
                self.blink_t = 0.0

    def _update_look(self):
        try:
            local = self.mapFromGlobal(QCursor.pos())
        except Exception:
            return
        dx = (local.x() - self.W * 0.5) / 260.0
        target = clamp(dx * self.facing, -1.0, 1.0)
        self.look += (target - self.look) * 0.07
        self.rig["head_rot"].target = self.look * 0.11

    def _update_tail(self, dt):
        anchor = QPointF(
            self.HIP_X - 7.0,
            self.BODY_Y - 5.0 - self.rig["lift"].value - self._flight_height()
        )

        speed = self._speed()

        if self._is_running():
            drive = -speed * 0.46
            gravity = 16.0
            drag = 0.978
            sway = math.sin(self.phase * math.tau) * 4.0 * self.rig["gait"].value
        else:
            drive = 0.0
            gravity = 40.0
            drag = 0.985
            sway = 0.0

        breathe = math.sin(self.breathe * 0.8) * 3.0

        self.tail.update(
            anchor, dt,
            gravity=gravity,
            drag=drag,
            wind=QPointF(drive, sway + breathe * 0.4),
        )
        self.tail.apply_curl(anchor, self.rig["curl"].value, 1)

    def _cleanup(self):
        if self._dead:
            return
        self._dead = True
        self._timer.stop()
        self.finished.emit()
        self.deleteLater()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.heart = 1.0
        self._enter("SIT")
        self._state_duration = 2.2        
        self.rig["ear"].target = 0.30
        self.rig["head_up"].target = 6.2
        event.accept()

    def _foot(self, key, hip_x, fold):
        amp = self.rig["gait"].value
        ph = (self.phase + self.PHASE[key]) % 1.0

        if ph < self.DUTY:                       
            t = ph / self.DUTY
            fx = hip_x + (self.STRIDE * 0.5 - self.STRIDE * t) * amp
            fy = self.GROUND
        else:                                    
            t = (ph - self.DUTY) / (1.0 - self.DUTY)
            e = smootherstep(t)
            fx = hip_x + (-self.STRIDE * 0.5 + self.STRIDE * e) * amp
            tuck = math.sin(math.pi * t)
            fy = self.GROUND - tuck * self.LIFT * amp

        if fold > 0.001:
            fx = lerp(fx, hip_x + 4.0, fold)
            fy = lerp(fy, self.GROUND - 1.0, fold)

        return QPointF(fx, fy)

    def _limb(self, p, key, hip_x, bend, fold, color, width):
        lift = self.rig["lift"].value + self._flight_height()
        hip = QPointF(hip_x, self.BODY_Y + 2.0 - lift)
        foot = self._foot(key, hip_x, fold)

        u = lerp(self.UPPER, self.UPPER * 0.72, fold)
        l = lerp(self.LOWER, self.LOWER * 0.70, fold)
        knee = solve_ik(hip, foot, u, l, bend * self.facing)

        pts = catmull_rom([hip, knee, foot], samples=5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        p.drawPath(tapered_path(pts, width, width * 0.62))
        p.drawEllipse(foot, width * 1.25, width * 0.86)

    def paintEvent(self, event):
        alpha = self.rig["alpha"].value
        if alpha <= 0.01:
            return

        p = QPainter(self)
        p.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        p.setOpacity(clamp(alpha, 0.0, 1.0))
        p.translate(self._x - int(self._x), self._y - int(self._y))

        if self.facing == -1:
            p.translate(self.W, 0)
            p.scale(-1, 1)

        self._draw_dust(p)
        self._draw_shadow(p)

        flight = self._flight_height()
        lift = self.rig["lift"].value + flight
        flex = self._spine_flex()

        tilt = self.rig["tilt"].value - flex * 0.05

        p.save()
        p.translate(self.HIP_X + 14.0, self.BODY_Y - lift)
        p.rotate(math.degrees(tilt))
        p.translate(-(self.HIP_X + 14.0), -(self.BODY_Y - lift))

        self._draw_far_legs(p)
        self._draw_tail(p)
        self._draw_body(p, lift, flex)
        self._draw_near_legs(p)
        self._draw_head(p, lift, flex)

        p.restore()

        if self.heart > 0.0:
            self._draw_heart(p)

        p.end()

    def _draw_dust(self, p):
        if not self.dust:
            return
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, vx, vy, life, size in self.dust:
            a = int(clamp(life, 0.0, 1.0) * 54)
            if a <= 0:
                continue
            p.setBrush(QBrush(QColor(210, 208, 220, a)))
            r = size * (1.0 + (1.0 - life) * 1.3)
            p.drawEllipse(QPointF(x, y), r, r * 0.68)
        
    def _draw_shadow(self, p):
        flight = self._flight_height()
        h = clamp(flight / max(1.0, self.FLIGHT), 0.0, 1.0)
        spread = 1.0 + h * 0.55
        fade = 1.0 - h * 0.62

        rx, ry = 30.0 * spread, 4.6 * spread
        cx, cy = self.HIP_X + 15.0, self.GROUND + 3.0

        grad = QRadialGradient(cx, cy, rx)
        grad.setColorAt(0.0, QColor(0, 0, 0, int(74 * fade)))
        grad.setColorAt(0.55, QColor(0, 0, 0, int(30 * fade)))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), rx, ry)

    def _draw_far_legs(self, p):
        far = mix_color(self.pal.shade, QColor(0, 0, 0), 0.22)
        fr = self.rig["fold_r"].value
        ff = self.rig["fold_f"].value
        self._limb(p, "far_rear",  self.HIP_X - 1.0, +1.0, fr, far, 3.7)
        self._limb(p, "far_front", self.SHO_X - 1.0, -1.0, ff, far, 3.4)

    def _draw_near_legs(self, p):
        near = self.pal.shade
        fr = self.rig["fold_r"].value
        ff = self.rig["fold_f"].value
        self._limb(p, "near_rear",  self.HIP_X + 3.0, +1.0, fr, near, 4.1)
        self._limb(p, "near_front", self.SHO_X + 3.0, -1.0, ff, near, 3.7)

    def _draw_tail(self, p):
        pts = catmull_rom(self.tail.pos, samples=4)
        path = tapered_path(pts, 3.5, 1.5)

        grad = QLinearGradient(pts[0], pts[-1])
        grad.setColorAt(0.0, self.pal.shade)
        grad.setColorAt(1.0, self.pal.base)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)

    def _body_path(self, squash, flex) -> QPainterPath:
        hx = self.HIP_X - flex * 2.6
        sx = self.SHO_X + flex * 2.6
        y = self.BODY_Y
        h = 10.4 * squash
        arch = -flex * 1.8               
        rump, chest = 12.6, 11.4

        path = QPainterPath()
        path.moveTo(hx - rump, y)
        path.cubicTo(hx - rump, y - h * 1.42 + arch,
                     hx + 4, y - h * 1.30 + arch,
                     (hx + sx) * 0.5, y - h * 1.12 + arch)
        path.cubicTo(sx - 4, y - h * 1.26 + arch,
                     sx + chest * 0.55, y - h * 1.20,
                     sx + chest, y - h * 0.28)
        path.cubicTo(sx + chest + 1.6, y + h * 0.62,
                     sx + 4, y + h * 1.02 - arch * 0.5,
                     (hx + sx) * 0.5, y + h * 0.96 - arch * 0.5)
        path.cubicTo(hx + 4, y + h * 0.92,
                     hx - rump + 1.0, y + h * 1.12,
                     hx - rump, y)
        path.closeSubpath()
        return path

    def _draw_body(self, p, lift, flex):
        gait = self.rig["gait"].value
        squash = 1.0 - flex * 0.055 * gait
        squash += math.sin(self.breathe) * 0.012
        squash *= 1.0 - self.rig["fold_r"].value * 0.05

        p.save()
        p.translate(0, -lift)

        path = self._body_path(squash, flex)

        grad = QLinearGradient(0, self.BODY_Y - 14, 0, self.BODY_Y + 12)
        grad.setColorAt(0.0, self.pal.light)
        grad.setColorAt(0.42, self.pal.base)
        grad.setColorAt(1.0, self.pal.shade)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 34), 1.4))
        p.save()
        p.setClipPath(path)
        p.translate(0, 1.6)
        p.drawPath(path)
        p.restore()

        p.restore()

    def _draw_head(self, p, lift, flex):
        r = self.rig
        hx = self.SHO_X + 13.0 + r["head_fwd"].value + flex * 2.2
        hy = self.BODY_Y - 12.0 - r["head_up"].value - lift

        if self.state == "GROOM":
            self.groom_t += 0.05
            hy += math.sin(self.groom_t * 5.2) * 2.4
            hx += math.sin(self.groom_t * 5.2) * 1.1

        p.save()
        p.translate(hx, hy)
        p.rotate(math.degrees(r["head_rot"].value) + 4.0 + flex * 1.6)

        self._draw_ears(p)

        skull = QPainterPath()
        skull.addEllipse(QRectF(-10.4, -8.6, 20.8, 17.6))

        grad = QRadialGradient(-2.0, -3.0, 15.0)
        grad.setColorAt(0.0, self.pal.light)
        grad.setColorAt(0.62, self.pal.base)
        grad.setColorAt(1.0, self.pal.shade)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawPath(skull)

        p.setBrush(QBrush(mix_color(self.pal.light, QColor("#FFFFFF"), 0.22)))
        p.drawEllipse(QRectF(1.2, 0.4, 10.2, 7.4))

        self._draw_eyes(p)
        self._draw_nose(p)
        self._draw_whiskers(p)

        p.restore()

    def _draw_ears(self, p):
        rot = self.rig["ear"].value
        twitch = math.sin(self.breathe * 3.1) * 0.02

        for sx, base_rot in ((-5.4, -0.30), (4.6, 0.24)):
            p.save()
            p.translate(sx, -7.0)
            p.rotate(math.degrees(base_rot + rot + twitch))

            outer = QPainterPath()
            outer.moveTo(-4.2, 1.6)
            outer.quadTo(-1.4, -8.4, 3.4, 0.4)
            outer.quadTo(0.0, 2.6, -4.2, 1.6)
            outer.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self.pal.base))
            p.drawPath(outer)

            inner = QPainterPath()
            inner.moveTo(-2.4, 0.9)
            inner.quadTo(-1.0, -5.2, 1.8, 0.2)
            inner.quadTo(-0.2, 1.5, -2.4, 0.9)
            inner.closeSubpath()
            p.setBrush(QBrush(self.pal.blush))
            p.drawPath(inner)

            p.restore()

    def _draw_eyes(self, p):
        openness = clamp(self.rig["eye"].value, 0.0, 1.0)
        yaw = self.look * 0.8

        for ex in (-3.6, 4.4):
            cy = -1.2

            if openness < 0.10:
                p.setPen(QPen(QColor(30, 30, 36, 210), 1.3,
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.setBrush(Qt.BrushStyle.NoBrush)
                path = QPainterPath()
                path.moveTo(ex - 2.4, cy)
                path.quadTo(ex, cy + 1.7, ex + 2.4, cy)
                p.drawPath(path)
                continue

            h = 4.2 * openness

            eye = QPainterPath()
            eye.moveTo(ex - 2.9, cy)
            eye.quadTo(ex, cy - h, ex + 2.9, cy)
            eye.quadTo(ex, cy + h * 0.86, ex - 2.9, cy)
            eye.closeSubpath()

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self.pal.eye))
            p.drawPath(eye)

            p.setBrush(QBrush(QColor(22, 22, 28)))
            p.drawEllipse(QPointF(ex + yaw, cy), 0.85, h * 0.66)

            p.setBrush(QBrush(QColor(255, 255, 255, 205)))
            p.drawEllipse(QPointF(ex + yaw - 1.0, cy - h * 0.30), 0.62, 0.62)

    def _draw_nose(self, p):
        nose = QPainterPath()
        nose.moveTo(7.4, 2.0)
        nose.quadTo(9.6, 2.0, 8.5, 4.0)
        nose.quadTo(7.4, 5.0, 6.3, 4.0)
        nose.quadTo(5.2, 2.0, 7.4, 2.0)
        nose.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self.pal.blush))
        p.drawPath(nose)

        p.setPen(QPen(QColor(40, 40, 48, 130), 0.8,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(7.4, 4.8), QPointF(7.4, 6.0))

    def _draw_whiskers(self, p):
        p.setPen(QPen(QColor(255, 255, 255, 62), 0.7,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        sweep = -2.4 if self._is_running() else 0.0
        flex = math.sin(self.breathe * 1.7) * 0.5

        for dy, curve in ((-0.6, -2.2), (0.9, 0.0), (2.4, 2.0)):
            w = QPainterPath()
            w.moveTo(9.0, 3.4 + dy)
            w.quadTo(15.0, 3.0 + dy + curve * 0.5 + flex - sweep * 0.4,
                     20.0 + sweep, 2.4 + dy + curve + flex - sweep * 0.8)
            p.drawPath(w)

    def _draw_heart(self, p):
        a = ease_out_cubic(self.heart)
        rise = (1.0 - self.heart) * 16.0

        p.save()
        p.setOpacity(a * self.rig["alpha"].value)

        cx = self.SHO_X + 16.0
        cy = self.BODY_Y - 34.0 - rise
        s = 0.85 + (1.0 - self.heart) * 0.35

        p.translate(cx, cy)
        p.scale(s, s)

        h = QPainterPath()
        h.moveTo(0, 3.4)
        h.cubicTo(0, 0.6, -5.2, -1.8, -5.2, 2.0)
        h.cubicTo(-5.2, 5.6, 0, 8.6, 0, 11.2)
        h.cubicTo(0, 8.6, 5.2, 5.6, 5.2, 2.0)
        h.cubicTo(5.2, -1.8, 0, 0.6, 0, 3.4)
        h.closeSubpath()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#FF6B8A")))
        p.drawPath(h)
        p.restore()

WalkingCat = PolishedCat
