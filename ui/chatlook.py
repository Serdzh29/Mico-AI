"""Внешний вид текстового чата Mico AI: навигация, поиск, сообщения и композер.
Здесь только элементы интерфейса; историю и логику ответов ведут main.py и brain.py.
Голосовой режим этим модулем не затрагивается."""
import html
import re
import math
import time

from PyQt6.QtCore import QEasingCurve, QEvent, QObject, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal
from PyQt6.QtGui import (QColor, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                         QRadialGradient, QTextDocument)
from PyQt6.QtWidgets import (QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

import i18n
from ui import settingslook as settings_look
from ui import theme
from ui import icons as uiicons
from ui.shapes import thinking_dot_lift

PALETTE = {
    True: {"head": "#202020", "card": "#2B2B2B", "card2": "#2B2B2B", "user": "#2D2D2D", "mico": "#202020",
           "text": "#FFFFFF", "muted": "#A6A6A6", "stroke": "#3A3A3A", "hover": "#333333", "side": "#202020",
           "base": "#202020", "glow": "#202020"},
    False: {"head": "#F3F3F3", "card": "#FFFFFF", "card2": "#FFFFFF", "user": "#EBEBEB", "mico": "#FFFFFF",
            "text": "#1A1A1A", "muted": "#5D5D5D", "stroke": "#E5E5E5", "hover": "#F0F0F0", "side": "#F3F3F3",
            "base": "#F3F3F3", "glow": "#F3F3F3"},
}


def _rgba(hex_color, alpha):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def icon_ink(dark):
    """Один цвет для всех значков чата: поиск, скрепка, плюс, крестик, микрофон — чтобы не было разных."""
    return PALETTE[bool(dark)]["text"]


def _mix(a, b, k):
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(ca, cb))


def chat_font_family():
    """Шрифт чата: Montserrat, если он есть в системе или в assets/fonts; иначе Segoe UI Variable (есть в Windows 11)."""
    return _pick_family(["Segoe UI Variable Text", "Segoe UI"], "Segoe UI")     # системный шрифт Windows 11


def display_font_family():
    """Заголовки и «Mico AI»: тяжёлый геометрический шрифт, как у логотипа Copilot."""
    return _pick_family(["Segoe UI Variable Display", "Segoe UI Variable Text", "Segoe UI"], "Segoe UI")


def _pick_family(names, fallback):
    try:
        have = set(QFontDatabase.families())
    except Exception:
        return fallback
    for n in names:
        if n in have:
            return n
    return fallback


_QSS = """
QFrame#chatHeadBar { background: transparent; border: none; }
QLabel#msgText, QLabel#chatRowTitle, QLabel#chatRowTime, QLineEdit#chatInput, QLineEdit#chatSearch,
QListWidget#results, QLabel#chatMuted, QLabel#styleLabel { font-family: "@FAM@"; }
QLabel#chatHead { color: @TEXT@; font-family: "@DISP@"; font-size: 17px; font-weight: 600; background: transparent; }
QLabel#chatMuted { color: @MUTED@; font-size: 11px; background: transparent; }
QFrame#sidebar { background: @SIDE@; border: none; border-right: 1px solid @STROKE@;
    border-top-left-radius: 22px; border-bottom-left-radius: 22px; }
QFrame#card { background: qradialgradient(cx:0.5, cy:0, radius:1.1, fx:0.5, fy:0, stop:0 @GLOW@, stop:0.45 @HEAD@, stop:1 @BASE@);
    border: 1px solid @STROKE@; border-radius: 24px; }
QLabel#profileName { color: @TEXT@; font-size: 14px; font-weight: 700; background: transparent; }
QFrame#profileCard { background: transparent; border-radius: 14px; }
QFrame#profileCard:hover { background: @HOVER@; }
QLabel#planPill { background: @ACC_T@; color: @ACCENT@; border-radius: 8px; padding: 2px 8px; font-size: 10px; font-weight: 700; }
QListWidget#results { background: @CARD@; border: 1px solid @STROKE@; border-radius: 16px; padding: 6px; outline: 0; color: @TEXT@; }
QListWidget#results::item { padding: 9px 10px; margin: 2px 0; border-radius: 10px; }
QListWidget#results::item:hover { background: @HOVER@; }
QScrollArea#chatScroll, QScrollArea#msgScroll { background: transparent; border: none; }
QWidget#chatListBox, QWidget#msgHost { background: transparent; }
QLabel#chatRowTitle { color: @TEXT@; font-size: 13px; font-weight: 600; background: transparent; }
QLabel#chatRowTime { color: @MUTED@; font-size: 11px; background: transparent; }
QLineEdit#chatSearch { background: @HEAD@; border: 1px solid @STROKE@; border-radius: 16px; padding: 7px 12px;
    color: @TEXT@; selection-background-color: @ACCENT@; }
QLineEdit#chatSearch:focus { border: 1px solid @ACCENT@; }
QFrame#bubbleMico { background: transparent; border: none; }
QFrame#bubbleUser { background: @USER@; border: none; border-top-left-radius: 20px; border-top-right-radius: 20px;
    border-bottom-left-radius: 20px; border-bottom-right-radius: 6px; }
QLabel#msgText { color: @TEXT@; font-size: 13px; background: transparent; }
QFrame#inputBox { background: @CARD2@; border: 1px solid @STROKE@; border-bottom: 2px solid @ACCENT@; border-radius: 8px; padding: 0; }
QFrame#inputStrip { background: transparent; border: none; padding: 0; }
QFrame#inputBox:focus-within { border: 1px solid @ACCENT@; }
QLabel#wordCount { color: @MUTED@; font-size: 10px; background: transparent; padding: 0 2px 0 0; }
QLineEdit#chatInput { background: transparent; border: none; color: @TEXT@; padding: 6px 2px; font-size: 13px; }
QPushButton#send { background: @ACCENT@; border: none; border-radius: 14px; min-width: 28px; max-width: 28px;
    min-height: 28px; max-height: 28px; }
QPushButton#send:hover { background: @ACC_HOVER@; }
QPushButton#send:pressed { background: @ACC_PRESS@; }
QPushButton#gateBtn { background: @ACCENT@; color: #1a1a1a; border: none; border-radius: 21px; min-height: 42px; max-height: 42px;
    padding: 0 26px; font-size: 14px; font-weight: 600; }
QPushButton#gateBtn:hover { background: @ACC_HOVER@; }
QPushButton#gateBtn:pressed { background: @ACC_PRESS@; }
QLabel#gateText { color: @MUTED@; font-size: 12px; background: transparent; }
QPushButton#send:disabled { background: @STROKE@; }
QPushButton#micBtn { background: transparent; border: 1px solid @STROKE@; border-radius: 14px; padding: 0; }
QPushButton#micBtn:hover { background: @HOVER@; border: 1px solid @ACCENT@; }
QPushButton#micBtn:pressed { background: @STROKE@; }
QPushButton#micBtn[active="true"] { background: @ACCENT@; border: 1px solid @ACCENT@; }
QPushButton#iconBtn { background: transparent; border: none; border-radius: 12px; padding: 6px; }
QPushButton#iconBtn:hover { background: @HOVER@; }
QPushButton#iconBtn:pressed { background: @STROKE@; }
QPushButton#navBtn { background: @CARD@; border: 1px solid @STROKE@; border-radius: 14px; padding: 9px 12px;
    color: @TEXT@; text-align: left; font-weight: 600; }
QPushButton#navBtn:hover { border: 1px solid @ACCENT@; background: @HOVER@; }
QPushButton#chip { background: @CARD@; border: 1px solid @STROKE@; border-radius: 16px; padding: 7px 14px;
    color: @TEXT@; font-size: 12px; }
QPushButton#chip:hover { border: 1px solid @ACCENT@; color: @ACCENT@; }
QPushButton#avatar { background: @ACCENT@; border: none; border-radius: 17px; color: #1a1a1a; font-weight: 700; font-size: 13px; }
QPushButton#avatar:hover { background: @ACC_HOVER@; }
QLabel#greeting { color: @TEXT@; font-family: "@DISP@"; font-size: 22px; font-weight: 600; background: transparent; }
QLabel#heroTitle { color: @TEXT@; font-family: "@DISP@"; font-size: 24px; font-weight: 600; background: transparent; }
QLabel#heroSub { color: @MUTED@; font-size: 13px; background: transparent; }
QLabel#heroHint { color: @MUTED@; font-size: 13px; font-weight: 400; background: transparent; }
QLabel#heroFoot { color: @MUTED@; font-size: 11px; background: transparent; }
QLabel#heroSep { color: @MUTED@; font-size: 11px; background: transparent; }
QPushButton#heroLink { background: transparent; border: none; color: @ACC_INK@; font-size: 11px; font-weight: 400; padding: 2px 4px; }
QPushButton#heroLink:hover { color: @TEXT@; text-decoration: underline; }
QPushButton#welcomeCard, QFrame#welcomeCard { background: @CARD@; border: 1px solid @STROKE@; border-radius: 8px; }
QFrame#welcomeCard:hover { border: 1px solid @STROKE@; background: @HOVER@; }
QLabel#welcomeText { color: @TEXT@; font-size: 13px; font-weight: 500; background: transparent; }
QWidget#blobSlot { background: transparent; border: none; }
QPushButton#modelPill { background: transparent; border: 1px solid @STROKE@; border-radius: 16px; padding: 2px 14px 2px 10px;
    color: @MUTED@; font-size: 11px; min-height: 26px; max-height: 30px; max-width: 210px; text-align: left; }
QPushButton#modelPill:hover { color: @TEXT@; border: 1px solid @ACCENT@; background: @HOVER@; }
QPushButton#modelPill::menu-indicator { image: none; width: 0; }
QFrame#styleRow { background: transparent; border: none; }
QLabel#styleLabel { color: @TEXT@; font-size: 13px; font-weight: 600; background: transparent; }
QFrame#segBar { background: @SEG@; border: none; border-radius: 8px; }
QPushButton#styleSeg { background: transparent; border: none; border-radius: 6px; padding: 0px 2px;
    min-height: 48px; max-height: 48px; color: @SEG_TEXT@; font-size: 11px; font-weight: 400; }
QPushButton#styleSeg:hover { background: @HOVER@; }
QPushButton#styleSeg:checked { background: @ACCENT@; color: @ON_ACC@; font-weight: 600; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px 0; }
QScrollBar::handle:vertical { background: @STROKE@; border-radius: 4px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: @MUTED@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""


_THEME = {"dark": True}      # текущая тема чата: значки приветствия берут чёрный или белый цвет


def qss(dark, accent):
    """Стиль чата. Добавляется после стиля окна, поэтому перекрывает общие кнопки."""
    _THEME["dark"] = bool(dark)
    p = dict(PALETTE[bool(dark)])
    tokens = {
        "@ACCENT@": accent,
        "@ACC_A@": _rgba(accent, 0.46),
        "@ACC_T@": _rgba(accent, 0.18),
        "@ACC_HOVER@": _mix(accent, "#ffffff", 0.18),
        "@ACC_PRESS@": _mix(accent, "#000000", 0.12),
        "@ACC2@": _mix(accent, "#FF8FA3", 0.5), "@CARD2@": p["card2"], "@GLOW@": p["glow"], "@BASE@": p["base"],
        "@HEAD@": p["head"], "@CARD@": p["card"], "@SIDE@": p["side"], "@MICO@": p["mico"], "@USER@": p["user"],
        "@TEXT@": p["text"], "@MUTED@": p["muted"], "@STROKE@": p["stroke"], "@HOVER@": p["hover"],
        "@FAM@": chat_font_family(), "@DISP@": display_font_family(),
        "@SEG@": "#2D2D2D" if dark else "#EBEBEB", "@SEG_TEXT@": "#D6D6D6" if dark else "#424242",
        "@ON_ACC@": theme.on_accent(accent), "@ACC_INK@": settings_look.ink(accent, dark),
    }
    out = _QSS
    for k, v in tokens.items():
        out = out.replace(k, v)
    return out


# ---------- значки, которые рисуем сами (ровные линии, без шрифтов) ----------

def _pixmap(draw, color, size):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), max(1.6, size / 11))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    draw(p, size)
    p.end()
    return pm


def menu_icon(color, size=18):
    def draw(p, s):
        for y in (0.28, 0.5, 0.72):
            p.drawLine(QPointF(s * 0.2, s * y), QPointF(s * 0.8, s * y))
    return QIcon(_pixmap(draw, color, size))


def close_icon(color, size=18):
    def draw(p, s):
        p.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
        p.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))
    return QIcon(_pixmap(draw, color, size))


def plus_icon(color, size=18):
    def draw(p, s):
        p.drawLine(QPointF(s * 0.5, s * 0.22), QPointF(s * 0.5, s * 0.78))
        p.drawLine(QPointF(s * 0.22, s * 0.5), QPointF(s * 0.78, s * 0.5))
    return QIcon(_pixmap(draw, color, size))


class ChatScroll(QScrollArea):
    """Лента сообщений. Если человек сам крутит колёсиком — Mico AI перестаёт тянуть ленту вниз."""
    user_scrolled = pyqtSignal()

    def wheelEvent(self, e):
        self.user_scrolled.emit()
        super().wheelEvent(e)


class Dots(QWidget):
    """Три точки «печатает»: волной поднимаются по очереди, активная — цвета Mico AI."""

    def __init__(self, accent, muted, parent=None):
        super().__init__(parent)
        self.accent, self.muted = QColor(90, 90, 90, 210), QColor(90, 90, 90, 210)
        self.setFixedSize(46, 16)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._step)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _step(self):
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        now = time.time()
        for i in range(3):
            lift = thinking_dot_lift(now, i)
            x = 8 + i * 14
            y = 8 - 4.5 * lift
            p.setBrush(self.accent)
            p.drawEllipse(QRectF(x - 3.2, y - 3.2, 6.4, 6.4))
        p.end()


class MicoIcon(QWidget):
    """Компактный Mico для чата: лёгкий QWidget, чтобы строки ответов всегда отображались."""
    def __init__(self, size=22, accent=None, parent=None):
        super().__init__(parent)
        self._size, self._accent, self._phase = size, accent or "#FFCFA3", 0.0
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._phase += 0.075
        self.update()

    def set_accent(self, accent):
        self._accent = accent or self._accent
        self.update()

    def set_size(self, size):
        """Другой размер портрета (например, под шапку боковой панели) без пересоздания виджета."""
        self._size = size
        self.setFixedSize(size, size)
        self.update()

    def paintEvent(self, _):
        """Компактная версия нижнего Mico: цветное тело, щёки и дружелюбное лицо вместо грустного значка."""
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        s = self._size
        bob = math.sin(self._phase) * max(0.55, s * 0.025)
        tilt = math.sin(self._phase * 0.52) * 2.0
        p.translate(self.width() / 2, self.height() / 2 + bob)
        p.rotate(tilt)
        p.translate(-self.width() / 2, -self.height() / 2)
        r = QRectF(1.5, 2, self.width() - 3, self.height() - 4)
        path = QPainterPath()
        path.moveTo(r.left() + r.width() * 0.50, r.top())
        path.cubicTo(r.left() + r.width() * 0.77, r.top() - s * 0.03, r.right() + s * 0.02, r.top() + r.height() * 0.22,
                     r.right() - s * 0.02, r.top() + r.height() * 0.52)
        path.cubicTo(r.right() - s * 0.01, r.bottom() - r.height() * 0.16, r.left() + r.width() * 0.75, r.bottom() + s * 0.02,
                     r.left() + r.width() * 0.49, r.bottom())
        path.cubicTo(r.left() + r.width() * 0.22, r.bottom() + s * 0.01, r.left() - s * 0.03, r.bottom() - r.height() * 0.19,
                     r.left(), r.top() + r.height() * 0.49)
        path.cubicTo(r.left() + s * 0.01, r.top() + r.height() * 0.20, r.left() + r.width() * 0.24, r.top() - s * 0.04,
                     r.left() + r.width() * 0.50, r.top())
        color = QColor(self._accent or "#79B5FF")
        gradient = QLinearGradient(r.topLeft(), r.bottomRight())
        gradient.setColorAt(0.0, color.lighter(125))
        gradient.setColorAt(0.53, color)
        gradient.setColorAt(1.0, color.darker(112))
        p.setPen(QPen(color.lighter(150), max(1.0, s * 0.045)))
        p.setBrush(gradient)
        p.drawPath(path)
        highlight = QColor("#FFFFFF")
        highlight.setAlpha(72)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(highlight)
        p.drawEllipse(QRectF(r.left() + s * 0.14, r.top() + s * 0.12, r.width() * 0.38, r.height() * 0.22))
        face = QColor("#22242B")
        eye = max(1.1, s * 0.06)
        cy = r.center().y() - s * 0.035
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(face)
        blink = 0.22 if math.sin(self._phase * 0.38) > 0.992 else 1.0
        for x in (r.center().x() - s * 0.18, r.center().x() + s * 0.18):
            p.drawEllipse(QRectF(x - eye, cy - eye * blink, eye * 2, eye * 2.35 * blink))
        blush = QColor("#FF9B8D")
        blush.setAlpha(105)
        p.setBrush(blush)
        p.drawEllipse(QRectF(r.center().x() - s * 0.31, cy + s * 0.16, s * 0.13, s * 0.07))
        p.drawEllipse(QRectF(r.center().x() + s * 0.18, cy + s * 0.16, s * 0.13, s * 0.07))
        p.setPen(QPen(face, max(1.0, s * 0.042), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        mouth_y = r.center().y() + s * 0.17
        p.drawArc(QRectF(r.center().x() - s * 0.12, mouth_y - s * 0.07, s * 0.24, s * 0.14), 200 * 16, 140 * 16)
        p.end()


_LIST_START = re.compile(r"^(\s*([-•*–]|\d+[.)]|#+)\s|[^\wА-Яа-яЁё\s\"«(])")


def reflow(text):
    """Переносы строк модели внутри абзаца склеиваем: текст переносится по ширине пузыря, а не по её строкам.
    Пустая строка — новый абзац; строка-пункт списка (- , 1., эмодзи, символ) остаётся с новой строки."""
    out = []
    for para in str(text or "").split("\n\n"):
        acc = ""
        for line in para.split("\n"):
            line = line.rstrip()
            if not line.strip():
                continue
            if acc and not _LIST_START.match(line):
                acc = acc.rstrip() + " " + line.lstrip()
            else:
                acc = (acc + "\n" + line) if acc else line
        if acc:
            out.append(acc)
    return "\n\n".join(out)


class MessageRow(QWidget):
    """Одна реплика: ответ Mico слева, вопрос пользователя справа."""
    link = pyqtSignal(object)

    def __init__(self, role, body_html="", parent=None, accent=None):
        super().__init__(parent)
        self.role = role
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.bubble = QFrame()
        self.bubble.setObjectName("bubbleMico" if role == "mico" else "bubbleUser")
        self.bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        bl = QVBoxLayout(self.bubble)
        bl.setContentsMargins(14, 10, 14, 11)
        self.label = QLabel()
        self.label.setObjectName("msgText")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(False)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.label.linkActivated.connect(lambda u: self.link.emit(QUrl(u)))
        self.label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._w, self._image = 0, False
        self.label.setText(body_html)
        _set = self.label.setText
        # Каждый новый текст (живой ответ, печать по буквам) — пересчитываем размер пузыря,
        # иначе Qt оставляет старую высоту: текст обрезается или налезает на соседние сообщения.
        self.label.setText = lambda t: (_set(t), self._refit())
        bl.addWidget(self.label)
        if role == "mico":
            row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
        else:
            row.addStretch(1)
            row.addWidget(self.bubble, 0)

    def fit(self, width):
        """Пузырь не шире ~80% ленты: длинный текст переносится, а не растягивает окно."""
        if not width or width < 120:                     # окно ещё не разложено: ширина 0 давала пузырь нулевой высоты
            width = 360
        self._w = width
        bubble_width = max(160, int(width * 0.84))
        self.bubble.setMaximumWidth(bubble_width)
        self.label.setMaximumWidth(max(80, bubble_width - 28))
        self._refit()

    def _refit(self):
        """Ширина пузыря — по тексту (не шире 84% ленты), высота — точно под перенесённые строки."""
        if self._image or not self._w:
            return
        max_label = max(80, max(160, int(self._w * 0.84)) - 28)
        self.label.ensurePolished()
        doc = QTextDocument()
        doc.setDefaultFont(self.label.font())
        doc.setDocumentMargin(0)
        doc.setHtml(self.label.text() or " ")
        w = max(24, min(max_label, int(math.ceil(doc.idealWidth())) + 4))
        self.label.setFixedWidth(w)
        h = self.label.heightForWidth(w)
        if h <= 0:
            doc.setTextWidth(w)
            h = int(math.ceil(doc.size().height()))
        self.label.setFixedHeight(max(h, self.label.fontMetrics().height()))
        self.label.updateGeometry()
        self.bubble.updateGeometry()
        self.updateGeometry()

    def set_image(self, path):
        pm = QPixmap(path)
        if not pm.isNull():
            self._image = True
            self.label.setMinimumSize(0, 0)
            self.label.setMaximumSize(16777215, 16777215)
            self.label.setPixmap(pm.scaledToWidth(260, Qt.TransformationMode.SmoothTransformation))


class TypingRow(QWidget):
    """Mico AI печатает: спокойный пузырь с точками до готового ответа."""

    def __init__(self, accent, muted, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        bubble = QFrame()
        bubble.setObjectName("bubbleMico")
        bl = QHBoxLayout(bubble)
        bl.setContentsMargins(14, 10, 14, 10)
        self.dots = Dots(accent, muted)
        bl.addWidget(self.dots)
        row.addWidget(bubble, 0)
        row.addStretch(1)

    def show_typing(self, on):
        self.setVisible(on)
        (self.dots.start if on else self.dots.stop)()


class ProfileCard(QFrame):
    """Профиль внизу бокового меню: аватар, имя и тариф. Нажимается целиком — и аватар, и имя."""
    clicked = pyqtSignal()

    def __init__(self, accent, parent=None):
        super().__init__(parent)
        self.setObjectName("profileCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Изменить профиль: имя и что Mico AI должен знать")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        self.avatar = AvatarButton()
        self.avatar.setFixedSize(40, 40)
        self.avatar.set_accent(accent)
        self.avatar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)   # клик по аватару = клик по карточке
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(4)
        self.name = QLabel()
        self.name.setObjectName("profileName")
        self.plan = QLabel()
        self.plan.setObjectName("planPill")
        self.plan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plan_row = QHBoxLayout()
        plan_row.setContentsMargins(0, 0, 0, 0)
        plan_row.addWidget(self.plan, 0, Qt.AlignmentFlag.AlignLeft)
        plan_row.addStretch(1)
        col.addWidget(self.name)
        col.addLayout(plan_row)
        lay.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(col, 1)

    def set_profile(self, name, plan="Pro"):
        shown = " ".join(str(name or "").split()) or "Пользователь"
        self.name.setText(shown)
        self.plan.setText(plan)
        self.avatar.set_name(name)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


def _lerp(a, b, k):
    """Цвет между a и b: k=0 — a, k=1 — b. Сплошной, без прозрачности."""
    k = max(0.0, min(1.0, float(k)))
    return QColor(round(a.red() + (b.red() - a.red()) * k),
                  round(a.green() + (b.green() - a.green()) * k),
                  round(a.blue() + (b.blue() - a.blue()) * k))


class ChatRow(QFrame):
    """Строка чата в боковом меню. У открытого чата подсветка плавно разгорается, а слева появляется полоска цвета Mico."""
    clicked = pyqtSignal(int)

    def __init__(self, cid, title, when, accent, dark, parent=None):
        super().__init__(parent)
        pal = PALETTE[bool(dark)]
        self.cid = int(cid)
        self._side = QColor(pal["side"])
        self._hover_c = QColor(pal["hover"])
        self._sel_c = _lerp(QColor(pal["side"]), QColor(accent), 0.22 if dark else 0.28)
        self._bar_c = QColor(accent)
        self._hl = 0.0                     # 0 — не открыт, 1 — открыт (анимируется)
        self._hov = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(56)                       # высота растёт, если название длинное: оно не обрезается
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 8, 10, 8)
        lay.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("chatRowTitle")
        self.title.setWordWrap(True)                    # полное название: переносим на новую строку
        self.title.setToolTip(title)
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.when = QLabel(when)
        self.when.setObjectName("chatRowTime")
        self.when.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        lay.addWidget(self.title)
        lay.addWidget(self.when)
        self._anim = QPropertyAnimation(self, b"hl", self)
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_hl(self):
        return self._hl

    def set_hl(self, v):
        self._hl = float(v)
        self.update()

    hl = pyqtProperty(float, fget=get_hl, fset=set_hl)

    def set_selected(self, on, animate=True):
        """Открыт этот чат или нет. animate — плавно (при клике), иначе сразу (при обновлении списка)."""
        target = 1.0 if on else 0.0
        self._anim.stop()
        if not animate:
            self.set_hl(target)
            return
        self._anim.setStartValue(self._hl)
        self._anim.setEndValue(target)
        self._anim.start()

    def enterEvent(self, e):
        self._hov = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hov = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.cid)
        super().mousePressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        r = QRectF(self.rect()).adjusted(4, 2, -4, -2)
        base = _lerp(self._side, self._hover_c, 0.6 if self._hov else 0.0)
        p.setBrush(_lerp(base, self._sel_c, self._hl))
        p.drawRoundedRect(r, 10, 10)
        if self._hl > 0.001:                                   # полоска слева: вырастает вместе с подсветкой
            h = (r.height() - 18) * self._hl
            cy = r.center().y()
            p.setBrush(self._bar_c)
            p.drawRoundedRect(QRectF(r.left() + 2, cy - h / 2, 3, h), 1.5, 1.5)
        p.end()


class Sidebar(QFrame):
    """Боковое меню: недавние чаты и создание нового чата без настроек профиля."""
    open_chat = pyqtSignal(int)
    new_chat = pyqtSignal()

    def __init__(self, accent, parent=None, dark=True):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._accent = accent
        self._dark = dark
        self._ink = icon_ink(dark)
        self._rows = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(10)
        title = QLabel(i18n.t("Недавние чаты"))
        title.setObjectName("chatMuted")
        lay.addWidget(title)
        new_b = QPushButton(i18n.t("Новый чат"))
        new_b.setObjectName("navBtn")
        new_b.setIcon(plus_icon(self._ink, 16))
        new_b.setIconSize(QSize(16, 16))
        new_b.setCursor(Qt.CursorShape.PointingHandCursor)
        new_b.clicked.connect(self.new_chat.emit)
        lay.addWidget(new_b)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("chatScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_box = QWidget()
        self.list_box.setObjectName("chatListBox")
        self.list_lay = QVBoxLayout(self.list_box)
        self.list_lay.setContentsMargins(0, 0, 0, 0)
        self.list_lay.setSpacing(2)
        self.list_lay.addStretch(1)
        self.scroll.setWidget(self.list_box)
        lay.addWidget(self.scroll, 1)
        self.empty = QLabel(i18n.t("Пока нет чатов. Напиши Mico AI первое сообщение."))
        self.empty.setObjectName("chatMuted")
        self.empty.setWordWrap(True)
        lay.addWidget(self.empty)
        self.empty.hide()
    def set_profile(self, name, plan="Pro"):
        """Оставлено для совместимости: профиль теперь на отдельной странице настроек."""
        return

    def set_chats(self, items, current_id):
        """items: [(id, название, время последнего сообщения)] — новые сверху. Открытый чат подсвечен."""
        import time as _t
        for row in self._rows:
            self.list_lay.removeWidget(row)
            row.deleteLater()
        self._rows = []
        for cid, title, upd in items:
            row = ChatRow(cid, title, _t.strftime("%d.%m %H:%M", _t.localtime(upd)), self._accent, self._dark)
            row.clicked.connect(self._pick)
            row.set_selected(int(cid) == current_id, animate=False)
            self.list_lay.insertWidget(self.list_lay.count() - 1, row)
            self._rows.append(row)
        self.empty.setVisible(not items)

    def _pick(self, cid):
        """Клик по чату: подсветка плавно переходит на него, чат открывается."""
        for row in self._rows:
            row.set_selected(row.cid == cid, animate=True)
        self.open_chat.emit(cid)


def snippet(text, needle, width=56):
    """Кусок текста вокруг найденного слова — чтобы в результатах было видно, где оно."""
    low = text.lower()
    i = low.find(needle.lower())
    if i < 0:
        return text[:width]
    a = max(0, i - width // 2)
    b = min(len(text), i + len(needle) + width // 2)
    return ("…" if a > 0 else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def result_item(title, text, needle, cid, rid):
    it = QListWidgetItem(f"{title}\n{snippet(text, needle)}")
    it.setData(Qt.ItemDataRole.UserRole, (int(cid), int(rid)))
    return it


def scroll_to_bottom(scroll, animate=True):
    """Плавно вниз. Без анимации — сразу (во время печати ответа)."""
    sb = scroll.verticalScrollBar()
    if not animate:
        sb.setValue(sb.maximum())
        return None
    a = QPropertyAnimation(sb, b"value", scroll)
    a.setDuration(260)
    a.setStartValue(sb.value())
    a.setEndValue(sb.maximum())
    a.setEasingCurve(QEasingCurve.Type.OutCubic)
    a.start()
    return a


# ---------- профиль: аватар, приветствие, окно «о себе» ----------

def user_title(name):
    """У пустого чата нет текстового приветствия: Mico показывает это анимацией."""
    return ""


class AvatarButton(QPushButton):
    """Аватар пользователя: круг в цвете Mico AI с первой буквой имени. Нажмёшь — откроется окно «о себе»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Мой профиль: имя и что Mico AI должен обо мне знать")
        self._accent = "#FFCFA3"
        self._letter = "П"

    def set_accent(self, color):
        self._accent = color or self._accent
        self.update()

    def set_name(self, name):
        name = " ".join(str(name or "").split())
        self._letter = name[0].upper() if name else "П"
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._accent))
        p.drawEllipse(QRectF(1, 1, self.width() - 2, self.height() - 2))
        if self._letter:
            p.setPen(QColor("#1a1a1a"))
            f = p.font()
            f.setBold(True)
            f.setPointSizeF(max(8.0, self.height() * 0.38))
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._letter)
        else:
            # Не тонируем и не уменьшаем логотип слишком сильно: должны оставаться видны глаза и улыбка Mico.
            size = max(34, int(self.height() * 0.86))
            pm = settings_look.logo_pixmap(size)
            p.drawPixmap(int((self.width() - pm.width()) / 2), int((self.height() - pm.height()) / 2), pm)
        p.end()


# какая карточка с каким значком: подбираем ближайший по смыслу, как у карточек Copilot
CARD_ICONS = {"screenshot": "screen", "recap": "history", "open": "app", "site": "globe",
              "settings": "general", "can": "chat", "timer": "timer", "remind": "bell", "alarm": "bell",
              "vol_up": "speaker", "vol_down": "speaker", "mute": "speaker", "bright_up": "sun",
              "bright_down": "sun", "next": "play", "prev": "play", "pause": "play", "lock": "lock",
              "sleep": "moon", "minimize": "resize", "desktop": "layers", "dark": "moon", "light": "sun",
              "battery": "battery", "cpu": "chip", "disk": "disk", "updates": "download", "dns": "globe",
              "tasks": "pulse"}


def action_icon(name, color, size=30):
    """Значок действия: минималистичный чёрно-белый линейный глиф, без цветной подложки."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    g = int(size * 0.62)                                   # лёгкий глиф с воздухом вокруг, тонкая линия
    glyph = uiicons.icon(name, color, g, width=1.35).pixmap(g, g)
    p.drawPixmap((size - g) // 2, (size - g) // 2, glyph)
    p.end()
    return QIcon(pm)


class WelcomeCard(QFrame):
    """Кнопка действия на пустом экране: одно нажатие — Mico сразу выполняет команду.
    Текст переносится по ширине — карточки одинаковые и в узкой панели."""

    clicked = pyqtSignal()

    def __init__(self, label, phrase, icon=None, parent=None):
        super().__init__(parent)
        self.phrase = phrase
        self.setObjectName("welcomeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(phrase.strip())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 14, 10)
        row.setSpacing(10)
        if icon is not None:
            ic = QLabel()
            ic.setPixmap(icon.pixmap(30, 30))
            ic.setFixedSize(30, 30)
            ic.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QLabel(label)
        text.setObjectName("welcomeText")
        text.setWordWrap(True)
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(text, 1)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class SegFit(QObject):
    """Все кнопки переключателя стиля одной ширины, как в Copilot: полоса делится поровну при каждом изменении размера."""

    def __init__(self, bar, buttons):
        super().__init__(bar)
        self._bar, self._buttons = bar, buttons
        bar.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self._bar and ev.type() == QEvent.Type.Resize:
            n = len(self._buttons)
            if n:
                inner = self._bar.width() - 6 - 2 * (n - 1)      # поля 3+3, промежутки 2
                w = max(40, inner // n)
                for b in self._buttons:
                    b.setFixedWidth(w)
        return False


class Greeting(QWidget):
    """Пустой чат — как Windows Copilot: Mico сверху, название, стиль общения и кнопки действий на ПК.
    Кнопки видны, пока человек не начал писать запрос. Нажатие отправляет команду сразу."""

    action = pyqtSignal(str)            # карточка или ссылка: выполнить команду сразу
    settings_clicked = pyqtSignal()     # «Настройки» в подвале приветствия
    style_picked = pyqtSignal(str)      # сегментированный выбор стиля общения

    STYLE_CHOICES = (("creative", "Более\nтворческий"), ("balanced", "Более\nсбалансированный"),
                     ("precise", "Более\nточный"))     # две строки, как «More Creative» у Copilot

    def __init__(self, accent=None, parent=None):
        super().__init__(parent)
        self._accent = accent or "#FFCFA3"
        # ширина — ровно ширина ленты: длинные надписи переносятся, а не выталкивают чат вправо за край
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 12, 8, 8)
        lay.setSpacing(4)
        self.mico = MicoIcon(170, accent)                 # крупный Mico в пустом чате (было 132)
        lay.addWidget(self.mico, 0, Qt.AlignmentFlag.AlignHCenter)
        self.title = QLabel("")
        self.title.setObjectName("heroTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.title)
        self.sub = QLabel(i18n.t("Твой ежедневный ИИ-компаньон"))
        self.sub.setObjectName("heroSub")
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub.setWordWrap(True)
        lay.addWidget(self.sub)
        lay.addSpacing(14)
        self._voice = False
        style_label = QLabel(i18n.t("Выбери стиль общения"))
        self.style_label = style_label
        style_label.setObjectName("styleLabel")
        style_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(style_label)
        seg = QFrame()
        seg.setObjectName("segBar")
        sh = QHBoxLayout(seg)
        sh.setContentsMargins(4, 4, 4, 4)
        sh.setSpacing(2)
        self.style_btns = []
        for key, name in self.STYLE_CHOICES:
            b = QPushButton(i18n.t(name))
            b.setObjectName("styleSeg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            b.setMinimumWidth(0)
            b.clicked.connect(lambda _=False, k=key: self.style_picked.emit(k))
            sh.addWidget(b, 1)
            self.style_btns.append(b)
        lay.addWidget(seg)
        self.style_bar = seg
        self._seg_fit = SegFit(seg, self.style_btns)
        # подсказки: карточки действий и подвал — уходят, как только человек пишет запрос
        self.suggest = QWidget()
        sv = QVBoxLayout(self.suggest)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(4)
        sv.addSpacing(16)
        self.hint = QLabel(i18n.t("Вот что Mico может сделать для тебя"))
        self.hint.setObjectName("heroHint")
        self.hint.setWordWrap(True)
        sv.addWidget(self.hint)
        sv.addSpacing(2)
        self.cards_host = QWidget()
        self.grid = QGridLayout(self.cards_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(0)
        self.grid.setVerticalSpacing(8)
        sv.addWidget(self.cards_host)
        sv.addSpacing(12)
        foot = QLabel(i18n.t("Mico использует ИИ для ответов, поэтому возможны ошибки."))
        foot.setObjectName("heroFoot")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setWordWrap(True)
        sv.addWidget(foot)
        # «Подробнее | Условия использования | Конфиденциальность» — одна надпись со ссылками:
        # в узком чате она переносится на две строки (кнопки раньше растягивали чат и сдвигали всё вправо)
        self.links = QLabel()
        self.links.setObjectName("heroFoot")
        self.links.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.links.setWordWrap(True)
        self.links.setTextFormat(Qt.TextFormat.RichText)
        self.links.setOpenExternalLinks(False)
        self.links.linkActivated.connect(lambda kind: InfoDialog(kind, self.window()).exec())
        sv.addWidget(self.links)
        self._render_links()
        lay.addWidget(self.suggest)
        self.set_style("balanced")

    def set_accent(self, accent):
        self._accent = accent or self._accent
        self.mico.set_accent(accent)
        self._render_links()
        self.update()

    def _render_links(self):
        """Ссылки в подвале: цвет Mico (на светлой теме — темнее, чтобы читалось), без подчёркивания."""
        if not hasattr(self, "links"):
            return
        ink = settings_look.ink(self._accent, bool(_THEME["dark"]))
        muted = PALETTE[bool(_THEME["dark"])]["muted"]
        from PyQt6.QtGui import QColor as _QC, QPalette as _QP
        pal = self.links.palette()                                    # Qt красит ссылки цветом палитры, а не стилем тега — задаём оба
        for role in (_QP.ColorRole.Link, _QP.ColorRole.LinkVisited):
            pal.setColor(role, _QC(ink))
        self.links.setPalette(pal)
        parts = [f'<a href="{k}" style="color:{ink}; text-decoration:none"><span style="color:{ink}">{html.escape(i18n.t(t))}</span></a>'
                 for t, k in (("Подробнее", "about"), ("Условия использования", "terms"),
                                  ("Конфиденциальность", "privacy"))]
        self.links.setText(f' <span style="color:{muted}">|</span> '.join(parts))

    def set_name(self, name):
        pass

    def set_title(self, text):
        self.title.setText(text)

    def set_style(self, key):
        """Подсвечивает выбранный стиль общения — как переключатель у Copilot."""
        for b, (k, _name) in zip(self.style_btns, self.STYLE_CHOICES):
            b.setChecked(k == key)

    def fade_out(self):
        """Запрос отправлен: приветствие с кнопками плавно тает за 0,25 с, а не пропадает рывком."""
        if self.isHidden() or getattr(self, "_fading", False):
            return
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        self._fading = True
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(250)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def done():
            self.hide()
            self.setGraphicsEffect(None)
            self._fading = False
        anim.finished.connect(done)
        self._fade_anim = anim
        anim.start()

    def show_again(self):
        if getattr(self, "_fade_anim", None) is not None:
            self._fade_anim.stop()
        self._fading = False
        self.setGraphicsEffect(None)
        self.show()

    def set_portrait_visible(self, on):
        """Портрет Mico в приветствии. В боковой панели сверху и так живой Mico — второго не нужно."""
        self.mico.setVisible(False)          # портрет-«колобок» не показываем никогда: в чате живёт настоящий Mico

    def set_suggest_visible(self, on):
        """Кнопки действий и подвал. Уходят, как только человек начал писать запрос (и пока идёт голосовой режим)."""
        self.suggest.setVisible(bool(on) and not self._voice)

    def set_voice(self, on):
        """Голосовой режим: пропадают кнопки с действиями и выбор стиля, остаётся только название."""
        self._voice = bool(on)
        self.style_label.setVisible(not on)
        self.style_bar.setVisible(not on)
        self.suggest.setVisible(not on)
        self.title.setVisible(not on)                     # в голосовом чате надписи «Mico — твой ежедневный ИИ-компаньон» нет
        self.sub.setVisible(not on)

    def set_locked(self, on, title="", sub=""):
        """Нужно обновление: в приветствии остаются Mico и две строки — что случилось и что будет без обновления."""
        self._locked = bool(on)
        if on:
            self.set_voice(True)
            self.title.setText(title)
            self.sub.setText(sub)
            self.title.setVisible(True)
            self.sub.setVisible(True)

    def set_actions(self, items):
        """items — команды Chip: карточки в один столбец; нажатие отправляет свою фразу сразу."""
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget() is not None:
                it.widget().deleteLater()
        ink = PALETTE[bool(_THEME["dark"])]["text"]          # чёрный на светлой, белый на тёмной
        self._render_links()                                  # тема могла смениться — ссылки в цвет темы
        personal = any(getattr(c, "personal", False) for c in items)
        self.hint.setText(i18n.t("Твои частые действия") if personal else i18n.t("Вот что Mico может сделать для тебя"))
        for i, c in enumerate(items):
            cid = str(getattr(c, "id", ""))
            icon = action_icon("app" if cid.startswith("app:") else CARD_ICONS.get(cid, "bolt"), ink)
            card = WelcomeCard(c.label, c.phrase, icon)
            card.clicked.connect(lambda _=False, p=c.phrase: self.action.emit(p))
            self.grid.addWidget(card, i, 0)
            if self.isVisible():
                from ui import motion
                motion.fade_slide_in(card, dy=10, ms=300, delay=40 * i)   # карточки появляются по очереди

    def paintEvent(self, event):
        """Фон приветствия — цвет самого чата (прозрачный поверх карточки), без своего свечения-прямоугольника."""
        super().paintEvent(event)



class InfoDialog(QDialog):
    """«Подробнее», «Условия использования» и «Конфиденциальность»: спокойное окно с текстом из ui/legal.py."""

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QTextBrowser
        from ui import legal
        title, body = legal.page(kind)
        dark = bool(_THEME["dark"])
        p = PALETTE[dark]
        self.setWindowTitle(title)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(560, 620)
        self.finished.connect(self._closed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(12)
        head = QLabel(title)
        head.setObjectName("infoTitle")
        lay.addWidget(head)
        text = QTextBrowser()
        text.setObjectName("infoText")
        text.setOpenExternalLinks(True)
        text.setHtml(body)
        lay.addWidget(text, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton(i18n.t("Понятно"))
        ok.setObjectName("infoOk")
        ok.setCursor(Qt.CursorShape.PointingHandCursor)
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)
        self.setStyleSheet(theme.FONT_QSS + f"""
            QDialog {{ background: {p['base']}; }}
            QLabel#infoTitle {{ color: {p['text']}; font-size: 20px; font-weight: 600; }}
            QTextBrowser#infoText {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['stroke']};
                border-radius: 8px; padding: 14px 16px; font-size: 13px; }}
            QPushButton#infoOk {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['stroke']};
                border-radius: 6px; padding: 6px 18px; min-height: 20px; }}
            QPushButton#infoOk:hover {{ background: {p['hover']}; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {p['stroke']}; border-radius: 3px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}""")

    def showEvent(self, e):
        super().showEvent(e)
        from ui import blob as blob_mod
        if not getattr(self, "_counted", False):
            self._counted = True
            blob_mod.MODAL[0] += 1                   # Mico не лезет поверх этого окна
        self.raise_()
        self.activateWindow()
        from ui import motion
        motion.window_fade_in(self, 200)                  # окно мягко проявляется

    def _closed(self, _r=0):
        from ui import blob as blob_mod
        if getattr(self, "_counted", False):
            self._counted = False
            blob_mod.MODAL[0] = max(0, blob_mod.MODAL[0] - 1)


class ModelPill(QPushButton):
    """Маленькая кнопка у поля ввода: какая модель отвечает сейчас. Нажал — меню: локальная модель или Groq.
    Выбор сразу сохраняется в настройки (llm_backend, cloud_model) и применяется со следующего вопроса.
    Все такие кнопки (обычный чат и чат Mico AI) обновляются вместе."""
    _all = []

    def __init__(self, cfg, save=None, parent=None):
        super().__init__(parent)
        import weakref
        self.cfg, self.save = cfg, save
        self.setObjectName("modelPill")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(i18n.t("Модель для ответов — нажми, чтобы сменить"))
        self.clicked.connect(self._menu)
        ModelPill._all.append(weakref.ref(self))
        self._stamp = -1.0
        self._poll = QTimer(self)                         # после каждого ответа облака остаток пересчитывается: кнопка и подсказка обновляются сами
        self._poll.setInterval(1500)
        self._poll.timeout.connect(self._poll_quota)
        self._poll.start()
        try:
            from llm import cloud as cloud_api
            cloud_api.ensure_quota_async()
        except Exception:
            pass
        self.refresh()

    def _poll_quota(self):
        try:
            from llm import cloud as cloud_api
            if cloud_api.QUOTA["stamp"] != self._stamp:
                self._stamp = cloud_api.QUOTA["stamp"]
                self.refresh()
        except RuntimeError:
            pass

    def _current(self):
        from llm import cloud as cloud_api
        if self.cfg.get("llm_backend", "mico") in cloud_api.PROVIDERS:
            return "mico", cloud_api.normalize_mode(self.cfg.get("cloud_model"))
        return "local", None

    def refresh(self):
        try:
            backend, model = self._current()
        except Exception:
            backend, model = "local", None
        ink = PALETTE[bool(_THEME["dark"])]["muted"]
        self.setIcon(uiicons.icon("s_ai", ink, 14, width=1.4))
        self.setIconSize(QSize(12, 12))
        if backend == "mico":
            from llm import cloud as cloud_api
            self.setText(i18n.t("Облако Mico") + " · " + i18n.t(cloud_api.mode_label(model)))
            summary = cloud_api.quota_summary()
            self.setToolTip(summary + ("\n" if summary else "") + i18n.t("Модель для ответов — нажми, чтобы сменить"))
        else:
            self.setText(i18n.t("Локальная модель"))
            self.setToolTip(i18n.t("Модель для ответов — нажми, чтобы сменить"))

    def _menu(self):
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QMenu
        from llm import cloud as cloud_api
        backend, model = self._current()
        menu = QMenu(self)
        menu.setStyleSheet(self.window().styleSheet() if self.window() else "")
        act = menu.addAction(i18n.t("Локальная модель — работает офлайн"))
        act.setCheckable(True)
        act.setChecked(backend == "local")
        act.triggered.connect(lambda _=False: self._pick("local", None))
        menu.addSeparator()
        cloud_api.ensure_quota_async(10.0)
        if cloud_api.QUOTA["left"] is not None:                       # шапка меню: сколько осталось и что из этого выйдет
            head = menu.addAction(i18n.t("Осталось нейронов сегодня") + ": ~%d" % cloud_api.QUOTA["left"])
            head.setEnabled(False)
        notes = {"auto": i18n.t("сам выбирает уровень"), "lite": i18n.t("простые и быстрые модели"),
                 "plus": i18n.t("сильные модели"), "max": i18n.t("самые мощные модели")}
        for mode_id, mode_name in cloud_api.MODES:
            n = cloud_api.requests_left(mode_id) if mode_id != "auto" else None
            tail = ("  ~%d " % n + i18n.t("запросов")) if n is not None else ("  " + notes[mode_id] if mode_id == "auto" else "")
            a = menu.addAction(i18n.t("Облако Mico") + " · " + i18n.t(mode_name) + tail)
            a.setCheckable(True)
            a.setChecked(backend == "mico" and mode_id == model)
            a.setToolTip(notes[mode_id])
            a.triggered.connect(lambda _=False, m=mode_id: self._pick("mico", m))
        pos = self.mapToGlobal(QPoint(0, 0))
        menu.exec(QPoint(pos.x(), pos.y() - menu.sizeHint().height() - 6))   # меню открывается над полем ввода

    @staticmethod
    def local_available():
        """Локальная модель скачана на этот ПК? Без неё выбрать «на компьютере» нельзя: отвечать было бы нечем."""
        try:
            from llm import store as model_store
            return bool(model_store.installed_ids())
        except Exception:
            return False

    def _pick(self, backend, model):
        if backend == "local" and not self.local_available():
            from PyQt6.QtGui import QCursor
            from PyQt6.QtWidgets import QToolTip
            QToolTip.showText(QCursor.pos(), i18n.t("Локальная модель не скачана. Пока отвечает облако Mico."), self)
            return
        self.cfg["llm_backend"] = backend
        if model:
            self.cfg["cloud_model"] = model
        if self.save:
            try:
                self.save()
            except Exception:
                pass
        for ref in list(ModelPill._all):
            w = ref()
            if w is None:
                ModelPill._all.remove(ref)
                continue
            try:
                w.refresh()
            except RuntimeError:
                ModelPill._all.remove(ref)
        from ui import motion
        motion.fade_slide_in(self, dy=3, ms=220)
