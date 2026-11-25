"""Боковое меню настроек: разделы слева, содержимое справа. Заменяет полоску вкладок.
Интерфейс повторяет нужное от QTabWidget (addTab, count, widget, setTabEnabled…), поэтому поиск и страницы не меняются."""
import time
from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QSize, Qt, QTimer, QVariantAnimation
from PyQt6.QtWidgets import QFrame, QStyledItemDelegate
from ui import icons as uiicons
from ui import winter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtGui import QColor, QPainter


class _Veil(QWidget):
    """Лёгкая завеса цвета фона: при смене раздела она тает за доли секунды, и новый раздел «проявляется».
    Раньше прошлый раздел целиком снимался в картинку и ещё двигался новый — на больших страницах это вешало интерфейс."""

    def __init__(self, color, parent):
        super().__init__(parent)
        self.color, self.k = color, 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        c = QColor(self.color)
        c.setAlphaF(max(0.0, min(1.0, self.k)))
        p.fillRect(self.rect(), c)
        p.end()


class _Ghost(QWidget):
    """Снимок прошлого раздела поверх нового: плавно тает и уезжает влево. Рисуем картинку с прозрачностью —
    это дешевле эффекта прозрачности на большом окне, поэтому переход идёт ровно и в развёрнутом окне."""

    def __init__(self, pix, parent):
        super().__init__(parent)
        self.pix, self.k = pix, 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setOpacity(max(0.0, self.k))
        p.drawPixmap(round(-(1 - self.k) * 24), 0, self.pix)
        p.end()

SLIDE_MS = 240                       # сколько длится переезд полоски от пункта к пункту
PAGE_MS = 240                        # сколько длится переезд нового раздела
SLIDE_PX = 48                        # с какого расстояния справа въезжает раздел
ICON_MS = 1000                        # сколько длится анимация иконки раздела (мягко, без рывков)


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
        self._winter = False                     # зимний вид: снежные значки и сугробы внизу меню
        self._frames = {}                        # готовые кадры анимаций иконок: рисуем один раз, потом только подставляем
        self._nav = QListWidget()
        self._nav.setObjectName("sideNav")
        self._nav.setFixedWidth(212)
        self._nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._delegate = _NavDelegate(self._nav)
        self._nav.setItemDelegate(self._delegate)
        self._nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._nav.setIconSize(QSize(18, 18))
        self._fx_timer = QTimer(self)                       # ход анимации иконки: кадр каждые 16 мс, время считаем сами
        self._fx_timer.setInterval(16)
        self._fx_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._fx_timer.timeout.connect(self._tick_icon)
        self._fx_t0 = 0.0
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

    FRAMES = 64

    def _animate_icon(self, row):
        """Иконка выбранного раздела проигрывает свою анимацию при КАЖДОМ нажатии. Раньше её вели через QVariantAnimation, и
        повторный запуск мог не сработать; теперь ход времени считаем сами, и новая анимация всегда начинается с нуля."""
        item = self._nav.item(row) if row >= 0 else None
        if item is None or item.data(Qt.ItemDataRole.UserRole) not in uiicons.ANIMATED:
            return
        self._stop_icon_fx()                      # прошлая анимация гасится сразу, её значок встаёт на место
        self._anim_item = item
        self._fx_t0 = time.monotonic()
        self._fx_timer.start()
        self._tick_icon()

    def _stop_icon_fx(self):
        self._fx_timer.stop()
        item, self._anim_item = self._anim_item, None
        if item is not None:
            name = item.data(Qt.ItemDataRole.UserRole)
            item.setIcon(self._static_icon(name))                        # обычная иконка

    def _tick_icon(self):
        item = self._anim_item
        if item is None:
            self._fx_timer.stop()
            return
        u = (time.monotonic() - self._fx_t0) / (ICON_MS / 1000.0)
        if u >= 1.0:
            self._stop_icon_fx()
            return
        item.setIcon(self._frame_icon(item.data(Qt.ItemDataRole.UserRole), u))

    def _frame_icon(self, name, v):
        """Кадр анимации из кэша: рисуется один раз (в двойном размере, поэтому края гладкие), потом только подставляется."""
        key = (name, self._icon_color, uiicons.ANIM_ACCENT, self._winter)
        frames = self._frames.get(key)
        if frames is None:
            col = winter.ICE if self._winter else self._icon_color
            frames = [uiicons.icon_frame(name, col, i / (self.FRAMES - 1), 36) for i in range(self.FRAMES)]
            self._frames[key] = frames
        return frames[max(0, min(self.FRAMES - 1, int(round(v * (self.FRAMES - 1)))))]

    def addTab(self, widget, title, icon=None):
        self._stack.addWidget(widget)
        self._names.append(title)
        item = QListWidgetItem(title)
        if icon:
            item.setIcon(self._static_icon(icon))
            item.setData(Qt.ItemDataRole.UserRole, icon)      # по имени рисуем анимированную версию
            item.setSizeHint(QSize(0, 44))
        self._nav.addItem(item)
        if self._nav.count() == 1:
            self._nav.setCurrentRow(0)
        return self._stack.count() - 1

    def _show_row(self, row):
        if 0 <= row < len(self._names):
            old = self._stack.currentWidget()
            animate = self.isVisible() and old is not None and self._stack.indexOf(old) != row
            color = self._bg_color(old) if animate else None
            self._stack.setCurrentIndex(row)
            self._title.setText(self._names[row])          # заголовок без анимации отступа: она пересчитывала всю страницу каждый кадр
            self._move_bar(animate=self.isVisible())
            if animate:
                try:
                    self._veil_in(color)
                except RuntimeError:
                    self._veil = None                      # любой сбой завесы не должен лишать раздел анимации иконки
                self._animate_icon(row)                    # выбранный раздел — его иконка оживает

    def _bg_color(self, page):
        """Цвет фона страницы: берём один пиксель, а не снимаем всю страницу."""
        try:
            img = page.grab(QRect(2, 2, 2, 2)).toImage()
            c = img.pixelColor(0, 0)
            if c.alpha() > 0:
                return c
        except Exception:
            pass
        return self.window().palette().window().color()

    def _veil_in(self, color):
        """Новый раздел проявляется из-под завесы: дёшево и без подвисаний."""
        if getattr(self, "_veil_anim", None) is not None:
            self._veil_anim.stop()
        old_veil = getattr(self, "_veil", None)
        self._veil = None
        if old_veil is not None:
            try:
                old_veil.deleteLater()
            except RuntimeError:                  # прошлая завеса уже удалена после своей анимации: это нормально
                pass
        veil = _Veil(color, self._stack)
        veil.setGeometry(self._stack.rect())
        veil.show()
        veil.raise_()
        anim = QVariantAnimation(self)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setDuration(PAGE_MS)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        def step(v):
            veil.k = float(v)
            veil.update()
        anim.valueChanged.connect(step)

        def done():
            if self._veil is veil:
                self._veil = None                 # ссылку отпускаем сразу: на следующем переключении к удалённой завесе не обращаемся
            try:
                veil.deleteLater()
            except RuntimeError:
                pass
        anim.finished.connect(done)
        self._veil, self._veil_anim = veil, anim
        anim.start()

    def _prewarm(self, i=0):
        """Пока человек читает первую страницу, остальные тихо готовятся (стили, раскладка): первое открытие уже не тормозит."""
        if i >= self._stack.count() or not self.isVisible():
            return
        page = self._stack.widget(i)
        try:
            page.ensurePolished()
            for w in page.findChildren(QWidget):
                w.ensurePolished()
            if page.layout() is not None:
                page.layout().activate()
        except RuntimeError:
            return
        QTimer.singleShot(30, lambda: self._prewarm(i + 1))

    def _ghost_from(self, old):
        try:
            pix = old.grab()
        except Exception:
            return
        if getattr(self, "_ghost", None) is not None:
            self._ghost.deleteLater()
        g = _Ghost(pix, self._stack)
        g.setGeometry(0, 0, self._stack.width(), self._stack.height())
        g.show()
        g.raise_()
        self._ghost = g
        anim = QVariantAnimation(self)
        anim.setDuration(int(PAGE_MS * 0.8))
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        def step(v):
            g.k = float(v)
            g.update()

        def done():
            g.deleteLater()
            if getattr(self, "_ghost", None) is g:
                self._ghost = None
        anim.valueChanged.connect(step)
        anim.finished.connect(done)
        self._ghost_anim = anim
        anim.start()

    def _fade_in_page(self, page):
        """Раздел мягко въезжает справа. Без эффекта прозрачности: тот дорогой на большом окне (особенно развёрнутом)
        и из-за него переключение раздела дёргалось. Сдвиг position дешёвый и идёт ровно."""
        if self._page_anim is not None:
            self._page_anim.stop()
            self._page_anim = None
        if page is None:
            return
        from ui import motion
        motion.hold(PAGE_MS + 60)                             # снег стоит, пока раздел въезжает
        start = QPoint(SLIDE_PX, 0)
        page.move(start)
        anim = QPropertyAnimation(page, b"pos", self)
        anim.setDuration(PAGE_MS)
        anim.setStartValue(start)
        anim.setEndValue(QPoint(0, 0))
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)      # ровный разгон и ровная остановка: без «торможения» в конце

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
        if not getattr(self, "_warmed", False):
            self._warmed = True
            QTimer.singleShot(400, self._prewarm)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._move_bar(animate=False)

    def set_accent(self, color):
        """Цвет полоски у выбранного раздела — тот же, что выбрал пользователь в Windows."""
        self._delegate.accent = color
        uiicons.set_anim_accent(color)                 # эффекты анимации иконок — цвета Mico
        self._set_bar_color(color)

    def _static_icon(self, name):
        """Обычная иконка раздела. Зимой: льдисто-голубая, со снежной шапкой сверху."""
        if self._winter:
            return uiicons.icon(name, winter.ICE, 18)
        return uiicons.icon(name, self._icon_color, 18)

    def set_winter(self, on):
        """Зимний вид меню: снежные значки и сцена с ёлками, снеговиком и сугробом внизу. Включается и выключается на ходу."""
        on = bool(on)
        if on == self._winter and getattr(self, "_scene", None) is not None:
            return
        self._winter = on
        self._stop_icon_fx()
        for i in range(self._nav.count()):
            item = self._nav.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setIcon(self._static_icon(name))
        if getattr(self, "_scene", None) is None:
            self._wcfg = {"winter_ui": on}

            def bottom():
                n = self._nav.count()
                return self._nav.visualItemRect(self._nav.item(n - 1)).bottom() if n else 0
            self._scene = winter.WinterScene(self._nav.viewport(), self._wcfg, top_fn=bottom)
        self._wcfg["winter_ui"] = on
        self._scene.sync()

    def set_icon_color(self, color):
        self._icon_color = color
        self._delegate.icon_color = color
        if self._winter:
            return                                             # зимой значки ледяные, цвет темы им не нужен
        for i in range(self._nav.count()):                 # уже добавленные иконки берут новый цвет
            item = self._nav.item(i)
            name = item.data(Qt.ItemDataRole.UserRole)
            if name:
                item.setIcon(self._static_icon(name))

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
