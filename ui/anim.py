"""Маленькие анимации интерфейса Mico AI: нажатие на кнопку даёт короткий отклик, «⋯» подпрыгивает,
а у переключателей в настройках появляется значок-галочка. Только PyQt6, без других модулей Mico."""
import math

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QPushButton, QWidget

from ui.tokens import MOTION


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


