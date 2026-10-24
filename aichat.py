"""Чат Mico AI — свой, минималистичный (не обычный чат Mico AI). Все надписи — тем же шрифтом, что в настройках (Segoe UI Variable).
Сообщения появляются плавно; пока Mico AI думает, думает и он сам (анимация Mico AI). Открывается над Mico AI, закрывается ✕."""
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QLineEdit, QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget)
import html
import chat_look


import intel
import theme
import uiicons
from ui_anim import pulse_icon
from onboarding import COLORS as PALETTE     # те же цвета, что при первом запуске
import voice_models

WIDTH = 560                     # ширина чата Intelligence, px (с боковым меню, было 350)
BASE_H = 520                    # стандартная высота чата, px (с боковым меню, было 420)
MAX_HEIGHT = 560                # верхний предел высоты, px (было 440)
CHAT_MIN_H = 240                 # ниже — чат неудобно читать
CHAT_GAP = 12                    # зазор между чатом и Mico AI, px


def _flags():
    return Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


class AIChat(QWidget):
    send = pyqtSignal(str)      # пользователь написал — уходит Mico AI
    closed = pyqtSignal()       # чат закрыли
    model_pick = pyqtSignal(str)       # выбрали другую модель в чате
    model_info_ready = pyqtSignal(str) # текст для кнопки модели (считаем в фоне)
    dnd = pyqtSignal(int)       # «не беспокоить» на N минут (0 — выключить)
    rewrite = pyqtSignal(str)   # «short» или «long» — переписать последний ответ
    file_cleared = pyqtSignal() # файл из чата убрали
    color_pick = pyqtSignal(str) # цвет из палитры: Mico AI крутится и перекрашивается
    voice_toggle = pyqtSignal(bool)  # озвучивать ответы: вкл/выкл
    voice_pick = pyqtSignal(str)     # выбрали другой голос
    listen = pyqtSignal()            # микрофон: начать или закончить запись
    settings_all = pyqtSignal()      # «Все настройки…» из меню бокового меню
    profile_requested = pyqtSignal() # аватар: открыть «о себе»
    attach_requested = pyqtSignal()  # скрепка: выбрать файл, с которым будет работать Mico

    def __init__(self, cfg):
        self._cfg = cfg                                    # общий словарь настроек: черновик хранится в нём
        super().__init__(None, _flags())
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anims = []
        self._fade = None
        self._blob = None                        # Mico AI, рядом с которым стоит чат
        self._pos_busy = False                   # первые ~320 мс чат выезжает на место — не мешаем анимации
        self._follow = QTimer(self)              # чат едет за Mico AI: он мог прыгнуть, уехать во сне или его перетащили
        self._follow.setTimerType(Qt.TimerType.PreciseTimer)   # ровно в ритме Mico AI, без рывков
        self._follow.setInterval(16)   # 60 кадров: как у Mico AI, без лишних перерисовок окна
        self._follow.timeout.connect(self._follow_blob)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame(self)
        self.card.setObjectName("card")
        root.setContentsMargins(14, 14, 14, 14)               # место для тени внутри окна
        root.addWidget(self.card)
        body = QHBoxLayout(self.card)                      # слева боковое меню (всегда открыто), справа — чат
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        lay = QVBoxLayout()
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
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
        self.menu_btn.clicked.connect(lambda: None)
        self.menu_btn.hide()                               # меню всегда открыто — кнопка-полоски не нужна
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
        top.addWidget(self.menu_btn)
        top.addWidget(self.search, 1)
        top.addWidget(close)
        hb.addLayout(top)
        self.head = QLabel("Текущий чат")
        self.head.setObjectName("chatHead")
        hb.addWidget(self.head)
        lay.addWidget(self.head_bar)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("msgScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.box = QWidget()
        self.col = QVBoxLayout(self.box)
        self.col.setContentsMargins(0, 4, 0, 4)
        self.col.setSpacing(10)
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
        self.chip = QFrame()                       # плашка прикреплённого файла: вопросы идут по нему
        self.chip.setObjectName("chip")
        cr = QHBoxLayout(self.chip)
        cr.setContentsMargins(10, 4, 4, 4)
        self.chip_lbl = QLabel("")
        self.chip_lbl.setObjectName("chipText")
        drop = QPushButton()
        drop.setIcon(uiicons.icon("close", "#8e8e93", 12))
        drop.setObjectName("ghost")
        drop.setCursor(Qt.CursorShape.PointingHandCursor)
        drop.clicked.connect(self.file_cleared.emit)
        cr.addWidget(self.chip_lbl, 1)
        cr.addWidget(drop)
        self.chip.setVisible(False)
        lay.addWidget(self.chip)
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
        body.insertWidget(0, self.side)                    # меню слева, всегда открыто
        self.side.setFixedWidth(206)
        self.side.profile.connect(self.profile_requested.emit)
        self.refresh_side()
        self._rw = None                            # строка «Короче / Подробнее» под последним ответом
        self._offer_row = None                     # кнопки под предложением Mico AI
        self._thinking = None                      # строка «Mico AI думает…» в ленте
        self._think_timer = None                   # мигает точками, пока Mico AI думает
        self._think_n = 1
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Напиши Mico AI…")
        self.inp.setObjectName("chatInput")
        self.inp.returnPressed.connect(self._send)
        self.on_draft = None                               # main сохраняет черновик на диск
        self._draft_timer = QTimer(self)                   # сохраняем через паузу, а не на каждую букву
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(800)
        self._draft_timer.timeout.connect(self._save_draft)
        self.inp.textChanged.connect(lambda _t: self._draft_timer.start())
        self.btn = QPushButton()
        self.btn.setObjectName("send")
        self.btn.setFixedSize(26, 26)                        # круглая кнопка отправки (компактная)
        self.btn.setToolTip("Отправить")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._send)
        row.setSpacing(6)
        self.mic_btn = QPushButton()
        self.mic_btn.setObjectName("iconBtn")
        self.mic_btn.setFixedSize(34, 34)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setToolTip("Голосовой режим: чат свернётся, Mico будет слушать")
        self.mic_btn.clicked.connect(self.listen.emit)
        self.clip_btn = QPushButton()                      # скрепка: прикрепить файл, по нему пойдут вопросы
        self.clip_btn.setObjectName("iconBtn")
        self.clip_btn.setIcon(chat_look.clip_icon(chat_look.icon_ink(theme.is_dark(self.cfg)), 18))
        self.clip_btn.setIconSize(QSize(18, 18))
        self.clip_btn.setFixedSize(30, 30)
        self.clip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clip_btn.setToolTip("Прикрепить файл")
        self.clip_btn.clicked.connect(self.attach_requested.emit)
        row.addWidget(self.clip_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.inp, 1)
        row.addWidget(self.mic_btn)
        row.addWidget(self.btn)
        box = QFrame()                                     # поле ввода в скруглённой рамке, как в обычном чате
        box.setObjectName("inputBox")
        box.setLayout(row)
        lay.addWidget(box)                                 # без аватара: поле ввода занимает всю ширину
        self.greeting = chat_look.Greeting()               # пустой чат: «<имя>, приступим»
        self.col.insertWidget(0, self.greeting)
        self.refresh_profile()
        self.setFont(theme.app_font(10))                # тот же шрифт с первого виджета
        self._apply_style()
        self.resize(round(WIDTH * self.factor()), round(MAX_HEIGHT * self.factor()))

    def refresh_model_info(self):
        """Кнопка модели: точное имя модели с тегом, например qwen2.5:7b."""
        self.model_info_ready.emit(self.cfg.get("text_model") or "модель")

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

    def _set_model_name(self, text):
        self._model_name = text

    def _open_menu(self, anchor=None):
        """Настройки внизу бокового меню: модель, цвет, голос и тишина, а также все настройки Mico AI."""
        anchor = anchor or self.menu_btn
        menu = QMenu(anchor)
        mm = menu.addMenu("Модель: " + (self._model_name or "…"))
        names = list(self.models_provider() or []) if self.models_provider else []
        if not names:
            act = QAction("Скачанных моделей нет. Скачай в ⚙ Настройки → Модели", mm)
            act.setEnabled(False)
            mm.addAction(act)
        for n in names:
            act = QAction(("✓ " if n == self.cfg.get("text_model") else "") + n, mm)
            act.triggered.connect(lambda _=False, m=n: self.model_pick.emit(m))
            mm.addAction(act)
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
        self._icon_color = chat_look.icon_ink(dark)
        send_text = "#1a1a1a"
        self.btn.setIcon(uiicons.send_icon(send_text))
        self.btn.setIconSize(QSize(12, 12))
        self.mic_btn.setIcon(uiicons.icon("mic", self._icon_color, 15))
        card_edge = f"2px solid {accent}" if self.cfg.get("chat_outline", True) else "none"
        pal = chat_look.PALETTE[bool(dark)]
        bg = pal["card"]                                   # непрозрачный матовый фон
        self.setStyleSheet(theme.FONT_QSS + chat_look.qss(dark, accent) + f"""
            QFrame#card {{ background:{bg}; border:{card_edge}; border-radius:24px; }}
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

    # ----- сообщения -----
    def add_user(self, text):
        self._bubble(text, "me")

    def add_mico(self, text):
        self._bubble(text, "mico")

    def set_file(self, name):
        """Показывает, по какому файлу сейчас отвечает Mico. None — файла нет."""
        self.chip.setVisible(bool(name))
        self.chip_lbl.setText(f"Файл: {name}" if name else "")
        self.inp.setPlaceholderText("Вопрос по файлу…" if name else "Напиши Mico AI…")

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

    def _bubble(self, text, kind, rid=None):
        self.clear_offer_row()                      # новое сообщение — старые варианты уже не актуальны
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
        self._add(wrap)
        if rid is not None:
            self._rows[rid] = wrap
        return wrap

    def _copy_reply(self, text, button):
        """Кладёт ответ Mico в буфер и на секунду показывает «Скопировано»."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        button.setText("Скопировано ✓")
        QTimer.singleShot(1500, lambda: button.setText("Копировать"))

    def _add(self, widget):
        """Новое сообщение — внизу ленты, плавно проявляется."""
        self.col.insertWidget(self.col.count() - 1, widget)         # перед растяжкой
        self.greeting.hide()                                        # есть реплика — приветствие уходит
        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(0.0)
        widget.setGraphicsEffect(eff)
        # после проявления эффект снимаем: прозрачный слой внутри прокрутки рвёт текст при листании
        self._run(eff, b"opacity", 0.0, 1.0, 320, after=lambda: widget.setGraphicsEffect(None))
        QTimer.singleShot(60, self._scroll_end)

    def _fade_history(self):
        """Переключили чат: лента плавно проявляется, а не появляется рывком."""
        eff = QGraphicsOpacityEffect(self.scroll)
        eff.setOpacity(0.0)
        self.scroll.setGraphicsEffect(eff)
        self._run(eff, b"opacity", 0.0, 1.0, 240, after=lambda: self.scroll.setGraphicsEffect(None))

    def _scroll_end(self):
        sb = self.scroll.verticalScrollBar()
        self._run(sb, b"value", sb.value(), sb.maximum(), 300)

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
        """Боковое меню открыто всегда: недавние чаты видны сразу. Оставлено для совместимости."""
        self.side.show()
        self.refresh_side()

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
            self._bubble(text, "me" if role == "user" else "mico", rid=rid)
        self.search.clear()
        self._fade_history()
        if focus_rid is not None and focus_rid in self._rows:
            QTimer.singleShot(60, lambda: self.scroll.ensureWidgetVisible(self._rows[focus_rid], 0, 24))
        else:
            QTimer.singleShot(60, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def clear_messages(self):
        """Новый чат: лента пустая, как у обычного чата."""
        self._stop_thinking()
        self._rw = None
        self._offer_row = None
        for i in reversed(range(self.col.count() - 1)):          # последняя позиция — растяжка, её не трогаем
            w = self.col.itemAt(i).widget()
            if w is not None and w is not self.greeting:
                self.col.takeAt(i)
                w.deleteLater()
        self._rows.clear()
        self.greeting.show()
        self.refresh_profile()

    def refresh_profile(self):
        name = self.cfg.get("user_name", "")
        self.greeting.set_name(name)
        self.side.set_profile(name)

    def _search_changed(self, text):
        q = " ".join(str(text).split())
        if len(q) < 2 or self._store is None:
            self.results.hide()
            return
        cur = self._current_cb() if self._current_cb else None
        hits = [h for h in self._store.conv_search(q, limit=200) if h[0] == cur][:25]
        titles = {}
        self.results.clear()
        for cid, rid, _ts, _role, t in hits:
            self.results.addItem(chat_look.result_item(titles.get(cid, "Чат"), t, q, cid, rid))
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
        from clipbuf import looks_secret
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
        if not text:
            return
        self._draft_timer.stop()
        self._push_draft("")
        self.inp.clear()
        self.send.emit(text)

    # ----- показ и закрытие -----
    def show_near(self, blob, activate=True):
        self._restore_draft()
        """Открывает чат над Mico. Если уже открыт — только поднимает и, при необходимости, даёт фокус."""
        if self.isVisible():
            self.raise_()
            if activate:
                self.activateWindow()
                self.inp.setFocus()
            return
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not activate)
        self._blob = blob
        x, y, w, h = self._spot(blob)
        self.resize(w, h)
        self.setWindowOpacity(0.0)
        self.move(x, y + 14)
        self.show()
        self.raise_()
        self._pos_busy = True
        QTimer.singleShot(320, self._done_opening)
        self._run_pos(QPoint(x, y + 14), QPoint(x, y))
        self._run(self, b"windowOpacity", 0.0, intel.chat_opacity(self.cfg), 300)
        self._follow.start()
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

    def _spot(self, blob):
        """Где стоит чат: над Mico AI и не выше экрана. Если над ним мало места — чат короче;
        если места нет совсем — чат встаёт под Mico. Так он никогда не лезет на Mico."""
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
        if not self.isVisible() or self._blob is None or self._pos_busy:
            return
        x, y, w, h = self._spot(self._blob)
        if abs(self.height() - h) > 2:
            self.resize(w, h)
        if abs(self.x() - x) > 1 or abs(self.y() - y) > 1:
            self.move(x, y)

    def _done_opening(self):
        self._pos_busy = False

    def _run_pos(self, start, end):
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(300)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
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
        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(220)
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade.finished.connect(self._hidden)
        self._fade.start()
        self.set_busy(False)

    def _hidden(self):
        if self.windowOpacity() <= 0.01:
            self._follow.stop()
            self.hide()
            self.setWindowOpacity(intel.chat_opacity(self.cfg))
            self.closed.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(e)
