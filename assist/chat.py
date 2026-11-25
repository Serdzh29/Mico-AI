"""Чат Mico AI — свой, минималистичный (не обычный чат Mico AI). Все надписи — тем же шрифтом, что в настройках (Segoe UI Variable).
Сообщения появляются плавно; пока Mico AI думает, думает и он сам (анимация Mico AI). Открывается над Mico AI, закрывается ✕."""
from PyQt6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import (QLayout, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QLineEdit, QMenu, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)
import html
import re
import time
import webbrowser
import i18n

i18n.EN.update({
    "Нужно обновить Mico": "Mico needs an update", "Без обновления я не буду работать": "I won't work without the update",
    "Обновить Mico": "Update Mico",
    "Пожалуйста, обнови Mico: вышла новая версия. Скачай её на сайте и поставь поверх.":
        "Please update Mico: a new version is out. Download it from the site and install it over this one.",
    "Нужно обновить Mico: без обновления я не буду работать. Скачай новую версию на сайте.":
        "Mico needs an update: I won't work without it. Download the new version from the site.",
    "Открыть чат": "Open chat", "Скачиваю распознавание речи, один раз": "Downloading speech recognition (one time)",
    "Скачиваю голос, один раз": "Downloading the voice (one time)", "Загружаю голос…": "Loading the voice…",
    "Загружаю распознавание речи…": "Loading speech recognition…",
})
from ui import chatlook as chat_look


from assist import intel
from ui import theme
from ui import icons as uiicons
from ui.onboarding import COLORS as PALETTE     # те же цвета, что при первом запуске
from voice import models as voice_models

WIDTH = 390                     # узкий, но более высокий чат рядом с Mico
BASE_H = 430
MAX_HEIGHT = 480
CHAT_MIN_H = 210
CHAT_GAP = 12                   # зазор между чатом и Mico AI, px
CHAR_LIMIT = 2000               # лимит символов в запросе: считаются все буквы, знаки и пробелы
WORD_LIMIT = CHAR_LIMIT         # прежнее имя оставлено для совместимости
BLOB_DOCK_K = 0.85              # доля размера Mico AI в шапке боковой панели (было 0.62)


def _flags():
    return Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


class LoadBar(QWidget):
    """Тонкая полоска загрузки: заполняется по мере скачивания; пока размер неизвестен, по ней бежит светлый отрезок."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self.value = None                    # 0…1 или None, если процент неизвестен
        self.accent = "#FFCFA3"
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)

    def set_value(self, v):
        self.value = v
        if v is None and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def showEvent(self, e):
        if self.value is None:
            self._timer.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def _tick(self):
        self._t = (self._t + 0.025) % 1.4
        self.update()

    def paintEvent(self, _):
        from PyQt6.QtGui import QColor, QPainter
        from PyQt6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        track = QColor(self.accent)
        track.setAlpha(46)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        p.setBrush(QColor(self.accent))
        if self.value is None:
            x = (self._t - 0.2) * w
            seg = QRectF(max(0.0, x), 0, min(w * 0.3, w - max(0.0, x)), h)
            if seg.width() > 0:
                p.drawRoundedRect(seg, h / 2, h / 2)
        else:
            p.drawRoundedRect(QRectF(0, 0, max(h, w * max(0.0, min(1.0, self.value))), h), h / 2, h / 2)
        p.end()


class AIChat(QWidget):
    send = pyqtSignal(str)      # пользователь написал — уходит Mico AI
    closed = pyqtSignal()       # чат закрыли
    dnd = pyqtSignal(int)       # «не беспокоить» на N минут (0 — выключить)
    rewrite = pyqtSignal(str)   # «short» или «long» — переписать последний ответ
    activity = pyqtSignal()     # человек трогает чат: Mico AI не засыпает
    color_pick = pyqtSignal(str) # цвет из палитры: Mico AI крутится и перекрашивается
    voice_toggle = pyqtSignal(bool)  # озвучивать ответы: вкл/выкл
    voice_pick = pyqtSignal(str)     # выбрали другой голос
    listen = pyqtSignal()            # микрофон: начать или закончить запись
    voice_mute = pyqtSignal()        # голосовой режим в чате: микрофон выключить/включить
    voice_speed = pyqtSignal(float)  # скорость речи
    voice_color = pyqtSignal(str)    # цвет Mico из палитры
    voice_subs = pyqtSignal(bool)    # субтитры (слова — переписка в чате) вкл/выкл
    voice_exit = pyqtSignal()        # завершить голосовой чат
    settings_all = pyqtSignal()      # «Все настройки…» из меню бокового меню
    profile_requested = pyqtSignal() # аватар: открыть «о себе»

    def __init__(self, cfg):
        self._cfg = cfg                                    # общий словарь настроек: черновик хранится в нём
        super().__init__(None, _flags())
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anims = []
        self._fade = None
        self._blob = None                        # Mico AI, рядом с которым стоит чат
        self._docked_blob = False                # живой Mico AI сейчас в шапке боковой панели
        self._blob_anim = None                   # полёт Mico AI в шапку панели
        self._last_lift = 0.0                    # когда последний раз поднимали Mico AI над панелью
        self.save_cfg = None                     # main: сохранить настройки (смена стиля общения)
        self._pos_busy = False                   # первые ~320 мс чат выезжает на место — не мешаем анимации
        self._follow = QTimer(self)              # чат едет за Mico AI: он мог прыгнуть, уехать во сне или его перетащили
        self._follow.setTimerType(Qt.TimerType.PreciseTimer)   # ровно в ритме Mico AI, без рывков
        self._follow.setInterval(16)   # 60 кадров: как у Mico AI, без лишних перерисовок окна
        self._follow.timeout.connect(self._follow_blob)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)   # содержимое не раздвигает окно: чат всегда своей ширины и на своём месте
        self.card = QFrame(self)
        self.card.setObjectName("card")
        from ui import winter as _winter
        self._winter_snow = _winter.install(self.card, self.cfg, radius=22, scene=True, festive=True)   # зимой в чате идёт снег и лежат сугробы
        root.setContentsMargins(16, 16, 16, 16)               # запас вокруг контура: он не обрезается краем прозрачного окна
        root.addWidget(self.card)
        body = QHBoxLayout(self.card)                      # слева выезжающее меню, справа — чат
        body.setContentsMargins(1, 1, 1, 1)                 # дочерние панели не перекрывают скруглённую границу карточки
        body.setSpacing(0)
        lay = QVBoxLayout()
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(12)
        body.addLayout(lay, 1)
        accent_c = self.cfg.get("color", "#FFCFA3")
        self.head_bar = QFrame()
        self.head_bar.setObjectName("chatHeadBar")
        hb = QVBoxLayout(self.head_bar)
        hb.setContentsMargins(10, 8, 10, 8)
        hb.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.menu_btn = QPushButton()                  # три полоски: недавние чаты
        self.menu_btn.setObjectName("iconBtn")
        self.menu_btn.setIcon(chat_look.menu_icon(accent_c, 18))
        self.menu_btn.setIconSize(QSize(18, 18))
        self.menu_btn.setFixedSize(30, 30)
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setToolTip("Недавние чаты")
        self.menu_btn.clicked.connect(lambda: self._toggle_side())
        self.search = QLineEdit()
        self.search.setObjectName("chatSearch")
        self.search.setPlaceholderText("Поиск по сообщениям")
        self.search.setToolTip("Поиск по чатам и сообщениям")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._search_changed)
        close = QPushButton()
        close.setObjectName("iconBtn")
        close.setIcon(chat_look.close_icon(chat_look.icon_ink(theme.is_dark(self.cfg)), 16))
        close.setIconSize(QSize(16, 16))
        close.setFixedSize(30, 30)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setToolTip("Закрыть чат")
        close.clicked.connect(self.dismiss)
        gear = QPushButton()                            # шестерёнка рядом с крестиком — все настройки
        gear.setObjectName("iconBtn")
        gear.setIcon(uiicons.icon("gear", chat_look.icon_ink(theme.is_dark(self.cfg)), 18, width=1.4))
        gear.setIconSize(QSize(18, 18))
        gear.setFixedSize(30, 30)
        gear.setCursor(Qt.CursorShape.PointingHandCursor)
        gear.setToolTip(i18n.t("Настройки"))
        gear.clicked.connect(lambda: self.settings_all.emit())
        top.addWidget(self.menu_btn)
        top.addWidget(self.search, 1)
        top.addWidget(gear)
        top.addWidget(close)
        hb.addLayout(top)
        lay.addWidget(self.head_bar)
        # живой Mico AI сверху панели — на месте логотипа Copilot; под ним — выбор стиля общения и чат
        self.blob_slot = QWidget()
        self.blob_slot.setObjectName("blobSlot")
        bs = QVBoxLayout(self.blob_slot)         # портрет Mico AI — пока живой Mico AI не встал в шапку
        bs.setContentsMargins(0, 0, 0, 0)
        self.dock_mico = chat_look.MicoIcon(120, accent_c)
        bs.addWidget(self.dock_mico, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.blob_slot)
        self.style_row = self._build_style_row()
        lay.addWidget(self.style_row)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("msgScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.box = QWidget()
        self.box.setObjectName("msgHost")
        self.col = QVBoxLayout(self.box)
        self.col.setContentsMargins(0, 4, 0, 4)
        self.col.setSpacing(10)
        self._has_msgs = False                           # в ленте пока нет ни одной реплики
        self._voice_view = False                         # идёт голосовой режим прямо в этом чате
        self.greeting = chat_look.Greeting(accent_c)     # пустой чат — как Windows Copilot: Mico, стиль и кнопки действий
        self.greeting.set_title("Mico")                   # название под иконкой, как «Copilot» у Windows
        self.col.addWidget(self.greeting)
        self.greeting.action.connect(lambda p: self.send.emit(p))
        self.greeting.style_picked.connect(self._set_style)
        self.greeting.settings_clicked.connect(self.settings_all.emit)
        self.col.addStretch(1)
        self.scroll.setWidget(self.box)
        # полоска цветов: внутри чата, между шапкой и сообщениями — сообщения сдвигаются, а не перекрываются
        self.palette_bar = QFrame()
        self.palette_bar.setObjectName("palette")
        self.palette_bar.setVisible(False)
        self.palette_row = QHBoxLayout(self.palette_bar)
        self.palette_row.setContentsMargins(12, 8, 12, 8)
        self.palette_row.setSpacing(7)
        lay.addWidget(self.palette_bar)
        lay.addWidget(self.scroll, 1)
        self._store = None                                 # хранилище чатов (см. attach)
        self._current_cb = self._open_cb = self._new_cb = None
        self._rows = {}                                    # id реплики → её блок (для перехода из поиска)
        self.results = QListWidget(self.card)              # результаты поиска поверх ленты
        self.results.setObjectName("results")
        self.results.setWordWrap(True)
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results.itemClicked.connect(self._open_result)
        self.results.hide()
        self.side = chat_look.Sidebar(accent_c, self.card, dark=theme.is_dark(self.cfg)) # боковое меню: недавние чаты, «Новый чат», настройки внизу
        self.side.open_chat.connect(lambda cid: self._open_conv(cid))
        self.side.new_chat.connect(self._new_conv)
        body.insertWidget(0, self.side)                    # меню скрыто до нажатия на кнопку-полоски
        self._side_width = 224
        self._side_open = False
        self._side_anim = None
        self.side.setMinimumWidth(0)
        self.side.setMaximumWidth(0)
        self.side.hide()
        self.refresh_side()
        self._rw = None                            # строка «Короче / Подробнее» под последним ответом
        self._offer_row = None                     # кнопки под предложением Mico AI
        self._thinking = None                      # строка с анимацией, пока Mico AI готовит ответ
        self._live = self._live_row = None         # живой пузырь ответа, пока он печатается
        self._live_buf = ""
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText(i18n.t("Спроси что угодно…"))
        self.inp.setObjectName("chatInput")
        self.inp.returnPressed.connect(self._send)
        self.on_draft = None                               # main сохраняет черновик на диск
        self._draft_timer = QTimer(self)                   # сохраняем через паузу, а не на каждую букву
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(800)
        self._draft_timer.timeout.connect(self._save_draft)
        self.inp.textChanged.connect(self._on_input_text)
        self.btn = QPushButton()
        self.btn.setObjectName("send")
        self.btn.setFixedSize(28, 28)                        # круглая кнопка отправки в нижнем ряду, как у Gemini
        self.btn.setToolTip("Отправить")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._send)
        row.setSpacing(6)
        self.mic_btn = QPushButton()
        self.mic_btn.setObjectName("iconBtn")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setFixedSize(28, 28)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setToolTip("Голосовой режим: чат свернётся, Mico будет слушать")
        self.mic_btn.clicked.connect(self.listen.emit)
        row.addWidget(self.inp, 1)                           # сверху — только поле ввода; модель, микрофон и отправка — в нижнем ряду, как у Gemini
        # поле ввода: сверху строка с текстом, снизу полоска под цвет Mico — снимок экрана слева, счётчик слов справа
        self.word_count = QLabel()                         # лимит слов в запросе: 0/300, красным — если превышен
        self.word_count.setObjectName("wordCount")
        self.word_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        row.setContentsMargins(12, 6, 12, 0)
        strip = QFrame()
        strip.setObjectName("inputStrip")
        sh = QHBoxLayout(strip)
        sh.setContentsMargins(12, 0, 8, 8)
        sh.setSpacing(6)
        self.model_pill = chat_look.ModelPill(self.cfg, save=lambda: self.save_cfg() if self.save_cfg else None)
        self.model_pill.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)   # узкий чат сжимает кнопку модели, а не растёт сам
        self.model_pill.setMinimumWidth(0)
        sh.addWidget(self.word_count, 0, Qt.AlignmentFlag.AlignVCenter)    # счётчик символов — слева
        sh.addStretch(1)
        sh.addWidget(self.model_pill, 0, Qt.AlignmentFlag.AlignVCenter)    # модель, микрофон и отправка — справа в один ряд, рядом с полем ввода
        sh.addWidget(self.mic_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        sh.addWidget(self.btn, 0, Qt.AlignmentFlag.AlignVCenter)
        box = QFrame()                                     # поле ввода в скруглённой рамке, светлее фона чата
        self.input_box = box                               # в голосовом режиме внутри чата строка ввода скрывается
        box.setObjectName("inputBox")
        bv = QVBoxLayout(box)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(0)
        bv.addLayout(row)
        bv.addWidget(strip)
        self._gate = None                                  # нужно обновление: чат закрыт просьбой обновить Mico
        self._build_gate()
        lay.addWidget(self.gate_box)
        self._build_voice_load()
        lay.addWidget(self.voice_load)
        self._build_voice_bar()
        lay.addWidget(self.voice_bar)                      # кнопки голосового режима — над полем ввода, только пока он идёт
        lay.addWidget(box)                                 # без аватара: поле ввода занимает всю ширину
        self._update_count()
        self.refresh_profile()
        self.refresh_welcome()                          # кнопки действий на пустом экране — свежий набор
        self._update_greeting()
        self.setFont(theme.app_font(10))                # тот же шрифт с первого виджета
        self._apply_style()
        self.resize(round(WIDTH * self.factor()), round(MAX_HEIGHT * self.factor()))

    def _palette_menu(self):
        """Полоска цветов открывается и закрывается в самом чате. Выбранный цвет уходит в color_pick."""
        if self.palette_bar.isVisible():
            self.palette_bar.setVisible(False)
            return
        self._build_palette()
        self.palette_bar.setVisible(True)

    def _build_palette(self):
        dark = theme.is_dark(self.cfg)
        ring = "#ffffff" if dark else "#1a1a1a"
        current = str(self.cfg.get("color", "#FFCFA3")).upper()
        while self.palette_row.count():                 # перестраиваем, чтобы обводка совпадала с текущим цветом
            item = self.palette_row.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.palette_row.addStretch(1)
        for hex_c, name in PALETTE:
            b = QPushButton()
            b.setFixedSize(24, 24)                   # круг держит border-radius, без маски: маска резала кнопку
            b.setToolTip(name)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            # рамка одинаковой толщины у всех: выбранный обведён цветом темы, остальные — прозрачной
            edge = f"2px solid {ring}" if hex_c.upper() == current else "2px solid transparent"
            b.setStyleSheet(f"QPushButton {{ background:{hex_c}; border:{edge}; border-radius:12px; "
                            f"padding:0; margin:0; min-width:0; min-height:0; }}"
                            f"QPushButton:hover {{ border:2px solid {ring}; }}")
            b.clicked.connect(lambda _=False, c=hex_c: self._palette_pick(c))
            self.palette_row.addWidget(b)
        self.palette_row.addStretch(1)

    def _palette_pick(self, hex_c):
        self.palette_bar.setVisible(False)
        self.color_pick.emit(hex_c)

    def _open_menu(self, anchor=None):
        """Меню чата: цвет, голос и тишина, а также все настройки Mico AI."""
        anchor = anchor or self.menu_btn
        menu = QMenu(anchor)
        color = QAction("Цвет Mico AI…", menu)
        color.triggered.connect(self._palette_menu)
        menu.addAction(color)
        menu.addSeparator()
        on = QAction("Озвучивать ответы", menu)
        on.setCheckable(True)
        on.setChecked(bool(self.cfg.get("voice_on")))
        on.toggled.connect(self.voice_toggle.emit)
        menu.addAction(on)
        vm = menu.addMenu("Голос")
        current = self.cfg.get("voice_name") or voice_models.DEFAULT_VOICE
        for key, title in voice_models.VOICE_TITLES.items():
            act = QAction(("✓ " if key == current else "   ") + title, vm)
            act.triggered.connect(lambda _=False, k=key: self.voice_pick.emit(k))
            vm.addAction(act)
        qm = menu.addMenu("Тишина")
        for minutes, text in intel.DND_CHOICES:
            act = QAction(text, qm)
            act.triggered.connect(lambda _=False, m=minutes: self.dnd.emit(m))
            qm.addAction(act)
        menu.addSeparator()
        allset = QAction("Все настройки Mico AI…", menu)
        allset.triggered.connect(self.settings_all.emit)
        menu.addAction(allset)
        pos = anchor.mapToGlobal(QPoint(anchor.width(), 0))
        menu.exec(QPoint(pos.x() - menu.sizeHint().width(), pos.y() - menu.sizeHint().height()))

    def _apply_style(self):
        """Оформление чата: тема, цвет Mico AI и настройки обводок. Вызывается и на лету, без перезапуска."""
        dark = theme.is_dark(self.cfg)
        r, g, b = intel.hex_rgb(self.cfg.get("color", "#FFCFA3"))
        accent = "#%02X%02X%02X" % (r, g, b)
        self._accent = accent
        if getattr(self, "greeting", None) is not None:
            self.greeting.set_accent(accent)                 # ссылки «Подробнее / Условия / Конфиденциальность» — в цвет Mico
        self.menu_btn.setIcon(chat_look.menu_icon(accent, 18))  # три полоски всегда повторяют цвет Mico
        self._icon_color = chat_look.icon_ink(dark)
        send_text = "#1a1a1a"
        self.btn.setIcon(uiicons.send_icon(send_text))
        self.btn.setIconSize(QSize(16, 16))
        self.mic_btn.setIcon(uiicons.icon("mic", self._icon_color, 15))
        if hasattr(self, "vb_mic"):
            self._refresh_voice_bar()                       # цвет значков голосовых кнопок — цвет Mico
        card_edge = f"1px solid {accent}" if self.cfg.get("chat_outline", True) else "none"
        pal = chat_look.PALETTE[bool(dark)]
        bg = pal["base"]                                   # фон чата = фон настроек: #202020 в тёмной, #F3F3F3 в светлой
        self.setStyleSheet(theme.FONT_QSS + chat_look.qss(dark, accent) + f"""
            QFrame#card {{ background:{bg}; border:{card_edge}; border-radius:22px; }}
            QLabel#chipText {{ color:#9a9aa6; font-size:12px; }}
            QFrame#chip {{ background:transparent; border-radius:8px; }}
            QFrame#palette {{ background:{bg}; border:1px solid rgba(128,128,128,0.25); border-radius:8px; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollArea QWidget {{ background:transparent; }}
            QPushButton#ghost {{ background:transparent; color:#9a9aa6; border:none; font-size:12px; padding:2px 6px; }}
            QPushButton#ghost:hover {{ color:{accent}; }}
            QScrollBar:vertical {{ background:transparent; width:6px; margin:0; }}
            QScrollBar::handle:vertical {{ background:rgba(128,128,128,0.4); border-radius:3px; min-height:24px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
        """)
        if getattr(self, "greeting", None) is not None:
            self.refresh_welcome()                      # значки действий — в цвет текущей темы

    # ----- сообщения -----
    def add_user(self, text):
        self._bubble(text, "me")

    def add_mico(self, text):
        """Итоговый ответ. Если он уже печатался кусками — живой пузырь заменяется финальным текстом на том же месте."""
        if text and text == getattr(self, "_expect_dup", None):   # этот ответ уже показан сразу по готовности
            self._expect_dup = None
            self._drop_live()
            return
        idx = self.col.indexOf(self._live) if self._live is not None else -1
        self._drop_live()
        wrap = self._bubble(chat_look.reflow(text), "mico", animate=idx < 0)
        if 0 <= idx < self.col.count() - 1:
            self.col.removeWidget(wrap)
            self.col.insertWidget(idx, wrap)

    def stream_delta(self, text):
        """Живой ответ: куски текста появляются по мере генерации, а не после полного ответа."""
        if self._live is None:
            self.set_busy(False)                       # точки больше не нужны: текст уже идёт
            self._live = self._bubble("", "mico", animate=False)
            self._live_row = self._live.findChild(chat_look.MessageRow)
            self._live_buf = ""
        self._live_buf += text
        if self._live_row is not None:
            self._live_row.label.setText(html.escape(self._live_buf).replace("\n", "<br>") + " ▌")
        QTimer.singleShot(0, self._scroll_to_bottom_now)

    def live_user(self, text):
        """Голосовой режим с субтитрами: слова пользователя появляются в чате прямо пока он говорит.
        Когда фраза распознана целиком, живой пузырь убирается (end_live_user) и на его место встаёт обычный."""
        text = " ".join(str(text or "").split())
        if not text:
            return
        if getattr(self, "_live_me", None) is None:
            self._live_me = self._bubble("", "me", animate=True)
            self._live_me_row = self._live_me.findChild(chat_look.MessageRow)
        if self._live_me_row is not None:
            self._live_me_row.label.setText(html.escape(text) + " <span style='color:#8a8a8a'>…</span>")
            try:
                self._live_me_row.fit(self.scroll.viewport().width() or WIDTH)
            except Exception:
                pass
        QTimer.singleShot(0, self._scroll_to_bottom_now)

    def end_live_user(self):
        w = getattr(self, "_live_me", None)
        if w is not None:
            self.col.removeWidget(w)
            w.deleteLater()
        self._live_me = self._live_me_row = None

    def _drop_live(self):
        if self._live is not None:
            self.col.removeWidget(self._live)
            self._live.deleteLater()
        self._live = self._live_row = None
        self._live_buf = ""

    def refresh_welcome(self):
        """Кнопки действий на пустом экране — как «Here are some things…» у Windows Copilot."""
        from ui import chips as ui_chips
        apps_fn = getattr(self, "apps_fn", None)            # частые программы — из того же журнала, что в обычном чате
        self.greeting.set_actions(ui_chips.welcome(self.cfg, apps=apps_fn() if apps_fn else None))

    def _update_greeting(self):
        """Пустой чат — как Windows Copilot: Mico сверху, стиль общения и кнопки действий на ПК.
        Появилась реплика или человек начал писать запрос — подсказки уходят.
        Портрет Mico в приветствии — только в обычном окне: в панели сверху и так живой Mico AI."""
        empty = not self._has_msgs
        if empty:
            self.greeting.show_again()
            self.greeting.set_suggest_visible(True)    # пока человек пишет, кнопки остаются
        else:
            self.greeting.fade_out()                   # запрос отправлен — плавно уходят
        self.greeting.set_portrait_visible(not self.side_panel())
        self.style_row.setVisible(not empty)   # выбор стиля живёт в приветствии; дальше — строкой над лентой

    def _update_count(self):
        """Счётчик символов под полем. Больше лимита — отправить нельзя, цифры краснеют."""
        n = len(self.inp.text())               # все символы, включая пробелы
        over = n > CHAR_LIMIT
        self.word_count.setText(f"{n}/{CHAR_LIMIT}")
        self.word_count.setStyleSheet("color: #E5484D;" if over else "")
        self.btn.setEnabled(not over)

    def mousePressEvent(self, e):
        self.activity.emit()
        super().mousePressEvent(e)

    def _on_input_text(self, _t):
        self.activity.emit()
        self._draft_timer.start()
        self._update_count()
        self._update_greeting()                # человек пишет запрос — кнопки действий уходят

    def show_rewrite_row(self):
        """Под последним ответом — «Короче» и «Подробнее». Старую строку убираем: она про прошлый ответ."""
        if self._rw is not None:
            self.col.removeWidget(self._rw)
            self._rw.deleteLater()
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        for mode in ("short", "long"):
            btn = QPushButton(intel.REWRITE_LABELS[mode])
            btn.setObjectName("chipBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, m=mode: self._rewrite_clicked(m))
            h.addWidget(btn)
        h.addStretch(1)
        self._rw = row
        self._add(row)

    def show_offer_row(self, options):
        """Кнопки под предложением Mico AI: [(подпись, действие или None)]. Нажал — кнопки исчезают, действие выполняется.
        None — просто убрать кнопки («Не сейчас»)."""
        self.clear_offer_row()
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        for label, action in options:
            btn = QPushButton(label)
            btn.setObjectName("chipBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, a=action: self._offer_picked(a))
            h.addWidget(btn)
        h.addStretch(1)
        self._offer_row = row
        self._add(row)

    def clear_offer_row(self):
        if self._offer_row is not None:
            self.col.removeWidget(self._offer_row)
            self._offer_row.deleteLater()
            self._offer_row = None

    def _offer_picked(self, action):
        self.clear_offer_row()
        if action is not None:
            action()

    def _rewrite_clicked(self, mode):
        if self._rw is not None:
            self.col.removeWidget(self._rw)
            self._rw.deleteLater()
            self._rw = None
        self.rewrite.emit(mode)

    def _bubble(self, text, kind, rid=None, animate=True):
        self.clear_offer_row()                      # новое сообщение — старые варианты уже не актуальны
        self._has_msgs = True                       # приветствие с кнопками действий больше не нужно
        if self._voice_view:
            self._dock_move()                       # пошла переписка — Mico уезжает из центра обратно в шапку
        self._update_greeting()
        role = "user" if kind == "me" else "mico"
        row = chat_look.MessageRow(role, html.escape(str(text or "")).replace("\n", "<br>"), accent=getattr(self, "_accent", None))
        row.fit(self.scroll.viewport().width() or WIDTH)
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(row)
        if kind == "mico" and str(text or "").strip():
            copy_b = QPushButton("Копировать")
            copy_b.setObjectName("ghost")
            copy_b.setCursor(Qt.CursorShape.PointingHandCursor)
            copy_b.setToolTip("Скопировать ответ в буфер обмена")
            copy_b.clicked.connect(lambda _=False, t=str(text): self._copy_reply(t, copy_b))
            cr = QHBoxLayout()
            cr.setContentsMargins(34, 0, 0, 0)
            cr.addWidget(copy_b)
            cr.addStretch(1)
            v.addLayout(cr)
        self._add(wrap, animate=animate)
        if rid is not None:
            self._rows[rid] = wrap
        return wrap

    def _copy_reply(self, text, button):
        """Кладёт ответ Mico в буфер и на секунду показывает «Скопировано»."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        button.setText("Скопировано ✓")
        QTimer.singleShot(1500, lambda: button.setText("Копировать"))

    def _add(self, widget, animate=True):
        """Добавляет реплику в конец ленты. История строится сразу, без десятков лишних анимаций."""
        self.col.insertWidget(self.col.count() - 1, widget)         # перед растяжкой
        if not animate:
            return
        from ui import motion
        motion.fade_slide_in(widget, dy=10, ms=260)     # реплика мягко всплывает снизу (эффект снимается в конце)
        QTimer.singleShot(40, self._scroll_end)

    def add_fx(self, spec):
        """Живая карточка под ответом: что переключилось (ui/switchfx.py)."""
        from ui import switchfx
        self._has_msgs = True
        self._update_greeting()
        wrap = switchfx.build_row(spec, getattr(self, "_accent", None) or "#FFCFA3", bool(theme.is_dark(self.cfg)))
        self._add(wrap, animate=True)

    def _fit_messages(self):
        """Пересчитывает перенос строк после открытия боковой панели или изменения размера окна."""
        width = self.scroll.viewport().width() or WIDTH
        for i in range(self.col.count()):
            wrap = self.col.itemAt(i).widget()
            lay = wrap.layout() if wrap is not None else None
            row = lay.itemAt(0).widget() if lay is not None and lay.count() else None
            if isinstance(row, chat_look.MessageRow):
                row.fit(width)

    def _fade_history(self):
        """Переключили чат: лента плавно проявляется, а не появляется рывком."""
        eff = QGraphicsOpacityEffect(self.scroll)
        eff.setOpacity(0.0)
        self.scroll.setGraphicsEffect(eff)
        self._run(eff, b"opacity", 0.0, 1.0, 300, after=lambda: self.scroll.setGraphicsEffect(None))

    def _scroll_end(self):
        sb = self.scroll.verticalScrollBar()
        self._run(sb, b"value", sb.value(), sb.maximum(), 300)

    def _scroll_to_bottom_now(self):
        """Открыли компактный чат — показываем свежий конец беседы без ожидания анимации."""
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _run(self, obj, prop, start, end, ms, after=None):
        anim = QPropertyAnimation(obj, prop, self)
        anim.setDuration(ms)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anims.append(anim)

        def done():
            if anim in self._anims:
                self._anims.remove(anim)
            if after is not None:
                after()
        anim.finished.connect(done)
        anim.start()

    def set_busy(self, on):
        """Mico AI думает: в ленте пузырь с иконкой и точками, которые волной поднимаются.
        Исчезает, как только ответ готов."""
        if on:
            if self._thinking is not None:
                return
            muted = chat_look.PALETTE[bool(theme.is_dark(self.cfg))]["muted"]
            self._thinking = chat_look.TypingRow(getattr(self, "_accent", "#FFCFA3"), muted)
            self._add(self._thinking)
            self._thinking.show_typing(True)
        else:
            self._stop_thinking()

    def _stop_thinking(self):
        if self._thinking is not None:
            self._thinking.show_typing(False)
            self.col.removeWidget(self._thinking)
            self._thinking.deleteLater()
            self._thinking = None

    # ----- недавние чаты, поиск, история: тот же журнал, что у обычного чата -----
    def attach(self, store, current_cb, open_cb, new_cb):
        """Подключает чат к журналу Mico AI. Открыть, начать или найти чат — делает обычный чат (Panel),
        AIChat только показывает ленту. Так память и сводка у обоих чатов общие."""
        self._store, self._current_cb, self._open_cb, self._new_cb = store, current_cb, open_cb, new_cb
        self.refresh_side()

    def _toggle_side(self, on=None):
        """Плавно открывает или прячет список недавних чатов, не меняя размер внешнего окна."""
        show = (not self._side_open) if on is None else bool(on)
        if show == self._side_open:
            return
        if self._side_anim is not None:
            self._side_anim.stop()
        self._side_open = show
        self.setFixedSize(self.size())                 # окно не растёт и не сдвигается, пока меню выезжает
        if show:
            self.refresh_side()
            self.side.show()
        anim = QPropertyAnimation(self.side, b"maximumWidth", self)
        anim.setDuration(240)
        anim.setStartValue(self.side.width())
        anim.setEndValue(self._side_width if show else 0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if not show:
            anim.finished.connect(self.side.hide)
        anim.finished.connect(self._fit_messages)
        anim.finished.connect(self._side_settled)
        self._side_anim = anim
        anim.start()

    def _side_settled(self):
        """Меню доехало: размер снова свободный, но окно ставим точно на его место и в его размер."""
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        if self._blob is not None and self.isVisible():
            x, y, w, h = self._spot(self._blob)
            self.setGeometry(x, y, w, h)

    def refresh_side(self):
        """Список недавних чатов с названиями, которые придумал Mico. Подсвечивает открытый."""
        if self._store is not None:
            self.side.set_chats(self._store.conv_list(60), self._current_cb() if self._current_cb else None)

    def _open_conv(self, cid, rid=None):
        if self._open_cb is not None:
            self._open_cb(cid, rid)
        self._toggle_side(False)

    def _new_conv(self):
        if self._new_cb is not None:
            self._new_cb()
        self._toggle_side(False)

    def show_history(self, rows, focus_rid=None):
        """Лента — реплики открытого чата: [(id, время, роль, текст)]. Старые блоки убираем, новые ставим по порядку."""
        self.clear_messages()
        for rid, _ts, role, text in rows:
            self._bubble(text, "me" if role == "user" else "mico", rid=rid, animate=False)
        self.search.clear()
        self._fit_messages()
        QTimer.singleShot(0, self._fade_history)             # после перерасчёта размеров лента проявляется без рывка
        if focus_rid is not None and focus_rid in self._rows:
            QTimer.singleShot(60, lambda: self.scroll.ensureWidgetVisible(self._rows[focus_rid], 0, 24))
        else:
            QTimer.singleShot(60, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def clear_messages(self):
        """Новый чат: лента пустая, как у обычного чата."""
        self._stop_thinking()
        self._drop_live()
        self._rw = None
        self._offer_row = None
        for i in reversed(range(self.col.count() - 1)):          # последняя позиция — растяжка, её не трогаем
            w = self.col.itemAt(i).widget()
            if w is not None and w is not self.greeting:
                self.col.takeAt(i)
                w.deleteLater()
        self._rows.clear()
        self._has_msgs = False
        if self._voice_view:
            self._dock_move()                       # лента очищена — в голосовом режиме Mico снова в центре
        self.refresh_profile()
        self.refresh_welcome()                    # новый чат — свежие кнопки действий, как у Copilot
        self._update_greeting()

    def refresh_profile(self):
        self.side.set_profile(self.cfg.get("user_name", ""))

    def _search_changed(self, text):
        q = " ".join(str(text).split())
        if len(q) < 2 or self._store is None:
            self.results.hide()
            return
        cur = self._current_cb() if self._current_cb else None
        hits = [h for h in self._store.conv_search(q, limit=200) if h[0] == cur][:25]
        titles = {int(cid): title for cid, title, _updated in self._store.conv_list(60)}
        self.results.clear()
        for cid, rid, _ts, _role, t in hits:
            self.results.addItem(chat_look.result_item(titles.get(int(cid), "Чат"), t, q, cid, rid))
        if not hits:
            it = QListWidgetItem("Ничего не нашлось. Попробуй другое слово.")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(it)
        h = min(240, 8 + 52 * self.results.count())
        top = self.head_bar.geometry().bottom() + 4
        self.results.setGeometry(self.head_bar.x() + 6, top, self.head_bar.width() - 12, h)
        self.results.raise_()
        self.results.show()

    def _open_result(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        cid, rid = data
        self.results.hide()
        self._open_conv(cid, rid)

    def _restore_draft(self):
        """Если в прошлый раз текст не отправили, он ждёт в строке ввода. Не отправляем сам."""
        draft = self._cfg.get("wi_draft") or ""
        if draft and not self.inp.text():
            self.inp.setText(draft)

    def _save_draft(self):
        self._push_draft(self.inp.text()[:2000])

    def _push_draft(self, text):
        from data.clipbuf import looks_secret
        if text and looks_secret(text):                    # пароли и номера карт в черновик не пишем
            text = ""
        self._cfg["wi_draft"] = text
        if self.on_draft:
            try:
                self.on_draft(text)
            except Exception:
                pass

    def _send(self):
        text = self.inp.text().strip()
        if not text or len(self.inp.text()) > CHAR_LIMIT:
            return
        self._draft_timer.stop()
        self._push_draft("")
        self.inp.clear()
        self.send.emit(text)

    # ----- показ и закрытие -----
    # ----- боковая панель (как Windows Copilot) -----
    def side_panel(self):
        """Чат выезжает панелью у правого края экрана, а живой Mico AI стоит в её шапке.
        False — привычное окно чата над Mico AI."""
        return bool(self.cfg.get("panel_side", True)) and not getattr(self, "voice_float", False)   # голосовой режим: окно над Mico

    def _dock_rect(self):
        """Панель: у правого края экрана, во всю доступную высоту — как Windows Copilot."""
        blob = self._blob
        scr = QGuiApplication.screenAt(blob.geometry().center()) if blob is not None else None
        g = (scr or QGuiApplication.primaryScreen()).availableGeometry()
        w = max(round(WIDTH * self.factor()), min(self._dock_blob_px(), round(g.width() * 0.45)))
        return g.right() - w + 1, g.top(), w, g.height()

    def _dock_blob_px(self):
        """Размер окна Mico AI в шапке панели: меньше обычного, как логотип Copilot."""
        from ui.blob import BASE_PX
        return max(1, int(BASE_PX * float(self.cfg.get("scale", 1.0)) * BLOB_DOCK_K))

    def _build_style_row(self):
        """Выбор стиля общения сразу в чате — три кнопки, как «Choose a conversation style» у Copilot."""
        row = QFrame()
        row.setObjectName("styleRow")
        v = QVBoxLayout(row)
        v.setContentsMargins(2, 0, 2, 0)
        v.setSpacing(8)
        label = QLabel(i18n.t("Выбери стиль общения"))
        label.setObjectName("styleLabel")
        v.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
        seg = QFrame()                                  # тот же сегментированный переключатель, что в приветствии
        seg.setObjectName("segBar")
        h = QHBoxLayout(seg)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(2)
        self.style_btns = []
        for key, title in chat_look.Greeting.STYLE_CHOICES:
            b = QPushButton(i18n.t(title))
            b.setObjectName("styleSeg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # влезают в узкую панель
            b.setMinimumWidth(0)
            b.clicked.connect(lambda _=False, k=key: self._set_style(k))
            h.addWidget(b, 1)
            self.style_btns.append((b, key))
        v.addWidget(seg)
        self._seg_fit = chat_look.SegFit(seg, [b for b, _k in self.style_btns])   # кнопки одной ширины
        self._sync_style()
        return row

    def _sync_style(self):
        cur = str(self.cfg.get("chat_style", "balanced"))
        for b, key in self.style_btns:
            b.setChecked(key == cur)
        if getattr(self, "greeting", None) is not None:
            self.greeting.set_style(cur)

    def event(self, e):
        """Чат стал активным (клик по кнопке стиля, полю ввода): Windows поднимает его окно над окном Mico,
        и Mico в шапке пропадал под ним. Сразу возвращаем Mico наверх."""
        from PyQt6.QtCore import QEvent
        if e.type() in (QEvent.Type.WindowActivate, QEvent.Type.ActivationChange):
            QTimer.singleShot(0, self._lift_blob)
            QTimer.singleShot(120, self._lift_blob)
        return super().event(e)

    def _set_style(self, key):
        """Стиль общения меняется сразу, без настроек, и запоминается."""
        self.activity.emit()
        self.cfg["chat_style"] = key
        self._sync_style()
        if self.save_cfg:
            self.save_cfg()
        self.inp.setFocus()
        self._keep_dock()                                  # Mico остаётся в шапке и поверх чата
        QTimer.singleShot(150, self._keep_dock)

    def _dock_blob(self, blob):
        """Живой Mico AI встаёт в шапку панели (место логотипа Copilot) и остаётся таким же живым."""
        if not self._docked_blob:
            self._docked_blob = True
            blob.voice_k = BLOB_DOCK_K    # плавно поджимается к размеру шапки (та же механика, что в голосе)
            blob.locked = True            # угол экрана больше не тянет его — он в шапке панели
        blob.pinned = True                # и его физика тоже: привязан к шапке, пока панель открыта
        self.blob_slot.setFixedHeight(self._dock_blob_px())
        self.dock_mico.set_size(self._dock_blob_px())   # портрет — того же размера, что живой Mico AI
        self._dock_move()
        self._sync_dock_mico()
        self._lift_blob()

    # ----- загрузка голоса и распознавания речи в голосовом чате: процент и полоска -----
    def _build_voice_load(self):
        box = QFrame()
        box.setObjectName("voiceLoad")
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 0, 14, 4)
        v.setSpacing(6)
        self.voice_load_label = QLabel()
        self.voice_load_label.setObjectName("gateText")
        self.voice_load_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.voice_load_label)
        self.voice_load_bar = LoadBar()
        v.addWidget(self.voice_load_bar)
        self.voice_load = box
        self._voice_status_text = ""
        box.hide()

    def set_voice_status(self, text):
        """Статус голоса из фонового потока. В голосовом чате строки ввода нет, поэтому раньше загрузка голоса и модели
        распознавания там не была видна совсем. Теперь над кнопками подпись с процентом и полоска."""
        self._voice_status_text = str(text or "")
        self._show_voice_status()

    def _show_voice_status(self):
        t = self._voice_status_text
        loading = t.startswith(("Скачиваю", "Загружаю"))
        if not (loading and self._voice_view):
            self.voice_load.hide()
            return
        m = re.search(r"(\d{1,3})%", t)
        pct = max(0, min(100, int(m.group(1)))) if m else None
        if t.startswith("Скачиваю распознавание"):
            label = i18n.t("Скачиваю распознавание речи, один раз")
        elif t.startswith("Скачиваю голос"):
            label = i18n.t("Скачиваю голос, один раз")
        elif t.startswith("Загружаю голос"):
            label = i18n.t("Загружаю голос…")
        else:
            label = i18n.t("Загружаю распознавание речи…")
        if pct is not None:
            label += f" · {pct}%"
        self.voice_load_label.setText(label)
        self.voice_load_bar.accent = getattr(self, "_accent", None) or "#FFCFA3"
        self.voice_load_bar.set_value(None if pct is None else pct / 100.0)
        self.voice_load.show()

    # ----- «нужно обновить Mico»: чат не работает, Mico стоит по центру, внизу просьба и кнопка на сайт -----
    def _build_gate(self):
        box = QFrame()
        box.setObjectName("gateBox")
        v = QVBoxLayout(box)
        v.setContentsMargins(8, 4, 8, 6)
        v.setSpacing(10)
        self.gate_label = QLabel()
        self.gate_label.setObjectName("gateText")
        self.gate_label.setWordWrap(True)
        self.gate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.gate_label)
        self.gate_btn = QPushButton(i18n.t("Обновить Mico"))
        self.gate_btn.setObjectName("gateBtn")
        self.gate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gate_btn.clicked.connect(self._open_site)
        v.addWidget(self.gate_btn)
        self.gate_box = box
        box.hide()

    def _open_site(self):
        if self._gate:
            try:
                webbrowser.open(self._gate["url"])
            except Exception:
                pass

    def set_update_gate(self, info):
        """Сайт сообщил, что есть версия новее: чат больше не работает, пока не обновят Mico."""
        self._gate = info
        self.gate_label.setText(i18n.t("Пожалуйста, обнови Mico: вышла новая версия. Скачай её на сайте и поставь поверх."))
        if self.isVisible():
            self._apply_gate()

    def _apply_gate(self):
        if not self._gate:
            return
        self.set_voice_view(True)                          # Mico уезжает в центр чата, как в голосовом режиме
        self.voice_bar.hide()
        self.input_box.hide()
        self.greeting.set_locked(True, i18n.t("Нужно обновить Mico"), i18n.t("Без обновления я не буду работать"))
        self.gate_box.show()
        self._dock_move()
        if self._blob is not None:
            self._blob.set_mood("curious", 4)

    # ----- кнопки голосового режима внутри чата: те же, что в полоске голосового режима -----
    def _build_voice_bar(self):
        bar = QFrame()
        bar.setObjectName("voiceStrip")
        bar.setStyleSheet("QPushButton#micBtn { border-radius: 19px; }")     # кнопки по 38 px — круглые
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 2, 12, 2)
        h.setSpacing(12)
        h.addStretch(1)

        def mk(tip, slot):
            b = QPushButton()
            b.setObjectName("micBtn")
            b.setFixedSize(38, 38)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False: slot())
            h.addWidget(b)
            return b
        self.vb_mic = mk("Микрофон — нажми, чтобы выключить", self.voice_mute.emit)
        self.vb_tune = mk("Голос и скорость речи", self._voice_menu)
        self.vb_color = mk("Цвет Mico: выбери из палитры", self._color_menu)
        self.vb_subs = mk("Субтитры: слова появляются в чате", self._subs_clicked)
        self.vb_exit = mk("Завершить голосовой чат", self.voice_exit.emit)
        h.addStretch(1)
        self.voice_bar = bar
        self._voice_muted = False
        bar.hide()

    def _subs_on(self):
        return bool(self.cfg.get("voice_chat_subs", True))

    def set_voice_muted(self, on):
        self._voice_muted = bool(on)
        self._refresh_voice_bar()

    def _refresh_voice_bar(self):
        accent = getattr(self, "_accent", None) or "#FFCFA3"
        red = "#ff6b6b"
        ic = 18
        self.vb_mic.setIcon(uiicons.icon("mic_off" if self._voice_muted else "mic", red if self._voice_muted else accent, ic))
        self.vb_mic.setToolTip("Микрофон выключен — нажми, чтобы снова слушать" if self._voice_muted
                               else "Микрофон — нажми, чтобы выключить")
        self.vb_tune.setIcon(uiicons.icon("tune", accent, ic))
        self.vb_color.setIcon(uiicons.icon("palette", accent, ic))
        self.vb_subs.setIcon(uiicons.icon("subs", accent, ic))
        self.vb_exit.setIcon(uiicons.icon("close", accent, ic))
        for b in (self.vb_mic, self.vb_tune, self.vb_color, self.vb_subs, self.vb_exit):
            b.setIconSize(QSize(ic, ic))
        from assist import intel as _intel
        r, g, b = _intel.hex_rgb(accent)                   # включённые субтитры — мягкая подсветка цветом Mico, как в полоске
        self.vb_subs.setStyleSheet(
            f"QPushButton#micBtn {{ background: rgba({r},{g},{b},0.24); border: 1px solid {accent}; border-radius: 19px; }}"
            if self._subs_on() else "")

    def _subs_clicked(self):
        on = not self._subs_on()
        self.cfg["voice_chat_subs"] = on
        self.voice_subs.emit(on)
        if not on:
            self.end_live_user()                          # субтитры выключили — живая реплика исчезает
        self._apply_voice_scroll()
        self._dock_move()                                 # без переписки Mico снова в центре, с перепиской — в шапке
        self._refresh_voice_bar()

    def _menu_for(self):
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())
        return menu

    def _voice_menu(self):
        """Голос и скорость речи — меню над кнопкой."""
        from voice import models as voice_models
        menu = self._menu_for()
        cur_voice = self.cfg.get("voice_name") or voice_models.DEFAULT_VOICE
        head = menu.addAction("Голос")
        head.setEnabled(False)
        for key, voice in voice_models.VOICES.items():
            act = menu.addAction(voice["title"])
            act.setCheckable(True)
            act.setChecked(key == cur_voice)
            act.triggered.connect(lambda _=False, k=key: self.voice_pick.emit(k))
        menu.addSeparator()
        head2 = menu.addAction("Скорость речи")
        head2.setEnabled(False)
        cur_speed = float(self.cfg.get("voice_speed", 1.0))
        for value, label in ((0.5, "0,5x"), (1.0, "1x"), (1.5, "1,5x"), (2.0, "2x")):
            act = menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(abs(cur_speed - value) < 0.01)
            act.triggered.connect(lambda _=False, v=value: self.voice_speed.emit(float(v)))
        self._popup_above(menu, self.vb_tune)

    def _color_menu(self):
        """Цвет Mico из той же палитры, что при первом запуске."""
        from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
        from ui.onboarding import COLORS
        menu = self._menu_for()
        cur = str(self.cfg.get("color", "")).upper()
        for hex_c, name in COLORS:
            pix = QPixmap(16, 16)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(hex_c))
            p.drawEllipse(1, 1, 14, 14)
            p.end()
            act = menu.addAction(QIcon(pix), i18n.t(name))
            act.setCheckable(True)
            act.setChecked(hex_c.upper() == cur)
            act.triggered.connect(lambda _=False, c=hex_c: self.voice_color.emit(c))
        self._popup_above(menu, self.vb_color)

    def _popup_above(self, menu, anchor):
        pos = anchor.mapToGlobal(QPoint(0, 0))
        menu.exec(QPoint(pos.x() + anchor.width() // 2 - menu.sizeHint().width() // 2,
                         pos.y() - menu.sizeHint().height() - 6))

    def set_voice_view(self, on):
        """Голосовой режим внутри открытого чата: чат стоит на месте, кнопки действий и выбор стиля пропадают,
        а Mico плавно уезжает в центр чата. Выход — всё возвращается."""
        self._voice_view = bool(on)
        self.greeting.set_voice(on)
        self.voice_bar.setVisible(bool(on))
        self.input_box.setVisible(not on)                  # в голосовом чате строка ввода сообщения не нужна
        self._show_voice_status()                          # загрузка голоса или распознавания идёт — сразу показываем процент
        self._apply_voice_scroll()
        if on:
            self._refresh_voice_bar()
        self.mic_btn.setProperty("active", bool(on))
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)
        self.mic_btn.setToolTip("Закончить голосовой режим" if on else "Голосовой режим: Mico будет слушать")
        self.inp.setPlaceholderText(i18n.t("Слушаю…") if on else i18n.t("Спроси что угодно…"))
        self._update_greeting()
        self._dock_move()

    def _apply_voice_scroll(self):
        """Субтитры выключены — в голосовом чате сообщений не видно (они не пропали, а вернутся при выходе или включении субтитров)."""
        self.scroll.setVisible(not (self._voice_view and not self._subs_on()))

    def _voice_center(self):
        """Mico стоит по центру чата, пока в нём ещё нет переписки или она скрыта; пошла переписка — возвращается в шапку."""
        return self._voice_view and (not self._has_msgs or not self._subs_on())

    def _dock_target(self):
        """Куда встаёт окно Mico AI: по центру места в шапке панели, под его будущий уменьшенный размер."""
        d = self._dock_blob_px()
        if self._voice_center():
            dock_x, dock_y, w, h = self._dock_rect()
            return QPoint(dock_x + (w - d) // 2, dock_y + (h - d) // 2 - 20)
        dock_x, dock_y, _w, _h = self._dock_rect()
        rel = self.blob_slot.mapTo(self, QPoint(0, 0))
        return QPoint(dock_x + rel.x() + (self.blob_slot.width() - d) // 2,
                      dock_y + rel.y() + (self.blob_slot.height() - d) // 2)

    def _dock_move(self):
        """Перелёт Mico AI в центр места в шапке панели (под его будущий уменьшенный размер)."""
        blob = self._blob
        if blob is None or not self._docked_blob:
            return
        target = self._dock_target()
        if self._blob_anim is not None:
            self._blob_anim.stop()
        self._blob_anim = QPropertyAnimation(blob, b"pos", self)
        self._blob_anim.setDuration(380)
        self._blob_anim.setStartValue(blob.pos())
        self._blob_anim.setEndValue(target)
        self._blob_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._blob_anim.finished.connect(self._lift_blob)
        self._blob_anim.start()

    def _keep_dock(self):
        """Пока панель открыта: Mico держится в шапке и остаётся поверх панели.
        Панель могли поднять кликом или вернуть из свёрнутого — шапка всегда должна быть с Mico."""
        if self._blob is None or not self._docked_blob:
            return
        if self.isVisible() and (not self._blob.isVisible() or self._blob.windowOpacity() < 0.05):
            self._blob.setWindowOpacity(1.0)              # Mico спрятали или погасили — возвращаем в шапку
            self._blob.show()
        self._sync_dock_mico()
        anim = self._blob_anim
        if anim is None or anim.state() != QAbstractAnimation.State.Running:
            target = self._dock_target()
            if abs(self._blob.x() - target.x()) > 2 or abs(self._blob.y() - target.y()) > 2:
                self._blob.move(target)
        now = time.time()
        if now - self._last_lift > 0.8:                 # порядок окон — раз в секунду, не чаще
            self._last_lift = now
            self._lift_blob()

    def _lift_blob(self):
        """Живой Mico AI в шапке — ПОВЕРХ панели: панель поднимается при активации и кликах."""
        if (self._docked_blob and self._blob is not None and self._blob.isVisible()
                and not self._blob.covered()):   # над открытыми настройками не поднимаем
            self._blob.raise_()

    def _sync_dock_mico(self):
        """В шапке панели всегда виден Mico: живой — только когда он реально стоит на месте в шапке,
        иначе показываем портрет. Раньше портрет прятался при любом видимом живом Mico, и если тот
        не вставал на место, в шапке оставалась пустота."""
        live = self._blob is not None and self._blob.isVisible()    # пока живой Mico летит в шапку, портрета («колобка») не показываем
        self.dock_mico.setVisible(self.blob_slot.isVisible() and not live)

    def _undock_blob(self):
        """Панель закрывается: Mico AI сам плавно возвращается на своё место на рабочем столе."""
        if not self._docked_blob:
            return
        self._docked_blob = False
        if self._blob_anim is not None:
            self._blob_anim.stop()
            self._blob_anim = None
        blob = self._blob
        if blob is not None:
            blob.pinned = False           # швартовка кончена
            blob.voice_k = None           # возвращается к обычному размеру
            blob.locked = False           # и к своему живому месту: его туда доведёт его же физика (_glide)
        self._sync_dock_mico()

    def show_near(self, blob, activate=True):
        self._restore_draft()
        if not self.isVisible() and not getattr(self, "_has_msgs", False):
            self.refresh_welcome()                   # при каждом открытии — свежие быстрые действия по привычкам
        """Открывает чат над Mico. Если уже открыт — только поднимает и, при необходимости, даёт фокус."""
        if self.isVisible():
            self.raise_()
            self._lift_blob()                    # живой Mico AI в шапке — поверх поднятой панели
            if activate:
                self.activateWindow()
                self.inp.setFocus()
            return
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not activate)
        self._blob = blob
        x, y, w, h = self._spot(blob)
        self.resize(w, h)
        side = self.side_panel()
        self.blob_slot.setVisible(side)
        self._sync_dock_mico()
        self._update_greeting()
        self._apply_gate()
        if side:
            # панель выезжает из-за правого края экрана — как Windows Copilot
            self.setWindowOpacity(intel.chat_opacity(self.cfg))
            self.move(x + w + 12, y)
            self.show()
            self.raise_()
            self.layout().activate()
            self._dock_blob(blob)             # живой Mico AI встаёт в шапку панели
            QTimer.singleShot(200, self._sync_dock_mico)   # после первой разметки — перепроверяем место
        else:
            self.setWindowOpacity(0.0)
            self.move(x, y + 14)
            self.show()
            self.raise_()
        QTimer.singleShot(0, self._scroll_to_bottom_now)   # при новом открытии всегда виден последний ответ
        QTimer.singleShot(90, self._scroll_to_bottom_now)  # после первого перерасчёта высоты сообщений
        self._pos_busy = True
        QTimer.singleShot(320, self._done_opening)
        self._run_pos(QPoint(x + w + 12, y) if side else QPoint(x, y + 14), QPoint(x, y))
        if not side:
            self._run(self, b"windowOpacity", 0.0, intel.chat_opacity(self.cfg), 300)
        self._follow.start()
        self._lift_blob()                            # живой Mico AI — поверх панели, и ещё раз с отсрочкой
        QTimer.singleShot(150, self._lift_blob)
        QTimer.singleShot(600, self._lift_blob)
        if activate:
            self.activateWindow()
            self.inp.setFocus()

    def factor(self):
        """Во сколько раз чат Mico AI больше или меньше базового. Тот же выбор, что у обычного чата:
        «чат вместе с Mico AI» или отдельный «Размер чата» в настройках."""
        cfg = self.cfg or {}
        if cfg.get("chat_linked", True):
            return max(0.6, float(cfg.get("scale", 1.0)))
        return max(0.6, float(cfg.get("chat_scale", 1.0)))

    def relayout(self):
        """Настройки изменили размер: если чат открыт — сразу перестраиваем его, без переоткрытия."""
        if not self.isVisible() or self._blob is None:
            return
        x, y, w, h = self._spot(self._blob)
        self.resize(w, h)
        self.move(x, y)
        if self.side_panel() and self._docked_blob:
            self.layout().activate()
            self._dock_blob(self._blob)       # и место Mico AI в шапке — под новый размер

    def _spot(self, blob):
        """Где стоит чат: над Mico AI и не выше экрана. Если над ним мало места — чат короче;
        если места нет совсем — чат встаёт под Mico. Так он никогда не лезет на Mico."""
        if self.side_panel():
            return self._dock_rect()          # боковая панель: у правого края экрана, во всю высоту
        scr = QGuiApplication.screenAt(blob.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        k = self.factor()
        w = round(WIDTH * k)
        want = min(round(MAX_HEIGHT * k), max(CHAT_MIN_H, g.height() // 2))
        x = blob.x() + blob.width() // 2 - w // 2
        x = max(g.left() + 8, min(x, g.right() - w - 8))
        room_above = blob.y() - CHAT_GAP - (g.top() + 8)
        if room_above >= CHAT_MIN_H:
            h = min(want, room_above)
            return x, blob.y() - CHAT_GAP - h, w, h
        below = blob.y() + blob.height() + CHAT_GAP
        h = min(want, max(CHAT_MIN_H, g.bottom() - 8 - below))
        return x, below, w, h

    def _follow_blob(self):
        """Mico AI прыгнул, уехал во сне или его перетащили — чат едет за ним и остаётся рядом, не наезжая."""
        if not self.isVisible() or self._blob is None:
            return
        if self.side_panel():
            self._keep_dock()                # боковая панель стоит у края: следим за шапкой с Mico AI
            side_busy = self._side_anim is not None and self._side_anim.state() == QAbstractAnimation.State.Running
            if not self._pos_busy and not self._anims and not side_busy:
                x, y, w, h = self._dock_rect()      # панель не уползает и не растёт: всегда своё место и размер
                if (self.x(), self.y(), self.width(), self.height()) != (x, y, w, h):
                    self.setGeometry(x, y, w, h)
            return
        if self._pos_busy:
            return                            # первые ~320 мс чат выезжает на место — не мешаем анимации
        x, y, w, h = self._spot(self._blob)
        if abs(self.height() - h) > 2:
            self.resize(w, h)
        if abs(self.x() - x) > 1 or abs(self.y() - y) > 1:
            self.move(x, y)

    def _done_opening(self):
        self._pos_busy = False

    def _run_pos(self, start, end):
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(360)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anims.append(anim)

        def done():
            if anim in self._anims:
                self._anims.remove(anim)
        anim.finished.connect(done)
        anim.start()

    def dismiss(self):
        """Плавно закрывается. Сообщения остаются — при следующем открытии они на месте."""
        if not self.isVisible():
            return
        self._undock_blob()                   # живой Mico AI возвращается на своё место на рабочем столе
        if self.side_panel():                 # панель уезжает за правый край экрана
            x, y, w, _h = self._dock_rect()
            self._run_pos(QPoint(self.pos()), QPoint(x + w + 12, y))
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(260)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._fade.finished.connect(self._hidden)
        self._fade.start()
        self.set_busy(False)

    def _hidden(self):
        if self.windowOpacity() <= 0.01:
            self._follow.stop()
            self.hide()
            self.setWindowOpacity(intel.chat_opacity(self.cfg))
            self.closed.emit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self._fit_messages)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(e)
