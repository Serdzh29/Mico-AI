"""Настройки в два уровня: раздел слева → плитки подразделов справа → настройки подраздела.
Во время поиска все подразделы показываются одним списком, чтобы совпадения были видны."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QScrollArea,
                             QStackedWidget, QVBoxLayout, QWidget)
import uiicons


def _scroll(w):
    sc = QScrollArea()
    sc.setWidgetResizable(True)
    sc.setFrameShape(QFrame.Shape.NoFrame)
    sc.setWidget(w)
    return sc


class Tile(QFrame):
    """Карточка подраздела в стиле панели системы: иконка слева вверху, название и описание внизу, стрелка справа.
    Нажатие открывает подраздел."""
    clicked = pyqtSignal()

    def __init__(self, title, desc="", parent=None, icon=None):
        super().__init__(parent)
        self.setObjectName("subTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(128)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 16, 16)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        if icon:                                       # минималистичная иконка, серая, без цвета
            ic = QLabel()
            ic.setFixedSize(24, 24)
            ic.setPixmap(uiicons.icon(icon, "#9a9a9a", 24).pixmap(24, 24))
            top.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        top.addStretch(1)
        arrow = QLabel()
        arrow.setFixedSize(14, 14)
        arrow.setPixmap(uiicons.icon("chev_right", "#9a9a9a", 14).pixmap(14, 14))
        top.addWidget(arrow, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(top)
        lay.addStretch(1)
        t = QLabel(title)
        t.setObjectName("tileTitle")
        t.setWordWrap(True)
        lay.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("hint")
            d.setWordWrap(True)
            lay.addWidget(d)

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class SubPages(QWidget):
    """sections: [(виджет настроек, название, описание[, имя иконки])]."""

    def __init__(self, sections, parent=None):
        super().__init__(parent)
        self._park = QWidget(self)                     # здесь живут подразделы, которые сейчас не показаны
        self._park.hide()
        self._sections = []
        self._icons = []
        for widget, title, desc, *rest in sections:
            self._icons.append(rest[0] if rest else None)
            gb = QGroupBox(title)
            lay = QVBoxLayout(gb)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)
            lay.addWidget(widget)
            gb.setParent(self._park)
            self._sections.append((gb, title, desc))
        self._stack = QStackedWidget()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._stack)

        hub = QWidget()                                # 0: плитки подразделов
        grid = QGridLayout(hub)
        grid.setContentsMargins(4, 4, 8, 4)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for i, (_gb, title, desc) in enumerate(self._sections):
            tile = Tile(title, desc, icon=self._icons[i])
            tile.clicked.connect(lambda i=i: self.open(i))
            grid.addWidget(tile, i // 2, i % 2)
        grid.setRowStretch(grid.rowCount(), 1)
        self._stack.addWidget(_scroll(hub))

        det = QWidget()                                # 1: один подраздел
        dl = QVBoxLayout(det)
        dl.setContentsMargins(2, 2, 6, 2)
        dl.setSpacing(10)
        back = QPushButton("‹  Назад")
        back.setObjectName("flat")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self.show_hub)
        dl.addWidget(back, 0, Qt.AlignmentFlag.AlignLeft)
        self._host = QVBoxLayout()
        dl.addLayout(self._host)
        dl.addStretch(1)
        self._stack.addWidget(_scroll(det))

        allw = QWidget()                               # 2: все подразделы сразу, во время поиска
        self._all = QVBoxLayout(allw)
        self._all.setContentsMargins(2, 2, 6, 2)
        self._all.setSpacing(10)
        self._all.addStretch(1)
        self._stack.addWidget(_scroll(allw))

    def _release(self):
        for layout in (self._host, self._all):
            for gb, _t, _d in self._sections:
                layout.removeWidget(gb)
        for gb, _t, _d in self._sections:
            gb.setParent(self._park)
        self._park.hide()

    def open(self, i):
        self._release()
        gb = self._sections[i][0]
        self._host.insertWidget(0, gb)
        gb.show()
        self._stack.setCurrentIndex(1)

    def show_hub(self):
        self._release()
        self._stack.setCurrentIndex(0)

    def show_all(self, on):
        if on:
            self._release()
            for gb, _t, _d in self._sections:
                self._all.insertWidget(self._all.count() - 1, gb)
                gb.show()
            self._stack.setCurrentIndex(2)
        elif self._stack.currentIndex() == 2:
            self.show_hub()
