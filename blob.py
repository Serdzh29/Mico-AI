"""Mico: мягкий blob с эмоциями, анимациями ожидания (моргает, крутится, становится сердечком),
анимацией «думает» и взглядом вниз, пока пользователь печатает."""
import math, random, time
import sleepmode
from PyQt6.QtCore import Qt, QTimer, QPointF, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPainterPath, QPen, QCursor, QGuiApplication, QFont
from PyQt6.QtWidgets import QWidget


from emotions import VALID as MOODS                # одна правда: все эмоции, которые можно выбрать
from shapes import HEART as HEART_PTS             # сглаженное сердце (см. shapes.py)
TILT = {"curious": 7, "sad": -4, "worried": -3, "thinking": 4, "proud": -6, "playful": 5, "confused": 6}
N = 96


def pebble(a, wob, t):
    """Асимметричная форма-«камушек» как на референсе."""
    r = 1.0 + 0.09 * math.sin(2 * a + 0.9) + 0.06 * math.sin(3 * a + 2.1) + 0.025 * math.sin(5 * a)
    return r + wob * (0.012 * math.sin(3 * a + t * 2) + 0.01 * math.sin(4 * a - t * 1.6))


def mix(c1, c2, k):
    return QColor(int(c1.red() * (1 - k) + c2.red() * k), int(c1.green() * (1 - k) + c2.green() * k),
                  int(c1.blue() * (1 - k) + c2.blue() * k))


class Blob(QWidget):
    clicked = pyqtSignal()
    settings_requested = pyqtSignal()        # двойной щелчок левой кнопкой — настройки
    menu_requested = pyqtSignal(QPoint)
    moved = pyqtSignal()
    slept = pyqtSignal()                  # Mico заснул: чат нужно спрятать
    woke = pyqtSignal()                   # Mico проснулся от клика: чат нужно вернуть

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.t0 = time.time()
        self._fonts = {}                                   # шрифты кешируем, а не создаём каждый кадр
        self.mood, self.mood_until = "idle", 0
        self.anim = None                      # (имя, старт, длительность)
        self.next_idle = time.time() + 6
        self.typing_until, self.talking = 0, False
        self.vx = self.vy = self.dvx = self.dvy = 0.0
        self.drag, self.moved_px, self.last_move = None, 0, (None, 0)
        self.squash = self.squash_v = 0.0
        self.jh = self.jv = 0.0               # прыжок
        self.heart = self.tilt = 0.0
        self.lean = 0.0                       # наклон при движении к углу
        self.look_at = None                   # глобальная точка, на которую смотрит Mico (строка ввода)
        self._fx, self._fy, self._last_glide = 0.0, 0.0, time.time()   # плавные (дробные) координаты
        self.blink_at, self.blink_until = time.time() + 3, 0
        self.last_cursor, self.last_input = QCursor.pos(), time.time()
        self.asleep = False                   # спит ли Mico
        self.size_k = 1.0                     # доля размера: 1 — обычный, sleepmode.SLEEP_SCALE — во сне
        self.rest_pos = None                  # где Mico стоял до сна — туда вернётся
        self.last_attention = time.time()     # когда к нему обращались в последний раз
        self.can_sleep = lambda: True         # main подставит: нет ли открытого разговора
        self.apply_config()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(8)                   # ~120 кадров в секунду (реально зависит от системы)
        self._click_timer = QTimer(self)      # одинарный щелчок ждёт паузы: вдруг это двойной
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.clicked.emit)

    # ---------- API ----------
    def apply_config(self):
        s = self._size_px()
        self.setFixedSize(s, s)
        self.setWindowOpacity(self.cfg["opacity"])
        self.update()

    def _size_px(self):
        return max(1, int(240 * self.cfg["scale"] * self.size_k))

    def touch(self):
        """К Mico обратились: отсчёт до сна начинается заново."""
        self.last_attention = time.time()

    def _sleep_limit(self):
        return sleepmode.limit_seconds(self.cfg.get("sleep_after_min", sleepmode.DEFAULT_MINUTES))

    def sleep_now(self):
        """Засыпает: запоминает место, мрачнеет лицом, сообщает чату, что пора спрятаться."""
        if self.asleep:
            return
        self.rest_pos = QPoint(self.pos())
        self.asleep = True
        self.mood, self.mood_until = "sleepy", 0
        self.slept.emit()

    def wake(self, silent=False, moved=False):
        """Просыпается: возвращается на прежнее место (если его не перетащили), радуется и открывает чат."""
        if not self.asleep:
            return
        self.asleep = False
        self.touch()
        if not moved and self.rest_pos is not None and sleepmode.home_corner(False, self.cfg.get("placement"), None) is None:
            self.move(self.rest_pos)            # на прежнее место; если выбран угол — плавно доведёт до него _glide
        self.rest_pos = None
        self.set_mood("happy", 5)
        self.jump(260)
        self.squash_v += 0.8
        if not silent:
            self.woke.emit()

    def set_mood(self, mood, secs=None):
        self.mood = mood if mood in MOODS else "idle"
        if self.mood == "proud":                           # гордится: чуть выпрямляется и подпрыгивает
            self.jump(140)
        self.mood_until = time.time() + secs if secs else 0
        self.last_input = time.time()

    def jump(self, power=280):
        self.jv = power

    def set_look(self, global_point):
        """Куда смотреть (глобальные координаты), например на строку ввода."""
        self.look_at = global_point

    def _glide(self, now):
        """Плавно едет в свой угол (во сне — угол для сна, иначе — выбранное положение). Возвращает наклон (lean)."""
        dt = min(0.05, max(0.001, now - self._last_glide))
        self._last_glide = now
        if self.drag is not None or abs(self.x() - self._fx) > 3 or abs(self.y() - self._fy) > 3:
            self._fx, self._fy = float(self.x()), float(self.y())      # перетащили или сдвинули сами
        corner = sleepmode.home_corner(self.asleep, self.cfg.get("placement"), self.cfg.get("sleep_corner"))
        if corner is None or self.drag is not None:      # стоит, где поставил, или его сейчас тащат
            return 0.0
        target = QPoint(*sleepmode.corner_spot(self._screen_avail(), self.width(), corner))
        dx, dy = target.x() - self._fx, target.y() - self._fy
        if abs(dx) < 0.5 and abs(dy) < 0.5:
            return 0.0
        k = 1 - math.exp(-dt * 6.0)                 # одинаково плавно на любом FPS
        self._fx += dx * k
        self._fy += dy * k
        nx, ny = round(self._fx), round(self._fy)
        lean = max(-6.0, min(6.0, dx * k * 0.6))
        if (nx, ny) != (self.x(), self.y()):
            self.move(nx, ny)
            self.last_input = now
        return lean

    def notify_typing(self):
        self.typing_until = time.time() + 1.5
        self.last_input = time.time()
        self.touch()

    def start_anim(self, name):
        dur = {"lookaround": 2.6, "blink2": 0.6, "wink": 0.9, "spin": 2.2}[name]   # все имена — из этой таблицы
        self.anim = (name, time.time(), dur)

    def anim_u(self):
        if not self.anim:
            return None
        return min(1.0, (time.time() - self.anim[1]) / self.anim[2])

    def _screen_avail(self):
        scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        return (g.left(), g.top(), g.right() + 1, g.bottom() + 1)

    def effective_mood(self):
        if self.mood == "idle" and time.time() - self.last_input > 120:
            return "sleepy"
        return self.mood

    # ---------- физика и таймеры ----------
    def tick(self):
        now = time.time()
        dt = min(0.05, max(0.001, now - getattr(self, "_last_tick", now - 0.016)))   # реальное время кадра
        self._last_tick = now
        if self.mood_until and now > self.mood_until:
            self.mood, self.mood_until = "idle", 0
        target_k = sleepmode.SLEEP_SCALE if self.asleep else 1.0
        self.size_k = sleepmode.ease(self.size_k, target_k, dt)
        if self._size_px() != self.width():
            self.setFixedSize(self._size_px(), self._size_px())
        if (not self.asleep and self.drag is None and self._sleep_limit()
                and sleepmode.should_sleep(now, self.last_attention, self._sleep_limit(), not self.can_sleep())):
            self.sleep_now()
        cur = QCursor.pos()
        if cur != self.last_cursor:
            self.last_cursor, self.last_input = cur, now
        if now > self.blink_at:
            self.blink_until, self.blink_at = now + 0.12, now + random.uniform(3, 6)
        if self.anim and now > self.anim[1] + self.anim[2]:
            self.anim = None
        if (not self.anim and self.effective_mood() == "idle" and now > self.next_idle and not self.talking
                and self.drag is None and now > self.typing_until):
            self.start_anim(random.choice(["lookaround", "blink2", "wink"]))   # простой: без прыжков и без сердечка — они только в ответ на события
            self.next_idle = now + random.uniform(8, 16)
        if self.jh > 0 or self.jv != 0:
            self.jv -= 900 * dt
            self.jh += self.jv * dt
            if self.jh <= 0 and self.jv < 0:
                if self.jv < -120:
                    self.squash_v += 0.6
                self.jh = self.jv = 0.0
        want_heart = self.mood == "love"          # сердечко — только при настроении «love»
        self.heart += ((1.0 if want_heart else 0.0) - self.heart) * 0.15
        lean_goal = self._glide(now)
        self.lean += (lean_goal - self.lean) * 0.2
        self.tilt += (TILT.get(self.effective_mood(), 0) + self.lean - self.tilt) * 0.15
        if self.drag is None and (abs(self.vx) > 0.3 or abs(self.vy) > 0.3):
            scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
            g, m = scr.availableGeometry(), int(self.width() * 0.15)
            nx, ny = self.x() + self.vx, self.y() + self.vy
            if nx < g.left() - m or nx > g.right() - self.width() + m:
                self.vx, self.squash_v = -self.vx * 0.6, self.squash_v + 0.6
                nx = max(g.left() - m, min(nx, g.right() - self.width() + m))
            if ny < g.top() - m or ny > g.bottom() - self.height() + m:
                self.vy, self.squash_v = -self.vy * 0.6, self.squash_v + 0.6
                ny = max(g.top() - m, min(ny, g.bottom() - self.height() + m))
            self.move(int(nx), int(ny))
            self.vx *= 0.9 ** (dt / 0.033)
            self.vy *= 0.9 ** (dt / 0.033)
        self.squash_v += (-60 * self.squash - 8 * self.squash_v) * dt
        self.squash += self.squash_v * dt
        self.update()

    def moveEvent(self, e):
        self.moved.emit()
        super().moveEvent(e)

    # ---------- мышь ----------
    def mousePressEvent(self, e):
        self.touch()
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag, self.moved_px, self.vx, self.vy = True, 0, 0, 0
            self.last_move, self.dvx, self.dvy = (e.globalPosition(), time.time()), 0, 0
        elif e.button() == Qt.MouseButton.RightButton:
            self.menu_requested.emit(e.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, e):
        """Двойной щелчок левой кнопкой — открывает настройки. Одинарный чат уже не откроет."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.drag = None
            self.settings_requested.emit()

    def mouseMoveEvent(self, e):
        if self.drag is None:
            return
        g, now = e.globalPosition(), time.time()
        d, dt = g - self.last_move[0], max(now - self.last_move[1], 1e-3)
        self.move(self.pos() + QPoint(int(d.x()), int(d.y())))
        self.moved_px += abs(d.x()) + abs(d.y())
        self.dvx, self.dvy = d.x() / dt / 30, d.y() / dt / 30
        self.last_move = (g, now)
        self.last_input = now

    def mouseReleaseEvent(self, e):
        if self.drag is None:
            return
        self.drag = None
        if self.asleep:                           # спящего тронули: просыпается, без лишнего клика
            self.wake(moved=self.moved_px >= 5)
            return
        if self.moved_px < 5:
            self.set_mood("happy", 1.5)
            self.squash_v += 1.0
            self._click_timer.start(QGuiApplication.styleHints().mouseDoubleClickInterval())
        if self.moved_px >= 5 and time.time() - self.last_move[1] < 0.1:
            self.vx, self.vy = max(-40, min(40, self.dvx)), max(-40, min(40, self.dvy))

    # ---------- рисование ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = time.time() - self.t0
        cx, R = w / 2, w * 0.28
        cy0 = h * 0.54
        cy = cy0 - self.jh
        mood, u = self.effective_mood(), self.anim_u()
        anim = self.anim[0] if self.anim else None
        if anim == "wink":
            mood = "curious"
        speed = 0.6 if mood == "sleepy" else 1.0
        breath = 1 + 0.03 * math.sin(t * 1.6 * speed)
        sx, sy = breath * (1 + self.squash), breath * (1 - self.squash)
        if mood == "proud":                                # грудь колесом: чуть выше и уже
            sx, sy = sx * 0.97, sy * 1.05
        wob = 2.5 if mood == "thinking" else 1.0
        spin_c, spin_s, spin_turn = 1.0, 0.0, 0.0               # без вращения, кроме анимации «spin» (радость)
        if anim == "spin" and u is not None:
            spin_turn = 360 * u                                 # тело делает оборот вокруг себя
            spin_c = abs(math.cos(math.pi * 2 * u))            # лицо на миг «поворачивается боком»
        shake = math.sin(t * 28) * 3 if mood == "laugh" else math.sin(t * 40) * 1.2 if mood == "scared" else 0
        col = QColor(self.cfg["color"])

        p.setPen(Qt.PenStyle.NoPen)                              # мягкая тень
        p.setBrush(QColor(120, 70, 40, max(8, int(34 - self.jh * 0.4))))
        p.drawEllipse(QPointF(cx, cy0 + R * 1.18), R * 0.85 * sx * (1 - self.jh / 300), R * 0.13)

        p.save()
        p.translate(cx, cy)
        p.rotate(self.tilt + shake + spin_turn)
        p.translate(-cx, -cy)
        path = QPainterPath()
        for i in range(N):
            a = 2 * math.pi * i / N
            r = pebble(a, wob, t)
            bx, by = math.cos(a) * r * 1.05, math.sin(a) * r * 0.98
            if self.heart > 0.001:
                hx, hy = HEART_PTS[i]
                bx += (hx * 1.42 - bx) * self.heart        # сердце крупнее и шире: как на референсе
                by += (hy * 1.30 - by) * self.heart
            x, y = cx + bx * R * sx, cy + by * R * sy
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        path.closeSubpath()
        # тело: кремово-персиковый градиент с розовым свечением по краю
        pink = QColor(255, 160, 150)
        g = QRadialGradient(QPointF(cx - R * 0.15, cy - R * 0.2), R * 1.3)
        g.setColorAt(0, mix(col, QColor(255, 250, 240), 0.35))
        g.setColorAt(0.55, col)
        g.setColorAt(0.85, mix(col, pink, 0.35))
        g.setColorAt(1, mix(col, pink, 0.6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        sheen = QRadialGradient(QPointF(cx - R * 0.45, cy - R * 0.6), R * 0.6)   # блик
        sheen.setColorAt(0, QColor(255, 255, 255, 130))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(sheen)
        p.drawRect(self.rect())
        irid = QRadialGradient(QPointF(cx + R * 0.85, cy + R * 0.6), R * 0.65)    # перламутр
        irid.setColorAt(0, QColor(170, 240, 220, 80))
        irid.setColorAt(1, QColor(170, 240, 220, 0))
        p.setBrush(irid)
        p.drawRect(self.rect())
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 95), R * 0.08))                       # светящийся край
        p.drawPath(path)
        p.restore()
        # лицо: маленькое, смещено вверх-влево (при вращении — «боком»)
        fx = cx - R * 0.12 * (1 - self.heart)
        fy = cy - R * 0.16 * (1 - self.heart) - R * 0.04 * self.heart
        if spin_c > 0.02:
            p.save()
            p.translate(fx + spin_s * R * 0.75, fy)
            p.scale(spin_c, 1)
            p.translate(-fx, -fy)
            self._face(p, fx, fy, R, col, mood, t, u, anim)
            p.restore()
        p.restore()
        self._overlays(p, cx, cy, R, mood, t)

    def _look(self, fx, fy, R, mood, u, anim):
        if time.time() < self.typing_until:
            if self.look_at is not None:                      # смотрит на строку ввода, что там пишут
                v = QPointF(self.mapFromGlobal(self.look_at)) - QPointF(fx, fy)
                d = math.hypot(v.x(), v.y()) or 1
                k = min(d / 200, 1) * R * 0.06 / d
                return QPointF(v.x() * k, v.y() * k)
            return QPointF(0, R * 0.07)
        if mood == "thinking":
            return QPointF(R * 0.04 * math.sin(time.time() * 2), -R * 0.05)
        if anim == "lookaround":
            return QPointF(math.sin(u * 2 * math.pi * 1.5) * R * 0.05, 0)
        if mood == "curious":
            return QPointF(R * 0.03, -R * 0.01)
        v = QPointF(self.mapFromGlobal(QCursor.pos())) - QPointF(fx, fy)
        d = math.hypot(v.x(), v.y()) or 1
        k = min(d / 200, 1) * R * 0.045 / d
        return QPointF(v.x() * k, v.y() * k)

    def _face(self, p, fx, fy, R, col, mood, t, u, anim):
        dark = col.lightness() > 110
        ink = QColor("#2a1d1d") if dark else QColor("#ffffff")
        pupil = ink
        shine = QColor(255, 255, 255) if dark else QColor(40, 30, 20)
        nopen = Qt.PenStyle.NoPen
        pen = QPen(ink, max(1.6, R * 0.03))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        typing = time.time() < self.typing_until
        look = self._look(fx, fy, R, mood, u, anim)
        blink = time.time() < self.blink_until or (anim == "blink2" and (u < 0.25 or 0.4 < u < 0.65))

        p.setPen(nopen)                                       # румянец
        p.setBrush(QColor(255, 120, 120, 160 if mood in ("shy", "proud") else 105 if mood in ("happy", "love", "laugh", "excited") else 55))
        for s in (-1, 1):
            p.drawEllipse(QPointF(fx + s * R * 0.52, fy + R * 0.22), R * 0.12, R * 0.075)

        for s in (-1, 1):
            ex, ey = fx + s * R * 0.38 + look.x(), fy + look.y() + (R * 0.05 if mood == "shy" else 0) \
                - (R * 0.02 if mood == "confused" and s == 1 else 0)
            ew, eh = R * 0.075, R * 0.105
            squint = mood == "curious" and s == -1
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            if mood == "sleepy" or blink or (mood == "playful" and s == 1):      # подмигивание — правый глаз
                p.drawLine(QPointF(ex - ew, ey), QPointF(ex + ew, ey))
            elif mood in ("happy", "laugh", "love", "proud", "playful"):
                p.drawArc(QRectF(ex - ew * 1.15, ey - eh * 0.5, ew * 2.3, eh * 1.5), 0, 180 * 16)
            elif squint:                                      # прищуренный глаз
                p.setBrush(pupil)
                p.setPen(nopen)
                p.drawEllipse(QPointF(ex, ey + eh * 0.2), ew * 1.05, eh * 0.4)
            else:
                big = 1.35 if mood == "surprised" else 1.3 if mood == "scared" else 1.15 if mood == "excited" else 1.0
                sq = 0.75 if (typing or mood == "angry") else 1.0
                p.setBrush(pupil)
                p.setPen(nopen)
                p.drawEllipse(QPointF(ex, ey), ew * big, eh * big * sq)
                p.setBrush(shine)
                p.drawEllipse(QPointF(ex + ew * 0.3, ey - eh * 0.3 * sq), ew * 0.32 * big, ew * 0.32 * big)
                if mood == "sad" and s == 1:                  # слезинка
                    f = (t * 0.8) % 1
                    p.setBrush(QColor(120, 180, 255, int(200 * (1 - f))))
                    p.drawEllipse(QPointF(ex + ew * 0.4, ey + eh * 1.3 + f * R * 0.3), ew * 0.4, ew * 0.55)
            # бровки — маленькие дужки
            by = ey - R * 0.2 - look.y() * 0.5
            so, si, curve = R * 0.01, -R * 0.005, R * 0.045
            if mood == "sad":
                so, si, curve = R * 0.03, -R * 0.05, R * 0.012
            elif mood == "worried":
                so, si, curve = R * 0.04, -R * 0.07, R * 0.01
            elif mood == "surprised":
                by -= R * 0.05
                curve = R * 0.06
            elif mood == "scared":
                by -= R * 0.07
                curve = R * 0.06
            elif mood == "excited":
                by -= R * 0.05
                curve = R * 0.06
            elif mood == "angry":
                so, si, curve = -R * 0.02, R * 0.05, R * 0.01
            elif mood == "shy":
                by += R * 0.02
                curve = R * 0.02
            elif mood == "confused" and s == 1:
                by -= R * 0.07
            elif mood in ("thinking", "curious"):
                if s == 1:
                    by -= R * 0.06
                elif squint:
                    by += R * 0.03
                    curve = R * 0.01
            bl = R * 0.09
            br = QPainterPath()
            br.moveTo(ex + s * bl, by + so)
            br.quadTo(ex, by - curve, ex - s * bl, by + si)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, max(1.4, R * 0.024), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(br)

        # крошечный рот
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        my = fy + R * 0.22
        if self.talking and self.heart < 0.5 and mood in ("idle", "happy", "curious", "love"):   # у сердца всегда улыбка
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawEllipse(QPointF(fx, my + R * 0.04), R * 0.06, R * (0.02 + 0.05 * abs(math.sin(t * 12))))
        elif mood in ("happy", "love", "proud", "playful"):
            p.drawArc(QRectF(fx - R * 0.17, my - R * 0.07, R * 0.34, R * 0.20), 200 * 16, 140 * 16)
        elif mood == "laugh":
            big = 1.0 + 0.2 * math.sin(t * 18)
            p.setPen(nopen)
            p.setBrush(ink)
            p.drawChord(QRectF(fx - R * 0.13 * big, my - R * 0.03, R * 0.26 * big, R * 0.2 * big), 180 * 16, 180 * 16)
        elif mood in ("sad", "worried"):
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawEllipse(QPointF(fx, my + R * 0.05), R * 0.03, R * 0.04)
        elif mood == "scared":                                  # испуг: дрожащая линия
            zz = QPainterPath()
            for i in range(6):
                zx = fx - R * 0.1 + i * R * 0.04
                zy = my + R * 0.05 + (R * 0.018 if i % 2 else -R * 0.018)
                zz.moveTo(zx, zy) if i == 0 else zz.lineTo(zx, zy)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(zz)
        elif mood == "angry":                                   # злость: сжатый рот, уголки вниз
            fr = QPainterPath()
            fr.moveTo(fx - R * 0.1, my + R * 0.02)
            fr.quadTo(fx, my + R * 0.1, fx + R * 0.1, my + R * 0.02)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(fr)
        elif mood == "shy":                                     # смущение: маленькая улыбка
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(fx - R * 0.06, my - R * 0.02, R * 0.12, R * 0.08), 200 * 16, 140 * 16)
        elif mood == "confused":                                # растерянность: волнистая линия
            cf = QPainterPath()
            for i in range(9):
                cx2 = fx - R * 0.1 + i * R * 0.025
                cy2 = my + R * 0.04 + math.sin(i * 1.4) * R * 0.012
                cf.moveTo(cx2, cy2) if i == 0 else cf.lineTo(cx2, cy2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(cf)
        elif mood == "excited":                                 # восторг: широкая улыбка
            p.setPen(nopen)
            p.setBrush(ink)
            p.drawChord(QRectF(fx - R * 0.14, my - R * 0.03, R * 0.28, R * 0.2), 180 * 16, 180 * 16)
        elif mood == "surprised":
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawEllipse(QPointF(fx, my + R * 0.05), R * 0.04, R * 0.058)
        elif mood in ("curious", "thinking"):
            p.drawLine(QPointF(fx - R * 0.05, my + R * 0.05), QPointF(fx + R * 0.09, my + R * 0.03))
        elif mood == "sleepy":
            r = R * (0.03 + 0.012 * math.sin(t * 1.2))
            p.drawEllipse(QPointF(fx, my + R * 0.05), r, r * 1.2)
        else:
            p.drawArc(QRectF(fx - R * 0.1, my - R * 0.04, R * 0.2, R * 0.12), 210 * 16, 120 * 16)

    def _font(self, family, size, bold=False):
        key = (family, size, bold)
        font = self._fonts.get(key)
        if font is None:
            font = QFont(family, size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
            self._fonts[key] = font
        return font

    def _overlays(self, p, cx, cy, R, mood, t):
        p.setPen(Qt.PenStyle.NoPen)
        if mood == "thinking":                                 # три прыгающие точки «думаю…» — внутри тела,
            for i in range(3):                                 # чтобы не перекрывать чат над Mico
                bounce = max(0, math.sin(t * 6 - i * 0.9)) * R * 0.08
                p.setBrush(QColor(90, 90, 90, 200))
                p.drawEllipse(QPointF(cx + R * 0.22 + i * R * 0.2, cy + R * 0.42 - bounce), R * 0.06, R * 0.06)
        elif mood == "sleepy":
            p.setPen(QColor(110, 110, 140, 200))
            for k in range(3):
                ph = ((t * 0.4) + k / 3) % 1
                p.setFont(QFont("Segoe UI", max(6, int(R * (0.14 + 0.1 * ph))), QFont.Weight.Bold))
                p.drawText(QPointF(cx + R * 0.6 + ph * R * 0.4, cy - R * 0.7 - ph * R * 0.7), "z")
        elif mood == "surprised":
            p.setPen(QColor(230, 90, 60))
            p.setFont(QFont("Segoe UI", max(8, int(R * 0.45)), QFont.Weight.Bold))
            p.drawText(QPointF(cx - R * 0.12, cy - R * 1.0), "!")
        if mood == "proud":                                 # гордость: искорки вокруг головы
            p.setFont(self._font("Segoe UI Symbol", max(8, int(R * 0.22))))
            for k in range(3):
                ph = (t * 0.7 + k / 3) % 1
                ang = -math.pi * 0.15 - k * 0.55
                rad = R * (1.05 + 0.15 * ph)
                p.setPen(QColor(255, 205, 90, int(255 * math.sin(ph * math.pi))))
                p.drawText(QPointF(cx + math.cos(ang) * rad, cy - R * 0.2 + math.sin(ang) * rad), "✦")
