"""Маленькие анимации интерфейса Mico AI: нажатие на кнопку даёт короткий отклик, «⋯» подпрыгивает,
а у переключателей в настройках появляется значок-галочка. Только PyQt6, без других модулей Mico."""
import math

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QWidget

from theme_tokens import MOTION


def pulse_icon(btn, scale=1.3, ms=None):
    """Значок кнопки на мгновение становится крупнее и возвращается — отклик на нажатие."""
    base = btn.iconSize()
    if base.isEmpty() or base.width() <= 0:
        return
    old = getattr(btn, "_pulse_anim", None)
    if old is not None:
        old.stop()
    anim = QVariantAnimation(btn)
    anim.setDuration(ms or MOTION["base"])
    anim.setStartValue(base)
    anim.setKeyValueAt(0.4, QSize(int(base.width() * scale), int(base.height() * scale)))
    anim.setEndValue(base)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.valueChanged.connect(btn.setIconSize)
    btn._pulse_anim = anim
    anim.start()


class DotsButton(QPushButton):
    """Кнопка «⋯»: при нажатии три точки подпрыгивают по очереди."""

    def __init__(self, color="#8e8e93", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._phase = 1.0                      # 1 — покой; 0…1 — идёт прыжок
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(MOTION["slow"])
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_phase)
        self.setFixedSize(32, 28)

    def _on_phase(self, v):
        self._phase = float(v)
        self.update()

    def setColor(self, color):
        self._color = QColor(color)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._anim.stop()
            self._anim.start()
        super().mousePressEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)                  # фон и наведение рисует стиль кнопки
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        cx, cy = self.width() / 2, self.height() / 2
        for i in range(3):
            x = cx + (i - 1) * 6.0
            lift = 0.0
            t = self._phase * 1.5 - i * 0.25      # точки стартуют по очереди
            if 0.0 < t < 1.0 and self._phase < 1.0:
                lift = math.sin(math.pi * t) * 4.0
            p.drawEllipse(QPointF(x, cy - lift), 1.9, 1.9)
        p.end()


class CheckPop(QWidget):
    """Значок-галочка рядом с переключателем: появляется с лёгким перелётом, когда пункт включают, и уходит, когда выключают."""

    def __init__(self, color="#4cc2c4", parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._on = False
        self._k = 0.0                          # 0 — не видно, 1 — полностью
        self.setFixedSize(18, 18)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(MOTION["base"])
        self._anim.valueChanged.connect(self._on_k)

    def _on_k(self, v):
        self._k = float(v)
        self.update()

    def set_on(self, on):
        on = bool(on)
        if on == self._on:
            return
        self._on = on
        self._anim.stop()
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack if on else QEasingCurve.Type.InCubic)
        self._anim.setStartValue(self._k)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, e):
        if self._k <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = max(0.0, self._k)
        p.translate(9, 9)                      # масштабируем от центра значка
        p.scale(s, s)
        p.translate(-9, -9)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QRectF(0, 0, 18, 18))
        pen = QPen(QColor("#1a1a1a"), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(5.2, 9.4), QPointF(7.9, 12.1))
        p.drawLine(QPointF(7.9, 12.1), QPointF(12.9, 6.4))
        p.end()
