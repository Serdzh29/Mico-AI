"""Текстовый чат Mico AI в новом виде: боковое меню с недавними чатами (открывается тремя полосками),
поиск по чатам и сообщениям, ответы с иконкой Mico AI, анимация печати и современные кнопки.
Здесь только внешний вид и элементы. Что сохранять и что говорить — в main.py (Panel) и brain.py.
Голосовой режим этим модулем не трогается."""
import html
import math

from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

import i18n
import settings_look
import theme
import uiicons

PALETTE = {
    True: {"head": "#1c1c22", "card": "#202027", "user": "#2d2d36", "mico": "#26262e", "text": "#f2f2f5",
           "muted": "#9a9aa6", "stroke": "#353540", "hover": "#2d2d36", "side": "#18181e"},
    False: {"head": "#efe6df", "card": "#fffaf6", "user": "#f3ebe4", "mico": "#fcf7f3", "text": "#2a201c",
            "muted": "#7d6e66", "stroke": "#e4d8ce", "hover": "#efe5dd", "side": "#f5eee8"},
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


def qss(dark, accent):
    """Стиль чата. Добавляется после стиля окна, поэтому перекрывает общие кнопки."""
    p = dict(PALETTE[bool(dark)])
    p["accent"] = accent
    p["accent_soft"] = _mix(accent, "#000000" if not dark else "#1d1d23", 0.55)
    p["on_accent"] = "#1a1a1a"
    p["bar"] = p["head"]                                  # прозрачности нет: шапка матовая, сплошная
    return f"""
    QFrame#chatHeadBar {{ background: {p['bar']}; border-radius: 12px; }}
    QLabel#chatHead {{ color: #ffffff; font-size: 15px; font-weight: 700; background: transparent; }}
    QLabel#chatMuted {{ color: {p['muted']}; font-size: 11px; background: transparent; }}
    QFrame#sidebar {{ background: {p['side']}; border: none;
        border-right: 1px solid {p['stroke']}; border-radius: 0px; }}
    QFrame#card {{ background: {p['card']}; border-radius: 16px; }}
    QLabel#profileName {{ color: {p['text']}; font-size: 14px; font-weight: 700; background: transparent; }}
    QFrame#profileCard {{ background: transparent; border-radius: 16px; }}
    QFrame#profileCard:hover {{ background: {'rgba(255,255,255,0.07)' if dark else 'rgba(0,0,0,0.05)'}; }}
    QLabel#planPill {{ background: {_rgba(accent, 0.22)}; color: {accent}; border-radius: 8px;
        padding: 2px 9px; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; }}
    QLabel#profileSub {{ color: {p['muted']}; font-size: 11px; background: transparent; }}
    QListWidget#results {{ background: transparent; border: none; outline: 0; color: {p['text']}; }}
    QListWidget#results::item {{ padding: 8px 10px; margin: 2px 4px; border-radius: 10px; }}
    QListWidget#results::item:hover {{ background: {p['hover']}; }}
    QScrollArea#chatScroll {{ background: transparent; border: none; }}
    QWidget#chatListBox {{ background: transparent; }}
    QLabel#chatRowTitle {{ color: {p['text']}; font-size: 13px; font-weight: 600; background: transparent; }}
    QLabel#chatRowTime {{ color: {p['muted']}; font-size: 11px; background: transparent; }}
    QListWidget#results {{ background: {p['side']}; border: 1px solid {p['stroke']}; border-radius: 14px; padding: 4px; }}
    QLineEdit#chatSearch {{ background: {'rgba(255,255,255,0.06)' if dark else 'rgba(0,0,0,0.04)'}; border: 1px solid {'rgba(255,255,255,0.10)' if dark else 'rgba(0,0,0,0.08)'}; border-radius: 12px;
        padding: 6px 12px; color: #f2f2f5; selection-background-color: {accent}; }}
    QLineEdit#chatSearch:focus {{ border: 1px solid {accent}; }}
    QFrame#bubbleMico {{ background: {p['mico']}; border: 1px solid {_mix(accent, p['stroke'], 0.55)}; border-radius: 16px; }}
    QFrame#bubbleUser {{ background: {p['user']}; border: 1px solid {p['stroke']}; border-radius: 16px; }}
    QLabel#msgText {{ color: {p['text']}; font-size: 13px; background: transparent; }}
    QFrame#inputBox {{ background: {p['head']}; border: 1px solid {p['stroke']}; border-radius: 18px; }}
    QFrame#inputBox:focus-within {{ border: 1px solid {accent}; }}
    QLineEdit#chatInput {{ background: transparent; border: none; color: {p['text']}; padding: 6px 4px; font-size: 13px; }}
    QPushButton#send {{ background: {accent}; border: none; border-radius: 13px; min-width: 26px; max-width: 26px;
        min-height: 26px; max-height: 26px; }}
    QPushButton#send:hover {{ background: {_mix(accent, '#ffffff', 0.2)}; }}
    QPushButton#send:pressed {{ background: {_mix(accent, '#000000', 0.12)}; }}
    QPushButton#send:disabled {{ background: {p['stroke']}; }}
    QPushButton#iconBtn {{ background: transparent; border: none; border-radius: 10px; padding: 6px; }}
    QPushButton#iconBtn:hover {{ background: {p['hover']}; }}
    QPushButton#iconBtn:pressed {{ background: {p['stroke']}; }}
    QPushButton#navBtn {{ background: transparent; border: 1px solid {p['stroke']}; border-radius: 12px;
        padding: 8px 12px; color: {p['text']}; text-align: left; }}
    QPushButton#navBtn:hover {{ border: 1px solid {accent}; background: {p['hover']}; }}
    QPushButton#chip {{ background: transparent; border: 1px solid {p['stroke']}; border-radius: 14px;
        padding: 4px 12px; color: {p['text']}; font-size: 12px; }}
    QPushButton#chip:hover {{ border: 1px solid {accent}; color: {accent}; }}
    QScrollArea#msgScroll {{ background: transparent; border: none; }}
    QWidget#msgHost {{ background: transparent; }}
    QPushButton#avatar {{ background: {accent}; border: none; border-radius: 16px; color: #1a1a1a;
        font-weight: 700; font-size: 13px; }}
    QPushButton#avatar:hover {{ background: {_mix(accent, '#ffffff', 0.2)}; }}
    QLabel#greeting {{ color: #ffffff; font-size: 20px; font-weight: 700; background: transparent; }}
    QWidget#chipsInner {{ background: transparent; }}
    QPushButton#avatar {{ border-radius: 17px; }}
    """


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


def attach_icon(color, size=18):
    return uiicons.icon("layers", color, size)


def clip_icon(color, size=18):
    """Скрепка: настоящая форма — внешняя петля и внутренняя, обе с закруглённым низом."""
    from PyQt6.QtGui import QPainterPath

    def draw(p, s):
        path = QPainterPath()
        # внешняя петля: вниз по левой стороне, закруглённый низ, вверх по правой
        path.moveTo(s * 0.28, s * 0.44)
        path.lineTo(s * 0.28, s * 0.68)
        path.arcTo(QRectF(s * 0.28, s * 0.46, s * 0.44, s * 0.44), 180, 180)
        path.lineTo(s * 0.72, s * 0.30)
        path.arcTo(QRectF(s * 0.28, s * 0.10, s * 0.44, s * 0.40), 0, 180)
        path.lineTo(s * 0.28, s * 0.50)
        p.drawPath(path)
        # внутренняя петля: короче, внутри внешней
        inner = QPainterPath()
        inner.moveTo(s * 0.42, s * 0.30)
        inner.lineTo(s * 0.42, s * 0.64)
        inner.arcTo(QRectF(s * 0.42, s * 0.56, s * 0.16, s * 0.16), 180, 180)
        inner.lineTo(s * 0.58, s * 0.36)
        p.drawPath(inner)
    return QIcon(_pixmap(draw, color, size))


# ---------- элементы ----------

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
        self.accent, self.muted = QColor(accent), QColor(muted)
        self.setFixedSize(46, 16)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._step)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _step(self):
        self._phase += 0.32
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            lift = max(0.0, math.sin(self._phase - i * 0.9))
            x = 8 + i * 14
            y = 8 - 4.5 * lift
            p.setBrush(self.accent if lift > 0.55 else self.muted)
            p.drawEllipse(QRectF(x - 3.2, y - 3.2, 6.4, 6.4))
        p.end()


class MessageRow(QWidget):
    """Одна реплика: пузырь. Ответ Mico AI — с его иконкой слева, вопрос пользователя — справа."""
    link = pyqtSignal(object)

    def __init__(self, role, body_html="", parent=None, accent=None):
        super().__init__(parent)
        self.role = role
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.bubble = QFrame()
        self.bubble.setObjectName("bubbleMico" if role == "mico" else "bubbleUser")
        self.bubble.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        bl = QVBoxLayout(self.bubble)
        bl.setContentsMargins(12, 9, 12, 10)
        self.label = QLabel()
        self.label.setObjectName("msgText")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(False)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.label.linkActivated.connect(lambda u: self.link.emit(QUrl(u)))
        self.label.setText(body_html)
        bl.addWidget(self.label)
        if role == "mico":
            row.setSpacing(3)                               # иконка вплотную к пузырю
            ic = QLabel()
            ic.setFixedSize(22, 22)
            ic.setPixmap(settings_look.logo_pixmap(22, accent))
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(ic, 0, Qt.AlignmentFlag.AlignBottom)
            row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
        else:
            row.addStretch(1)
            row.addWidget(self.bubble, 0)

    def fit(self, width):
        """Пузырь не шире ~80% ленты: длинный текст переносится, а не растягивает окно."""
        self.bubble.setMaximumWidth(max(120, int(width * 0.8) - (34 if self.role == "mico" else 0)))

    def set_image(self, path):
        pm = QPixmap(path)
        if not pm.isNull():
            self.label.setPixmap(pm.scaledToWidth(260, Qt.TransformationMode.SmoothTransformation))


class TypingRow(QWidget):
    """Mico AI печатает: иконка и пузырь с точками. Показывается, пока думает, и прячется перед ответом."""

    def __init__(self, accent, muted, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        ic = QLabel()
        ic.setFixedSize(26, 26)
        ic.setPixmap(settings_look.logo_pixmap(24, accent))
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(ic, 0, Qt.AlignmentFlag.AlignBottom)
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
        self.setFixedHeight(56)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 8, 10, 8)
        lay.setSpacing(2)
        self.title = QLabel(title)
        self.title.setObjectName("chatRowTitle")
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
    """Боковое меню: недавние чаты с названиями, «Новый чат» и профиль внизу."""
    open_chat = pyqtSignal(int)
    new_chat = pyqtSignal()
    profile = pyqtSignal()           # профиль нажали: открыть «о себе»

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
        self.profile_card = ProfileCard(accent)
        self.profile_card.clicked.connect(self.profile.emit)
        lay.addWidget(self.profile_card)

    def set_profile(self, name, plan="Pro"):
        self.profile_card.set_profile(name, plan)

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
    """Что показывать в приветствии: имя пользователя или нейтральное «Приступим»."""
    name = " ".join(str(name or "").split())
    return f"{name}, приступим" if name else "Приступим"


class AvatarButton(QPushButton):
    """Аватар пользователя: круг в цвете Mico AI с первой буквой имени. Нажмёшь — откроется окно «о себе»."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Мой профиль: имя и что Mico AI должен обо мне знать")
        self._accent = "#FFCFA3"
        self._letter = ""

    def set_accent(self, color):
        self._accent = color or self._accent
        self.update()

    def set_name(self, name):
        name = " ".join(str(name or "").split())
        self._letter = name[0].upper() if name else ""
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
            pm = settings_look.logo_pixmap(int(self.height() * 0.66))
            p.drawPixmap(int((self.width() - pm.width()) / 2), int((self.height() - pm.height()) / 2), pm)
        p.end()


class Greeting(QWidget):
    """Пустой чат: иконка Mico и «<имя>, приступим» белым крупным шрифтом."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 18, 0, 18)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic.setPixmap(settings_look.logo_pixmap(44))
        lay.addWidget(ic)
        self.title = QLabel()
        self.title.setObjectName("greeting")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        lay.addWidget(self.title)

    def set_name(self, name):
        self.title.setText(user_title(name))


class ProfileDialog(QDialog):
    """«О себе»: имя и то, что Mico AI должен знать о пользователе, чтобы персонализировать чат."""

    def __init__(self, name, about, dark, accent, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Мой профиль")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(340)
        p = PALETTE[bool(dark)]
        self.setStyleSheet(theme.FONT_QSS + f"""
            QDialog {{ background:{p['card']}; }}
            QLabel {{ color:{p['text']}; background:transparent; }}
            QLabel#hint {{ color:{p['muted']}; font-size:12px; }}
            QLineEdit, QPlainTextEdit {{ background:{p['side']}; border:1px solid {p['stroke']}; border-radius:10px;
                color:{p['text']}; padding:8px 10px; }}
            QLineEdit:focus, QPlainTextEdit:focus {{ border:1px solid {accent}; }}
            QPushButton {{ background:transparent; border:1px solid {p['stroke']}; border-radius:10px;
                padding:7px 16px; color:{p['text']}; }}
            QPushButton:hover {{ border:1px solid {accent}; }}
            QPushButton#primary {{ background:{accent}; border:1px solid {accent}; color:#1a1a1a; font-weight:700; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(8)
        t = QLabel("Мой профиль")
        t.setStyleSheet("font-size:16px; font-weight:700;")
        lay.addWidget(t)
        lay.addWidget(self._hint("Как тебя называть"))
        self.name = QLineEdit(name or "")
        self.name.setPlaceholderText("Например, Сергей")
        self.name.setMaxLength(40)
        lay.addWidget(self.name)
        lay.addWidget(self._hint("Что Mico AI должен знать о тебе: чем занимаешься, что любишь, как лучше отвечать. "
                                 "Это поможет ему быть полезнее и говорить на твоём языке."))
        self.about = QPlainTextEdit(about or "")
        self.about.setPlaceholderText("Например: работаю программистом, пишу на Python. "
                                      "Отвечай коротко, без лишних вступлений.")
        self.about.setFixedHeight(120)
        lay.addWidget(self.about)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Сохранить")
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(save)
        lay.addLayout(row)

    @staticmethod
    def _hint(text):
        lab = QLabel(text)
        lab.setObjectName("hint")
        lab.setWordWrap(True)
        return lab

    def values(self):
        return self.name.text().strip(), self.about.toPlainText().strip()
