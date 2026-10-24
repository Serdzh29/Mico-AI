"""Боковое меню настроек: разделы слева, содержимое справа. Заменяет полоску вкладок.
Интерфейс повторяет нужное от QTabWidget (addTab, count, widget, setTabEnabled…), поэтому поиск и страницы не меняются."""
from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QSize, Qt, QTimer, QVariantAnimation
from PyQt6.QtWidgets import QFrame, QStyledItemDelegate
import uiicons
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget, QVBoxLayout, QWidget

SLIDE_MS = 240                       # сколько длится переезд полоски от пункта к пункту
PAGE_MS = 220                        # сколько длится переезд нового раздела
SLIDE_PX = 28                        # с какого расстояния справа въезжает раздел
ICON_MS = 760                        # сколько длится анимация иконки раздела (мягко, без рывков)


class _NavDelegate(QStyledItemDelegate):
    """Пункт меню рисует стиль целиком: фон, текст и иконку. Полоску рисует SideTabs.
    Иконку не рисуем сами поверх пункта: иначе её место расходилось с остальными иконками.
    Анимация иконки — это смена обычной иконки на её кадры, так что все иконки стоят одинаково."""
    accent = "#4cc2c4"
    icon_color = "#9a9a9a"


class SideTabs(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._names = []
        self._icon_color = "#9a9a9a"             # нейтральный серый: подходит светлой и тёмной теме
        self._anim_item = None                   # пункт, чья иконка сейчас оживает
        self._nav = QListWidget()
        self._nav.setObjectName("sideNav")
        self._nav.setFixedWidth(212)
        self._nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._delegate = _NavDelegate(self._nav)
        self._nav.setItemDelegate(self._delegate)
        self._nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav.setIconSize(QSize(18, 18))
        self._nav.itemPressed.connect(lambda item: self._animate_icon(self._nav.row(item)))
        self._icon_anim = QVariantAnimation(self)           # прогресс анимации иконки: один проход
        self._icon_anim.setDuration(ICON_MS)
        self._icon_anim.setStartValue(0.0)
        self._icon_anim.setEndValue(1.0)
        self._icon_anim.setEasingCurve(QEasingCurve.Type.InOutSine)   # начало и конец движения плавные
        self._icon_anim.valueChanged.connect(self._on_icon_anim)
        self._icon_anim.finished.connect(self._icon_done)
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
        self._page_anim = None                   # текущее проявление раздела (одно за раз)

    def _animate_icon(self, row):
        """Иконка выбранного раздела проигрывает свою анимацию один раз (глаз моргает, часы делают круг…)."""
        item = self._nav.item(row) if row >= 0 else None
        if item is None or item.data(Qt.ItemDataRole.UserRole) not in uiicons.ANIMATED:
            return
        self._anim_item = item
        self._icon_anim.stop()
        self._icon_anim.start()

    def _on_icon_anim(self, v):
        item = self._anim_item
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        # кадр — обычная иконка того же размера, что и остальные: положение совпадает
        item.setIcon(uiicons.icon_frame(name, self._icon_color, float(v), 18))

    def _icon_done(self):
        item, self._anim_item = self._anim_item, None
        if item is not None:
            name = item.data(Qt.ItemDataRole.UserRole)
            item.setIcon(uiicons.icon(name, self._icon_color, 18))     # возвращаем обычную иконку

    def addTab(self, widget, title, icon=None):
        self._stack.addWidget(widget)
        self._names.append(title)
        item = QListWidgetItem(title)
        if icon:
            item.setIcon(uiicons.icon(icon, self._icon_color, 18))
            item.setData(Qt.ItemDataRole.UserRole, icon)      # по имени рисуем анимированную версию
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
            if self.isVisible():
                self._fade_in_page(self._stack.currentWidget())
                self._animate_icon(row)                        # выбранный раздел — его иконка оживает

    def _fade_in_page(self, page):
        """Раздел мягко въезжает справа. Без эффекта прозрачности: тот дорогой на большом окне (особенно развёрнутом)
        и из-за него переключение раздела дёргалось. Сдвиг position дешёвый и идёт ровно."""
        if self._page_anim is not None:
            self._page_anim.stop()
            self._page_anim = None
        if page is None:
            return
        start = QPoint(SLIDE_PX, 0)
        page.move(start)
        anim = QPropertyAnimation(page, b"pos", self)
        anim.setDuration(PAGE_MS)
        anim.setStartValue(start)
        anim.setEndValue(QPoint(0, 0))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def done():
            if self._page_anim is anim:
                self._page_anim = None
                page.move(0, 0)
        anim.finished.connect(done)
        self._page_anim = anim
        anim.start()

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
        self._delegate.icon_color = color
        for i in range(self._nav.count()):                 # уже добавленные иконки берут новый цвет
            item = self._nav.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setIcon(uiicons.icon(name, color, 18))

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
