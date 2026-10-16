"""Остров сна: когда Mico засыпает, из него вытягивается чёрная «пилюля» сверху по центру экрана — как
Dynamic Island на iPhone. Внутри — спящий Mico и плавающие «z». Остров растёт из того места, где был Mico,
и втягивается обратно, когда Mico просыпается. Нажатие на остров тоже будит Mico.

Рисуется здесь; геометрию (размер и место) задают методы этого класса. Волны при сне гасит intel_ui.EdgeGlow."""
import math

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

import theme


class SleepIsland(QWidget):
    wake = pyqtSignal()                       # нажали на остров — Mico просыпается
    W, H = 132, 38                            # «пилюля» в полном размере, px (как у Dynamic Island: узкая и длинная)
    TOP = 10                                  # отступ от верхнего края экрана, px
    GROW_MS, SHRINK_MS = 620, 420             # появление из Mico и втягивание обратно, мс
    MICO_SHARE = 0.35                         # стартовый размер острова — доля от размера Mico

    def __init__(self, cfg):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Mico спит. Нажми, чтобы разбудить.")
        self.resize(self.W, self.H)
        self.t = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.anim = None

    # ----- геометрия -----
    def _pill(self, screen):
        """Пилюля сверху по центру того экрана, где стоит Mico."""
        g = screen.geometry()
        return QRect(g.center().x() - self.W // 2, g.top() + self.TOP, self.W, self.H)

    def _mico_spot(self, blob):
        """Маленький круг в центре Mico: отсюда остров вырастает и сюда втягивается."""
        g = blob.geometry()
        d = max(12, int(g.width() * self.MICO_SHARE))
        return QRect(g.center().x() - d // 2, g.center().y() - d // 2, d, d)

    def _run(self, start, end, ms, curve, after=None):
        """Плавное изменение геометрии. Прошлую анимацию останавливаем, чтобы не спорили."""
        if self.anim is not None:
            self.anim.stop()
        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.anim.setDuration(ms)
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.setEasingCurve(curve)
        if after is not None:
            self.anim.finished.connect(after)
        self.anim.start()

    # ----- показ и уборка -----
    def show_from(self, blob):
        """Mico засыпает: из его места вырастает чёрная пилюля сверху по центру и остаётся там спящим островком."""
        scr = QGuiApplication.screenAt(blob.geometry().center()) or QGuiApplication.primaryScreen()
        start, end = self._mico_spot(blob), self._pill(scr)
        self.setGeometry(start)
        self.show()
        self.timer.start()
        self._run(start, end, self.GROW_MS, QEasingCurve.Type.OutCubic)

    def retract_to(self, blob):
        """Mico проснулся: остров втягивается обратно в Mico и исчезает."""
        if not self.isVisible():
            return
        self._run(self.geometry(), self._mico_spot(blob), self.SHRINK_MS, QEasingCurve.Type.InCubic,
                  after=self.hide_island)

    def hide_island(self):
        if self.anim is not None:
            self.anim.stop()
        self.timer.stop()
        self.hide()

    # ----- рисование -----
    def _tick(self):
        self.t += 0.033
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.wake.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        radius = min(w, h) / 2                                 # круг в начале, пилюля в конце — плавный переход
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0))                            # чёрный, как у Dynamic Island
        p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
        k = min(w / self.W, h / self.H)                        # содержимое растёт вместе с пилюлей
        if k < 0.55:                                           # совсем маленький — внутри пусто, не мельтешим
            p.end()
            return
        p.setOpacity(min(1.0, (k - 0.55) / 0.3))              # содержимое проявляется в конце роста
        p.translate(w / 2, h / 2)
        p.scale(k, k)
        self._draw_sleeper(p)
        p.end()

    def _draw_sleeper(self, p):
        """Спящий Mico в логических координатах пилюли (начало — центр пилюли)."""
        cx, cy = -self.W / 2 + 30, 0.0                         # Mico слева, «z» — справа от него
        rx, ry = 12.0, 11.0 * (1.0 + 0.03 * math.sin(self.t * 1.3))   # спокойное дыхание
        body = QPainterPath()
        body.addEllipse(QRectF(cx - rx, cy - ry, 2 * rx, 2 * ry))
        col = QColor(self.cfg.get("color", "#FFCFA3"))
        grad = QRadialGradient(QPointF(cx - rx * 0.3, cy - ry * 0.4), rx * 1.3)
        grad.setColorAt(0.0, col.lighter(118))
        grad.setColorAt(1.0, col.darker(112))
        p.fillPath(body, grad)
        pen = QPen(QColor("#2a1d1d"), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for sgn in (-1, 1):                                    # закрытые глаза — дуги
            ex = cx + sgn * rx * 0.38
            p.drawArc(QRectF(ex - 3.5, cy - ry * 0.18 - 2.5, 7, 5), 200 * 16, 140 * 16)
        p.drawArc(QRectF(cx - 2.5, cy + ry * 0.3 - 1.5, 5, 3), 200 * 16, 140 * 16)   # ротик спокойный
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 120, 120, 90))
        for sgn in (-1, 1):                                    # щёчки
            p.drawEllipse(QPointF(cx + sgn * rx * 0.6, cy + ry * 0.2), rx * 0.14, ry * 0.1)
        font = QFont(theme.FONT_FAMILY)                        # тот же шрифт, что во всём Mico (Inter)
        font.setPixelSize(10)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(150, 170, 255, 220))
        for n in range(3):                                     # «z» всплывают из Mico и гаснут (внутри пилюли)
            ph = (self.t * 0.45 + n / 3.0) % 1.0
            p.setOpacity(math.sin(ph * math.pi) * 0.95)
            p.drawText(QPointF(cx + rx + 4 + ph * 10 + n * 5, -6 - ph * 8 - n * 1.5), "z")
