"""Чат Mico AI — свой, минималистичный (не обычный чат Mico AI). Все надписи — тем же шрифтом, что в настройках (Inter).
Сообщения появляются плавно; пока Mico AI думает, думает и он сам (анимация Mico AI). Открывается над Mico AI, закрывается ✕."""
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QAction, QColor, QGuiApplication
from PyQt6.QtWidgets import (QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                             QLineEdit, QMenu, QPushButton, QScrollArea, QVBoxLayout, QWidget)

import threading
import time

import intel
import theme
import uiicons

WIDTH = 360
MAX_HEIGHT = 480
CHAT_MIN_H = 240                 # ниже — чат неудобно читать
CHAT_GAP = 12                    # зазор между чатом и Mico AI, px


def _flags():
    return Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


class WiChat(QWidget):
    send = pyqtSignal(str)      # пользователь написал — уходит Mico AI
    closed = pyqtSignal()       # чат закрыли
    model_pick = pyqtSignal(str)       # выбрали другую модель в чате
    model_info_ready = pyqtSignal(str) # текст для кнопки модели (считаем в фоне)
    dnd = pyqtSignal(int)       # «не беспокоить» на N минут (0 — выключить)
    rewrite = pyqtSignal(str)   # «short» или «long» — переписать последний ответ
    file_cleared = pyqtSignal() # файл из чата убрали

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
        self._follow.setInterval(8)
        self._follow.timeout.connect(self._follow_blob)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame(self)
        self.card.setObjectName("card")
        root.setContentsMargins(14, 14, 14, 14)               # место для тени внутри окна
        root.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(4)
        title = QLabel("Mico AI")
        title.setObjectName("title")
        self.model_btn = QPushButton("модель")
        self.model_btn.setObjectName("ghost")
        self.model_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_btn.setToolTip("Какая модель отвечает и сколько памяти она занимает. Нажми, чтобы сменить.")
        self.model_btn.clicked.connect(self._model_menu)
        self.model_info_ready.connect(self.model_btn.setText)
        self.models_provider = None        # подставляет intel_ui: список скачанных моделей
        quiet = QPushButton("Тишина")
        quiet.setIcon(uiicons.icon("moon", "#8e8e93", 14))
        quiet.setObjectName("ghost")
        quiet.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(quiet)
        for minutes, text in intel.DND_CHOICES:
            act = QAction(text, menu)
            act.triggered.connect(lambda _=False, m=minutes: self.dnd.emit(m))
            menu.addAction(act)
        quiet.setMenu(menu)
        close = QPushButton()
        close.setIcon(uiicons.icon("close", "#8e8e93", 14))
        close.setObjectName("ghost")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.dismiss)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.model_btn)
        head.addWidget(quiet)
        head.addWidget(close)
        lay.addLayout(head)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.box = QWidget()
        self.col = QVBoxLayout(self.box)
        self.col.setContentsMargins(0, 4, 0, 4)
        self.col.setSpacing(10)
        self.col.addStretch(1)
        self.scroll.setWidget(self.box)
        lay.addWidget(self.scroll, 1)
        self.chip = QFrame()                       # плашка прикреплённого файла: вопросы идут по нему
        self.chip.setObjectName("chip")
        cr = QHBoxLayout(self.chip)
        cr.setContentsMargins(10, 4, 4, 4)
        self.chip_lbl = QLabel("")
        self.chip_lbl.setObjectName("chipText")
        drop = QPushButton("✕")
        drop.setObjectName("ghost")
        drop.setCursor(Qt.CursorShape.PointingHandCursor)
        drop.clicked.connect(self.file_cleared.emit)
        cr.addWidget(self.chip_lbl, 1)
        cr.addWidget(drop)
        self.chip.setVisible(False)
        lay.addWidget(self.chip)
        self._rw = None                            # строка «Короче / Подробнее» под последним ответом
        self._offer_row = None                     # кнопки под предложением Mico AI
        self._thinking = None                      # строка «Mico AI думает…» в ленте
        self._think_timer = None                   # мигает точками, пока Mico AI думает
        self._think_n = 1
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Напиши Mico AI…")
        self.inp.setObjectName("field")
        self.inp.returnPressed.connect(self._send)
        self.on_draft = None                               # main сохраняет черновик на диск
        self._draft_timer = QTimer(self)                   # сохраняем через паузу, а не на каждую букву
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(800)
        self._draft_timer.timeout.connect(self._save_draft)
        self.inp.textChanged.connect(lambda _t: self._draft_timer.start())
        self.btn = QPushButton()
        self.btn.setObjectName("send")
        self.btn.setFixedSize(34, 34)                        # круглая кнопка отправки
        self.btn.setToolTip("Отправить")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._send)
        row.setSpacing(6)
        row.addWidget(self.inp, 1)
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.setFont(theme.app_font(10))                # Inter с первого же виджета, не системный шрифт
        self._apply_style()
        self.resize(WIDTH, MAX_HEIGHT)

    def refresh_model_info(self):
        """Кнопка модели: точное имя модели с тегом, например qwen2.5:7b."""
        self.model_info_ready.emit(self.cfg.get("text_model") or "модель")

    def _model_menu(self):
        menu = QMenu(self.model_btn)
        names = list(self.models_provider() or []) if self.models_provider else []
        if not names:
            act = QAction("Скачанных моделей нет. Скачай в ⚙ Настройки → Модели", menu)
            act.setEnabled(False)
            menu.addAction(act)
        for n in names:
            act = QAction(("✓ " if n == self.cfg.get("text_model") else "") + n, menu)
            act.triggered.connect(lambda _=False, m=n: self.model_pick.emit(m))
            menu.addAction(act)
        menu.exec(self.model_btn.mapToGlobal(QPoint(0, self.model_btn.height())))

    def _apply_style(self):
        """Оформление чата: тема, цвет Mico AI и настройка «Подсветка кнопок». Вызывается и на лету, без перезапуска."""
        dark = theme.is_dark(self.cfg)
        r, g, b = intel.hex_rgb(self.cfg.get("color", "#FFCFA3"))
        accent = "#%02X%02X%02X" % (r, g, b)
        glow = intel.glow_on(self.cfg)
        if dark:
            bg, fg, muted = "rgba(24,22,28,240)", "#f1ebe1", "#7d7787"
            field, border, hover = "rgba(255,255,255,0.055)", "rgba(255,255,255,0.08)", "rgba(255,255,255,0.09)"
            icon, send_text = "#8f899a", "#1a1620"
        else:
            bg, fg, muted = "rgba(255,252,246,244)", "#2b2118", "#9a8e7b"
            field, border, hover = "rgba(60,40,20,0.05)", "rgba(60,40,20,0.10)", "rgba(60,40,20,0.08)"
            icon, send_text = "#8a7d6a", "#1a1620"
        # подсветка кнопок: при наведении акцентный цвет; выключена — кнопки просто темнеют/светлеют
        hover_accent = f"border:1px solid {accent}; background:rgba({r},{g},{b},0.14);" if glow else \
            f"border:1px solid {border}; background:{hover};"
        send_hover = uiicons.mix(accent, "#FFFFFF", 0.18) if glow else accent
        self._icon_color = icon
        # обводка окна чата: по настройке «Обводка вокруг окна чата» (раньше здесь была всегда одна линия)
        card_edge = f"2px solid {accent}" if self.cfg.get("chat_outline", True) else "none"
        # обводка поля ввода: по настройке «Обводка поля ввода»
        in_on = bool(self.cfg.get("wi_input_outline", True))
        field_border = f"border:1px solid {border};" if in_on else "border:none;"
        focus_border = f"border:1px solid {accent};" if in_on else "border:none;"
        self.btn.setIcon(uiicons.send_icon(send_text))
        self.btn.setIconSize(QSize(17, 17))
        self.setStyleSheet(theme.FONT_QSS + f"""
            QFrame#card {{ background:{bg}; border:{card_edge}; border-radius:20px; }}
            QLabel {{ background:transparent; color:{fg}; font-size:13px; }}
            QLabel#title {{ color:{fg}; font-size:13px; font-weight:600; }}
            QLabel#tag {{ color:{accent}; font-size:10px; font-weight:600; padding:1px 6px;
                          border:1px solid rgba({r},{g},{b},0.45); border-radius:10px; }}
            QLabel#me {{ background:rgba({r},{g},{b},0.16); color:{fg}; border-radius:16px;
                         padding:9px 14px; font-size:13px; }}
            QLabel#mico {{ color:{fg}; padding:4px 2px; font-size:13px; }}
            QFrame#tl {{ background:{field}; border-radius:12px; }}
            QFrame#chip {{ background:{field}; border-radius:12px; }}
            QLabel#chipText {{ color:{muted}; font-size:12px; }}
            QLabel#tlTime {{ color:{muted}; font-size:11px; }}
            QPushButton#chipBtn {{ background:transparent; color:{fg}; border:1px solid {border};
                                   border-radius:12px; padding:5px 13px; font-size:12px; }}
            QPushButton#chipBtn:hover {{ {hover_accent} }}
            QLineEdit#field {{ background:{field}; color:{fg}; {field_border} border-radius:16px;
                               padding:8px 15px; font-size:13px; selection-background-color:{accent};
                               selection-color:{send_text}; }}
            QLineEdit#field:focus {{ {focus_border} }}
            QPushButton#send {{ background:{accent}; border:none; border-radius:16px; padding:0; }}
            QPushButton#send:hover {{ background:{send_hover}; }}
            QPushButton#ghost {{ background:transparent; color:{muted}; border:none; border-radius:10px;
                                 font-size:12px; padding:4px 8px; }}
            QPushButton#ghost:hover {{ color:{fg}; background:{field}; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollArea > QWidget > QWidget {{ background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:6px; margin:0; }}
            QScrollBar::handle:vertical {{ background:{border}; border-radius:8px; min-height:24px; }}
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
        self.chip_lbl.setText(f"📎 {name}" if name else "")
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

    def _bubble(self, text, kind):
        self.clear_offer_row()                      # новое сообщение — старые варианты уже не актуальны
        lab = QLabel(str(text or ""))
        lab.setObjectName(kind)
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.TextFormat.PlainText)
        lab.setMaximumWidth(int(WIDTH * 0.8))
        lab.setMinimumWidth(40)                                   # иначе колонка сжимается до самого узкого слова
        lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if kind == "me":
            row.addStretch(0)
            row.addWidget(lab, 1)
        else:
            row.addWidget(lab, 1)
            row.addStretch(0)
        wrap = QWidget()
        wrap.setLayout(row)
        self._add(wrap)

    def _add(self, widget):
        """Новое сообщение — внизу ленты, плавно проявляется."""
        self.col.insertWidget(self.col.count() - 1, widget)         # перед растяжкой
        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(0.0)
        widget.setGraphicsEffect(eff)
        # после проявления эффект снимаем: прозрачный слой внутри прокрутки рвёт текст при листании
        self._run(eff, b"opacity", 0.0, 1.0, 320, after=lambda: widget.setGraphicsEffect(None))
        QTimer.singleShot(60, self._scroll_end)

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
        """Mico AI думает: в ленте появляется строка «Mico AI думает» с мигающими точками.
        Исчезает, как только ответ готов. Так видно сразу, и в режиме полоски тоже."""
        if on:
            if self._thinking is not None:
                return
            self._thinking = QLabel("Mico AI думает.")
            self._thinking.setObjectName("mico")
            self._thinking.setWordWrap(True)
            self._thinking.setTextFormat(Qt.TextFormat.PlainText)
            self._think_n = 1
            self._add(self._thinking)
            if self._think_timer is None:
                self._think_timer = QTimer(self)
                self._think_timer.timeout.connect(self._think_tick)
            self._think_timer.start(380)
        else:
            self._stop_thinking()

    def _think_tick(self):
        if self._thinking is None:
            return
        self._think_n = self._think_n % 3 + 1
        self._thinking.setText("Mico AI думает" + "." * self._think_n)

    def _stop_thinking(self):
        if self._think_timer is not None:
            self._think_timer.stop()
        if self._thinking is not None:
            self.col.removeWidget(self._thinking)
            self._thinking.deleteLater()
            self._thinking = None


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

    def _spot(self, blob):
        """Где стоит чат: над Mico AI и не выше экрана. Если над ним мало места — чат короче;
        если места нет совсем — чат встаёт под Mico. Так он никогда не лезет на Mico."""
        scr = QGuiApplication.screenAt(blob.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        w = WIDTH
        want = min(MAX_HEIGHT, max(CHAT_MIN_H, g.height() // 2))
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
