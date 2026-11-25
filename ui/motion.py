"""Анимации интерфейса Mico: один набор движений для чата, настроек и окон, чтобы всё двигалось одинаково.
Появление — прозрачность и лёгкий сдвиг снизу (ease-out), всё короче 0,35 с. Эффект прозрачности снимается
сразу после анимации: постоянный эффект внутри прокрутки рвёт текст и тормозит."""
import time

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, QVariantAnimation
from PyQt6.QtWidgets import QGraphicsOpacityEffect

_BUSY = [0.0]


def hold(ms):
    """Тяжёлая анимация началась (раскрытие карточки, смена раздела): зимний снег ждёт, пока она не кончится."""
    _BUSY[0] = max(_BUSY[0], time.monotonic() + ms / 1000.0)


def busy():
    return time.monotonic() < _BUSY[0]


_LIVE = set()                                   # держим ссылки на анимации, пока они идут


def _keep(anim):
    _LIVE.add(anim)
    anim.finished.connect(lambda: _LIVE.discard(anim))
    return anim


def fade_slide_in(widget, dy=10, ms=260, delay=0):
    """Виджет плавно проявляется и поднимается на dy пикселей (сдвиг — верхним отступом, без спора с раскладкой)."""
    if widget is None:
        return None
    eff = QGraphicsOpacityEffect(widget)
    eff.setOpacity(0.0)
    widget.setGraphicsEffect(eff)
    m = widget.contentsMargins()
    base_top = m.top()
    anim = QVariantAnimation(widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(ms)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def step(v):
        v = float(v)
        try:
            eff.setOpacity(v)
            widget.setContentsMargins(m.left(), base_top + round(dy * (1 - v)), m.right(), m.bottom())
        except RuntimeError:
            anim.stop()

    def done():
        try:
            widget.setGraphicsEffect(None)
            widget.setContentsMargins(m.left(), base_top, m.right(), m.bottom())
        except RuntimeError:
            pass
    anim.valueChanged.connect(step)
    anim.finished.connect(done)
    step(0.0)
    _keep(anim)
    if delay:
        QTimer.singleShot(delay, anim.start)
    else:
        anim.start()
    return anim


def window_fade_in(win, ms=200, target=1.0):
    """Окно мягко проявляется вместо резкого появления."""
    win.setWindowOpacity(0.0)
    anim = QPropertyAnimation(win, b"windowOpacity", win)
    anim.setDuration(ms)
    anim.setStartValue(0.0)
    anim.setEndValue(target)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    _keep(anim)
    anim.start()
    return anim
