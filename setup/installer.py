"""Мастер установки и удаление Mico. Работает только в собранном Mico.exe.
Оформление в духе Mico AI: тёмная тема, персиковый акцент, без лишнего текста.
Тексты — через i18n.t(): мастер и удаление показываются на английском (см. i18n_installer_en.py)."""
import json, math, os, random, shutil, subprocess, sys, time

from PyQt6.QtCore import QPointF, QRectF, QEasingCurve, QThread, QVariantAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (QPainterPath, QBrush, QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter, QPen, QPixmap,
                         QRadialGradient)
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox,
                             QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget, QButtonGroup,
                             QRadioButton, QComboBox, QLineEdit, QInputDialog)
import i18n
from ui import theme
from ui.controls import Switch, WrapCheck    # переключатели — как в настройках Mico AI
from ui.theme import FONT_FAMILY, FONT_DISPLAY

FROZEN = bool(getattr(sys, "frozen", False))
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", "Mico")
INSTALL_EXE = os.path.join(INSTALL_DIR, "Mico.exe")
ICON_PATH = os.path.join(INSTALL_DIR, "mico.ico")
APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Mico"

# Ключи — русские тексты; переводятся в момент показа (i18n.t), не при импорте модуля.
STEPS = [
    ("Копирую Mico AI в папку программ", "curious"),
    ("Создаю ярлык на рабочем столе", "happy"),
    ("Настраиваю автозапуск", "thinking"),
    ("Регистрирую Mico AI в Windows", "thinking"),
    ("Сохраняю настройки", "happy"),
    ("Готовлю ответы Mico AI", "curious"),
]


def should_run():
    """Запускать мастер: только в собранной версии и только не из папки установки."""
    if not FROZEN:
        return False
    return os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(INSTALL_EXE))


# Что Mico AI рассказывает во время установки: (текст, настроение лица). Только то, что Mico умеет на самом деле.
FACTS = [
    ("Я Mico AI, компаньон для Windows. Живу на рабочем столе, и я рядом, пока ты работаешь.", "happy"),
    ("Открываю программы и сайты одной фразой: «открой блокнот» или «открой ютуб».", "love"),
    ("Громкость, яркость, Wi-Fi и Bluetooth: «громкость 30», «выключи Wi-Fi».", "laugh"),
    ("Ставлю таймер и напоминания: «таймер на 10 минут», «напомни через час позвонить».", "curious"),
    ("Переключаю больше 130 настроек Windows и объясню, что каждая из них делает.", "thinking"),
    ("Опасные команды, например выключение компьютера, я сначала спрошу «да или нет».", "worried"),
    ("Отвечаю на вопросы прямо на этом компьютере.", "curious"),
    ("В голосовом режиме нажми на меня, и я обрадуюсь.", "happy"),
    ("Ответы считаются прямо на твоём компьютере, без облака.", "thinking"),
    ("Ты можешь сказать «запомни», и я сохраню заметку. Потом спросишь — и я вспомню.", "love"),
    ("Скоро установка закончится. В меню Mico AI, по правому щелчку, есть всё, что я умею.", "happy"),
]
FACT_MS = 4800                       # сколько показывается один факт

# Умения, которые плывут по орбите вокруг Mico в мастере (как на сайте). Только то, что Mico умеет на самом деле.
SHOWCASE = ["«открой ютуб»", "«громкость 30»", "«таймер на 10 минут»", "«включи тёмную тему»",
            "«напомни через час»", "«запомни: …»", "«агент, напиши маме»", "«что ты умеешь?»"]
# Какое умение подсветить, пока Mico рассказывает факт: номер в FACTS -> номер в SHOWCASE.
FACT_SHOW = {1: 0, 2: 1, 3: 2, 4: 3, 9: 5, 10: 7}


class MicoAvatar(QLabel):
    """Mico AI в мастере установки и удаления. Рисуется программой, живой: моргает, дышит, и настроение
    меняется плавно — старое лицо растворяется в новое за FADE_MS, а не прыгает."""
    SIZE = 120                       # аккуратный Mico над текстом страницы
    FRAME_MS = 33
    FADE_MS = 520

    def __init__(self, mood="happy", color="#FFCFA3", size=None):
        super().__init__()
        from ui.blob import Blob, BASE_PX
        if size:
            self.SIZE = size                             # на живой сцене мастера Mico крупнее
        self.setMinimumSize(self.SIZE, self.SIZE)
        self._blob = Blob({"color": color, "scale": self.SIZE / BASE_PX, "opacity": 1.0,
                           "sleep_after_min": 3, "assist_style": "classic", "placement": "manual",
                           "sleep_corner": "br", "anim_sleep_fps": 20})
        self._blob.can_sleep = lambda: False                 # в установке Mico не засыпает
        self._blob.timer.stop()                              # кадры двигаем сами, ниже
        self._mood = mood
        self._blob.set_mood(mood, 999)
        self._old = None                                     # кадр прошлого настроения, пока он растворяется
        self._fade = 1.0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._frame)
        self._timer.start()
        self._frame()

    def set_mood(self, mood):
        if mood == self._mood:
            return
        self._old = self._pixmap_now()
        self._mood = mood
        self._blob.set_mood(mood, 999)
        self._fade = 0.0

    def _pixmap_now(self):
        pix = QPixmap(self._blob.width(), self._blob.height())
        pix.fill(Qt.GlobalColor.transparent)
        self._blob.render(pix)
        return pix

    def _frame(self):
        self._blob.tick()
        cur = self._pixmap_now()
        if self._old is not None:
            self._fade = min(1.0, self._fade + self.FRAME_MS / self.FADE_MS)
            t = QEasingCurve(QEasingCurve.Type.InOutSine).valueForProgress(self._fade)
            out = QPixmap(cur.size())
            out.fill(Qt.GlobalColor.transparent)
            p = QPainter(out)
            p.setOpacity(1.0 - t)
            p.drawPixmap(0, 0, self._old)
            p.setOpacity(t)
            p.drawPixmap(0, 0, cur)
            p.end()
            cur = out
            if self._fade >= 1.0:
                self._old = None
        self.setPixmap(cur)


def _asset(name):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", name)
    return p if os.path.exists(p) else None


def column(*items):
    """Страница из элементов по вертикали (виджеты и отступы числом). Страница листается, если не влезает:
    раньше при выборе Groq появлялись подсказки, и карточки с кнопками сжимались в полоски."""
    from PyQt6.QtWidgets import QScrollArea
    w = QWidget()
    w.setObjectName("pageBody")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 6, 0)
    for it in items:
        if isinstance(it, int):
            lay.addSpacing(it)
        else:
            lay.addWidget(it)
    lay.addStretch()
    scroll = QScrollArea()
    scroll.setObjectName("pageScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(w)
    return scroll


# Палитры мастера — те же поверхности, что в чате и настройках Mico (Windows 11), акцент — цвет Mico.
# Тёмная и светлая: какая нужна, решает тема Windows на этом ПК.
_DARK = {
    "bg": "#202020", "card": "#2b2b2b", "stroke": "#3a3a3a", "foot": "#1b1b1b", "seg": "#2d2d2d",
    "text": "#ffffff", "title": "#ffffff", "sub": "#a6a6a6", "step": "#8a8a8a", "brand": "#a6a6a6",
    "accent": "#FFCFA3", "accent_text": "#1a1a1a", "accent_hover": "#ffdcbd",
    "accent_off_bg": "rgba(255,255,255,0.06)", "accent_off_text": "#6e6e6e",
    "ok": "#6ccb5f", "warn": "#fce100", "check": "#ffffff",
    "box": "transparent", "box_edge": "#5a5a5a",
    "btn_bg": "#2d2d2d", "btn_edge": "#3a3a3a", "btn_text": "#ffffff",
    "btn_hover": "#333333", "btn_press": "#292929",
    "btn_off": "#6e6e6e", "bar": "#3a3a3a", "side_edge": "#3a3a3a",
}
_LIGHT = {
    "bg": "#f3f3f3", "card": "#ffffff", "stroke": "#e5e5e5", "foot": "#ebebeb", "seg": "#e6e6e6",
    "text": "#1a1a1a", "title": "#1a1a1a", "sub": "#5d5d5d", "step": "#7a7a7a", "brand": "#5d5d5d",
    "accent": "#FFCFA3", "accent_text": "#1a1a1a", "accent_hover": "#ffc48f",
    "accent_off_bg": "rgba(0,0,0,0.06)", "accent_off_text": "#9a9a9a",
    "ok": "#0f7b0f", "warn": "#9d5d00", "check": "#1a1a1a",
    "box": "transparent", "box_edge": "#c4c4c4",
    "btn_bg": "#ffffff", "btn_edge": "#e0e0e0", "btn_text": "#1a1a1a",
    "btn_hover": "#f6f6f6", "btn_press": "#f0f0f0",
    "btn_off": "#a0a0a0", "bar": "#e0e0e0", "side_edge": "#e5e5e5",
}


def _mico_color():
    """Цвет Mico: из настроек, если Mico уже стоял (обновление, удаление), иначе фирменный персиковый."""
    try:
        with open(os.path.join(APPDIR, "config.json"), encoding="utf-8") as f:
            color = str(json.load(f).get("color") or "")
        if len(color) == 7 and color.startswith("#"):
            return color
    except Exception:
        pass
    return "#FFCFA3"


def _shade(hex_color, k):
    """Светлее (k>0, к белому) или темнее (k<0, к чёрному) на долю k."""
    h = str(hex_color).lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    t = (255, 255, 255) if k > 0 else (0, 0, 0)
    k = abs(k)
    return "#%02x%02x%02x" % tuple(int(v * (1 - k) + tv * k) for v, tv in zip((r, g, b), t))


def _palette(dark):
    c = dict(_DARK if dark else _LIGHT)
    c["accent"] = _mico_color()
    c["accent_text"] = theme.on_accent(c["accent"])
    # цвет кнопки при наведении считаем от цвета Mico: раньше он оставался фиксированным бежевым, и кнопка «Закрыть» при
    # наведении меняла цвет на чужой. Тёмная тема: чуть светлее, светлая: чуть темнее.
    c["accent_hover"] = _shade(c["accent"], 0.22 if dark else -0.12)
    return c


def card(*widgets):
    """Карточка с пунктами один под другим и тонкими линиями между ними — как в Параметрах Windows 11."""
    box = QFrame()
    box.setObjectName("card")
    lay = QVBoxLayout(box)
    lay.setContentsMargins(16, 6, 16, 6)
    lay.setSpacing(0)
    for i, w in enumerate(widgets):
        if i:
            sep = QFrame()
            sep.setObjectName("sep")
            sep.setFixedHeight(1)
            lay.addWidget(sep)
        w.setContentsMargins(0, 8, 0, 8)
        lay.addWidget(w)
    return box


def qss(dark=None):
    """Стиль мастера установки и удаления. dark=None — как в Windows на этом ПК."""
    if dark is None:
        dark = theme.system_dark()
    c = _palette(dark)
    Switch.ON, Switch.OFF = c["accent"], ("#4a4a4a" if dark else "#d1d1d6")   # переключатели — цвет Mico
    Switch.OFF_EDGE = "#a6a6a6" if dark else "#5d5d5d"                          # выключен — тонкий контур
    Switch.KNOB_ON = c["accent_text"]
    return f"""
QDialog#wizard {{ background: {c['bg']}; }}
QLabel {{ color: {c['text']}; font-family: "{FONT_FAMILY}"; font-size: 13px; background: transparent; }}
QLabel#title {{ font-family: "{FONT_DISPLAY}"; font-size: 24px; font-weight: 700; color: {c['title']}; }}
QLabel#sub {{ color: {c['sub']}; font-size: 13px; }}
QLabel#section {{ color: {c['text']}; font-size: 13px; font-weight: 600; }}
QLabel#fact {{ color: {c['sub']}; font-size: 13px; }}
QLabel#step {{ color: {c['step']}; font-size: 12px; }}
QLabel#brand {{ font-family: "{FONT_DISPLAY}"; color: {c['brand']}; font-size: 13px; font-weight: 600; }}
QLabel#percent {{ font-family: "{FONT_DISPLAY}"; font-size: 40px; font-weight: 700; color: {c['title']}; }}
QLabel#ok {{ color: {c['ok']}; font-size: 13px; }}
QLabel#warn {{ color: {c['warn']}; font-size: 13px; }}
QFrame#card {{ background: {c['card']}; border: 1px solid {c['stroke']}; border-radius: 8px; }}
QFrame#sep {{ background: {c['stroke']}; border: none; }}
QFrame#footLine {{ background: {c['stroke']}; border: none; }}
QFrame#foot {{ background: {c['foot']}; border: none; }}
QFrame#seg {{ background: {c['seg']}; border: none; border-radius: 8px; }}
QPushButton#segBtn {{ background: transparent; border: none; border-radius: 6px; padding: 6px 18px; color: {c['text']}; }}
QPushButton#segBtn:hover {{ background: {c['btn_hover']}; }}
QPushButton#segBtn:checked {{ background: {c['accent']}; color: {c['accent_text']}; font-weight: 600; }}
QRadioButton {{ color: {c['text']}; font-size: 13px; background: {c['card']}; border: 1px solid {c['stroke']};
               border-radius: 8px; padding: 12px 14px; spacing: 10px; min-height: 20px; }}
QRadioButton:hover {{ background: {c['btn_hover']}; }}
QRadioButton:checked {{ border: 1px solid {c['accent']}; }}
QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 9px; border: 1px solid {c['box_edge']}; background: transparent; }}
QRadioButton::indicator:checked {{ border: 1px solid {c['accent']}; background: {c['accent']}; }}
QCheckBox {{ color: {c['check']}; font-size: 13px; spacing: 12px; padding: 6px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {c['box_edge']}; background: {c['box']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border: 1px solid {c['accent']}; }}
QPushButton {{ font-family: "{FONT_FAMILY}"; font-size: 13px; padding: 6px 20px; border-radius: 6px; min-height: 20px;
              background: {c['btn_bg']}; color: {c['btn_text']}; border: 1px solid {c['btn_edge']}; }}
QPushButton:hover {{ background: {c['btn_hover']}; }}
QPushButton:pressed {{ background: {c['btn_press']}; }}
QPushButton:disabled {{ color: {c['btn_off']}; }}
QPushButton#primary {{ font-family: "{FONT_FAMILY}"; background: {c['accent']}; color: {c['accent_text']};
                      border: 1px solid {c['accent']}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {c['accent_hover']}; border: 1px solid {c['accent_hover']}; }}
QPushButton#primary:disabled {{ background: {c['accent_off_bg']}; color: {c['accent_off_text']}; border: none; }}
QScrollArea#pageScroll, QWidget#pageBody {{ background: transparent; border: none; }}
QScrollArea#pageScroll > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['bar']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QProgressBar {{ background: {c['bar']}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}
QProgressBar#glowBar {{ background: transparent; max-height: 16px; min-height: 16px; }}
"""


def _ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _back_out(x, c=1.70158):
    x = max(0.0, min(1.0, x))
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


class GlowBar(QProgressBar):
    """Полоска прогресса со свечением: по заливке бежит блик, у края горит огонёк. Те же методы, что у QProgressBar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glowBar")
        self.setTextVisible(False)
        self.setFixedHeight(16)
        self._t0 = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def paintEvent(self, e):
        c = _palette(theme.system_dark())
        t = time.monotonic() - self._t0
        span = max(1, self.maximum() - self.minimum())
        frac = max(0.0, min(1.0, (self.value() - self.minimum()) / span))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 4, self.width(), 8)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["bar"]))
        p.drawRoundedRect(r, 4, 4)
        if frac <= 0:
            p.end()
            return
        fw = max(r.height(), r.width() * frac)
        fill = QRectF(r.left(), r.top(), fw, r.height())
        acc = QColor(c["accent"])
        g = QLinearGradient(fill.left(), 0, fill.right(), 0)
        g.setColorAt(0, acc.darker(112))
        g.setColorAt(1, acc.lighter(125))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(fill, 4, 4)
        p.save()                                         # блик бежит по заливке
        clip = QPainterPath()
        clip.addRoundedRect(fill, 4, 4)
        p.setClipPath(clip)
        bx = fill.left() + ((t * .55) % 1.6 - .3) * fw
        sh = QLinearGradient(bx - 40, 0, bx + 40, 0)
        sh.setColorAt(0, QColor(255, 255, 255, 0))
        sh.setColorAt(.5, QColor(255, 255, 255, 120))
        sh.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(sh))
        p.drawRect(QRectF(bx - 40, fill.top(), 80, fill.height()))
        p.restore()
        hx = fill.right()                                # огонёк на краю
        hg = QRadialGradient(QPointF(hx, r.center().y()), 14 + 3 * math.sin(t * 6))
        h0, h1 = QColor(acc), QColor(acc)
        h0.setAlpha(170)
        h1.setAlpha(0)
        hg.setColorAt(0, h0)
        hg.setColorAt(1, h1)
        p.setBrush(QBrush(hg))
        p.drawEllipse(QPointF(hx, r.center().y()), 14, 14)
        p.end()


class _PageSlide(QWidget):
    """Переход между страницами: прошлая уезжает влево и тает, новая выезжает справа. Рисуются два снимка — это дёшево,
    сами страницы не двигаются и не пересчитываются каждый кадр (раньше из-за этого переход подвисал)."""

    def __init__(self, old, new, bg, parent):
        super().__init__(parent)
        self.old, self.new, self.bg, self.k = old, new, bg, 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), self.bg)
        e = max(0.0, min(1.0, self.k))
        p.setOpacity(1 - e)
        p.drawPixmap(QPointF(-46 * e, 0), self.old)
        p.setOpacity(e)
        p.drawPixmap(QPointF(46 * (1 - e), 0), self.new)
        p.end()


class _SlideMixin:
    """Смена страниц мастера: снимок до и после, плавный переезд (общий для установки и удаления)."""

    def _grab_old(self):
        self._old_pix = self.pages.grab() if self.isVisible() else None

    def _fade_pages(self):
        old = getattr(self, "_old_pix", None)
        self._old_pix = None
        if old is None or old.isNull():
            return
        new = self.pages.grab()
        c = _palette(theme.system_dark())
        prev = getattr(self, "_slide_ov", None)
        if prev is not None:
            try:
                prev.deleteLater()
            except RuntimeError:
                pass
        ov = _PageSlide(old, new, QColor(c["bg"]), self.pages)
        ov.setGeometry(self.pages.rect())
        ov.show()
        ov.raise_()
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(480)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        def step(v):
            ov.k = float(v)
            ov.update()
        anim.valueChanged.connect(step)
        anim.finished.connect(ov.deleteLater)
        self._slide_ov, self._slide_anim = ov, anim
        anim.start()


class StepDots(QWidget):
    """Индикатор шагов: точки, текущий шаг — вытянутая акцентная таблетка. Цвет берётся из палитры мастера."""

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.count = count
        self.current = 0
        self.setFixedHeight(10)
        self.setMinimumWidth(count * 22)

    def set_current(self, i):
        self.current = max(0, min(self.count - 1, i))
        self.update()

    def paintEvent(self, e):
        dark = theme.system_dark()
        c = _palette(dark)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        x = 0
        for i in range(self.count):
            if i == self.current:
                p.setBrush(QColor(c["accent"]))
                p.drawRoundedRect(QRectF(x, 2, 20, 6), 3, 3)
                x += 28
            else:
                p.setBrush(QColor(c["box_edge"]))
                p.drawEllipse(QRectF(x + 2, 2, 6, 6))
                x += 14
        p.end()


class ShowStage(QWidget):
    """Живая сцена над страницами мастера, как на сайте Mico. За Mico переливается мягкое сияние в его цветах,
    вокруг по орбите плывут его умения: дальние — меньше и бледнее, ближние — крупнее. Пока идёт установка,
    вокруг Mico бежит кольцо прогресса, а умение, о котором он рассказывает, подсвечивается. В конце — салют.
    При удалении умения разлетаются и сияние гаснет. Щелчок по Mico — он подпрыгивает.
    Кадры Mico берутся у MicoAvatar (он сам моргает и плавно меняет лицо), сцена только рисует его в центре."""
    FULL_H, COMPACT_H = 250, 132
    GLOWS = ("#FFB3C6", "#B8C0FF", "#9FD3FF")
    MICO_PX = 150

    def __init__(self, avatar, leaving=False, parent=None):
        super().__init__(parent)
        self.avatar = avatar
        self.leaving = leaving
        self.setFixedHeight(self.FULL_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._t0 = time.monotonic()
        self._last = self._t0
        self._chips = [i18n.t(c) for c in SHOWCASE]
        self._hot, self._hot_t = -1, -9.0
        self._jump_t = -9.0
        self._prog = None                 # 0..1 — кольцо прогресса; None — кольца нет
        self._shown = 0.0                 # что видно сейчас: догоняет _prog плавно
        self._leave = self._leave_to = 0.0
        self._compact = self._compact_to = 0.0
        self._sparks = []
        self._rings = [0.2]               # ударные волны от Mico: время запуска (в секундах сцены)
        self._motes = [[random.random(), random.random(), random.uniform(.015, .05), random.uniform(1.2, 3.0),
                        random.uniform(0, 6.28)] for _ in range(30)]    # пылинки света медленно плывут вверх
        self._stream = []                 # частицы потока: при установке летят к Mico, при удалении — от него
        self._spawn = 0.0
        self._pulse = 0.0                 # короткая пульсация Mico, когда частица долетела
        self._timer = QTimer(self)
        self._timer.setInterval(16)       # ~60 кадров в секунду
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ---------- управление сценой ----------
    def set_progress(self, value):
        self._prog = None if value is None else max(0.0, min(1.0, float(value)))

    def set_leave(self, value):
        self._leave_to = max(0.0, min(1.0, float(value)))

    def set_compact(self, on):
        self._compact_to = 1.0 if on else 0.0

    def highlight(self, index):
        self._hot, self._hot_t = index, self._now()

    def replay_intro(self):
        """Вступление: Mico влетает с отскоком, орбита с умениями раскрывается, по сцене проходит волна."""
        self._t0 = time.monotonic()
        self._jump_t = -9.0
        self._rings = [0.25, 0.7]
        self.burst(36)

    def jump(self):
        self._jump_t = self._now()
        self._rings.append(self._now())

    def burst(self, count=70):
        """Салют из конфетти от Mico: в конце установки и при щелчке по нему."""
        w, h = self.width(), self.height()
        cols = [QColor(_mico_color())] + [QColor(x) for x in ("#FFB3C6", "#B8C0FF", "#9FD3FF", "#A8E6CF", "#F6D365")]
        for i in range(count):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(160, 520)
            self._sparks.append([w / 2, h * .5, math.cos(a) * v, math.sin(a) * v - 200, random.uniform(0, 360),
                                 random.uniform(-540, 540), 1.0, cols[i % len(cols)], random.choice((4, 5, 6))])

    def _now(self):
        return time.monotonic() - self._t0

    def mousePressEvent(self, e):
        if (e.position() - QPointF(self.width() / 2, self.height() * .5)).manhattanLength() < 100:
            self.jump()
            self.burst(18)
        super().mousePressEvent(e)

    def _tick(self):
        now = time.monotonic()
        dt = min(0.05, now - self._last)
        self._last = now
        k = 1 - math.pow(0.004, dt)                      # плавное «догоняние» без рывков, не зависит от частоты кадров
        self._leave += (self._leave_to - self._leave) * k * .6
        self._compact += (self._compact_to - self._compact) * k
        if self._prog is not None:
            self._shown += (self._prog - self._shown) * k
        for s in self._sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 620 * dt                             # конфетти падает
            s[2] *= math.pow(0.35, dt)
            s[4] += s[5] * dt
            s[6] -= dt * .75
        self._sparks = [s for s in self._sparks if s[6] > 0]
        t_now = self._now()
        self._rings = [r for r in self._rings if t_now - r < 1.3]
        self._pulse *= math.pow(0.02, dt)
        for m in self._motes:
            m[1] -= m[2] * dt
            if m[1] < -0.05:
                m[1], m[0] = 1.05, random.random()
        if self._prog is not None and 0.0 < self._prog < 1.0:     # поток частиц ускоряется вместе с прогрессом
            self._spawn += (16 + 60 * self._prog) * dt
            while self._spawn >= 1 and len(self._stream) < 90:
                self._spawn -= 1
                a = random.uniform(0, 2 * math.pi)
                self._stream.append([a, random.uniform(.5, .95), 0.0, random.uniform(1.6, 3.2),
                                     random.choice((0, 0, 1, 2))])
        for q in self._stream:
            q[2] += q[1] * dt
            if q[2] >= 1.0:
                self._pulse = min(1.0, self._pulse + .35)
        self._stream = [q for q in self._stream if q[2] < 1.0]
        want = int(round(self.FULL_H + (self.COMPACT_H - self.FULL_H) * self._compact))
        if want != self.height():
            self.setFixedHeight(want)                    # на «Параметрах» сцена плавно становится ниже
        self.update()

    # ---------- рисование ----------
    def _chip(self, p, c, text, x, y, depth, hot_k, fade):
        sc = .8 + .28 * depth + .24 * hot_k
        alpha = max((.25 + .75 * depth) * fade * (1 - .85 * self._compact), hot_k)
        if alpha <= .02:
            return
        f = QFont(FONT_FAMILY)
        f.setPixelSize(max(8, int(round(12 * sc))))
        p.setFont(f)
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(text)
        hh = fm.height() + 10 * sc
        ww = tw + 28 * sc
        r = QRectF(x - ww / 2, y - hh / 2, ww, hh)
        p.setOpacity(min(1.0, alpha))
        if hot_k > 0:                                    # подсвеченное умение светится цветом Mico
            glow = QColor(c["accent"])
            glow.setAlpha(int(90 * hot_k))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(r.adjusted(-6, -6, 6, 6), hh / 2 + 6, hh / 2 + 6)
        edge = QColor(c["accent"]) if hot_k > .1 else QColor(c["stroke"])
        p.setPen(QPen(edge, 1.6 if hot_k > .1 else 1.0))
        p.setBrush(QColor(c["card"]))
        p.drawRoundedRect(r, hh / 2, hh / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["accent"]))
        p.drawEllipse(QPointF(r.left() + 12 * sc, y), 3.2 * sc, 3.2 * sc)
        p.setPen(QColor(c["text"]))
        p.drawText(QRectF(r.left() + 19 * sc, r.top(), tw + 6, hh),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        p.setOpacity(1.0)

    def paintEvent(self, e):
        dark = theme.system_dark()
        c = _palette(dark)
        t = self._now()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h * .5
        iu = min(1.0, t / 1.5)                           # вступление: 0..1
        ib = _back_out(iu)
        fade = (1 - .8 * self._leave) * min(1.0, iu * 2.2)
        p.fillRect(self.rect(), QColor(c["bg"]))
        for i, col in enumerate((c["accent"],) + self.GLOWS):   # сияние: четыре мягких пятна медленно плывут
            ph = i * 1.7
            g = QRadialGradient(QPointF(w * (.5 + .34 * math.sin(t * .21 + ph)), h * (.5 + .3 * math.cos(t * .27 + ph * 1.3))),
                                max(w, h) * .5)
            c0, c1 = QColor(col), QColor(col)
            c0.setAlpha(int((60 if dark else 84) * fade))
            c1.setAlpha(0)
            g.setColorAt(0, c0)
            g.setColorAt(1, c1)
            p.fillRect(self.rect(), QBrush(g))
        bg = QColor(c["bg"])
        clear = QColor(bg)
        clear.setAlpha(0)
        lg = QLinearGradient(0, h * .55, 0, h)            # низ сцены уходит в фон страницы без шва
        lg.setColorAt(0, clear)
        lg.setColorAt(1, bg)
        p.fillRect(self.rect(), QBrush(lg))
        for m in self._motes:                            # пылинки света
            tw = .5 + .5 * math.sin(t * 1.3 + m[4])
            mc = QColor(c["accent"])
            mc.setAlpha(int((26 + 50 * tw) * fade))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(mc)
            p.drawEllipse(QPointF(m[0] * w, m[1] * h), m[3] * (.7 + .5 * tw), m[3] * (.7 + .5 * tw))
        s = (1 - .4 * self._compact) * (.22 + .78 * ib) * (1 + .07 * self._pulse)
        ease = _ease_out(iu)
        rx = w * .41 * (1 + 1.5 * self._leave) * (.3 + .7 * ease)
        ry = h * .3 * (1 + 1.2 * self._leave) * (.3 + .7 * ease)
        for t0 in self._rings:                           # ударные волны от Mico
            age = (t - t0) / 1.2
            if 0 <= age <= 1:
                rc = QColor(c["accent"])
                rc.setAlpha(int(120 * (1 - age) * (1 - .6 * self._compact)))
                p.setPen(QPen(rc, 1.5 + 4 * (1 - age)))
                p.setBrush(Qt.BrushStyle.NoBrush)
                rr_ = _ease_out(age) * max(w, h) * .55
                p.drawEllipse(QPointF(cx, cy), rr_, rr_ * .62)
        orbit = QColor(c["accent"])
        orbit.setAlpha(int(70 * fade * (1 - self._compact)))
        pen = QPen(orbit, 1.2)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), rx, ry)
        n = len(self._chips)
        chips = []
        for i, text in enumerate(self._chips):
            a = t * .16 + i * 2 * math.pi / n
            chips.append(((math.sin(a) + 1) / 2, i, text, cx + math.cos(a) * rx, cy + math.sin(a) * ry))
        chips.sort()
        hot = max(0.0, 1 - (t - self._hot_t) / 3.8)
        for depth, i, text, x, y in chips:              # дальние умения — за Mico
            if depth < .5:
                self._chip(p, c, text, x, y, depth, hot if i == self._hot else 0.0, fade)
        if self._stream:                                 # поток частиц к Mico (или от него при удалении)
            p.setPen(Qt.PenStyle.NoPen)
            for ang, _sp, u, sz, ci in self._stream:
                k = u * u if not self.leaving else 1 - (1 - u) * (1 - u)
                R0 = max(w, h) * .52
                ex, ey = cx + math.cos(ang) * R0, cy + math.sin(ang) * R0 * .55
                if self.leaving:
                    px_, py_ = cx + (ex - cx) * k, cy + (ey - cy) * k
                else:
                    px_, py_ = ex + (cx - ex) * k, ey + (cy - ey) * k
                col = QColor(self.GLOWS[ci - 1] if ci else c["accent"])
                col.setAlpha(int(200 * (1 - u * .6)))
                p.setBrush(col)
                p.drawEllipse(QPointF(px_, py_), sz, sz)
                tail = QColor(col)
                tail.setAlpha(int(70 * (1 - u)))
                p.setBrush(tail)
                tk = max(0.0, (u - .05)) ** 2 if not self.leaving else 1 - (1 - max(0.0, u - .05)) ** 2
                tx_ = (ex + (cx - ex) * tk) if not self.leaving else (cx + (ex - cx) * tk)
                ty_ = (ey + (cy - ey) * tk) if not self.leaving else (cy + (ey - cy) * tk)
                p.drawEllipse(QPointF(tx_, ty_), sz * .6, sz * .6)
        jt = t - self._jump_t
        jy = -30 * s * math.sin(math.pi * jt / .6) if 0 <= jt <= .6 else 0.0
        my = cy + jy + 4 * math.sin(t * 1.6)
        pix = self.avatar.pixmap()
        if pix is not None and not pix.isNull():
            k = self.MICO_PX * s / max(1, max(pix.width(), pix.height()))
            pw, ph = pix.width() * k, pix.height() * k
            shadow = QColor(0, 0, 0, int(40 if dark else 26))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(shadow)
            p.drawEllipse(QPointF(cx, cy + ph * .42), pw * .3 * (1 + jy / 120), ph * .05)
            p.drawPixmap(QRectF(cx - pw / 2, my - ph / 2, pw, ph), pix, QRectF(pix.rect()))
        if self._prog is not None:                       # кольцо прогресса вокруг Mico
            R = self.MICO_PX * s * .58
            ring = QRectF(cx - R, cy - R, 2 * R, 2 * R)
            base = QPen(QColor(c["bar"]), 4)
            base.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(base)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ring)
            arc = QPen(QColor(c["accent"]), 5)
            arc.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc)
            p.drawArc(ring, 90 * 16, -int(self._shown * 360 * 16))
            a = math.radians(90 - self._shown * 360)
            ex, ey = cx + R * math.cos(a), cy - R * math.sin(a)
            g = QRadialGradient(QPointF(ex, ey), 14)
            g0, g1 = QColor(c["accent"]), QColor(c["accent"])
            g1.setAlpha(0)
            g.setColorAt(0, g0)
            g.setColorAt(1, g1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(g))
            p.drawEllipse(QPointF(ex, ey), 14, 14)
        for depth, i, text, x, y in chips:              # ближние — перед ним
            if depth >= .5:
                self._chip(p, c, text, x, y, depth, hot if i == self._hot else 0.0, fade)
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, _vx, _vy, rot, _vr, life, col, size in self._sparks:
            p.save()
            p.translate(x, y)
            p.rotate(rot)
            p.setOpacity(max(0.0, min(1.0, life)))
            p.setBrush(col)
            p.drawRoundedRect(QRectF(-size / 2, -size / 4, size, size / 2), 1.5, 1.5)
            p.restore()
        p.end()


class Wizard(_SlideMixin, QDialog):
    PAGE_MOOD = {0: "happy", 1: "curious", 2: "thinking", 3: "love"}

    def __init__(self):
        super().__init__()
        self.lang_request = None                 # код языка, если человек сменил его на первом экране
        self.setObjectName("wizard")
        self.setWindowTitle(i18n.t("Установка Mico AI"))
        self.setFixedSize(620, 660)              # вертикальная карточка: живая сцена с Mico сверху, страница под ней
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(_asset("mico.ico") or ""))
        self.setStyleSheet(qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QVBoxLayout()                              # Mico сверху по центру, под ним страница — без боковой панели
        body.setContentsMargins(56, 0, 56, 16)
        body.setSpacing(0)
        self.avatar = MicoAvatar(self.PAGE_MOOD[0], _mico_color(), size=ShowStage.MICO_PX)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.hide()                               # кадры Mico рисует живая сцена
        self.stage = ShowStage(self.avatar)
        root.addWidget(self.stage)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(brand)
        body.addSpacing(16)
        self.pages = QStackedWidget()
        for page in (self._page_welcome(), self._page_options(), self._page_install(), self._page_finish()):
            self.pages.addWidget(page)
        body.addWidget(self.pages, 1)
        root.addLayout(body, 1)
        line = QFrame()
        line.setObjectName("footLine")
        line.setFixedHeight(1)
        root.addWidget(line)
        foot = QFrame()                                   # подвал: шаги слева, кнопки справа
        foot.setObjectName("foot")
        row = QHBoxLayout(foot)
        row.setContentsMargins(24, 14, 24, 14)
        row.setSpacing(8)
        self.step_lbl = StepDots(4)                      # точки шагов: 4 экрана
        row.addWidget(self.step_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()
        self.cancel_b = QPushButton(i18n.t("Отмена"))
        self.back_b = QPushButton(i18n.t("Назад"))
        self.next_b = QPushButton(i18n.t("Далее"))
        self.next_b.setObjectName("primary")
        for b_ in (self.cancel_b, self.back_b, self.next_b):
            b_.setCursor(Qt.CursorShape.PointingHandCursor)
            b_.setMinimumWidth(96)
        self.cancel_b.clicked.connect(self.reject)
        self.back_b.clicked.connect(lambda: self._go(self.pages.currentIndex() - 1))
        self.next_b.clicked.connect(self._next)
        row.addWidget(self.cancel_b)
        row.addWidget(self.back_b)
        row.addWidget(self.next_b)
        root.addWidget(foot)
        self._go(0)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_mica_done", False):
            self._mica_done = True
            pass                                         # сплошной фон в цвет чата: Mica делала окно неровным на разных обоях
            from ui import motion
            motion.window_fade_in(self, 420)             # окно проявляется, а не выскакивает
            self.stage.replay_intro()                    # Mico влетает, сияние и умения разлетаются по орбите

    # ---------- страницы ----------
    def _title(self, text):
        t = QLabel(i18n.t(text))
        t.setObjectName("title")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return t

    def _sub(self, text):
        s = QLabel(i18n.t(text))
        s.setObjectName("sub")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return s

    def _page_welcome(self):
        return column(self._title("Установка Mico AI"),
                      10,
                      self._sub("Компаньон на рабочем столе. Понимает текст, управляет Windows "
                                "и отвечает на вопросы. Всё работает на твоём ПК."),
                      10,
                      self._sub("Займёт около минуты."),
                      22,
                      self._lang_row())

    def _lang_row(self):
        """Язык определён по системе; здесь его можно сменить. Выбранный подсвечен."""
        row = QWidget()
        outer = QHBoxLayout(row)
        outer.setContentsMargins(0, 0, 0, 0)
        seg = QFrame()
        seg.setObjectName("seg")
        h = QHBoxLayout(seg)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(2)
        for code, label in (("ru", "Русский"), ("en", "English")):
            b = QPushButton(label)
            b.setObjectName("segBtn")
            b.setCheckable(True)
            if code == i18n.LANG:
                b.setChecked(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: self._switch_language(c))
            h.addWidget(b)
        outer.addStretch(1)
        outer.addWidget(seg)
        outer.addStretch(1)
        return row

    def _switch_language(self, code):
        """Смена языка на первом экране: мастер закрывается и открывается заново на новом языке."""
        if code == i18n.LANG:
            return
        self.lang_request = code
        self.done(2)

    def _page_options(self):
        self.opt_auto = WrapCheck(i18n.t("Запускать вместе с Windows"))
        self.opt_auto.setChecked(True)
        self.opt_short = WrapCheck(i18n.t("Ярлык на рабочем столе"))
        self.opt_short.setChecked(True)
        self.model_entry = _builtin_entry()
        self.opt_model = None
        # Выбор «на ПК или в облаке» убран отсюда: он стал красивым шагом первой настройки при первом запуске Mico AI.
        return column(self._title("Параметры"), 4, self._sub("Это можно поменять потом в настройках."), 14,
                      card(self.opt_auto, self.opt_short))

    def _page_install(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = GlowBar()
        self.bar.setRange(0, 100)
        self.status = QLabel(i18n.t("Готовлюсь…"))
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        self.dl = QLabel("")                                   # счётчик скачивания модели: всегда виден, пока качается
        self.dl.setObjectName("sub")
        self.dl.setWordWrap(True)
        self.dl.setVisible(False)
        self.talk = QLabel("")                                 # Mico рассказывает о себе
        self.talk.setObjectName("fact")
        self.talk.setWordWrap(True)
        self.talk.setMinimumHeight(56)
        self._type_timer = QTimer(self)                        # факт печатается, а не появляется целиком
        self._type_timer.setInterval(18)
        self._type_timer.timeout.connect(self._type_step)
        self._talk_full, self._talk_n = "", 0
        self._talk_order = list(range(len(FACTS)))
        random.shuffle(self._talk_order)                       # каждый раз в другом порядке
        self._talk_i = 0
        self._talk_timer = QTimer(self)
        self._talk_timer.setInterval(FACT_MS)
        self._talk_timer.timeout.connect(self._say_next)
        for w in (self.percent, self.dl, self.status, self.talk):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return column(self._title("Устанавливаю"), 14, self.percent, 10, self.bar, 8, self.dl, 12, self.status, 8, self.talk)

    def _say_next(self):
        """Следующий факт о Mico AI: текст и лицо меняются вместе."""
        index = self._talk_order[self._talk_i % len(FACTS)]
        text, mood = FACTS[index]
        self._talk_i += 1
        self._talk_full, self._talk_n = i18n.t(text), 0
        self._type_timer.start()
        self.avatar.set_mood(mood)
        if index in FACT_SHOW:                                 # Mico показывает умение, о котором говорит
            self.stage.highlight(FACT_SHOW[index])
            self.stage.jump()

    def _type_step(self):
        self._talk_n = min(len(self._talk_full), self._talk_n + 2)
        self.talk.setText(self._talk_full[:self._talk_n])
        if self._talk_n >= len(self._talk_full):
            self._type_timer.stop()

    def _page_finish(self):
        self.run_cb = WrapCheck(i18n.t("Запустить Mico AI"))
        self.run_cb.setChecked(True)
        return column(self._title("Готово"), 6,
                      self._sub("Mico AI установлен и готов к работе."), 20,
                      card(self.run_cb))

    # ---------- переходы ----------
    def _go(self, i):
        self._grab_old()
        self.pages.setCurrentIndex(i)
        self.step_lbl.set_current(i)
        self.back_b.setVisible(i == 1)
        self.next_b.setText({0: i18n.t("Далее"), 1: i18n.t("Установить"), 2: "…", 3: i18n.t("Закрыть")}[i])
        self.stage.set_compact(i == 1)                   # на «Параметрах» место нужно настройкам: сцена ниже
        self.stage.jump()                                # Mico подпрыгивает на каждом новом экране
        if i == 3:
            self.stage.set_progress(None)
            self.stage.burst()                           # установка закончилась — салют
            QTimer.singleShot(380, lambda: self.stage.burst(60))
            QTimer.singleShot(820, lambda: self.stage.burst(50))
        self.next_b.setEnabled(i != 2)
        self.cancel_b.setVisible(i != 3)
        self.avatar.set_mood(self.PAGE_MOOD[i])

    def _next(self):
        i = self.pages.currentIndex()
        if i == 0:
            self._go(1)
            self._fade_pages()
        elif i == 1:
            self._api_provider_value = "mico"                   # где отвечать, решается при первом запуске, в знакомстве; по умолчанию облако Mico
            self._go(2)
            self._fade_pages()
            self._start_install()
        elif i == 3:
            if self.run_cb.isChecked() and os.path.exists(INSTALL_EXE):
                os.startfile(INSTALL_EXE)
            self.accept()

    # ---------- установка ----------
    def _start_install(self):
        self._worker = _Worker(self)
        self._worker.progress.connect(self._on_progress)
        self._worker.download.connect(self._on_download)
        self._worker.done.connect(self._on_done)
        self._worker.start()
        self.stage.set_progress(0)
        self._say_next()                                       # первый факт сразу, потом — по таймеру
        self._talk_timer.start()

    def _animate_to(self, target, ms, after=None):
        """Полоска и проценты плавно едут к target. Новый вызов отменяет предыдущий ход."""
        if getattr(self, "_bar_anim", None) is not None:
            self._bar_anim.stop()
        anim = QVariantAnimation(self)
        anim.setStartValue(self.bar.value())
        anim.setEndValue(int(target))
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def show(v):
            n = int(round(float(v)))
            self.bar.setValue(n)
            self.percent.setText(f"{n}%")
            if self.pages.currentIndex() == 1 + isinstance(self, Wizard):   # страница прогресса: кольцо вокруг Mico
                self.stage.set_progress(n / 100)
        anim.valueChanged.connect(show)
        if after is not None:
            anim.finished.connect(after)
        self._bar_anim = anim
        anim.start()

    def _on_download(self, done_mb, total_mb):
        self.dl.setText(i18n.t("Скачано {done} из {total} МБ").format(done=done_mb, total=total_mb))
        self.dl.setVisible(True)

    def _on_progress(self, pct, text, mood):
        self.status.setText(text)
        if mood:                                         # пустое настроение — лицо ведут факты, не полоска
            self.avatar.set_mood(mood)
        self._animate_to(pct, 620)

    def _on_done(self, err):
        self._talk_timer.stop()
        if err:
            self.status.setText(i18n.t("Не получилось: {err}. Если Mico AI открыт, закрой его и запусти установку снова.").format(err=err))
            self.next_b.setEnabled(True)
            self.next_b.setText(i18n.t("Закрыть"))
            self.next_b.clicked.disconnect()
            self.next_b.clicked.connect(self.reject)
            return
        def finish():                                    # полоска дошла до 100% — даём её увидеть и переходим
            QTimer.singleShot(260, lambda: (self._go(3), self._fade_pages()))
        self.status.setText(i18n.t("Готово"))
        self._animate_to(100, 520, after=finish)


def _install_steps(wizard, report):
    """Все шаги установки. report(i, пояснение) сообщает о прогрессе."""
    from setup import autostart
    os.makedirs(INSTALL_DIR, exist_ok=True)
    report(0)
    shutil.copy2(sys.executable, INSTALL_EXE)
    _clear_compatibility_elevation()           # Run не способен открыть программу, помеченную RUNASADMIN
    _write_legacy_remover()                    # старые записи Windows тоже должны открыть новый мастер
    icon = _asset("mico.ico")
    if icon:
        shutil.copy2(icon, ICON_PATH)            # значок для ярлыка и списка приложений
    report(1)
    if wizard.opt_short.isChecked():
        _desktop_shortcut(create=True)
    try:
        _start_menu_shortcut(create=True)        # в списке приложений «Пуск», откуда Mico можно удалить
    except Exception:
        pass
    report(2)
    auto_on = False
    if wizard.opt_auto.isChecked():
        auto_on, msg = autostart.install(exe=INSTALL_EXE)
        if not auto_on:
            report(2, i18n.t("не получилось, включи позже в настройках"))
    report(3)
    _register_uninstall()
    report(4)
    use_api = getattr(wizard, "_api_provider_value", "mico") in ("mico", "groq")        # облако: тяжёлую модель на ПК не качаем
    entry = getattr(wizard, "model_entry", None) if not use_api else None
    _save_settings(auto_on, model_entry=entry, api_provider=getattr(wizard, "_api_provider_value", "mico"),
                   cloud_model=getattr(wizard, "_api_model_value", None))
    if not use_api and entry is not None and getattr(wizard, "opt_model", None) is not None and wizard.opt_model.isChecked():
        report(5, i18n.t("скачиваю {title}").format(title=entry["title"]))
        worker = getattr(wizard, "_worker", None)
        def make_show(lo, hi, title):
            """Полоска идёт от lo% до hi% вместе со скачиванием одной модели (с проектором, если он есть)."""
            last = {"mb": -1, "t": 0.0}

            def show(done, total):
                if worker is None or not total:
                    return
                # строка с мегабайтами обновляется по мере скачивания (раз в полсекунды или на каждый новый МБ),
                # а не только когда сдвинулся общий процент — иначе на медленной сети она кажется замершей
                mb = done // 1024 ** 2
                now = time.monotonic()
                if mb == last["mb"] and now - last["t"] < 0.5:
                    return
                last["mb"], last["t"] = mb, now
                pct = int(lo + (hi - lo) * min(done, total) / total)
                text = i18n.t("Готовлю ответы Mico AI — скачиваю {title}").format(title=title)
                worker.progress.emit(min(pct, 99), text, "")      # "" — лицо не меняем: его ведут факты о Mico
                worker.download.emit(mb, total // 1024 ** 2)
            return show
        # Короткие таймауты: если сервер не отвечает, установка не виснет, а идёт дальше.
        got = _download_model(entry, make_show(83, 92, entry["title"]), retries=2, timeout=15)
        if not got and worker is not None:
            worker.progress.emit(83, i18n.t("Модель не скачалась сейчас, скачаю позже в настройках"), "worried")
    else:
        report(5)


def _builtin_entry():
    """Модель под память этого ПК для встроенного движка (без Ollama). None — движок не установлен."""
    try:
        from llm import engine as local_llm
        from llm import catalog as model_catalog
        if not local_llm.available():
            return None
        import psutil
        return model_catalog.recommend(psutil.virtual_memory().total / (1024 ** 3))
    except Exception:
        return None


def _download_model(entry, show=None, retries=3, timeout=30):
    """Скачивает модель из каталога. True — файл на месте. Ошибка сети не валит установку.
    show(скачано_байт, всего_байт) — вызывается с прогрессом, чтобы окно не висело молча."""
    try:
        from llm import store as model_store
        return model_store.download(entry["id"], progress=show, retries=retries, timeout=timeout)
    except Exception:
        return False


class _Worker(QThread):
    """Установка в фоне, чтобы окно не зависало."""
    progress = pyqtSignal(int, str, str)
    download = pyqtSignal(int, int)                      # скачано МБ, всего МБ — для счётчика на экране
    done = pyqtSignal(str)

    def __init__(self, wizard):
        super().__init__(wizard)
        self.wizard = wizard

    def run(self):
        def report(i, extra=""):
            if i:
                time.sleep(0.45)                         # шаги идут не мгновенно: прогресс успевает быть видным
            text, mood = STEPS[i]
            self.progress.emit(int(i / len(STEPS) * 100),
                               i18n.t(text) + (f" — {extra}" if extra else ""), mood)
        try:
            _install_steps(self.wizard, report)
            self.done.emit("")
        except Exception as e:
            self.done.emit(f"{e.__class__.__name__}: {e}")


def _shortcut(folder, create):
    """Ярлык Mico AI. folder='Desktop' — на рабочем столе; 'Programs' — в меню «Пуск → Все приложения»."""
    from win import system as winctl
    path = f"[Environment]::GetFolderPath('{folder}')+'\\Mico.lnk'"
    if create:
        icon_ps = f"$s.IconLocation='{ICON_PATH}';" if os.path.exists(ICON_PATH) else ""
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({path});"
              f"$s.TargetPath='{INSTALL_EXE}';$s.WorkingDirectory='{INSTALL_DIR}';{icon_ps}$s.Save()")
    else:
        ps = f"Remove-Item -ErrorAction SilentlyContinue -Path ({path})"
    winctl.ps(ps, timeout=30)


def _desktop_shortcut(create):
    _shortcut("Desktop", create)


def _start_menu_shortcut(create):
    """Без этого ярлыка Mico AI не видно в «Пуск → Все приложения», а удалить его оттуда нельзя."""
    _shortcut("Programs", create)


REMOVER_PATH = os.path.join(INSTALL_DIR, "remove_mico.cmd")
COMPATIBILITY_KEY = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"


def _clear_compatibility_elevation():
    """Убирает только флаг «запускать от имени администратора» для Mico.exe.
    Такой флаг (RUNASADMIN) может сохраниться от старой версии или быть включён Windows вручную.
    Из-за него Explorer не имеет права запускать программу из HKCU\\Run и выдаёт CreateProcessW 740."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, COMPATIBILITY_KEY, 0,
                             winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE)
        value, kind = winreg.QueryValueEx(key, INSTALL_EXE)
        if kind != winreg.REG_SZ or not isinstance(value, str):
            winreg.CloseKey(key)
            return
        kept = [part for part in value.split() if part.upper() != "RUNASADMIN"]
        if len(kept) == len(value.split()):
            winreg.CloseKey(key)
            return
        if not kept or kept == ["~"]:
            winreg.DeleteValue(key, INSTALL_EXE)
        else:
            winreg.SetValueEx(key, INSTALL_EXE, 0, winreg.REG_SZ, " ".join(kept))
        winreg.CloseKey(key)
    except (ImportError, OSError):
        pass


def _write_legacy_remover():
    """Совместимость со старыми записями Windows, где удаление вело на remove_mico.cmd.
    Скрипт лишь открывает актуальный мастер, поэтому не держит файлы установки занятыми."""
    lines = [
        "@echo off",
        f'start "" "{INSTALL_EXE}" --uninstall',
        "exit /b",
    ]
    try:
        with open(REMOVER_PATH, "w", encoding="ascii", errors="replace") as f:
            f.write("\r\n".join(lines) + "\r\n")
    except OSError:
        pass


def _register_uninstall():
    """Регистрирует Mico AI в «Параметры → Приложения», чтобы его можно было удалить штатным способом."""
    import winreg
    uninstall_cmd = f'"{INSTALL_EXE}" --uninstall'          # удаление через наш мастер, а не консольный скрипт
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE)
    values = {"DisplayName": "Mico AI", "DisplayVersion": _user_version(), "Publisher": "Mico AI",
              "InstallLocation": INSTALL_DIR,
              "DisplayIcon": ICON_PATH if os.path.exists(ICON_PATH) else INSTALL_EXE,
              "UninstallString": uninstall_cmd}
    for name, value in values.items():
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(k)


def refresh_icon(color):
    """Значок установленной программы (список приложений Windows, ярлыки) — настоящий Mico, а не старая картинка из
    установщика. Файл mico.ico перерисовывается с живого Mico при запуске, если цвет или версия значка поменялись."""
    if not FROZEN or os.path.normcase(sys.executable) != os.path.normcase(INSTALL_EXE):
        return
    try:
        from ui import appicon
        stamp = "v2:" + str(color).lower()
        marker = os.path.join(INSTALL_DIR, "icon.version")
        try:
            with open(marker, encoding="utf-8") as f:
                if f.read().strip() == stamp and os.path.exists(ICON_PATH):
                    return
        except OSError:
            pass
        pm = appicon.blob_pixmap(256, color)
        if pm is None:
            return
        tmp = ICON_PATH + ".new"
        if not pm.save(tmp, "ICO"):
            return
        os.replace(tmp, ICON_PATH)
        with open(marker, "w", encoding="utf-8") as f:
            f.write(stamp)
        _register_uninstall()                    # DisplayIcon в «Приложениях» смотрит на этот файл
        try:                                     # просим Проводник забыть старый значок
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except Exception:
            pass
    except Exception:
        pass


def refresh_uninstall_entry():
    """При запуске установленной копии обновляет регистрацию удаления и снимает устаревший RUNASADMIN.
    Совместимый remove_mico.cmd остаётся для старых ссылок Windows, но открывает актуальный мастер."""
    if not FROZEN or os.path.normcase(sys.executable) != os.path.normcase(INSTALL_EXE):
        return
    _clear_compatibility_elevation()             # ручной запуск сам чинит следующий вход в Windows
    import winreg
    expected = f'"{INSTALL_EXE}" --uninstall'
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_READ)
        current, _ = winreg.QueryValueEx(k, "UninstallString")
        winreg.CloseKey(k)
    except OSError:
        current = None
    if current != expected:
        _register_uninstall()
    lnk = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Microsoft", "Windows",
                       "Start Menu", "Programs", "Mico.lnk")
    if not os.path.exists(lnk):                 # установки до этого обновления не имели ярлыка в «Пуск»
        try:
            _start_menu_shortcut(create=True)
        except Exception:
            pass
    _write_legacy_remover()       # старый UninstallString с remove_mico.cmd остаётся рабочим после обновления


def _unregister_uninstall():
    import winreg
    try:
        _start_menu_shortcut(create=False)       # пункт в «Пуск → Все приложения» не должен остаться после удаления
    except Exception:
        pass
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass


def _save_settings(autostart_on, model_entry=None, api_provider="mico", cloud_model=None):
    """Минимальные настройки для первого запуска. Остальное — значения по умолчанию в программе."""
    os.makedirs(APPDIR, exist_ok=True)
    path = os.path.join(APPDIR, "config.json")
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    from setup import version
    cfg.update(autostart=autostart_on, greet_on_start=True, update_channel=version.BUILD_CHANNEL,
               language=i18n.LANG)                # язык, выбранный в мастере, становится языком программы
    cfg["llm_backend"] = "local" if api_provider == "local" else "mico"
    if cloud_model:
        cfg["cloud_model"] = cloud_model
    if model_entry is not None:
        cfg.update(text_model=model_entry["id"])
    cfg.setdefault("last_version", _version())            # не показывать «что нового» сразу после установки
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _version():
    from setup import version
    return version.APP_VERSION           # внутренний номер: сравнивается с last_version


def _user_version():
    from setup import version
    return version.user_version()        # то, что видит человек (реестр, «Установка программ»)


# ============================ Мастер установки ============================
def _system_language():
    """Язык по системе: русская Windows — русский, остальные — английский."""
    from PyQt6.QtCore import QLocale
    return "ru" if QLocale.system().name().lower().startswith("ru") else "en"


def run():
    """Мастер установки. Язык — по системе; сменить его можно на первом экране, мастер тогда откроется заново
    на новом языке (до первого шага ничего не выбрано, терять нечего). Установленная копия запускается сама."""
    code = _system_language()
    while True:
        i18n.set_language(code)
        dlg = Wizard()
        dlg.exec()
        if dlg.lang_request is None:
            break
        code = dlg.lang_request


# ============================ Удаление ============================
def is_uninstall_request():
    return "--uninstall" in sys.argv


_NOWIN = 0x08000000 if os.name == "nt" else 0        # не показывать окно консоли (только Windows)
_DETACHED = 0x00000008 if os.name == "nt" else 0


def _dir_size_mb(path):
    total = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                total += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return total // (1024 * 1024)


class _Remover(QThread):
    """Шаги удаления, которые можно сделать, пока Mico AI работает. Файлы программы и данных удаляет отдельный скрипт после выхода."""
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str)

    def __init__(self, choices):
        super().__init__()
        self.choices = choices
        self.errors = []          # понятные сообщения о том, что не удалось
        self.failed = set()       # ключи шагов, которые не выполнились: такие не попадают в «удалено»

    def _steps(self):
        steps = []
        if self.choices.get("autostart"):
            steps.append(("autostart", "Снимаю автозапуск", self._autostart))
        if self.choices.get("shortcut"):
            steps.append(("shortcut", "Удаляю ярлык на рабочем столе", self._shortcut))
        steps.append(("program", "Убираю запись из «Приложений» Windows", _unregister_uninstall))
        return steps

    def _autostart(self):
        from setup import autostart
        autostart.remove()

    def _shortcut(self):
        _desktop_shortcut(create=False)


    def run(self):
        steps = self._steps()
        try:
            for i, (key, text, fn) in enumerate(steps):
                if i:
                    time.sleep(0.45)                     # шаги видны, а не мелькают
                self.progress.emit(int(i / len(steps) * 100), i18n.t(text))
                try:
                    fn()
                except Exception as e:
                    self.failed.add(key)
                    self.errors.append(f"{i18n.t(text)} ({e})")
            self.progress.emit(100, i18n.t("Почти готово"))
            self.done.emit("")
        except Exception as e:
            self.done.emit(f"{e.__class__.__name__}: {e}")


class Uninstaller(_SlideMixin, QDialog):
    """Мастер удаления в стиле установщика: сначала выбор, что удалить, потом плавный прогресс и итог."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.removed = False
        self.worker = None
        self.setObjectName("wizard")
        self.setWindowTitle(i18n.t("Удаление Mico AI"))
        self.setFixedSize(620, 660)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(qss())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QVBoxLayout()                              # тот же каркас, что у установки
        body.setContentsMargins(56, 0, 56, 16)
        body.setSpacing(0)
        self.avatar = MicoAvatar("worried", _mico_color(), size=ShowStage.MICO_PX)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.hide()                               # кадры Mico рисует живая сцена
        self.stage = ShowStage(self.avatar, leaving=True)
        root.addWidget(self.stage)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.addWidget(brand)
        body.addSpacing(16)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._page_choose())
        self.pages.addWidget(self._page_progress())
        self.pages.addWidget(self._page_done())
        body.addWidget(self.pages, 1)
        root.addLayout(body, 1)
        line = QFrame()
        line.setObjectName("footLine")
        line.setFixedHeight(1)
        root.addWidget(line)
        foot = QFrame()
        foot.setObjectName("foot")
        row = QHBoxLayout(foot)
        row.setContentsMargins(24, 14, 24, 14)
        row.setSpacing(8)
        self.step_lbl = StepDots(3)                      # точки шагов: выбор, прогресс, итог
        row.addWidget(self.step_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addStretch()
        self.cancel_b = QPushButton(i18n.t("Отмена"))
        self.cancel_b.clicked.connect(self.reject)
        self.next_b = QPushButton(i18n.t("Удалить"))
        self.next_b.setObjectName("primary")
        self.next_b.clicked.connect(self._start)
        for b_ in (self.cancel_b, self.next_b):
            b_.setCursor(Qt.CursorShape.PointingHandCursor)
            b_.setMinimumWidth(96)
        row.addWidget(self.cancel_b)
        row.addWidget(self.next_b)
        self.btn_row_widget = row
        root.addWidget(foot)
        self._go(0)

    # ---------- страницы ----------
    def _choice(self, key, title, hint, checked):
        box = WrapCheck(i18n.t(title))
        box.setChecked(checked)
        self.choices[key] = box
        hint_lbl = QLabel(i18n.t(hint))
        hint_lbl.setObjectName("sub")
        hint_lbl.setWordWrap(True)
        hint_lbl.setContentsMargins(0, 2, 52, 0)    # подсказка под подписью, не заезжает под переключатель
        hint_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        block = QWidget()
        lay = QVBoxLayout(block)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(box)
        lay.addWidget(hint_lbl)
        return block

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_mica_done", False):
            self._mica_done = True
            pass                                         # сплошной фон в цвет чата: Mica делала окно неровным на разных обоях
            from ui import motion
            motion.window_fade_in(self, 420)
            self.stage.replay_intro()

    def _page_choose(self):
        self.choices = {}
        items = [self._title("Удалить Mico AI?"), 6,
                 self._sub("Программу удалим в любом случае. Остальное выбираешь сам."), 14]
        blocks = []
        blocks.append(self._choice("shortcut", "Ярлык на рабочем столе",
                                  "Запись в «Приложениях» Windows удалится в любом случае.", True))
        blocks.append(self._choice("autostart", "Автозапуск с Windows",
                                  "Mico AI перестанет запускаться при входе в систему.", True))
        blocks.append(self._choice("data", "История, настройки и напоминания",
                                  "Чат, память и напоминания. Оставь, если переустановишь Mico AI с прежними данными.",
                                  False))
        items.append(card(*blocks))                   # пункты — в одной карточке с тонкими линиями
        size = _dir_size_mb(INSTALL_DIR) if os.path.isdir(INSTALL_DIR) else 0
        size_lbl = self._sub("Программа Mico AI · {size} МБ")
        size_lbl.setText(size_lbl.text().format(size=size))
        items += [14, size_lbl]
        return column(*items)

    def _page_progress(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = GlowBar()
        self.bar.setRange(0, 100)
        self.status = QLabel(i18n.t("Готовлюсь…"))
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        for w in (self.percent, self.status):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return column(self._title("Удаляю"), 14, self.percent, 10, self.bar, 12, self.status)

    def _page_done(self):
        self.done_text = QLabel("")
        self.done_text.setObjectName("sub")
        self.done_text.setWordWrap(True)
        self.done_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return column(self._title("Mico AI удалён"), 10, self.done_text)

    def _title(self, text):
        t = QLabel(i18n.t(text))
        t.setObjectName("title")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return t

    def _sub(self, text):
        s = QLabel(i18n.t(text))
        s.setObjectName("sub")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return s

    # ---------- переходы ----------
    def _go(self, i):
        self._grab_old()
        self.pages.setCurrentIndex(i)
        self.step_lbl.set_current(i)
        self.cancel_b.setVisible(i == 0)
        self.next_b.setVisible(i != 2)
        self.next_b.setText({0: i18n.t("Удалить"), 1: "…"}[i] if i != 2 else "")
        self.next_b.setEnabled(i != 1)
        self.avatar.set_mood({0: "worried", 1: "sad", 2: "sad"}[i])     # при удалении Mico грустит

    def _animate_to(self, target, ms, after=None):
        if getattr(self, "_bar_anim", None) is not None:
            self._bar_anim.stop()
        anim = QVariantAnimation(self)
        anim.setStartValue(self.bar.value())
        anim.setEndValue(int(target))
        anim.setDuration(ms)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def show(v):
            n = int(round(float(v)))
            self.bar.setValue(n)
            self.percent.setText(f"{n}%")
            if self.pages.currentIndex() == 1 + isinstance(self, Wizard):   # страница прогресса: кольцо вокруг Mico
                self.stage.set_progress(n / 100)
        anim.valueChanged.connect(show)
        if after is not None:
            anim.finished.connect(after)
        self._bar_anim = anim
        anim.start()

    # ---------- удаление ----------
    def _start(self):
        picked = {k: box.isChecked() for k, box in self.choices.items()}
        self.picked = picked
        self._go(1)
        self._fade_pages()
        self.stage.set_progress(0)
        self.worker = _Remover(picked)
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct, text):
        self.status.setText(text)
        self.stage.set_leave(pct / 100)                   # умения Mico разлетаются по мере удаления
        self._animate_to(pct, 620)

    def _on_done(self, err):
        if err:
            self.status.setText(i18n.t("Не получилось: {err}").format(err=err))
            self.next_b.setEnabled(True)
            return

        def finish():
            QTimer.singleShot(260, self._finish_removal)
        self.status.setText(i18n.t("Готово"))
        self._animate_to(100, 520, after=finish)

    def _finish_removal(self):
        """Программу и данные удаляет скрипт: он ждёт, пока Mico AI закроется, и только потом трогает файлы."""
        picked = self.picked
        failed = self.worker.failed if self.worker else set()
        _schedule_file_removal(delete_data=picked.get("data", False))
        self.removed = True
        removed = ["программа Mico AI"]
        if picked.get("shortcut") and "shortcut" not in failed:
            removed.append("ярлык на рабочем столе")
        if "program" not in failed:
            removed.append("запись в «Приложениях» Windows")
        if picked.get("autostart") and "autostart" not in failed:
            removed.append("автозапуск")
        if picked.get("data"):
            removed.append("история и настройки")
        kept = []
        if not picked.get("data"):
            kept.append("история и настройки в папке Mico AI (AppData)")
        text = i18n.t("Удалено") + ": " + ", ".join(i18n.t(x) for x in removed) + "."
        if kept:
            text += "\n\n" + i18n.t("Осталось по твоему выбору") + ": " + ", ".join(i18n.t(x) for x in kept) + "."
        if self.worker and self.worker.errors:
            text += ("\n\n" + i18n.t("Не получилось") + ": " + "; ".join(self.worker.errors) + ". "
                     + i18n.t("Можно повторить позже."))
        self.done_text.setText(text)
        self.stage.set_progress(None)
        self.stage.set_leave(1.0)
        self._go(2)
        self._fade_pages()
        self.next_b.setText(i18n.t("Закрыть"))
        self.next_b.setVisible(True)
        self.next_b.setEnabled(True)
        self.next_b.clicked.disconnect()
        self.next_b.clicked.connect(self._close_app)

    def _close_app(self):
        self.accept()
        if self.app is not None:
            self.app.quit()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            event.ignore()                                  # во время удаления окно не закрыть: иначе шаги оборвутся
            return
        super().closeEvent(event)


def uninstall(app):
    """Мастер удаления: выбор, что удалить, плавный прогресс и итог. Возвращает True, если удаление выполнено."""
    if not FROZEN:
        QMessageBox.information(None, "Mico AI", i18n.t("Удаление доступно только для установленной версии Mico AI."))
        return False
    dlg = Uninstaller(app)                   # язык — тот же, что у программы: отдельного вопроса нет
    dlg.exec()
    return dlg.removed


def _schedule_file_removal(delete_data):
    """Скрипт в %TEMP%: ждёт выхода Mico AI, удаляет его папку и по выбору данные, затем удаляет себя."""
    script = os.path.join(os.environ.get("TEMP", "."), "mico_uninstall.cmd")
    lines = [
        "@echo off",
        f'taskkill /f /im Mico.exe /fi "PID ne {os.getpid()}" >nul 2>&1',   # другие запущенные копии Mico AI не дадут удалить файл
        ":wait",
        "ping 127.0.0.1 -n 2 >nul",
        f'del /f /q "{INSTALL_EXE}" 2>nul',
        f'if exist "{INSTALL_EXE}" goto wait',
        f'rmdir /s /q "{INSTALL_DIR}" 2>nul',
    ]
    if delete_data:
        lines.append(f'rmdir /s /q "{APPDIR}" 2>nul')
    lines.append('del /f /q "%~f0"')
    with open(script, "w", encoding="ascii", errors="replace") as f:
        f.write("\r\n".join(lines) + "\r\n")
    # Раньше здесь стояло «без окна» вместе с «отдельным процессом без консоли»: эти флаги спорят, и каждая команда
    # скрипта (ping в цикле ожидания, taskkill, del) открывала своё чёрное окно терминала: при удалении они мигали
    # десятки раз. Теперь у скрипта одна скрытая консоль, а все его команды работают внутри неё.
    kwargs = {}
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0                                  # SW_HIDE
        kwargs = {"startupinfo": si, "creationflags": _NOWIN | 0x00000200}     # CREATE_NO_WINDOW + своя группа процессов
    subprocess.Popen(["cmd", "/c", script], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, **kwargs)
