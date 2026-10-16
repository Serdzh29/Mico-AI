"""Чат Mico WI — свой, минималистичный (не обычный чат Mico). Все надписи — тем же шрифтом, что в настройках (Inter).
Сообщения появляются плавно; пока Mico думает, думает и он сам (анимация Mico). Открывается над Mico, закрывается ✕."""
import voice
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

import threading
import time

import intel
import theme

WIDTH = 360
MAX_HEIGHT = 480
CHAT_MIN_H = 240                 # ниже — чат неудобно читать
CHAT_GAP = 12                    # зазор между чатом и Mico, px


def _flags():
    return Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


class WiChat(QWidget):
    send = pyqtSignal(str)      # пользователь написал — уходит Mico
    _heard = pyqtSignal(str)    # распознанная фраза с микрофона (из фонового потока)
    closed = pyqtSignal()       # чат закрыли
    journal = pyqtSignal()      # просят таймлайн дня
    dnd = pyqtSignal(int)       # «не беспокоить» на N минут (0 — выключить)
    rewrite = pyqtSignal(str)   # «short» или «long» — переписать последний ответ
    file_cleared = pyqtSignal() # файл из чата убрали

    def __init__(self, cfg):
        super().__init__(None, _flags())
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anims = []
        self._fade = None
        self._blob = None                        # Mico, рядом с которым стоит чат
        self._pos_busy = False                   # первые ~320 мс чат выезжает на место — не мешаем анимации
        self._follow = QTimer(self)              # чат едет за Mico: он мог прыгнуть, уехать во сне или его перетащили
        self._follow.setInterval(40)
        self._follow.timeout.connect(self._follow_blob)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame(self)
        self.card.setObjectName("card")
        root.addWidget(self.card)
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel("Mico · WI (BETA)")
        title.setObjectName("title")
        journal = QPushButton("Таймлайн")
        journal.setObjectName("ghost")
        journal.setCursor(Qt.CursorShape.PointingHandCursor)
        journal.clicked.connect(self.journal.emit)
        quiet = QPushButton("Тишина")
        quiet.setObjectName("ghost")
        quiet.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(quiet)
        for minutes, text in intel.DND_CHOICES:
            act = QAction(text, menu)
            act.triggered.connect(lambda _=False, m=minutes: self.dnd.emit(m))
            menu.addAction(act)
        quiet.setMenu(menu)
        close = QPushButton("✕")
        close.setObjectName("ghost")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.dismiss)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(journal)
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
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Напиши Mico…")
        self.inp.returnPressed.connect(self._send)
        self.mic = QPushButton("🎤")
        self.mic.setFixedWidth(36)
        self.mic.setToolTip("Сказать голосом")
        self.mic.setVisible(bool(cfg.get("voice_listen", True)))
        self.mic.clicked.connect(self._listen)
        self._heard.connect(self._on_heard)
        self.btn = QPushButton("↑")
        self.btn.setObjectName("send")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self._send)
        row.addWidget(self.inp, 1)
        row.addWidget(self.mic)
        row.addWidget(self.btn)
        lay.addLayout(row)
        self.setFont(theme.app_font(10))                # Inter с первого же виджета, не системный шрифт
        self._apply_style()
        self.resize(WIDTH, MAX_HEIGHT)

    def _apply_style(self):
        dark = theme.is_dark(self.cfg)
        r, g, b = intel.hex_rgb(self.cfg.get("color", "#FFCFA3"))
        accent = "#%02X%02X%02X" % (r, g, b)
        bg, fg, muted, field, border = (
            ("rgba(28,26,32,238)", "#efe9df", "#8a8494", "rgba(255,255,255,0.06)", "rgba(255,255,255,0.10)") if dark
            else ("rgba(255,252,245,242)", "#2b2118", "#8a7d6a", "rgba(0,0,0,0.04)", "rgba(0,0,0,0.08)"))
        self.setStyleSheet(theme.FONT_QSS + f"""
            QFrame#card {{ background:{bg}; border:1px solid {border}; border-radius:18px; }}
            QLabel {{ background:transparent; color:{fg}; font-size:13px; }}
            QLabel#title {{ color:{muted}; font-size:10px; font-weight:600; }}
            QLabel#me {{ background:rgba({r},{g},{b},0.22); color:{fg}; border-radius:12px; padding:7px 11px; }}
            QLabel#mico {{ color:{fg}; padding:2px 2px; }}
            QFrame#tl {{ background:rgba(127,127,127,0.10); border-radius:12px; }}
            QFrame#chip {{ background:{field}; border-radius:10px; }}
            QLabel#chipText {{ color:{muted}; font-size:12px; }}
            QPushButton#chipBtn {{ background:{field}; color:{fg}; border:1px solid {border}; border-radius:10px;
                                   padding:3px 10px; font-size:12px; }}
            QPushButton#chipBtn:hover {{ border-color:{accent}; }}
            QLabel#tlTime {{ color:{muted}; font-size:11px; }}
            QLineEdit {{ background:{field}; color:{fg}; border:1px solid {border}; border-radius:14px;
                         padding:7px 12px; font-size:13px; selection-background-color:{accent}; }}
            QLineEdit:focus {{ border:1px solid {accent}; }}
            QPushButton#send {{ background:{accent}; color:#201a14; border:none; border-radius:14px;
                                min-width:28px; max-width:28px; min-height:28px; max-height:28px;
                                font-size:14px; font-weight:600; }}
            QPushButton#ghost {{ background:transparent; color:{muted}; border:none; font-size:12px; padding:0 4px; }}
            QPushButton#ghost:hover {{ color:{fg}; }}
            QScrollArea {{ background:transparent; border:none; }}
            QScrollArea > QWidget > QWidget {{ background:transparent; }}
            QScrollBar:vertical {{ background:transparent; width:6px; margin:0; }}
            QScrollBar::handle:vertical {{ background:{border}; border-radius:3px; min-height:24px; }}
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
        self.inp.setPlaceholderText("Вопрос по файлу…" if name else "Напиши Mico…")

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

    def _rewrite_clicked(self, mode):
        if self._rw is not None:
            self.col.removeWidget(self._rw)
            self._rw.deleteLater()
            self._rw = None
        self.rewrite.emit(mode)

    def show_timeline(self, rows, summary_text):
        """Таймлайн дня: одна строка итога и лента по времени. Полоски — доля времени за день."""
        self._bubble(summary_text, "mico")
        card = QFrame()
        card.setObjectName("tl")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)
        if not rows:
            v.addWidget(QLabel("Пока ничего нет."))
        for r in rows:
            line = QHBoxLayout()
            when = QLabel(time.strftime("%H:%M", time.localtime(r["ts"])))
            when.setObjectName("tlTime")
            when.setFixedWidth(44)
            text = f'{r["label"]} · {r["detail"]}' if r["kind"] == "app" else f'{r["label"]}: {r["detail"]}'
            lab = QLabel(text)
            lab.setWordWrap(True)
            line.addWidget(when)
            line.addWidget(lab, 1)
            v.addLayout(line)
            if r["kind"] == "app":
                w = max(2, int(r["share"] * 100))
                bar = QHBoxLayout()
                bar.setContentsMargins(44, 0, 0, 0)
                bar.setSpacing(0)
                fill = QFrame()
                fill.setFixedHeight(6)
                fill.setStyleSheet(f"background:{r['colour']}; border-radius:3px;")
                rest = QWidget()
                rest.setFixedHeight(6)
                bar.addWidget(fill, w)
                bar.addWidget(rest, max(1, 100 - w))
                v.addLayout(bar)
        self._add(card)

    def _bubble(self, text, kind):
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
        """Mico думает. Точек в чате больше нет: это показывает сам Mico (его анимация «думаю»)."""

    def _send(self):
        text = self.inp.text().strip()
        if not text:
            return
        self.inp.clear()
        self.send.emit(text)

    def _listen(self):
        """Микрофон: одна фраза в фоне; распознанный текст уходит Mico как обычный запрос."""
        self.mic.setEnabled(False)
        self.inp.setPlaceholderText("Слушаю…")

        def work():
            try:
                text, err = voice.listen_once(self.cfg, 8)     # Vosk, офлайн
                text = voice.strip_wake(text, voice.wake_words_from(self.cfg.get("wake_words")))
            except Exception as e:
                text, err = "", f"Микрофон не запустился: {e}"
            self._mic_error = err
            self._heard.emit(text)
        threading.Thread(target=work, daemon=True).start()

    def _on_heard(self, text):
        self.mic.setEnabled(True)
        self.inp.setPlaceholderText("Напиши Mico…")
        if text:
            self.send.emit(text)
            return
        note = self._mic_error or "Не расслышал. Нажми 🎤 и скажи ещё раз."
        self.inp.setPlaceholderText(note)
        QTimer.singleShot(5000, lambda: self.inp.setPlaceholderText("Напиши Mico…"))

    # ----- показ и закрытие -----
    def show_near(self, blob, activate=True):
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
        self._run(self, b"windowOpacity", 0.0, 1.0, 300)
        self._follow.start()
        if activate:
            self.activateWindow()
            self.inp.setFocus()

    def _spot(self, blob):
        """Где стоит чат: над Mico и не выше экрана. Если над ним мало места — чат короче;
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
        """Mico прыгнул, уехал во сне или его перетащили — чат едет за ним и остаётся рядом, не наезжая."""
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
            self.setWindowOpacity(1.0)
            self.closed.emit()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(e)
