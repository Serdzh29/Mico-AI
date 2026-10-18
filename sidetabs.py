"""Боковое меню настроек: разделы слева, содержимое справа. Заменяет полоску вкладок.
Интерфейс повторяет нужное от QTabWidget (addTab, count, widget, setTabEnabled…), поэтому поиск и страницы не меняются."""
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QStyledItemDelegate
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget, QVBoxLayout, QWidget

SLIDE_MS = 240                       # сколько длится переезд полоски от пункта к пункту


class _NavDelegate(QStyledItemDelegate):
    """Пункт меню: фон и текст задаёт стиль (включая подсветку при наведении). Полоску рисует SideTabs."""
    accent = "#4cc2c4"


class SideTabs(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._names = []
        self._icon_color = "#9a9a9a"             # нейтральный серый: подходит светлой и тёмной теме
        self._nav = QListWidget()
        self._nav.setObjectName("sideNav")
        self._nav.setFixedWidth(212)
        self._nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._delegate = _NavDelegate(self._nav)
        self._nav.setItemDelegate(self._delegate)
        self._nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._title = QLabel()
        self._title.setObjectName("pageTitle")
        self._stack = QStackedWidget()
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(10)
        right.addWidget(self._title)
        right.addWidget(self._stack, 1)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(self._nav)
        lay.addLayout(right, 1)
        self._nav.currentRowChanged.connect(self._show_row)
        # Полоска у выбранного пункта: один виджет, который плавно переезжает к нужному пункту (как в видео).
        self._bar = QFrame(self._nav.viewport())
        self._bar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._bar.setObjectName("navBar")
        self._slide = QPropertyAnimation(self._bar, b"geometry", self)
        self._slide.setDuration(SLIDE_MS)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._set_bar_color(self._delegate.accent)
        self._nav.verticalScrollBar().valueChanged.connect(lambda _v: self._move_bar(animate=False))

    def addTab(self, widget, title, icon=None):
        self._stack.addWidget(widget)
        self._names.append(title)
        item = QListWidgetItem(title)
        if icon:
            import uiicons
            item.setIcon(uiicons.icon(icon, self._icon_color, 18))
            item.setSizeHint(QSize(0, 44))
        self._nav.addItem(item)
        if self._nav.count() == 1:
            self._nav.setCurrentRow(0)
        return self._stack.count() - 1

    def _show_row(self, row):
        if 0 <= row < len(self._names):
            self._stack.setCurrentIndex(row)
            self._title.setText(self._names[row])
            self._move_bar(animate=self.isVisible())

    def _set_bar_color(self, color):
        self._bar.setStyleSheet(f"QFrame#navBar {{ background:{color}; border-radius:1px; }}")

    def _target_rect(self, row):
        """Куда встаёт полоска: узкая вертикальная черта у левого края выбранного пункта."""
        item = self._nav.item(row)
        if item is None:
            return None
        r = self._nav.visualItemRect(item)
        return QRect(r.left() + 1, r.top() + 9, 3, max(0, r.height() - 18))

    def _move_bar(self, animate=True):
        row = self._nav.currentRow()
        target = self._target_rect(row) if row >= 0 else None
        if target is None:
            self._bar.hide()
            return
        self._bar.show()
        self._bar.raise_()
        self._slide.stop()
        if animate and self._bar.geometry() != target and not self._bar.geometry().isNull():
            self._slide.setStartValue(self._bar.geometry())
            self._slide.setEndValue(target)
            self._slide.start()
        else:
            self._bar.setGeometry(target)

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, lambda: self._move_bar(animate=False))   # после первой расстановки пунктов

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._move_bar(animate=False)

    def set_accent(self, color):
        """Цвет полоски у выбранного раздела — тот же, что выбрал пользователь в Windows."""
        self._delegate.accent = color
        self._set_bar_color(color)

    def set_icon_color(self, color):
        self._icon_color = color

    def count(self):
        return self._stack.count()

    def widget(self, i):
        return self._stack.widget(i)

    def indexOf(self, w):
        return self._stack.indexOf(w)

    def currentIndex(self):
        return self._stack.currentIndex()

    def setCurrentIndex(self, i):
        self._nav.setCurrentRow(i)

    def setTabEnabled(self, i, on):
        item = self._nav.item(i)
        if item is None:
            return
        flags = item.flags()
        item.setFlags(flags | Qt.ItemFlag.ItemIsEnabled if on else flags & ~Qt.ItemFlag.ItemIsEnabled)
