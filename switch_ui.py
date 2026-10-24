"""Переключатели Mico AI: пилюля (Switch), подпись, по которой можно кликнуть (ClickLabel), и пункт
«подпись слева — переключатель справа» (WrapCheck). Одни и те же в настройках и в установщике.
Только PyQt6, без других модулей Mico, поэтому его можно импортировать откуда угодно."""
from PyQt6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QSizePolicy, QSlider, QWidget

from theme_tokens import MOTION


class ClickLabel(QLabel):
    """Подпись, по которой можно кликнуть: нажатие переключает галочку рядом."""
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class Switch(QAbstractButton):
    """Переключатель-пилюля: дорожка и белая кнопка. Включён — цвет акцента Windows.
    Кнопка переезжает плавно, а не прыгает."""
    ON = "#4cc2c4"
    OFF = "#4a4a4a"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 22)
        self._pos = 1.0 if self.isChecked() else 0.0      # 0 — кнопка слева, 1 — справа
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(MOTION["base"])
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_pos)
        self.toggled.connect(self._slide)

    def _on_pos(self, v):
        self._pos = float(v)
        self.update()

    def _slide(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.ON if self.isChecked() else self.OFF))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), self.height() / 2, self.height() / 2)
        d = self.height() - 6
        x = 3 + (self.width() - 6 - d) * self._pos
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()


class WrapCheck(QWidget):
    """Пункт настройки: подпись слева (переносится), переключатель справа. Интерфейс тот же, что у галочки."""
    toggled = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self._sw = Switch()
        self._lbl = ClickLabel(text)
        self._lbl.setWordWrap(True)
        self._lbl.clicked.connect(self._sw.toggle)
        lay.addWidget(self._lbl, 1)
        lay.addWidget(self._sw, 0, Qt.AlignmentFlag.AlignVCenter)
        self._sw.toggled.connect(self.toggled)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def isChecked(self):
        return self._sw.isChecked()

    def setChecked(self, on):
        self._sw.setChecked(bool(on))

    def setToolTip(self, text):
        super().setToolTip(text)
        self._lbl.setToolTip(text)
        self._sw.setToolTip(text)

    def setText(self, text):
        self._lbl.setText(text)

    def text(self):
        return self._lbl.text()


class RoundSlider(QSlider):
    """Ползунок с круглой ручкой и мягкой дорожкой. Рисуем сами: стиль Windows делает ручку квадратной.
    Цвета задаются один раз на класс (как у Switch): ACCENT — заполненная часть и ручка, TRACK — дорожка,
    RING — кольцо вокруг ручки (цвет фона карточки). Колесо мыши окно листает, поэтому оно не двигает ползунок."""
    ACCENT = "#ffcfa3"
    TRACK = "#46464f"
    RING = "#26262c"
    HEIGHT = 22

    def __init__(self, orientation=None, parent=None):
        super().__init__(orientation if orientation is not None else Qt.Orientation.Horizontal, parent)
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def wheelEvent(self, e):
        e.ignore()

    def _margin(self):
        return self.HEIGHT / 2

    def _x_for(self, value):
        m = self._margin()
        span = max(1.0, self.width() - 2 * m)
        k = (value - self.minimum()) / max(1, self.maximum() - self.minimum())
        return m + span * k

    def _value_at(self, x):
        m = self._margin()
        span = max(1.0, self.width() - 2 * m)
        k = max(0.0, min(1.0, (x - m) / span))
        return int(round(self.minimum() + k * (self.maximum() - self.minimum())))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            self.setValue(self._value_at(e.position().x()))
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.isSliderDown():
            self.setValue(self._value_at(e.position().x()))
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.isSliderDown():
            self.setSliderDown(False)
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        h = self.HEIGHT
        cy = self.height() / 2
        x = self._x_for(self.value())
        groove_h = 4
        m = self._margin()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.TRACK))
        p.drawRoundedRect(QRectF(m, cy - groove_h / 2, self.width() - 2 * m, groove_h), groove_h / 2, groove_h / 2)
        p.setBrush(QColor(self.ACCENT))
        p.drawRoundedRect(QRectF(m, cy - groove_h / 2, max(0.0, x - m), groove_h), groove_h / 2, groove_h / 2)
        r = h / 2 - 1
        p.setPen(QPen(QColor(self.RING), 2))
        p.setBrush(QColor(self.ACCENT))
        p.drawEllipse(QRectF(x - r, cy - r, 2 * r, 2 * r))
        p.end()
