"""Голосовой чат Mico AI Pro: полоска 350×42 внизу экрана.
Слева — живой Mico (тот же, что на рабочем столе: двигается, моргает, говорит) и под ним время разговора.
Посередине — волны голоса (или субтитры, если включены). Справа — микрофон, голос и скорость,
палитра, субтитры и завершение разговора. Палитра и голос/скорость открываются над полоской.
Экрана в голосовом режиме нет: Mico смотрит только на разговор."""
import math
import time

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QFontMetrics, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

import chat_look
import intel
import settings_look
import theme
import uiicons
import voice_models
from blob import BASE_PX                       # размер Mico AI при масштабе 100%
from onboarding import COLORS as PALETTE       # те же цвета, что при первом запуске
from theme_tokens import RADIUS
from ui_anim import pulse_icon
from aichat import _flags

BAR_W, BAR_H = 420, 80     # полоска голосового чата, px (небольшая)
GLOW = 16                 # поле вокруг полоски под свечение, px
SLOT_X, SLOT_W = 8, 92    # слот Mico слева: отступ и ширина
BLOB_PX = 80              # Mico в полоске, px (крупнее прежнего)
DETACH_GAP = 10            # Mico, вынутый из полоски, висит над ней на это расстояние, px
CAPTION_GAP = 10           # субтитры над полоской, px
END_PAD = 14              # правый отступ: кнопка закрытия не прижата к скруглённому краю
FULL_H = BAR_H + 2 * GLOW  # высота полоски (окно)
BODY_CY = 0.54            # тело Mico рисуется на этой доле высоты окна (см. Blob.paintEvent)
EDGE = 14                 # отступ полоски от низа экрана, px
MUTED_RED = "#ff6b6b"     # значок микрофона, когда он выключен
ICON = 20                 # значок в кнопке, px
BTN = 40                  # кнопка полоски, px
SPEEDS = [(0.5, "0,5x"), (1.0, "1x"), (1.5, "1,5x"), (2.0, "2x")]   # скорость речи
SUB_CHARS = 220           # сколько последних символов ответа помещаем в субтитры


def _tail(text, n):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else "…" + text[-n:]


def _lift(hex_c):
    """Светлее — для наведения на кнопку завершения."""
    r, g, b = intel.hex_rgb(hex_c)
    k = 0.18
    return "#%02X%02X%02X" % (round(r + (255 - r) * k), round(g + (255 - g) * k), round(b + (255 - b) * k))


class VoiceDock(QWidget):
    color_pick = pyqtSignal(str)    # цвет из палитры: Mico крутится и меняет цвет
    mute_clicked = pyqtSignal()     # микрофон: выключить или снова включить
    all_settings = pyqtSignal()     # «Все настройки Mico AI» из панели голоса
    exit_clicked = pyqtSignal()     # завершить голосовой чат
    voice_pick = pyqtSignal(str)    # голос из настроек
    speed_pick = pyqtSignal(float)  # скорость речи из настроек
    subs_toggled = pyqtSignal(bool) # субтитры включили или выключили

    def __init__(self, cfg):
        super().__init__(None, _flags())
        self.cfg = cfg
        self._blob = None               # настоящий Mico: окно, которое переезжает в левый слот полоски
        self._anims = []
        self._gliding = False           # Mico сейчас переезжает: полоска его не догоняет
        self._expected = QPoint()       # где Mico должен быть по нашим расчётам
        self._drag_from = None          # перетаскивание полоски за фон
        self._muted = False
        self._user_v = 0.0              # громкость пользователя и Mico — по ним волна
        self._mico_v = 0.0
        self._sub_text = ""             # последняя фраза для субтитров
        self._status = ""               # короткий статус голоса («Слушаю…»)
        self._detached = False          # Mico вынут из полоски (стоит в центре экрана)
        self._pill = False              # Mico спит внутри узкой обводки
        self._mode = "full"             # full — полная полоска, controls — вынут, mico — только Mico в обводке
        self._w_anim = None             # анимация ширины полоски
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)     # не забираем фокус у других окон
        self.setFixedSize(BAR_W + 2 * GLOW, BAR_H + 2 * GLOW)     # поле под свечение вокруг полоски
        self._accent = "#FFCFA3"
        self._follow = QTimer(self)
        self._follow.setTimerType(Qt.TimerType.PreciseTimer)
        self._follow.setInterval(16)    # 60 кадров, как у Mico AI
        self._follow.timeout.connect(self._sync)

        root = QVBoxLayout(self)
        root.setContentsMargins(GLOW, GLOW, GLOW, GLOW)
        self.card = QFrame(self)
        self.card.setObjectName("voiceBar")
        root.addWidget(self.card)
        row = QHBoxLayout(self.card)
        self.row_lay = row                                 # отступы меняются: в режиме Mico — симметричные
        row.setContentsMargins(SLOT_X, 0, END_PAD, 0)
        row.setSpacing(3)

        # слот Mico: место под живого Mico и время разговора под ним
        self.slot = QWidget()
        self.slot.setFixedWidth(SLOT_W)
        sl = QVBoxLayout(self.slot)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        sl.addStretch(1)                                  # Mico стоит окном выше; время — у самого низа
        row.addWidget(self.slot)

        self.spacer = QWidget()                            # распорка между Mico и кнопками; в режимах «вынут»/«сон» её нет
        self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row.addWidget(self.spacer)

        # кнопки: микрофон, голос и скорость, палитра, субтитры, завершить
        self.mic_btn = self._button(row, "Микрофон", self.mute_clicked.emit)
        self.settings_btn = self._button(row, "Голос и скорость речи", self._toggle_settings)
        self.palette_btn = self._button(row, "Цвет Mico: выбери из палитры", self._toggle_colors)
        self.subs_btn = self._button(row, "Субтитры", self._toggle_subs)
        self.exit_btn = self._button(row, "Завершить голосовой чат", self.exit_clicked.emit)
        self.exit_btn.setObjectName("endBtn")

        # всплывающие панели над полоской: палитра и голос со скоростью
        self.colors = self._popover()
        crow = QHBoxLayout()
        crow.setSpacing(8)
        self._color_btns = []
        for hex_c, name in PALETTE:
            b = QPushButton()
            b.setFixedSize(24, 24)                   # круг держит border-radius
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(name)
            b.clicked.connect(lambda _=False, c=hex_c: self._pick_color(c))
            crow.addWidget(b)
            self._color_btns.append((b, hex_c))
        self.colors.layout().insertWidget(0, self._caption("Цвет Mico"))
        self.colors.layout().addLayout(crow)

        self.settings = self._popover()
        sl2 = self.settings.layout()
        sl2.addWidget(self._caption("Голос"))
        self._voice_btns = []
        items = list(voice_models.VOICES.items())
        for i in range(0, len(items), 4):                    # по четыре голоса в ряд, чтобы панель оставалась компактной
            vrow = QHBoxLayout()
            vrow.setSpacing(6)
            for key, voice in items[i:i + 4]:
                b = self._chip(voice["title"], lambda k=key: self._pick_voice(k))
                vrow.addWidget(b)
                self._voice_btns.append((b, key))
            sl2.addLayout(vrow)
        sl2.addWidget(self._caption("Скорость речи"))
        srow = QHBoxLayout()
        srow.setSpacing(6)
        self._speed_btns = []
        for value, label in SPEEDS:
            b = self._chip(label, lambda v=value: self._pick_speed(v))
            srow.addWidget(b)
            self._speed_btns.append((b, value))
        sl2.addLayout(srow)
        sl2.addWidget(self._chip("Все настройки Mico AI", self._open_all_settings))

        # субтитры — отдельная плашка над полоской: видна, когда включены и Mico говорит или слушает
        self.caption = QFrame(None, _flags())
        self.caption.setObjectName("subtitleBox")
        self.caption.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.caption.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        cl = QVBoxLayout(self.caption)
        cl.setContentsMargins(16, 10, 16, 10)
        self.cap_lbl = QLabel("")
        self.cap_lbl.setObjectName("capText")
        self.cap_lbl.setWordWrap(True)
        self.cap_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cap_lbl.setMaximumWidth(BAR_W)
        cl.addWidget(self.cap_lbl)
        self.caption.hide()

        self.setFont(theme.app_font(10))
        self.refresh(False)

    # ----- элементы -----
    def _button(self, row, tip, slot):
        b = QPushButton()
        b.setObjectName("dockBtn")
        b.setStyleSheet(f"QPushButton {{ border-radius:{BTN // 2}px; }}")
        b.setFixedSize(BTN, BTN)
        b.setIconSize(QSize(ICON, ICON))          # явный размер значка: на нём работает отклик на нажатие
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tip)
        b.setProperty("on", "false")
        b.clicked.connect(lambda _=False, btn=b: pulse_icon(btn))
        b.clicked.connect(lambda _=False: self._after_click(slot))
        row.addWidget(b)
        return b

    def _popover(self):
        """Всплывающая панель над полоской: своё окно, как у палитры. Закрывается повторным нажатием."""
        pop = QFrame(None, _flags())
        pop.setObjectName("pop")
        pop.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        lay = QVBoxLayout(pop)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        pop.hide()
        return pop

    def _chip(self, text, slot):
        b = QPushButton(text)
        b.setObjectName("chip")
        b.setStyleSheet("QPushButton { border-radius:16px; }")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedHeight(32)
        b.setProperty("on", "false")
        b.clicked.connect(lambda _=False: self._after_click(slot))
        return b

    def _after_click(self, slot):
        """Нажатие на кнопку: действие, затем Mico снова на виду и поверх полоски."""
        slot()
        if self._blob is not None:
            if not self._blob.isVisible():
                self._blob.show()
            self._blob.raise_()
    @staticmethod
    def _caption(text):
        lab = QLabel(text)
        lab.setObjectName("caption")
        return lab

    @staticmethod
    def _set_on(w, on):
        """Подсветка кнопки: свойство «on» меняет вид по стилю, без пересоздания кнопки."""
        w.setProperty("on", "true" if on else "false")
        w.style().unpolish(w)
        w.style().polish(w)

    # ----- вид -----
    def refresh(self, muted):
        """Цвета по теме и цвету Mico. Значки показывают состояние: микрофон, субтитры."""
        self._muted = bool(muted)
        dark = theme.is_dark(self.cfg)
        r, g, b = intel.hex_rgb(self.cfg.get("color", "#FFCFA3"))
        accent = "#%02X%02X%02X" % (r, g, b)
        pal = theme.fluent(dark)                       # цвета — из общей палитры Mico AI, как в чате и настройках
        cp = chat_look.PALETTE[bool(dark)]
        fg, muted_c = cp["text"], cp["muted"]
        soft = f"rgba({r},{g},{b},0.24)"
        accent_edge = f"rgba({r},{g},{b},0.85)"
        subs_on = bool(self.cfg.get("voice_subs", False))
        cur_voice = self.cfg.get("voice_name") or voice_models.DEFAULT_VOICE
        cur_speed = float(self.cfg.get("voice_speed", 1.0))

        self.mic_btn.setIcon(uiicons.icon("mic_off" if muted else "mic", MUTED_RED if muted else accent, ICON))
        self.mic_btn.setToolTip("Микрофон выключен — нажми, чтобы снова слушать" if muted
                                else "Микрофон — нажми, чтобы выключить")
        # значки тонкие и цвета Mico — как на образце; выключенные субтитры приглушаем
        self.settings_btn.setIcon(uiicons.icon("tune", accent, ICON))
        self.palette_btn.setIcon(uiicons.icon("palette", accent, ICON))
        self.subs_btn.setIcon(uiicons.icon("subs", accent, ICON))
        self.subs_btn.setToolTip("Субтитры включены — нажми, чтобы вернуть волны" if subs_on
                                 else "Субтитры: показывать текст вместо волн")
        self.exit_btn.setIcon(uiicons.icon("close", accent, ICON))
        self._accent = accent
        self._set_on(self.subs_btn, subs_on)
        self._set_on(self.palette_btn, self.colors.isVisible())
        self._set_on(self.settings_btn, self.settings.isVisible())
        for btn, hex_c in self._color_btns:
            sel = hex_c.upper() == accent.upper()
            edge_c = f"2px solid {fg}" if sel else f"1px solid {cp['stroke']}"
            btn.setStyleSheet(f"QPushButton {{ background:{hex_c}; border:{edge_c}; border-radius:11px; }}")
        for btn, key in self._voice_btns:
            self._set_on(btn, key == cur_voice)
        for btn, value in self._speed_btns:
            self._set_on(btn, abs(cur_speed - value) < 0.01)
        self.setStyleSheet(theme.FONT_QSS + chat_look.qss(dark, accent) + f"""
            QFrame#voiceBar {{ background:{cp['card']}; border:2px solid {accent};
                               border-radius:{BAR_H // 2}px; }}
            QPushButton#dockBtn {{ background:transparent; border:none; border-radius:{BTN // 2}px; }}
            QPushButton#dockBtn:hover {{ background:rgba(255,255,255,0.08); }}
            QPushButton#dockBtn[on="true"] {{ background:{soft}; }}
            QPushButton#endBtn {{ background:rgba(255,255,255,0.14); border:1px solid {accent_edge};
                                  border-radius:{BTN // 2}px; }}
            QPushButton#endBtn:hover {{ background:rgba(255,255,255,0.24); }}
            QFrame#pop {{ background:{cp['card']}; border:1px solid {cp['stroke']}; border-radius:{RADIUS["card"]}px; }}
            QPushButton#chip {{ background:transparent; border:1px solid {cp['stroke']}; border-radius:13px;
                                color:{muted_c}; font-size:13px; padding:4px 12px; }}
            QPushButton#chip:hover {{ background:{cp['hover']}; }}
            QPushButton#chip[on="true"] {{ background:{soft}; border:1px solid {accent_edge}; color:{fg}; }}
            QLabel#caption {{ color:{muted_c}; font-size:11px; background:transparent; }}
            QLabel#vsub {{ color:{fg}; font-size:17px; background:transparent; }}
        """)
        pop_qss = theme.FONT_QSS + f"""
            QFrame#pop {{ background:{cp['head']}; border:1px solid {accent_edge}; border-radius:22px; }}
            QLabel#caption {{ color:{muted_c}; font-size:11px; font-weight:600; background:transparent; }}
            QPushButton#chip {{ background:{cp['side']}; border:1px solid {cp['stroke']}; border-radius:17px;
                                color:{muted_c}; font-size:13px; padding:0px 16px; min-height:30px; }}
            QPushButton#chip:hover {{ background:{cp['hover']}; color:{fg}; }}
            QPushButton#chip[on="true"] {{ background:{soft}; border:1px solid {accent_edge}; color:{fg}; font-weight:600; }}
        """
        self.colors.setStyleSheet(pop_qss)
        self.settings.setStyleSheet(pop_qss)
        self.caption.setStyleSheet(theme.FONT_QSS + f"""
            QFrame#subtitleBox {{ background:{cp['head']}; border:1px solid {accent_edge}; border-radius:20px; }}
            QLabel#capText {{ color:{fg}; font-size:15px; background:transparent; }}
        """)
        self._show_mid()

    def set_user_level(self, v):
        """Пользователь говорит: волна раскачивается от его голоса."""
        self._user_v = 0.0 if self._muted else float(v)

    def set_mico_level(self, v):
        """Mico говорит вслух: волна и рот раскачиваются от его голоса."""
        self._mico_v = float(v)
        if self._blob is not None:
            self._blob.set_voice_level(self._mico_v)

    def set_status(self, text):
        """Статус голоса («Слушаю…», «Скачиваю голос…») не пишем в полоске: при разговоре пользователя
        здесь волна. Текст остаётся в подсказке у полоски."""
        self._status = text or ""
        self.card.setToolTip(self._status)
        self._show_mid()

    def clear_subs(self):
        """Новый голосовой режим: старые субтитры не показываем."""
        self._sub_text = ""
        self._show_mid()

    def show_user(self, text):
        """Субтитры: что сказал пользователь."""
        self._sub_text = _tail(text, SUB_CHARS)
        self._show_mid()

    def show_mico(self, text):
        """Субтитры: что говорит Mico. Показываем последние слова, если ответ длинный."""
        self._sub_text = _tail(text, SUB_CHARS)
        self._show_mid()

    def _show_mid(self):
        """Субтитры: плашка над полоской. Если речи ещё не было — подсказка, чтобы было видно, что кнопка работает."""
        if not (self._subs_on() and self._mode == "full"):
            self.cap_lbl.setText("")
            self.caption.hide()
            return
        text = self._sub_text or "Субтитры включены: здесь будет всё, что я говорю и слышу"
        self.cap_lbl.setText(text)
        self.caption.show()
        self._place_caption()
    def _place_caption(self):
        if not self.caption.isVisible():
            return
        self.caption.adjustSize()
        x = self.x() + (self.width() - self.caption.width()) // 2
        y = self.y() + GLOW - self.caption.height() - CAPTION_GAP
        self.caption.move(x, max(0, y))

    def moveEvent(self, e):
        super().moveEvent(e)
        self._place_caption()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._place_caption()

    def _open_all_settings(self):
        self.settings.hide()
        self.all_settings.emit()

    def _toggle_colors(self):
        self._show_section(None if self.colors.isVisible() else self.colors)

    def _toggle_settings(self):
        self._show_section(None if self.settings.isVisible() else self.settings)

    def _show_section(self, which):
        for pop in (self.colors, self.settings):
            if pop is which:
                self._position_pop(pop)
                pop.show()
                pop.raise_()
            else:
                pop.hide()
        self.refresh(self._muted)

    def _position_pop(self, pop):
        pop.adjustSize()
        x = self.x() + (self.width() - pop.width()) // 2
        y = self.y() + GLOW - pop.height() - 8
        pop.move(x, max(0, y))

    def _pick_color(self, hex_c):
        """Цвет выбран: палитра закрывается, Mico крутится и меняет цвет."""
        self.colors.hide()
        self.color_pick.emit(hex_c)
        self.refresh(self._muted)

    def _pick_voice(self, key):
        self.voice_pick.emit(key)                 # сохраняется и применяется сразу, голосовой режим не закрываем
        self.refresh(self._muted)

    def _pick_speed(self, value):
        self.speed_pick.emit(float(value))
        self.refresh(self._muted)

    def _toggle_subs(self):
        on = not bool(self.cfg.get("voice_subs", False))
        self.cfg["voice_subs"] = on
        self.subs_toggled.emit(on)
        self.refresh(self._muted)
    def _screen_geo(self):
        center = self._blob.geometry().center() if self._blob is not None else self.geometry().center()
        scr = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        return scr.availableGeometry()             # не заходим на панель задач

    def _stage_pos(self):
        """Полоска внизу по центру экрана."""
        g = self._screen_geo()
        x = g.left() + (g.width() - self.width()) // 2
        y = max(g.top() + EDGE, g.bottom() - self.height() - EDGE)
        return QPoint(x, y)

    def _mico_spot(self, x=None, size=None):
        """Где стоит окно Mico в слоте: центр тела — по центру полоски. В режиме сна слот — ровно под Mico."""
        b = self._blob
        h = b.height() if size is None else size
        x0 = self.x() if x is None else x
        sw = BLOB_PX if self._mode == "mico" else SLOT_W
        y = self.y() + GLOW + int(BAR_H / 2 - BODY_CY * h)
        return QPoint(x0 + GLOW + SLOT_X + (sw - h) // 2, y)

    def _detach_spot(self, px):
        """Вынутый Mico висит над полоской по центру, чуть выше неё, а не в центре экрана."""
        cx = self.x() + self.width() // 2
        g = self._screen_geo()
        y = max(g.top() + 8, self.y() + GLOW - DETACH_GAP - px)
        return QPoint(cx - px // 2, y)
    def _unit(self):
        """Размер Mico при доле 1 (как _blob_k): BLOB_PX = unit * _blob_k()."""
        return BASE_PX * max(0.5, float(self.cfg.get("scale", 1.0)))
    def paintEvent(self, _):
        """Ровный мягкий ореол вокруг полоски: несколько тонких контуров, каждый бледнее предыдущего."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(self.rect()).adjusted(GLOW, GLOW, -GLOW, -GLOW)
        base = QColor(self._accent)
        steps = 6
        for i in range(steps):
            c = QColor(base)
            c.setAlpha(int(64 * (1 - i / steps)))
            p.setPen(QPen(c, 1.0))
            k = 1.0 + i * 2.0
            p.drawRoundedRect(rect.adjusted(-k, -k, k, k), BAR_H / 2 + k, BAR_H / 2 + k)
        p.end()

    def _blob_k(self):
        """Доля размера, при которой Mico помещается в слот полоски."""
        try:
            scale = float(self.cfg.get("scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        return BLOB_PX / (BASE_PX * max(0.5, scale))

    def show_stage(self, blob, *_, **__):
        """Разговор начался: полоска внизу, Mico переезжает в левый слот и начинает говорить и двигаться."""
        self._blob = blob
        self._follow.stop()
        self._stop_anims()
        self._detached = False
        self._pill = False
        self._reset_layout()
        self.move(self._stage_pos())
        blob.voice_k = None                       # размер плавно меняет _morph ниже
        blob.locked = True                        # движением Mico управляет полоска, а не сам Mico
        blob.keep_awake = False                   # Mico может уснуть в полоске (голосовой режим)
        blob._apply_opacity()                     # в полоске Mico яркий
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        blob.show()
        blob.raise_()
        self._run(self, b"windowOpacity", 0.0, 1.0, 260)
        k = self._blob_k()
        px = int(self._unit() * k)
        spot = self._mico_spot(size=px)
        self._morph(k, QPoint(spot.x() + px // 2, spot.y() + px // 2), after=self._settled, ms=640)

    def _settled(self):
        self._expected = QPoint(self._blob.pos())
        self._follow.start()

    def _subs_on(self):
        return bool(self.cfg.get("voice_subs", False))

    def _subs_on(self):
        return bool(self.cfg.get("voice_subs", False))

    def _mode_visibility(self, mode):
        """full — полоска с Mico и кнопками; controls — вынут: только кнопки; mico — спит: только Mico в обводке."""
        self.slot.setVisible(mode != "controls")
        self.slot.setFixedWidth(BLOB_PX if mode == "mico" else SLOT_W)
        self.spacer.setVisible(mode == "full")
        for btn in (self.mic_btn, self.settings_btn, self.palette_btn, self.subs_btn, self.exit_btn):
            btn.setVisible(mode != "mico")
        # в режиме сна обводка облегает Mico: отступы справа и слева одинаковые
        self.row_lay.setContentsMargins(SLOT_X, 0, SLOT_X if mode == "mico" else END_PAD, 0)
    def _controls_w(self):
        """Точная ширина полоски «только кнопки»: пять кнопок, промежутки и отступы — без пустого места."""
        return 2 * GLOW + SLOT_X + END_PAD + 5 * BTN + 4 * self.row_lay.spacing()

    def _full_w(self):
        """Ширина полной полоски по формуле: Mico, пять кнопок и отступы. Одна и та же при уходе и возврате."""
        return 2 * GLOW + SLOT_X + SLOT_W + 5 * BTN + 4 * self.row_lay.spacing() + END_PAD

    def _controls_w(self):
        """Точная ширина полоски «только кнопки»: пять кнопок, промежутки и отступы — без пустого места."""
        return 2 * GLOW + SLOT_X + END_PAD + 5 * BTN + 4 * self.row_lay.spacing()

    def _target_w(self, mode):
        """Ширина полоски: полная — по формуле, «только кнопки» — точная, сон — по содержимому."""
        if mode == "full":
            return self._full_w()
        if mode == "controls":
            return self._controls_w()
        return self.sizeHint().width()
    def _reset_layout(self):
        """Мгновенно — полная полоска (перед показом и после скрытия)."""
        if self._w_anim is not None:
            self._w_anim.stop()
            self._w_anim = None
        self._mode = "full"
        self._mode_visibility("full")
        self.setFixedSize(self._target_w("full"), FULL_H)
    def _set_mode(self, mode, follow=True, ms=640):
        """Плавный переход: полоска сужается или растёт вокруг центра, Mico переезжает и меняет размер
        одновременно. Возвращает место Mico в конце перехода."""
        self._mode = mode
        self._mode_visibility(mode)
        target = self._target_w(mode)
        cx = self.x() + self.width() // 2
        final_x = cx - target // 2
        if mode == "controls":
            k1 = None
            px1 = int(self._unit())
            spot = self._detach_spot(px1)
        else:
            k1 = self._blob_k()
            px1 = int(self._unit() * k1)
            spot = self._mico_spot(x=final_x, size=px1)
        center = QPoint(spot.x() + px1 // 2, spot.y() + px1 // 2)
        if self._w_anim is not None:
            self._w_anim.stop()
        anim = QVariantAnimation(self)
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setStartValue(float(self.width()))
        anim.setEndValue(float(target))

        def step(v):
            w = int(round(v))
            if abs(w - self.width()) >= 2:                  # реже перерисовываем: полоска не дёргается
                self.setFixedSize(w, FULL_H)
            x = cx - self.width() // 2
            if x != self.x():
                self.move(x, self.y())
        anim.valueChanged.connect(step)
        anim.finished.connect(lambda: self._snap_width(target, cx))   # в конце — ровно нужная ширина
        self._w_anim = anim
        anim.start()
        self._morph(k1, center, after=self._settled if follow else None, ms=ms)
        return spot
    def _snap_width(self, w, cx):
        self.setFixedSize(w, FULL_H)
        self.move(cx - w // 2, self.y())

    def _morph(self, k_to, center_to, after=None, ms=640):
        """Mico плавно меняет размер и переезжает к center_to одновременно. Размер меняем вокруг центра,
        поэтому он не уезжает: при росте окна левый верхний угол сдвигался бы и центр тоже."""
        b = self._blob
        if getattr(self, "_morph_anim", None) is not None:
            self._morph_anim.stop()                        # новый переезд заменяет прежний, а не спорит с ним
        unit = self._unit()
        k0 = b.size_k
        k1 = 1.0 if k_to is None else k_to
        c0 = QPoint(b.x() + b.width() // 2, b.y() + b.height() // 2)
        b.voice_k = k_to
        b.locked = True
        b.morphing = True
        self._gliding = True

        anim = QVariantAnimation(self)
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def step(t):
            k = k0 + (k1 - k0) * t
            px = max(1, int(unit * k))
            cx = c0.x() + (center_to.x() - c0.x()) * t
            cy = c0.y() + (center_to.y() - c0.y()) * t
            b.size_k = k
            if px != b.width():
                b.setFixedSize(px, px)
            b.move(int(round(cx)) - px // 2, int(round(cy)) - px // 2)

        def done():
            px = max(1, int(unit * k1))
            b.size_k = k1
            b.setFixedSize(px, px)
            b.move(center_to.x() - px // 2, center_to.y() - px // 2)
            b.morphing = False
            self._gliding = False
            if not b.isVisible():
                b.show()
            if after is not None:
                after()
        anim.valueChanged.connect(lambda v: step(float(v)))
        anim.finished.connect(done)
        self._anims.append(anim)
        self._morph_anim = anim
        anim.start()
    def toggle_detach(self):
        """Один клик по Mico: плавно вынимает его из полоски в центр экрана (полоска сужается до кнопок);
        ещё клик — плавно возвращает в полоску."""
        b = self._blob
        if b is None or self._pill:
            return
        self._detached = not self._detached
        if self._detached:
            self._follow.stop()
            b.locked = True
            self._set_mode("controls", follow=False)
        else:
            b.locked = True
            self._set_mode("full", follow=True)
    def in_pill(self):
        return self._pill

    def sleep_pill(self):
        """Mico уснул в полоске: если был вынут — плавно заезжает в полоску, полоска сужается до обводки.
        Возвращает место сна (чтобы при пробуждении он не прыгал)."""
        b = self._blob
        if b is None or self._pill:
            return None
        self._pill = True
        self._detached = False
        b.locked = True
        self._follow.stop()
        b.set_mood("sleepy")                              # спит: настроение держим, пока не проснётся
        return self._set_mode("mico", follow=True)
    def expand_pill(self):
        """Mico проснулся в обводке: полоска разворачивается обратно, Mico садится в слот."""
        if not self._pill or self._blob is None:
            return
        self._pill = False
        self._blob.locked = True
        self._set_mode("full", follow=True)
    def dismiss(self, return_to=None, after=None):
        """Разговор закончился: Mico сворачивается обратно на рабочий стол и возвращается в свою обычную форму,
        полоска плавно гаснет. after — что сделать, когда Mico на месте (здесь показываем чат)."""
        self._follow.stop()
        self._stop_anims()
        self._detached = False
        self.colors.hide()
        self.settings.hide()
        b = self._blob
        if b is None:
            self._released(after)
            self._hide_now()
            return
        b.voice_k = None                          # Mico возвращается к своему обычному размеру
        b._apply_opacity()                        # и к прозрачности из настроек
        if self.isVisible() and b.isVisible() and return_to is not None:
            self._glide_blob(return_to, 320, after=lambda: self._released(after))
        else:
            if return_to is not None:
                b.move(return_to)
            self._released(after)
        if self.isVisible():
            self._run(self, b"windowOpacity", self.windowOpacity(), 0.0, 220, after=self._hide_now)
        else:
            self._hide_now()

    def _released(self, after):
        if self._blob is not None:
            self._blob.locked = False                # Mico снова сам решает, где стоять
            self._blob.set_voice_level(0.0)
        if after is not None:
            after()

    def _hide_now(self):
        self.hide()
        self.caption.hide()
        self.setWindowOpacity(1.0)
        self._pill = False
        self._reset_layout()

    def _sync(self):
        """Каждый кадр: полоска и Mico держатся вместе. Mico утащили — полоска едет за ним."""
        b = self._blob
        if b is None or not self.isVisible() or self._gliding or self._detached:
            return
        if b.pos() != self._expected:
            self.move(self.pos() + b.pos() - self._expected)
        spot = self._mico_spot()
        if b.pos() != spot:
            b.move(spot)
        self._expected = QPoint(b.pos())

    def _run(self, obj, prop, start, end, ms, after=None):
        anim = QPropertyAnimation(obj, prop, self)
        anim.setDuration(int(ms))
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

    def _stop_anims(self):
        for a in list(self._anims):
            a.stop()
        self._anims = []
        self._gliding = False
        self._morph_anim = None
        if self._blob is not None:
            self._blob.morphing = False                    # прерванный переезд не оставляет Mico в режиме «вокруг центра»

    def _glide_blob(self, target, ms, after=None):
        """Mico плавно переезжает в target. Полоска пока не догоняет его, а после — вызываем after."""
        b = self._blob
        b.locked = True
        self._gliding = True
        anim = QPropertyAnimation(b, b"pos", self)
        anim.setDuration(int(ms))
        anim.setStartValue(QPoint(b.pos()))
        anim.setEndValue(QPoint(target))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anims.append(anim)

        def done():
            if anim in self._anims:
                self._anims.remove(anim)
            self._gliding = False
            if after is not None:
                after()
        anim.finished.connect(done)
        anim.start()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_from = e.globalPosition().toPoint() - self.pos()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_from is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_from)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_from = None
