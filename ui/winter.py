"""Зимнее оформление Mico AI: плавный снег, сугробы, ёлки и снеговик в настройках и чате, снежные значки разделов.
Всё рисуется кодом, без картинок. Включается в «Настройки → Зима» (winter_ui); зимний колпак Mico (winter_mico) рисует blob.py.
Все слои прозрачны для мыши: нажатия проходят к кнопкам под ними."""
import math
import random
import time
import weakref

from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget

from ui import motion

_LAYERS = []                                           # живые слои: weakref, чтобы переключатель обновлял всех сразу


def enabled(cfg):
    return bool(cfg.get("winter_ui")) if cfg is not None else False


def refresh_all():
    """Показывает или прячет все слои по текущим настройкам (вызывается переключателем)."""
    for ref in list(_LAYERS):
        w = ref()
        if w is None:
            _LAYERS.remove(ref)
            continue
        try:
            w.sync()
        except RuntimeError:
            _LAYERS.remove(ref)


def _static_pixmap(widget, draw):
    """Неподвижную часть оформления рисуем один раз в картинку нужного размера и потом только показываем её."""
    dpr = max(1.0, float(widget.devicePixelRatioF()))
    w, h = max(1, widget.width()), max(1, widget.height())
    pm = QPixmap(int(w * dpr), int(h * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw(p, w, h)
    p.end()
    return pm


class _Layer(QWidget):
    """Общая основа: прозрачный слой на всю площадь родителя, сам следит за его размером и показом."""

    def __init__(self, parent, cfg, radius=0):
        super().__init__(parent)
        self.cfg, self.radius = cfg, radius
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        parent.installEventFilter(self)
        _LAYERS.append(weakref.ref(self))
        self.setGeometry(parent.rect())
        self.hide()
        QTimer.singleShot(0, self.sync)

    def eventFilter(self, obj, ev):
        if obj is self.parent():
            kind = ev.type().name if hasattr(ev.type(), "name") else str(ev.type())
            if kind in ("Resize", "Show", "LayoutRequest", "Move"):
                self.setGeometry(self.parent().rect())
                if self.isVisible():
                    self.raise_()
                if kind == "Show":
                    QTimer.singleShot(0, self.sync)
            elif kind == "Hide":
                self._stop()
        return False

    def sync(self):
        on = enabled(self.cfg) and self.parent() is not None and self.parent().isVisible()
        if on:
            self.setGeometry(self.parent().rect())
            self.show()
            self.raise_()
            self._start()
        else:
            self.hide()
            self._stop()

    def _start(self):
        pass

    def _stop(self):
        pass

    def _clip(self, p):
        if self.radius:
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
            p.setClipPath(path)


class SnowOverlay(_Layer):
    """Плавно падающий снег. Хлопья разного размера, качаются из стороны в сторону, крупные падают быстрее и ярче.
    Снежинки рисуются из готовых картинок, а перерисовываются только области вокруг них, не всё окно.
    Пока идёт анимация карточки или смена раздела, снег стоит на месте."""

    def __init__(self, parent, cfg, radius=0, scene=False):
        super().__init__(parent, cfg, radius)
        self.scene = scene                              # рисовать ли ещё сугробы по нижнему краю
        self.flakes = []
        self._sprites = {}
        self._static = None                             # сугробы, нарисованные заранее
        self._static_key = None
        self._last = time.monotonic()
        self._t0 = self._last
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.setTimerType(Qt.TimerType.CoarseTimer)
        self._timer.timeout.connect(self._step)

    def _start(self):
        if not self._timer.isActive():
            self._last = time.monotonic()
            self._timer.start()

    def _stop(self):
        self._timer.stop()

    def _fill(self):
        w, h = max(1, self.width()), max(1, self.height())
        n = int(max(22, min(80, w * h / 7500)))
        rnd = random.Random()
        while len(self.flakes) < n:
            self.flakes.append(self._new(w, h, rnd, True))
        del self.flakes[n:]

    @staticmethod
    def _new(w, h, rnd, anywhere):
        depth = rnd.random()                            # 0: далёкая мелкая, 1: близкая крупная
        return {"x": rnd.uniform(0, w), "y": rnd.uniform(-h * 0.1, h) if anywhere else rnd.uniform(-30, -4),
                "r": round((1.1 + 2.6 * depth) * 2) / 2, "v": 16 + 38 * depth, "ph": rnd.uniform(0, 6.28),
                "sw": 6 + 16 * rnd.random(), "a": 110 + int(120 * depth) // 16 * 16}   # размер и яркость по ступеням: мало разных картинок

    def _sprite(self, r, a):
        """Готовая картинка снежинки с лёгким ореолом: рисуем один раз для каждой пары размер/яркость."""
        key = (r, a)
        pm = self._sprites.get(key)
        if pm is None:
            dpr = max(1.0, float(self.devicePixelRatioF()))
            side = int(r * 1.9 * 2) + 3
            pm = QPixmap(int(side * dpr), int(side * dpr))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            c = QPointF(side / 2.0, side / 2.0)
            p.setBrush(QColor(255, 255, 255, int(a * 0.22)))
            p.drawEllipse(c, r * 1.9, r * 1.9)
            p.setBrush(QColor(255, 255, 255, a))
            p.drawEllipse(c, r, r)
            p.end()
            self._sprites[key] = pm
        return pm

    @staticmethod
    def _rect(f):
        half = int(f["r"] * 1.9) + 2
        return QRect(int(f["x"]) - half, int(f["y"]) - half, half * 2 + 2, half * 2 + 2)

    def _step(self):
        now = time.monotonic()
        dt = min(0.08, now - self._last)
        self._last = now
        if not self.isVisible() or motion.busy():       # карточка или раздел двигаются: снег ждёт, чтобы не мешать
            return
        self._fill()
        w, h = self.width(), self.height()
        rnd = random
        t = now - self._t0
        for f in self.flakes:
            old = self._rect(f)
            f["y"] += f["v"] * dt
            f["x"] += math.sin(t * 0.8 + f["ph"]) * f["sw"] * dt
            if f["y"] > h + 6:
                f.update(self._new(w, h, rnd, False))
            elif f["x"] < -8:
                f["x"] = w + 6
            elif f["x"] > w + 8:
                f["x"] = -6
            self.update(old)                            # перерисовываем только старое и новое место снежинки
            self.update(self._rect(f))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._clip(p)
        dirty = ev.rect()
        if self.scene:
            key = (self.width(), self.height(), self.devicePixelRatioF())
            if self._static is None or self._static_key != key:
                self._static = _static_pixmap(self, lambda q, w, h: paint_drifts(q, QRectF(0, 0, w, h), 0.0, height=26))
                self._static_key = key
            p.drawPixmap(0, 0, self._static)
        for f in self.flakes:
            if not self._rect(f).intersects(dirty):
                continue
            pm = self._sprite(f["r"], f["a"])
            half = pm.width() / pm.devicePixelRatio() / 2.0
            p.drawPixmap(QPointF(f["x"] - half, f["y"] - half), pm)
        p.end()


class WinterScene(_Layer):
    """Сцена внизу бокового меню настроек: сугроб, две ёлки и снеговик. Рисуется под пунктами меню, сколько там места.
    Мороз и сугробы нарисованы заранее; на каждом кадре перерисовывается только область ёлок и снеговика."""

    def __init__(self, parent, cfg, top_fn=None):
        super().__init__(parent, cfg)
        self.top_fn = top_fn                            # где кончаются пункты меню: ниже можно рисовать сцену
        self._t0 = time.monotonic()
        self._static = None
        self._static_key = None
        self._timer = QTimer(self)
        self._timer.setInterval(66)                     # гирлянды и снеговик: 15 кадров в секунду достаточно
        self._timer.timeout.connect(self._tick)

    def _start(self):
        if not self._timer.isActive():
            self._timer.start()

    def _stop(self):
        self._timer.stop()

    def _top(self):
        try:
            return int(self.top_fn()) if self.top_fn else 0
        except Exception:
            return 0

    def _tick(self):
        if motion.busy():
            return
        w, h = self.width(), self.height()
        free = h - self._top()
        if free < 60:
            return                                      # деревьев нет: перерисовывать нечего
        zone = min(free, 200) + 12
        self.update(QRect(0, max(0, h - zone), w, zone))

    @staticmethod
    def _draw_static(p, w, h):
        g = QLinearGradient(0, 0, 0, 60)                # мороз по верхнему краю: лёгкая голубая дымка
        g.setColorAt(0, QColor(170, 215, 255, 46))
        g.setColorAt(1, QColor(170, 215, 255, 0))
        p.fillRect(QRectF(0, 0, w, 60), QBrush(g))
        paint_drifts(p, QRectF(0, h - 70, w, 70), 0.0, height=34)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        key = (w, h, self.devicePixelRatioF())
        if self._static is None or self._static_key != key:
            self._static = _static_pixmap(self, self._draw_static)
            self._static_key = key
        p.drawPixmap(0, 0, self._static)
        t = time.monotonic() - self._t0
        free = h - self._top()
        if free >= 120:
            base = h - 22
            size = min(1.0, free / 190.0)
            draw_tree(p, w * 0.22, base, 96 * size, t, 1)
            draw_tree(p, w * 0.50, base + 4, 66 * size, t, 2)
            draw_snowman(p, w * 0.80, base, 26 * size, t)
        elif free >= 60:
            draw_tree(p, w * 0.30, h - 20, 54, t, 1)
            draw_snowman(p, w * 0.72, h - 20, 15, t)
        p.end()


class FestiveLayer(_Layer):
    """Праздничные украшения окна: мигающая гирлянда по верхнему краю, сосульки и (по желанию) подарки с конфетной тростью внизу.
    Провод гирлянды, сосульки и подарки нарисованы заранее; на каждом кадре перерисовывается только полоска с лампочками."""

    STRIP = 46                                           # высота полоски гирлянды

    def __init__(self, parent, cfg, radius=0, gifts_x=None):
        super().__init__(parent, cfg, radius)
        self.gifts_x = gifts_x                           # слева направо: где ставить подарки; None: без подарков
        self._t0 = time.monotonic()
        self._static = None
        self._static_key = None
        self._timer = QTimer(self)
        self._timer.setInterval(66)
        self._timer.timeout.connect(self._tick)

    def _start(self):
        if not self._timer.isActive():
            self._timer.start()

    def _stop(self):
        self._timer.stop()

    def _tick(self):
        if not motion.busy():
            self.update(QRect(0, 0, self.width(), self.STRIP))

    def _draw_static(self, p, w, h):
        draw_icicles(p, w)
        draw_garland(p, w, 0.0, part="wire")
        if self.gifts_x is not None and h > 260:
            draw_gifts(p, self.gifts_x, h - 12, 0.0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._clip(p)
        w, h = self.width(), self.height()
        key = (w, h, self.gifts_x, self.devicePixelRatioF())
        if self._static is None or self._static_key != key:
            self._static = _static_pixmap(self, self._draw_static)
            self._static_key = key
        p.drawPixmap(0, 0, self._static)
        draw_garland(p, w, time.monotonic() - self._t0, part="bulbs")
        p.end()


def install(widget, cfg, radius=0, scene=False, festive=False, gifts_x=None):
    """Вешает на окно зимние слои: украшения (по желанию) и поверх них снег. Возвращает слой снега (все слои держатся за родителем)."""
    if festive:
        FestiveLayer(widget, cfg, radius=radius, gifts_x=gifts_x)
    layer = SnowOverlay(widget, cfg, radius=radius, scene=scene)
    return layer


# ---------- рисование ----------
def paint_drifts(p, rect, t, height=30):
    """Два слоя сугробов вдоль нижнего края rect: дальний голубоватый и ближний белый, края плавно колышутся."""
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    for layer, (col, amp, lift) in enumerate(((QColor(205, 224, 245, 215), 0.55, 0.0), (QColor(255, 255, 255, 245), 0.4, -9.0))):
        path = QPainterPath()
        x0, x1, base = rect.left(), rect.right(), rect.bottom()
        path.moveTo(x0, base)
        n = 24
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = base - height * (0.62 + amp * 0.3 * math.sin(i * 0.55 + layer * 1.7 + t * 0.15)) + lift
            path.lineTo(x, y)
        path.lineTo(x1, base)
        path.closeSubpath()
        g = QLinearGradient(0, base - height, 0, base)
        g.setColorAt(0, col)
        g.setColorAt(1, QColor(col.red() - 12, col.green() - 8, min(255, col.blue()), col.alpha()))
        p.setBrush(QBrush(g))
        p.drawPath(path)
    p.restore()


def draw_tree(p, x, base, h, t, seed=1):
    """Ёлка: ствол, три яруса с шапками снега, звезда и мигающая гирлянда."""
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    w = h * 0.62
    p.setBrush(QColor(110, 74, 48))
    p.drawRoundedRect(QRectF(x - w * 0.07, base - h * 0.1, w * 0.14, h * 0.12), 2, 2)
    tiers = ((0.10, 0.92, 0.50), (0.34, 0.70, 0.40), (0.56, 0.48, 0.30))
    lights = []
    for i, (y0, wf, hf) in enumerate(tiers):
        top = base - h * (y0 + hf) - h * 0.04
        bot = base - h * y0
        half = w * wf / 2
        g = QLinearGradient(x - half, bot, x + half, top)
        g.setColorAt(0, QColor(28, 104, 70))
        g.setColorAt(1, QColor(54, 148, 96))
        p.setBrush(QBrush(g))
        path = QPainterPath()
        path.moveTo(x, top)
        path.lineTo(x + half, bot)
        path.quadTo(x, bot + h * 0.04, x - half, bot)
        path.closeSubpath()
        p.drawPath(path)
        cap = QPainterPath()                            # снег лежит шапкой на ярусе
        cap.moveTo(x, top)
        cap.lineTo(x + half * 0.55, top + (bot - top) * 0.52)
        for k in range(4):
            xx = x + half * (0.55 - 0.275 * (k + 1) * 2 / 2)
            cap.quadTo(xx + half * 0.12, top + (bot - top) * (0.66 if k % 2 else 0.5), xx, top + (bot - top) * 0.52)
        cap.lineTo(x - half * 0.55, top + (bot - top) * 0.52)
        cap.closeSubpath()
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawPath(cap)
        for k in range(3):
            lights.append((x + (k - 1) * half * 0.46, bot - (bot - top) * 0.2 - ((k + i) % 2) * 3))
    cols = ((255, 90, 90), (255, 214, 90), (110, 190, 255), (255, 140, 220))
    for j, (lx, ly) in enumerate(lights):
        a = 0.5 + 0.5 * math.sin(t * 2.4 + j * 1.3 + seed)
        c = cols[(j + seed) % len(cols)]
        p.setBrush(QColor(c[0], c[1], c[2], int(60 + 170 * a)))
        p.drawEllipse(QPointF(lx, ly), 2.6, 2.6)
    star = QPainterPath()
    cx, cy, r = x, base - h * 0.97 - 3, h * 0.07
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pt = QPointF(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr)
        star.moveTo(pt) if i == 0 else star.lineTo(pt)
    star.closeSubpath()
    p.setBrush(QColor(255, 214, 90, 235))
    p.drawPath(star)
    p.restore()


def draw_snowman(p, x, base, r, t):
    """Снеговик с шарфом, ведёрком-шапкой и морковкой. Голова чуть покачивается."""
    p.save()
    p.setPen(Qt.PenStyle.NoPen)

    def ball(cx, cy, rad):
        g = QRadialGradient(QPointF(cx - rad * 0.3, cy - rad * 0.35), rad * 1.3)
        g.setColorAt(0, QColor(255, 255, 255))
        g.setColorAt(0.7, QColor(232, 242, 252))
        g.setColorAt(1, QColor(190, 212, 238))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), rad, rad)
    sway = math.sin(t * 1.3) * r * 0.06
    r1, r2, r3 = r, r * 0.74, r * 0.54
    c1 = base - r1
    c2 = base - r1 * 2 + r2 * 0.28
    c3 = c2 - r2 - r3 * 0.62
    p.setPen(QPen(QColor(110, 74, 48), max(1.6, r * 0.09), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for s in (-1, 1):                                   # руки-веточки
        p.drawLine(QPointF(x + s * r2 * 0.85, c2 - r2 * 0.1), QPointF(x + s * r2 * 1.7, c2 - r2 * 0.75 + math.sin(t * 1.6 + s) * 2))
    p.setPen(Qt.PenStyle.NoPen)
    ball(x, c1, r1)
    ball(x, c2, r2)
    ball(x + sway, c3, r3)
    hx = x + sway
    p.setBrush(QColor(40, 40, 52))                      # глаза и пуговицы
    for s in (-1, 1):
        p.drawEllipse(QPointF(hx + s * r3 * 0.32, c3 - r3 * 0.14), r * 0.06, r * 0.06)
    for k in range(2):
        p.drawEllipse(QPointF(x, c2 + r2 * (0.0 + 0.38 * k)), r * 0.06, r * 0.06)
    nose = QPainterPath()
    nose.moveTo(hx, c3 + r3 * 0.02)
    nose.lineTo(hx + r3 * 0.95, c3 + r3 * 0.16)
    nose.lineTo(hx, c3 + r3 * 0.26)
    nose.closeSubpath()
    p.setBrush(QColor(255, 140, 50))
    p.drawPath(nose)
    p.setBrush(QColor(225, 62, 70))                     # шарф
    p.drawRoundedRect(QRectF(hx - r3 * 0.85, c3 + r3 * 0.62, r3 * 1.7, r3 * 0.36), r3 * 0.18, r3 * 0.18)
    p.drawRoundedRect(QRectF(hx + r3 * 0.3, c3 + r3 * 0.74, r3 * 0.34, r3 * 0.9), r3 * 0.12, r3 * 0.12)
    p.setBrush(QColor(60, 64, 82))                      # шапка-ведёрко
    p.drawRoundedRect(QRectF(hx - r3 * 0.62, c3 - r3 * 1.2, r3 * 1.24, r3 * 0.8), r3 * 0.12, r3 * 0.12)
    p.drawRoundedRect(QRectF(hx - r3 * 0.85, c3 - r3 * 0.5, r3 * 1.7, r3 * 0.16), r3 * 0.08, r3 * 0.08)
    p.restore()


BULBS = ((255, 82, 82), (255, 206, 84), (96, 214, 130), (96, 170, 255), (255, 140, 220))


def draw_garland(p, w, t, part=None):
    """Гирлянда: провисающий провод, цветные лампочки по очереди мигают и светятся.
    part: \"wire\" — только провод (его рисуют заранее), \"bulbs\" — только лампочки, None — всё."""
    p.save()
    step = 120.0
    n = max(2, int(w / step) + 1)
    sw = w / n
    wire = QPen(QColor(20, 70, 52, 230), 1.6)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(n):
        x0, x1 = i * sw, (i + 1) * sw
        if part != "bulbs":
            path = QPainterPath()
            path.moveTo(x0, 1)
            path.quadTo((x0 + x1) / 2, 30, x1, 1)
            p.setPen(wire)
            p.drawPath(path)
        if part == "wire":
            continue
        for k in range(1, 5):                             # лампочки вдоль провисания
            u = k / 5.0
            x = x0 + (x1 - x0) * u
            y = 1 + 2 * 14.5 * u * (1 - u) * 1.0 * 2 - 0.0
            col = BULBS[(i * 4 + k) % len(BULBS)]
            tw = 0.5 + 0.5 * math.sin(t * 2.6 + i * 1.7 + k * 0.9)
            glow = QRadialGradient(QPointF(x, y + 6), 13)
            glow.setColorAt(0, QColor(col[0], col[1], col[2], int(50 + 110 * tw)))
            glow.setColorAt(1, QColor(col[0], col[1], col[2], 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QPointF(x, y + 6), 13, 13)
            p.setBrush(QColor(40, 60, 52, 240))             # цоколь
            p.drawRoundedRect(QRectF(x - 2, y - 1, 4, 4), 1, 1)
            p.setBrush(QColor(col[0], col[1], col[2], int(150 + 105 * tw)))
            p.drawEllipse(QPointF(x, y + 5.5), 3.2, 4.4)
            p.setBrush(QColor(255, 255, 255, int(120 * tw)))
            p.drawEllipse(QPointF(x - 1, y + 4), 1.0, 1.4)
    p.restore()


def draw_icicles(p, w):
    """Сосульки по верхней кромке: разной длины, чуть голубоватые и прозрачные."""
    rnd = random.Random(11)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    x = 4.0
    while x < w - 4:
        wd = rnd.uniform(5, 9)
        ln = rnd.uniform(6, 20)
        g = QLinearGradient(0, 0, 0, ln)
        g.setColorAt(0, QColor(235, 247, 255, 200))
        g.setColorAt(1, QColor(170, 215, 250, 70))
        p.setBrush(QBrush(g))
        tri = QPainterPath()
        tri.moveTo(x, 0)
        tri.lineTo(x + wd, 0)
        tri.quadTo(x + wd * 0.55, ln * 0.55, x + wd * 0.5, ln)
        tri.quadTo(x + wd * 0.45, ln * 0.55, x, 0)
        p.drawPath(tri)
        x += wd + rnd.uniform(6, 22)
    p.restore()


def draw_gifts(p, x, base, t):
    """Стопка подарков с бантами, рядом конфетная трость и маленькая ёлочная игрушка."""
    p.save()
    p.setPen(Qt.PenStyle.NoPen)

    def box(bx, by, bw, bh, col, rib):
        g = QLinearGradient(bx, by, bx + bw, by + bh)
        g.setColorAt(0, QColor(*col))
        g.setColorAt(1, QColor(max(0, col[0] - 40), max(0, col[1] - 40), max(0, col[2] - 40)))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), 4, 4)
        p.setBrush(QColor(*rib))
        p.drawRect(QRectF(bx + bw / 2 - 2.5, by, 5, bh))
        p.drawRect(QRectF(bx, by + bh * 0.38, bw, 5))
        p.drawEllipse(QPointF(bx + bw / 2 - 5, by - 2), 5, 3.5)           # бант
        p.drawEllipse(QPointF(bx + bw / 2 + 5, by - 2), 5, 3.5)
        p.setBrush(QColor(rib[0] - 25, rib[1] - 25, rib[2] - 25))
        p.drawEllipse(QPointF(bx + bw / 2, by - 1), 2.4, 2.4)
    box(x, base - 30, 36, 30, (220, 60, 66), (255, 214, 120))
    box(x + 40, base - 22, 28, 22, (70, 150, 220), (255, 255, 255))
    box(x + 12, base - 54, 24, 24, (60, 160, 100), (255, 120, 140))
    # конфетная трость
    cx, cy = x + 82, base
    cane = QPainterPath()
    cane.moveTo(cx, cy)
    cane.lineTo(cx, cy - 40)
    cane.arcTo(QRectF(cx - 8, cy - 56, 16, 16), 0, 180)
    pen = QPen(QColor(255, 255, 255), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(pen)
    p.drawPath(cane)
    pen2 = QPen(QColor(226, 50, 60), 5.0, Qt.PenStyle.DashLine, Qt.PenCapStyle.FlatCap)
    pen2.setDashPattern([0.9, 1.9])
    p.setPen(pen2)
    p.drawPath(cane)
    p.restore()


# ---------- значки зимой: только цвет, без снега ----------
def snowy_icon(icon, size=18):
    """Значок раздела с снежной шапкой сверху: белая «шапка» поверх рисунка."""
    pm = icon.pixmap(size, size)
    if pm.isNull():
        return icon
    out = QPixmap(pm)
    q = QPainter(out)
    q.setRenderHint(QPainter.RenderHint.Antialiasing)
    q.setPen(Qt.PenStyle.NoPen)
    w = out.width()
    q.setBrush(QColor(255, 255, 255, 240))
    cap = QPainterPath()
    cap.addEllipse(QRectF(w * 0.18, -w * 0.02, w * 0.64, w * 0.2))
    cap.addEllipse(QRectF(w * 0.12, w * 0.02, w * 0.3, w * 0.16))
    cap.addEllipse(QRectF(w * 0.5, w * 0.03, w * 0.36, w * 0.15))
    q.drawPath(cap)
    q.end()
    return QIcon(out)


ICE = "#8DC4F2"                                        # льдисто-голубой цвет значков зимой


class PreviewCard(QWidget):
    """Живая открытка справа в разделе «Зима»: ночное небо, падающий снег, ёлки и снеговик."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(230, 300)
        self._t0 = time.monotonic()
        rnd = random.Random(7)
        self._flakes = [(rnd.random(), rnd.random(), 1 + 2.2 * rnd.random(), 0.05 + 0.1 * rnd.random(), rnd.random() * 6.28) for _ in range(46)]
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self.update)

    def showEvent(self, e):
        self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = time.monotonic() - self._t0
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), 18, 18)
        p.setClipPath(path)
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(28, 44, 92))
        g.setColorAt(0.6, QColor(70, 110, 170))
        g.setColorAt(1, QColor(150, 190, 235))
        p.fillRect(QRectF(0, 0, w, h), QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(14):                                       # звёзды мерцают
            sx, sy = (i * 0.173 + 0.07) % 1.0, (i * 0.291 + 0.05) % 0.45
            p.setBrush(QColor(255, 255, 255, int(70 + 150 * (0.5 + 0.5 * math.sin(t * 1.7 + i)))))
            p.drawEllipse(QPointF(sx * w, sy * h), 1.3, 1.3)
        p.setBrush(QColor(255, 244, 214, 235))                      # луна
        p.drawEllipse(QPointF(w * 0.8, h * 0.16), 15, 15)
        p.setBrush(QColor(28, 44, 92, 255))
        p.drawEllipse(QPointF(w * 0.8 + 7, h * 0.16 - 3), 13, 13)
        paint_drifts(p, QRectF(0, h - 90, w, 90), t, height=46)
        base = h - 34
        draw_tree(p, w * 0.24, base, 118, t, 1)
        draw_tree(p, w * 0.52, base + 6, 80, t, 2)
        draw_snowman(p, w * 0.80, base + 4, 28, t)
        for fx, fy, r, v, ph in self._flakes:                       # снег
            y = ((fy + t * v) % 1.0) * h
            x = (fx * w + math.sin(t * 0.8 + ph) * 10) % w
            p.setBrush(QColor(255, 255, 255, 60))
            p.drawEllipse(QPointF(x, y), r * 1.9, r * 1.9)
            p.setBrush(QColor(255, 255, 255, 220))
            p.drawEllipse(QPointF(x, y), r, r)
        p.end()


# ---------- Дед Мороз на санях с оленями и зимняя ночь (сцена знакомства) ----------
def _grad(y0, y1, c0, c1, x0=0.0, x1=0.0):
    g = QLinearGradient(x0, y0, x1, y1)
    g.setColorAt(0, QColor(*c0))
    g.setColorAt(1, QColor(*c1))
    return QBrush(g)


def draw_hat_icon(p, x, y, s, rot=0.0):
    """Красный колпак с меховой опушкой и помпоном: летит от Деда Мороза к Mico."""
    p.save()
    p.translate(x, y)
    p.rotate(rot)
    p.scale(s, s)
    p.setPen(Qt.PenStyle.NoPen)
    body = QPainterPath()
    body.moveTo(-26, 6)
    body.cubicTo(QPointF(-28, -22), QPointF(-8, -44), QPointF(14, -38))
    body.cubicTo(QPointF(30, -35), QPointF(40, -24), QPointF(44, -6))
    body.cubicTo(QPointF(32, -22), QPointF(22, -12), QPointF(26, 6))
    body.closeSubpath()
    p.setBrush(_grad(-44, 6, (250, 96, 90), (170, 24, 44), -26, 30))
    p.drawPath(body)
    p.setBrush(QColor(120, 12, 30, 60))
    p.drawEllipse(QPointF(16, -10), 10, 16)
    fur = _grad(-6, 14, (255, 255, 255), (214, 226, 244))
    p.setBrush(fur)
    p.drawRoundedRect(QRectF(-34, -5, 68, 16), 8, 8)
    for i in range(7):
        p.drawEllipse(QPointF(-28 + i * 9.4, -4), 5.6, 5.6)
        p.drawEllipse(QPointF(-23 + i * 9.4, 11), 5.6, 5.6)
    pg = QRadialGradient(QPointF(42, -11), 10)
    pg.setColorAt(0, QColor(255, 255, 255))
    pg.setColorAt(1, QColor(212, 226, 246))
    p.setBrush(QBrush(pg))
    for k in range(9):
        a = k * 2 * math.pi / 9
        p.drawEllipse(QPointF(44 + math.cos(a) * 6, -8 + math.sin(a) * 6), 5, 5)
    p.drawEllipse(QPointF(44, -8), 8, 8)
    p.restore()


def _leg(p, hx, hy, ph, front, col_up, col_lo):
    """Нога оленя из двух звеньев: бедро, колено, голень и копыто. ph — фаза галопа."""
    a1 = 0.62 * math.sin(ph)                                           # бедро
    a2 = (0.55 if front else -0.5) + 0.75 * math.sin(ph - 1.3) * (1 if front else -1)   # голень сгибается в колене
    ln1, ln2 = 17.0, 19.0
    kx, ky = hx + math.sin(a1) * ln1, hy + math.cos(a1) * ln1
    ex, ey = kx + math.sin(a1 + a2) * ln2, ky + math.cos(a1 + a2) * ln2
    ey = min(ey, 3.0)
    p.setPen(QPen(col_up, 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(hx, hy), QPointF(kx, ky))
    p.setPen(QPen(col_lo, 4.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(kx, ky), QPointF(ex, ey))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(38, 28, 24))
    p.drawEllipse(QPointF(ex + 1.5, ey + 0.5), 3.6, 2.6)               # копыто


def _deer(p, x, t, i, lead):
    """Олень в галопе (смотрит вправо): шерсть с объёмом, белая грудка, ветвистые рога, ошейник с бубенцом, дыхание на морозе.
    У передового светится красный нос."""
    ph = t * 9 + i * 0.9
    bob = math.sin(ph * 2) * 2.4
    p.save()
    p.translate(x, bob)
    fur_a, fur_b = QColor(176, 122, 80), QColor(116, 74, 44)
    far_up, far_lo = QColor(92, 58, 36), QColor(106, 68, 42)
    near_up, near_lo = QColor(132, 86, 54), QColor(150, 102, 66)
    for hx, front, k in ((20, True, 0.0), (-22, False, 2.1)):          # дальние ноги: темнее, рисуем под телом
        _leg(p, hx - 4, -40, ph + k + 1.6, front, far_up, far_lo)
    p.setPen(Qt.PenStyle.NoPen)
    # туловище: тёмная спина, светлое брюхо, белая грудка
    p.setBrush(_grad(-66, -30, (186, 132, 88), (118, 76, 46)))
    p.drawEllipse(QPointF(0, -50), 36, 18)
    p.setBrush(QColor(236, 214, 184, 190))
    p.drawEllipse(QPointF(2, -40), 28, 8)
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(QPointF(30, -50), 9, 11)
    for hx, front, k in ((26, True, 0.0), (-16, False, 2.1)):          # ближние ноги
        _leg(p, hx, -38, ph + k, front, near_up, near_lo)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(246, 238, 226))
    p.drawEllipse(QPointF(-38, -56 + math.sin(ph * 2) * 1.5), 7, 5.5)    # хвостик
    # шея и голова
    neck = QPainterPath()
    neck.moveTo(22, -60)
    neck.cubicTo(QPointF(32, -72), QPointF(38, -84), QPointF(46, -92))
    neck.lineTo(58, -82)
    neck.cubicTo(QPointF(50, -70), QPointF(44, -56), QPointF(36, -40))
    neck.closeSubpath()
    p.setBrush(_grad(-92, -40, (178, 124, 82), (136, 90, 56)))
    p.drawPath(neck)
    p.setBrush(QColor(255, 255, 255, 200))
    ruff = QPainterPath()
    ruff.moveTo(34, -52)
    ruff.cubicTo(QPointF(44, -62), QPointF(48, -74), QPointF(52, -86))
    ruff.lineTo(58, -82)
    ruff.cubicTo(QPointF(50, -66), QPointF(46, -54), QPointF(40, -42))
    ruff.closeSubpath()
    p.drawPath(ruff)
    p.save()
    p.translate(54, -92)
    p.rotate(-12 + math.sin(ph * 2 - 0.6) * 5)
    p.setBrush(_grad(-10, 10, (190, 136, 92), (140, 94, 58)))
    p.drawEllipse(QPointF(0, 0), 15, 10.5)                              # голова
    p.setBrush(QColor(224, 190, 152))
    p.drawEllipse(QPointF(12, 3), 8.5, 6.4)                             # морда
    p.setBrush(QColor(176, 118, 124))
    p.save()
    p.translate(-8, -9)
    p.rotate(-30)
    p.setBrush(QColor(150, 100, 62))
    p.drawEllipse(QPointF(0, -4), 4.2, 9)                               # ухо
    p.setBrush(QColor(226, 160, 160, 200))
    p.drawEllipse(QPointF(0, -3), 2.3, 6)
    p.restore()
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(QPointF(4, -2.5), 3.4, 3.0)                           # глаз
    p.setBrush(QColor(24, 18, 18))
    p.drawEllipse(QPointF(4.8, -2.4), 1.9, 2.0)
    p.setBrush(QColor(255, 255, 255, 230))
    p.drawEllipse(QPointF(5.4, -3.2), 0.7, 0.7)
    if lead:                                                            # светящийся красный нос
        glow = QRadialGradient(QPointF(19, 3.4), 20)
        glow.setColorAt(0, QColor(255, 90, 90, 210))
        glow.setColorAt(1, QColor(255, 90, 90, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(19, 3.4), 20, 20)
        p.setBrush(QColor(255, 70, 70))
    else:
        p.setBrush(QColor(54, 36, 32))
    p.drawEllipse(QPointF(19.5, 3.4), 3.7, 3.3)
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawEllipse(QPointF(18.6, 2.4), 1.1, 0.9)
    p.setPen(QPen(QColor(110, 70, 46, 150), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(QRectF(10, 4, 8, 5), 200 * 16, 130 * 16)                 # рот
    # рога: два, дальний темнее; у каждого ствол и три отростка
    for far, dx, col in ((True, 7.0, QColor(96, 64, 44)), (False, 0.0, QColor(132, 92, 62))):
        pen = QPen(col, 3.4 if not far else 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        beam = QPainterPath()
        beam.moveTo(-2 + dx, -9)
        beam.cubicTo(QPointF(-12 + dx, -22), QPointF(-10 + dx, -36), QPointF(2 + dx, -46))
        p.drawPath(beam)
        for (bx, by, tx, ty) in ((-9, -20, -20, -26), (-8, -29, -17, -40), (-3, -38, -8, -50)):
            p.drawLine(QPointF(bx + dx, by), QPointF(tx + dx, ty))
        p.drawLine(QPointF(0 + dx, -44), QPointF(10 + dx, -50))
    p.restore()
    # ошейник с бубенцом
    p.setPen(QPen(QColor(210, 46, 56), 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(34, -70), QPointF(50, -80))
    p.setPen(Qt.PenStyle.NoPen)
    sw = math.sin(ph * 2 + 1) * 2
    p.setBrush(_grad(-6, 6, (255, 226, 120), (214, 150, 40)))
    p.drawEllipse(QPointF(41 + sw * .4, -62 + abs(sw) * .5), 4.8, 4.8)
    p.setBrush(QColor(120, 70, 10, 180))
    p.drawLine(QPointF(0, 0), QPointF(0, 0))
    p.drawEllipse(QPointF(41 + sw * .4, -59.5 + abs(sw) * .5), 1.0, 1.0)
    # упряжь вдоль тела
    p.setPen(QPen(QColor(200, 46, 56, 230), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(30, -64), QPointF(-30, -58))
    # облачко дыхания на морозе
    p.setPen(Qt.PenStyle.NoPen)
    for k in range(3):
        a = ((t * 1.1 + k / 3.0 + i * .21) % 1.0)
        p.setBrush(QColor(255, 255, 255, int(120 * (1 - a))))
        p.drawEllipse(QPointF(76 + a * 26, -88 - a * 14), 2.5 + a * 6, 2.5 + a * 6)
    p.restore()


def draw_sleigh(p, x, y, s, t):
    """Сани Деда Мороза с тремя оленями. (x, y): точка на полозьях; s: масштаб; t: время (галоп, взмах руки, колокольчики).
    Всё едет вправо: олени впереди, сани сзади. Рисуем по слоям: упряжь, олени, сани, мешок с подарками, Дед Мороз."""
    p.save()
    p.translate(x, y)
    p.scale(s, s)
    # снежная пыль из-под полозьев
    p.setPen(Qt.PenStyle.NoPen)
    for k in range(16):
        a = (t * 1.6 + k * 0.137) % 1.0
        p.setBrush(QColor(255, 255, 255, int(150 * (1 - a))))
        p.drawEllipse(QPointF(-70 - a * 70 + math.sin(k) * 6, -2 - a * 16 + math.cos(k * 2) * 3), 3 + a * 6, 3 + a * 5)
    # поводья и постромки к трём оленям
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(3):
        ex = 138 + i * 94
        p.setPen(QPen(QColor(120, 70, 40), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        rope = QPainterPath()
        rope.moveTo(84, -38)
        rope.quadTo((84 + ex) / 2, -30 + math.sin(t * 5 + i) * 3, ex - 26, -56)
        p.drawPath(rope)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_grad(-4, 4, (255, 226, 120), (214, 150, 40)))
        p.drawEllipse(QPointF((84 + ex) / 2, -34 + math.sin(t * 5 + i) * 1.5), 3.6, 3.6)             # бубенчик на постромке
        p.setBrush(Qt.BrushStyle.NoBrush)
    for i in (2, 1, 0):
        _deer(p, 138 + i * 94, t, i, lead=(i == 2))
    # полозья
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(150, 110, 40), 5.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    far = QPainterPath()
    far.moveTo(-70, -6)
    far.lineTo(66, -6)
    p.drawPath(far)
    run = QPainterPath()
    run.moveTo(-84, 2)
    run.lineTo(64, 2)
    run.cubicTo(QPointF(92, 2), QPointF(100, -16), QPointF(92, -34))
    run.cubicTo(QPointF(88, -42), QPointF(80, -40), QPointF(82, -34))                                    # завиток на носу
    p.setPen(QPen(QColor(244, 200, 90), 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawPath(run)
    p.setPen(QPen(QColor(255, 244, 190, 160), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(-80, 0.2), QPointF(60, 0.2))
    p.setPen(QPen(QColor(236, 188, 80), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for px in (-52, -2, 46):                                                                              # стойки между полозом и кузовом
        post = QPainterPath()
        post.moveTo(px, 0)
        post.cubicTo(QPointF(px - 6, -6), QPointF(px + 6, -10), QPointF(px, -16))
        p.drawPath(post)
    p.setPen(Qt.PenStyle.NoPen)
    # кузов
    body = QPainterPath()
    body.moveTo(-74, -14)
    body.cubicTo(QPointF(-90, -30), QPointF(-90, -58), QPointF(-72, -68))
    body.cubicTo(QPointF(-42, -58), QPointF(8, -54), QPointF(52, -62))
    body.cubicTo(QPointF(72, -66), QPointF(86, -54), QPointF(80, -38))
    body.cubicTo(QPointF(76, -22), QPointF(52, -12), QPointF(8, -12))
    body.cubicTo(QPointF(-22, -12), QPointF(-52, -12), QPointF(-74, -14))
    p.setBrush(_grad(-70, -10, (238, 66, 76), (156, 20, 40)))
    p.drawPath(body)
    p.setBrush(QColor(255, 255, 255, 38))
    p.drawEllipse(QPointF(-10, -52), 40, 5)                                                              # блик лака
    p.setBrush(QColor(110, 8, 28, 70))
    p.drawEllipse(QPointF(10, -17), 56, 4)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(250, 214, 110), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))          # золотая отделка по борту
    trim = QPainterPath()
    trim.moveTo(-72, -66)
    trim.cubicTo(QPointF(-42, -56), QPointF(8, -52), QPointF(52, -60))
    trim.cubicTo(QPointF(70, -64), QPointF(84, -52), QPointF(79, -38))
    p.drawPath(trim)
    p.setPen(QPen(QColor(250, 214, 110, 200), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    wave = QPainterPath()
    wave.moveTo(-70, -22)
    wave.cubicTo(QPointF(-40, -30), QPointF(-10, -16), QPointF(20, -24))
    wave.cubicTo(QPointF(40, -28), QPointF(56, -22), QPointF(66, -26))
    p.drawPath(wave)
    p.setPen(QPen(QColor(255, 255, 255, 235), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))    # снежинка на борту
    for k in range(6):
        a = k * math.pi / 3
        p.drawLine(QPointF(34 + math.cos(a) * 2, -36 + math.sin(a) * 2), QPointF(34 + math.cos(a) * 8, -36 + math.sin(a) * 8))
    p.setPen(Qt.PenStyle.NoPen)
    # мешок с подарками позади
    sack = QPainterPath()
    sack.moveTo(-62, -12)
    sack.cubicTo(QPointF(-100, -30), QPointF(-98, -76), QPointF(-72, -92))
    sack.cubicTo(QPointF(-64, -96), QPointF(-54, -90), QPointF(-50, -80))
    sack.cubicTo(QPointF(-40, -56), QPointF(-42, -30), QPointF(-44, -12))
    sack.closeSubpath()
    p.setBrush(_grad(-96, -10, (176, 126, 82), (122, 82, 48)))
    p.drawPath(sack)
    p.setPen(QPen(QColor(100, 64, 38, 160), 1.4))
    for k in range(4):
        p.drawLine(QPointF(-84 + k * 10, -60 + k * 3), QPointF(-80 + k * 9, -26))
    p.setPen(Qt.PenStyle.NoPen)
    for (gx, gy, gw, col, rib, rot) in ((-90, -86, 20, (70, 160, 110), (255, 220, 120), -18), (-68, -102, 18, (96, 150, 230), (255, 255, 255), 12),
                                      (-52, -92, 15, (240, 180, 70), (220, 50, 66), 24)):
        p.save()
        p.translate(gx + gw / 2, gy + gw / 2)
        p.rotate(rot)
        p.setBrush(_grad(-gw / 2, gw / 2, col, (max(0, col[0] - 40), max(0, col[1] - 40), max(0, col[2] - 40))))
        p.drawRoundedRect(QRectF(-gw / 2, -gw / 2, gw, gw), 3, 3)
        p.setBrush(QColor(*rib))
        p.drawRect(QRectF(-1.8, -gw / 2, 3.6, gw))
        p.drawRect(QRectF(-gw / 2, -1.8, gw, 3.6))
        p.drawEllipse(QPointF(-4, -gw / 2 - 1.5), 4, 2.8)
        p.drawEllipse(QPointF(4, -gw / 2 - 1.5), 4, 2.8)
        p.restore()
    p.setBrush(QColor(210, 60, 66))                                                                      # верёвка на горловине мешка
    p.drawEllipse(QPointF(-62, -82), 6, 3.2)
    # Дед Мороз, сидит боком, едет вправо
    sway = math.sin(t * 5) * 1.2
    p.save()
    p.translate(0, sway)
    # сапоги
    p.setBrush(QColor(34, 26, 28))
    p.drawRoundedRect(QRectF(-4, -34, 34, 12), 5, 5)
    p.setBrush(QColor(255, 255, 255))
    p.drawRoundedRect(QRectF(-8, -41, 14, 9), 4, 4)
    # шуба: тело с животом, мех по подолу, пояс с золотой пряжкой
    coat = QPainterPath()
    coat.moveTo(-56, -50)
    coat.cubicTo(QPointF(-60, -92), QPointF(-34, -118), QPointF(-12, -112))
    coat.cubicTo(QPointF(10, -108), QPointF(22, -84), QPointF(16, -62))
    coat.cubicTo(QPointF(12, -50), QPointF(-4, -44), QPointF(-26, -44))
    coat.closeSubpath()
    p.setBrush(_grad(-116, -44, (240, 66, 72), (160, 24, 42)))
    p.drawPath(coat)
    p.setBrush(QColor(255, 255, 255))
    p.drawRoundedRect(QRectF(-54, -52, 74, 10), 5, 5)
    p.setBrush(QColor(28, 24, 28))
    belt = QPainterPath()
    belt.moveTo(-52, -80)
    belt.lineTo(16, -76)
    belt.lineTo(15, -69)
    belt.lineTo(-52, -73)
    belt.closeSubpath()
    p.drawPath(belt)
    p.setBrush(_grad(-82, -68, (255, 232, 130), (214, 150, 40)))
    p.drawRoundedRect(QRectF(-24, -82, 14, 14), 3, 3)
    p.setBrush(QColor(28, 24, 28))
    p.drawRoundedRect(QRectF(-20.5, -78.5, 7, 7), 1.5, 1.5)
    # левая рука с поводьями, правая машет
    wv = math.sin(t * 6)
    p.setPen(QPen(QColor(226, 54, 62), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(-36, -98), QPointF(-4, -78))
    p.drawLine(QPointF(-4, -78), QPointF(30, -80))
    p.setPen(QPen(QColor(120, 70, 40), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(30, -80), QPointF(84, -40))
    p.setPen(QPen(QColor(226, 54, 62), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    sh = QPointF(-14, -106)
    el = QPointF(14, -118 + wv * 4)
    hd = QPointF(34 + wv * 6, -142 + wv * 3)
    p.drawLine(sh, el)
    p.drawLine(el, hd)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255))
    p.drawEllipse(hd, 7.4, 7.4)                                                                          # меховая варежка
    p.drawEllipse(QPointF(30, -80), 6.6, 6.6)
    p.setBrush(QColor(240, 240, 250))
    p.drawEllipse(QPointF(hd.x() + 4, hd.y() - 6), 3, 3.6)                                              # большой палец
    # голова: лицо с румянцем и носом, брови, усы и большая борода
    hx, hy = -34, -130
    p.setBrush(_grad(hy - 16, hy + 16, (255, 224, 196), (240, 184, 152)))
    p.drawEllipse(QPointF(hx, hy), 17, 17)
    p.setBrush(QColor(255, 120, 130, 120))
    p.drawEllipse(QPointF(hx + 8, hy + 5), 5.4, 3.8)
    p.drawEllipse(QPointF(hx - 9, hy + 5), 5.0, 3.6)
    p.setBrush(QColor(236, 120, 120))
    p.drawEllipse(QPointF(hx + 3, hy + 3), 4.2, 3.8)                                                    # нос
    p.setBrush(QColor(255, 255, 255, 190))
    p.drawEllipse(QPointF(hx + 2, hy + 2), 1.2, 1.0)
    p.setBrush(QColor(255, 255, 255))
    beard = QPainterPath()
    beard.moveTo(hx - 17, hy - 2)
    beard.cubicTo(QPointF(hx - 24, hy + 22), QPointF(hx - 16, hy + 46), QPointF(hx + 2, hy + 50))
    beard.cubicTo(QPointF(hx + 20, hy + 46), QPointF(hx + 26, hy + 22), QPointF(hx + 17, hy - 2))
    beard.cubicTo(QPointF(hx + 10, hy + 6), QPointF(hx - 10, hy + 6), QPointF(hx - 17, hy - 2))
    p.setBrush(_grad(hy, hy + 50, (255, 255, 255), (214, 224, 240)))
    p.drawPath(beard)
    p.setBrush(QColor(255, 255, 255))
    for (cx_, cy_, r_) in ((-12, 22, 8), (0, 30, 9), (12, 22, 8), (-6, 12, 7), (8, 13, 7)):            # завитки бороды
        p.drawEllipse(QPointF(hx + cx_, hy + cy_), r_, r_)
    p.setBrush(QColor(255, 255, 255))
    mus = QPainterPath()
    mus.moveTo(hx + 3, hy + 6)
    mus.cubicTo(QPointF(hx + 14, hy + 1), QPointF(hx + 22, hy + 6), QPointF(hx + 18, hy + 11))
    mus.cubicTo(QPointF(hx + 12, hy + 9), QPointF(hx + 8, hy + 10), QPointF(hx + 3, hy + 8))
    mus.closeSubpath()
    p.drawPath(mus)
    mus2 = QPainterPath()
    mus2.moveTo(hx + 1, hy + 6)
    mus2.cubicTo(QPointF(hx - 10, hy + 1), QPointF(hx - 18, hy + 6), QPointF(hx - 14, hy + 11))
    mus2.cubicTo(QPointF(hx - 8, hy + 9), QPointF(hx - 4, hy + 10), QPointF(hx + 1, hy + 8))
    mus2.closeSubpath()
    p.drawPath(mus2)
    p.setBrush(QColor(176, 80, 90))
    p.drawEllipse(QPointF(hx + 1, hy + 13), 3.2, 1.8)                                                   # улыбка
    p.setBrush(QColor(255, 255, 255))                                                                   # брови
    p.drawEllipse(QPointF(hx + 9, hy - 8), 5.2, 2.4)
    p.drawEllipse(QPointF(hx - 8, hy - 8), 5.2, 2.4)
    p.setBrush(QColor(36, 28, 30))
    p.drawEllipse(QPointF(hx + 9, hy - 3.5), 2.0, 2.4)
    p.drawEllipse(QPointF(hx - 7, hy - 3.5), 2.0, 2.4)
    p.setBrush(QColor(255, 255, 255, 220))
    p.drawEllipse(QPointF(hx + 9.6, hy - 4.4), 0.7, 0.7)
    p.drawEllipse(QPointF(hx - 6.4, hy - 4.4), 0.7, 0.7)
    # колпак: наклонён назад по ходу движения, помпон болтается
    swing = math.sin(t * 8) * 4
    hat = QPainterPath()
    hat.moveTo(hx - 19, hy - 10)
    hat.cubicTo(QPointF(hx - 22, hy - 32), QPointF(hx - 4, hy - 46), QPointF(hx + 14, hy - 36))
    hat.cubicTo(QPointF(hx + 20, hy - 31), QPointF(hx + 20, hy - 18), QPointF(hx + 18, hy - 10))
    hat.closeSubpath()
    p.setBrush(_grad(hy - 44, hy - 8, (250, 90, 86), (176, 26, 44)))
    p.drawPath(hat)
    tail = QPainterPath()
    tail.moveTo(hx - 12, hy - 34)
    tail.cubicTo(QPointF(hx - 28, hy - 42), QPointF(hx - 42, hy - 36 + swing), QPointF(hx - 50, hy - 24 + swing))
    tail.lineTo(hx - 40, hy - 18 + swing)
    tail.cubicTo(QPointF(hx - 34, hy - 28), QPointF(hx - 24, hy - 30), QPointF(hx - 6, hy - 24))
    tail.closeSubpath()
    p.setBrush(QColor(214, 40, 54))
    p.drawPath(tail)
    p.setBrush(QColor(255, 255, 255))
    p.drawRoundedRect(QRectF(hx - 21, hy - 14, 43, 9), 4.5, 4.5)
    for k in range(6):
        p.drawEllipse(QPointF(hx - 17 + k * 7.6, hy - 13.5), 4.4, 4.4)
        p.drawEllipse(QPointF(hx - 13 + k * 7.6, hy - 4.5), 4.4, 4.4)
    pg = QRadialGradient(QPointF(hx - 52, hy - 24 + swing), 8)
    pg.setColorAt(0, QColor(255, 255, 255))
    pg.setColorAt(1, QColor(212, 226, 246))
    p.setBrush(QBrush(pg))
    p.drawEllipse(QPointF(hx - 52, hy - 22 + swing), 7, 7)
    p.restore()
    p.restore()


def draw_winter_night(p, W, H, t, a=1.0):
    """Зимняя ночь на весь экран: небо с северным сиянием, звёзды, луна, холмы с ёлками, домики с тёплыми окнами и дымом, сугробы."""
    p.save()
    p.setOpacity(max(0.0, min(1.0, a)))
    sky = QLinearGradient(0, 0, 0, H)
    sky.setColorAt(0.0, QColor(8, 12, 40))
    sky.setColorAt(0.45, QColor(26, 40, 96))
    sky.setColorAt(0.78, QColor(88, 76, 140))
    sky.setColorAt(1.0, QColor(214, 150, 170))
    p.fillRect(QRectF(0, 0, W, H), QBrush(sky))
    p.setPen(Qt.PenStyle.NoPen)
    # северное сияние: три мягкие ленты
    for k, col in enumerate(((80, 255, 190), (110, 190, 255), (190, 130, 255))):
        path = QPainterPath()
        base = H * (0.20 + 0.07 * k)
        path.moveTo(0, base)
        n = 28
        for i in range(n + 1):
            x = W * i / n
            y = base + math.sin(i * 0.5 + t * 0.4 + k * 1.7) * H * 0.045 + math.sin(i * 0.23 + t * 0.25) * H * 0.03
            path.lineTo(x, y)
        for i in range(n, -1, -1):
            x = W * i / n
            y = base + H * 0.17 + math.sin(i * 0.45 - t * 0.35 + k) * H * 0.04
            path.lineTo(x, y)
        path.closeSubpath()
        g = QLinearGradient(0, base - H * 0.05, 0, base + H * 0.2)
        g.setColorAt(0, QColor(col[0], col[1], col[2], 0))
        g.setColorAt(0.35, QColor(col[0], col[1], col[2], 58))
        g.setColorAt(1, QColor(col[0], col[1], col[2], 0))
        p.setBrush(QBrush(g))
        p.drawPath(path)
    # звёзды
    rnd = random.Random(3)
    for i in range(110):
        sx, sy = rnd.random() * W, rnd.random() * H * 0.55
        tw = 0.5 + 0.5 * math.sin(t * 1.8 + i * 1.3)
        p.setBrush(QColor(255, 255, 255, int(70 + 160 * tw)))
        r_ = 0.7 + 1.5 * rnd.random() * (0.6 + 0.4 * tw)
        p.drawEllipse(QPointF(sx, sy), r_, r_)
    # луна с ореолом и кратерами
    mx, my, mr = W * 0.84, H * 0.16, min(W, H) * 0.055
    halo = QRadialGradient(QPointF(mx, my), mr * 4.2)
    halo.setColorAt(0, QColor(255, 244, 210, 120))
    halo.setColorAt(1, QColor(255, 244, 210, 0))
    p.setBrush(QBrush(halo))
    p.drawEllipse(QPointF(mx, my), mr * 4.2, mr * 4.2)
    p.setBrush(_grad(my - mr, my + mr, (255, 248, 226), (236, 222, 184)))
    p.drawEllipse(QPointF(mx, my), mr, mr)
    p.setBrush(QColor(214, 200, 164, 120))
    for (dx, dy, rr) in ((-0.3, -0.2, 0.2), (0.25, 0.1, 0.14), (-0.05, 0.35, 0.12)):
        p.drawEllipse(QPointF(mx + dx * mr, my + dy * mr), rr * mr, rr * mr)

    def hills(base, amp, col_top, col_bot, seed, step=40):
        path = QPainterPath()
        path.moveTo(0, H)
        r = random.Random(seed)
        ph = [r.random() * 6.28 for _ in range(3)]
        for x in range(0, int(W) + step, step):
            y = base + math.sin(x * 0.0042 + ph[0]) * amp + math.sin(x * 0.011 + ph[1]) * amp * 0.4 + math.sin(x * 0.0021 + ph[2]) * amp * 0.6
            path.lineTo(x, y)
        path.lineTo(W, H)
        path.closeSubpath()
        p.setBrush(_grad(base - amp, H, col_top, col_bot))
        p.drawPath(path)
        return lambda x: base + math.sin(x * 0.0042 + ph[0]) * amp + math.sin(x * 0.011 + ph[1]) * amp * 0.4 + math.sin(x * 0.0021 + ph[2]) * amp * 0.6
    far = hills(H * 0.58, H * 0.05, (44, 56, 112), (28, 36, 84), 1)
    mid = hills(H * 0.66, H * 0.04, (60, 74, 130), (38, 50, 100), 2)
    # ёлки на дальнем холме
    r = random.Random(9)
    for i in range(26):
        x = r.random() * W
        h_ = H * (0.045 + 0.04 * r.random())
        y = far(x) + 4
        p.setBrush(QColor(22, 38, 70))
        for lv in range(3):
            w_ = h_ * (0.5 - lv * 0.1)
            yy = y - lv * h_ * 0.32
            tri = QPainterPath()
            tri.moveTo(x, yy - h_ * 0.5)
            tri.lineTo(x + w_, yy)
            tri.lineTo(x - w_, yy)
            tri.closeSubpath()
            p.drawPath(tri)
    # домики на среднем холме: освещённые окна, снег на крышах, дым из труб
    for hx_ in (0.12, 0.31, 0.68, 0.9):
        x = W * hx_
        y = mid(x) + 6
        bw, bh = H * 0.07, H * 0.045
        p.setBrush(QColor(36, 28, 52))
        p.drawRect(QRectF(x - bw / 2, y - bh, bw, bh))
        roof = QPainterPath()
        roof.moveTo(x - bw * 0.62, y - bh)
        roof.lineTo(x, y - bh - bh * 0.7)
        roof.lineTo(x + bw * 0.62, y - bh)
        roof.closeSubpath()
        p.setBrush(QColor(72, 52, 74))
        p.drawPath(roof)
        p.setBrush(QColor(238, 244, 255))
        snow = QPainterPath()
        snow.moveTo(x - bw * 0.62, y - bh)
        snow.lineTo(x, y - bh - bh * 0.7)
        snow.lineTo(x + bw * 0.62, y - bh)
        snow.quadTo(x + bw * 0.3, y - bh - bh * 0.18, x, y - bh - bh * 0.12)
        snow.quadTo(x - bw * 0.3, y - bh - bh * 0.18, x - bw * 0.62, y - bh)
        p.drawPath(snow)
        lit = 0.85 + 0.15 * math.sin(t * 2 + hx_ * 20)
        glow = QRadialGradient(QPointF(x, y - bh * 0.5), bw * 0.9)
        glow.setColorAt(0, QColor(255, 206, 110, int(110 * lit)))
        glow.setColorAt(1, QColor(255, 206, 110, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(x, y - bh * 0.5), bw * 0.9, bw * 0.9)
        p.setBrush(QColor(255, 214, 120, int(240 * lit)))
        p.drawRect(QRectF(x - bw * 0.3, y - bh * 0.78, bw * 0.24, bh * 0.4))
        p.drawRect(QRectF(x + bw * 0.06, y - bh * 0.78, bw * 0.24, bh * 0.4))
        p.setBrush(QColor(60, 44, 62))
        p.drawRect(QRectF(x + bw * 0.28, y - bh - bh * 0.55, bw * 0.12, bh * 0.4))
        for k in range(4):                                                                  # дым из трубы
            a2 = ((t * 0.35 + k / 4.0 + hx_) % 1.0)
            p.setBrush(QColor(220, 228, 245, int(90 * (1 - a2))))
            p.drawEllipse(QPointF(x + bw * 0.34 + a2 * 18 + math.sin(a2 * 6) * 3, y - bh - bh * 0.6 - a2 * bh * 1.6), 3 + a2 * 7, 3 + a2 * 7)
    # передний снег
    hills(H * 0.80, H * 0.018, (232, 240, 255), (190, 206, 236), 3)
    gl = QLinearGradient(0, H * 0.78, 0, H * 0.84)
    gl.setColorAt(0, QColor(255, 255, 255, 80))
    gl.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, H * 0.78, W, H * 0.06), QBrush(gl))
    p.restore()
