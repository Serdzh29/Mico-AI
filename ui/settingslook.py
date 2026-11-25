"""Оформление окна настроек Mico AI в стиле макета: тёмная панель, карточки с иконками,
персиковый акцент (это цвет Mico AI), переключатели-пилюли, рамка с мягким свечением.
Здесь только внешний вид. Что сохраняется и как работает — в main.py (SettingsDialog).

Модуль не зависит от других модулей Mico, кроме theme, uiicons и i18n."""
import hashlib
import os
import string
import sys
import tempfile

from PyQt6.QtCore import QEasingCurve, QPoint, QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import (QGridLayout, QFrame, QGraphicsOpacityEffect, QGroupBox, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from ui import blob
import i18n
from ui import theme
from ui import icons as uiicons

# Палитра: нейтральные поверхности Windows 11 (как у Windows Copilot), акцент — цвет Mico AI.
PALETTE = {
    True: {"bg": "#202020", "card": "#2b2b2b", "field": "#2b2b2b", "stroke": "#3a3a3a",
           "text": "#ffffff", "muted": "#a6a6a6", "hover": "#333333", "track": "#444444"},
    False: {"bg": "#f3f3f3", "card": "#ffffff", "field": "#ffffff", "stroke": "#e5e5e5",     # те же цвета, что в чате
            "text": "#1a1a1a", "muted": "#5d5d5d", "hover": "#f0f0f0", "track": "#e0e0e0"},
}

QSS = string.Template("""
QDialog#settingsWin { background: transparent; }
QFrame#frame { background: qlineargradient(x1:0, y1:0, x2:0.55, y2:0.45, stop:0 $wash, stop:1 $bg);
    border: 1px solid $stroke; border-radius: 12px; }
QLabel#winTitle { color: $text; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#pageTitle { color: $text; font-size: 22px; font-weight: 600; background: transparent; padding: 2px 0 6px 2px; }
QLabel#cardTitle { color: $text; font-size: 14px; font-weight: 600; background: transparent; }
QLabel#previewName { color: $text; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#hint, QLabel#settingDesc { color: $muted; font-family: "$family"; font-size: 12px; font-style: normal;
    font-weight: 400; border: none; padding: 0px; background: transparent; }
QLabel { color: $text; background: transparent; }
QWidget#cardHost, QWidget#cardHost > QWidget { background: transparent; }
QScrollArea { background: transparent; border: none; }
QGroupBox#card, QFrame#card {
    background: $card; border: 1px solid $stroke; border-radius: 10px; margin: 0px; padding: 0px; }
QGroupBox#card:hover { border: 1px solid $edge; }
QLabel#cardBadge { background: $tint; border-radius: 9px; }
QFrame#cardLine { background: $stroke; border: none; min-height: 1px; max-height: 1px; }
QLineEdit#search {
    background: $field; border: 1px solid $stroke; border-radius: 6px; padding: 6px 10px; color: $text; }
QLineEdit#search:focus { border: 1px solid $stroke; border-bottom: 2px solid $accent; }
QPushButton#winBtn { background: transparent; border: none; color: $muted; font-size: 13px;
    padding: 4px 10px; border-radius: 6px; min-width: 22px; }
QPushButton#winBtn:hover { background: $hover; color: $text; }
QPushButton#winClose { background: transparent; border: none; color: $muted; font-size: 13px;
    padding: 4px 10px; border-radius: 6px; min-width: 22px; }
QPushButton#winClose:hover { background: #c42b1c; color: #ffffff; }
QListWidget#sideNav { background: transparent; border: none; outline: 0; padding: 4px 0; }
QListWidget#sideNav::item { color: $text; padding: 9px 12px; margin: 1px 6px; border-radius: 6px; }
QListWidget#sideNav::item:hover:!selected { background: $hover; }
QListWidget#sideNav::item:selected { background: $tint; color: $text; font-weight: 600; }
QPushButton { background: $field; border: 1px solid $stroke; border-radius: 6px; padding: 6px 14px; color: $text; }
QPushButton:hover { background: $hover; }
QPushButton:pressed { background: $card; color: $muted; }
QPushButton:disabled { color: $muted; }
QPushButton#primary { background: $accent; border: 1px solid $accent; color: $on_accent; font-weight: 600; }
QPushButton#primary:hover { background: $accent_hi; border: 1px solid $accent_hi; }
QPushButton#flat { background: transparent; border: none; color: $muted; padding: 6px 10px; }
QPushButton#flat:hover { color: $text; background: $hover; }
QComboBox, QLineEdit, QPlainTextEdit, QSpinBox, QAbstractSpinBox {
    background: $field; border: 1px solid $stroke; border-radius: 6px; padding: 5px 10px; color: $text;
    selection-background-color: $accent; selection-color: $on_accent; }
QComboBox:hover, QLineEdit:hover, QSpinBox:hover { background: $hover; }
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus { border: 1px solid $stroke; border-bottom: 2px solid $accent; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: $card; color: $text; border: 1px solid $stroke; border-radius: 6px;
    selection-background-color: $tint; selection-color: $text; outline: 0; padding: 4px; }
QListWidget { background: $field; border: 1px solid $stroke; border-radius: 8px; color: $text; outline: 0; }
QListWidget::item { padding: 6px 8px; border-radius: 4px; }
QListWidget::item:hover { background: $hover; }
QListWidget::indicator { width: 38px; height: 22px; border: none; background: transparent; image: url($ind_off); }
QListWidget::indicator:checked { image: url($ind_on); }
QCheckBox { color: $text; spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid $muted; background: transparent; }
QCheckBox::indicator:checked { background: $accent; border: 1px solid $accent; }
QCheckBox::indicator:hover { border: 1px solid $accent; }
QProgressBar { background: $track; border: none; border-radius: 2px; max-height: 4px; }
QProgressBar::chunk { background: $accent; border-radius: 2px; }
QToolTip { background: $card; color: $text; border: 1px solid $stroke; padding: 4px 8px; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 2px; }
QScrollBar::handle:vertical { background: $track; border-radius: 3px; min-height: 36px; }
QScrollBar::handle:vertical:hover { background: $muted; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
""")



def _mix(hex_color, other, k):
    """Смешивает два цвета: k=0 — hex_color, k=1 — other."""
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * k) for x, y in zip(a, b))


def indicator_pictures(accent, dark):
    """Пилюли-переключатели для списков с галочками (QListWidget): картинки делаем сами, по цвету Mico AI.
    Возвращает пути к файлам (для url() в стиле). Файлы одинаковые для одинаковых цветов — пишутся один раз."""
    track_off = "#4a4a4a" if dark else "#d1d1d6"
    key = hashlib.md5(f"{accent}|{track_off}".encode()).hexdigest()[:10]
    folder = os.path.join(tempfile.gettempdir(), "mico_settings_ui")
    os.makedirs(folder, exist_ok=True)
    paths = []
    for name, on in (("on", True), ("off", False)):
        path = os.path.join(folder, f"switch_{key}_{name}.png")
        if not os.path.exists(path):
            img = QImage(38, 22, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            pa = QPainter(img)
            pa.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pa.setPen(Qt.PenStyle.NoPen)
            pa.setBrush(QColor(accent if on else track_off))
            pa.drawRoundedRect(QRectF(0, 0, 38, 22), 11, 11)
            pa.setBrush(QColor("#ffffff"))
            x = 38 - 3 - 16 if on else 3
            pa.drawEllipse(QRectF(x, 3, 16, 16))
            pa.end()
            img.save(path, "PNG")
        paths.append(path.replace("\\", "/"))
    return paths[0], paths[1]


def ink(accent, dark):
    """Цвет текста и иконок с акцентом: сам акцент на тёмном фоне, потемнее — на светлом (иначе не видно)."""
    return accent if dark else _mix(accent, "#000000", 0.42)


def _rgba(hex_color, alpha):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def qss(dark, accent):
    """Стиль окна настроек. accent — цвет Mico AI (cfg['color'])."""
    p = dict(PALETTE[bool(dark)])
    # фоны непрозрачные и те же, что в чате: #202020 / #f3f3f3, карточки #2b2b2b / белые (без оттенка акцента)
    p["accent"] = accent
    p["ink"] = ink(accent, dark)
    p["accent_hi"] = _mix(accent, "#ffffff", 0.22)
    p["on_accent"] = theme.on_accent(accent)
    p["tint"] = _rgba(accent, 0.20 if dark else 0.28)
    p["wash"] = _mix(p["bg"], accent, 0.10 if dark else 0.22)   # отсвет цвета Mico — сплошной цвет, без прозрачности
    p["edge"] = _rgba(accent, 0.55)
    p["family"] = theme.FONT_FAMILY
    p["ind_on"], p["ind_off"] = indicator_pictures(accent, dark)
    # общий стиль приложения идёт раньше, наши правила — последними, чтобы перекрыть его подсказки
    return theme.FONT_QSS + theme.RESET_QSS + QSS.substitute(p)


def _asset(name):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", name)


def logo_pixmap(size, color=None):
    """Значок Mico — тело и лицо настоящего Mico из приложения (в цвете Mico AI), а не старая картинка."""
    try:
        from ui import appicon
        pm = appicon.blob_pixmap(size, color)
        if pm is not None:
            return pm
    except Exception:
        pass
    pm = QPixmap(_asset("mico.png")).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
    return pm


_BADGE_FRAMES = {}                                   # готовые кадры анимаций значков карточек: рисуем один раз


class AnimBadge(QLabel):
    """Значок карточки настроек в плашке цвета Mico. Играет свою анимацию того же набора, что и пункты бокового меню
    (у каждого значка она своя): при открытии карточки и когда на неё наводят мышь."""
    FRAMES = 30

    def __init__(self, name, ink, accent):
        super().__init__()
        self.name, self.ink, self.accent = name, ink, accent
        self.setObjectName("cardBadge")
        self.setFixedSize(36, 36)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frames = self._build()
        self.setPixmap(self._frames[0])
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(900)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.valueChanged.connect(self._on_frame)
        self._anim.finished.connect(lambda: self.setPixmap(self._frames[0]))

    def _build(self):
        key = (self.name, self.ink, self.accent)
        frames = _BADGE_FRAMES.get(key)
        if frames is None:
            uiicons.set_anim_accent(self.accent)
            try:
                frames = [uiicons.icon_frame(self.name, self.ink, i / (self.FRAMES - 1), 20).pixmap(20, 20) for i in range(self.FRAMES)]
            except Exception:                            # значка нет в наборе анимаций: остаётся обычный, без движения
                still = uiicons.icon(self.name, self.ink, 20, width=1.5).pixmap(20, 20)
                frames = [still] * self.FRAMES
            _BADGE_FRAMES[key] = frames
        return frames

    def _on_frame(self, v):
        self.setPixmap(self._frames[max(0, min(self.FRAMES - 1, int(round(float(v) * (self.FRAMES - 1)))))])

    def play(self):
        if self._anim.state() != QVariantAnimation.State.Running:
            self._anim.start()


class Card(QGroupBox):
    """Карточка раздела, как в Параметрах Windows 11: строка «иконка — название — пояснение — стрелка».
    Нажал на строку — карточка раскрывается; страница короткая, листать не нужно."""
    opened = pyqtSignal(object)

    def __init__(self, title, desc, icon, body, accent, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._ink = accent
        self._expanded = True
        self._badge = None
        self._chev_angle = 0.0
        self._chev_anim = None
        self._hover_t = 0.0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)
        self._head = QWidget()
        self._head.setCursor(Qt.CursorShape.PointingHandCursor)
        head = QHBoxLayout(self._head)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(12)
        if icon:
            ic = AnimBadge(icon, accent, accent)          # значок в плашке цвета Mico: у каждой карточки своя анимация
            self._badge = ic
            head.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("cardTitle")
        t.setWordWrap(True)
        text.addWidget(t)
        if desc:
            d = QLabel(desc)
            d.setObjectName("hint")
            d.setWordWrap(True)
            text.addWidget(d)
        head.addLayout(text, 1)
        self._chev = QLabel()
        self._chev.setFixedSize(14, 14)
        head.addWidget(self._chev, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(self._head)
        self._line = QFrame()                            # тонкая линия между шапкой и пунктами
        self._line.setObjectName("cardLine")
        lay.addWidget(self._line)
        self._body = body
        lay.addWidget(body)
        self.set_expanded(True)

    ANIM_MAX_PX = 360                                    # выше этого карточка раскрывается без анимации высоты

    def set_expanded(self, on, animate=False):
        """Раскрыть или свернуть. animate — содержимое плавно выезжает вниз и проявляется (и так же уезжает)."""
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
        self._expanded = bool(on)
        self._turn_chevron(animate and self.isVisible())
        if animate and self._expanded and self._badge is not None:
            self._badge.play()                           # открыли карточку — значок оживает
        old = getattr(self, "_anim", None)
        if old is not None:
            old.stop()
        if not animate or not self.isVisible():
            self._body.setMaximumHeight(16777215)
            self._body.setVisible(self._expanded)
            self._line.setVisible(self._expanded)
            return
        full = max(1, self._body.sizeHint().height())
        if self._expanded and full > self.ANIM_MAX_PX:
            # большая карточка: анимация высоты заставляла бы заново раскладывать всю страницу на каждом кадре. Открываем сразу
            self._line.setVisible(True)
            self._body.setMaximumHeight(16777215)
            self._body.setVisible(True)
            return
        from ui import motion
        motion.hold(400)                                 # зимний снег не мешает анимации
        self._line.setVisible(True)
        self._body.setVisible(True)
        start = self._body.height() if self._body.height() > 0 and not self._expanded else (0 if self._expanded else full)
        anim = QPropertyAnimation(self._body, b"maximumHeight", self)
        anim.setDuration(340 if self._expanded else 260)
        anim.setStartValue(start)
        anim.setEndValue(full if self._expanded else 0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        def done():
            if self._expanded:
                self._body.setMaximumHeight(16777215)
            else:
                self._body.setVisible(False)
                self._line.setVisible(False)
                self._body.setMaximumHeight(16777215)
        anim.finished.connect(done)
        self._anim = anim
        anim.start()

    def _turn_chevron(self, animate):
        """Стрелка справа плавно поворачивается на 180°, когда карточку раскрывают или сворачивают."""
        from PyQt6.QtGui import QTransform
        base = uiicons.icon("chev_down", self._ink, 14).pixmap(14, 14)
        target = 180.0 if self._expanded else 0.0

        def show(a):
            self._chev_angle = float(a)
            t = QTransform()
            t.translate(7, 7)
            t.rotate(self._chev_angle)
            t.translate(-7, -7)
            self._chev.setPixmap(base.transformed(t, Qt.TransformationMode.SmoothTransformation))
        if self._chev_anim is not None:
            self._chev_anim.stop()
        if not animate:
            show(target)
            return
        anim = QVariantAnimation(self)
        anim.setDuration(300)
        anim.setStartValue(self._chev_angle)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        anim.valueChanged.connect(show)
        self._chev_anim = anim
        anim.start()

    def enterEvent(self, e):
        import time as _t
        if self._badge is not None and _t.time() - self._hover_t > 2.5:      # наведи на карточку — значок играет, но не чаще раза в пару секунд
            self._hover_t = _t.time()
            self._badge.play()
        super().enterEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= self._head.geometry().bottom() + 6:
            self.set_expanded(not self._expanded, animate=True)
            if self._expanded:
                self.opened.emit(self)
            e.accept()
            return
        super().mousePressEvent(e)


class CardPage(QWidget):
    """Страница раздела: все карточки одна под другой, прокрутка. Вместо плиток с переходами.
    sections: [(виджет настроек, название, описание[, имя иконки])] — тот же вид, что раньше у SubPages.
    side: необязательная колонка справа (например, предпросмотр). Методы show_all/show_hub/open
    оставлены для совместимости с поиском: здесь всё и так видно сразу."""

    def __init__(self, sections, accent, side=None, parent=None, title=None):
        super().__init__(parent)
        self._cards = []
        host = QWidget()
        host.setObjectName("cardHost")
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 12, 0)
        row.setSpacing(14)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)
        # заголовок раздела уже показывает само окно настроек — второй не нужен (был дубль)
        for widget, card_title, desc, *rest in sections:
            card = Card(card_title, desc, rest[0] if rest else None, widget, accent)
            card.set_expanded(False)                     # при открытии настроек все блоки закрыты: видны только заголовки
            card.opened.connect(self._only)
            self._cards.append(card)
            col.addWidget(card)
        col.addStretch(1)
        row.addLayout(col, 1)
        if side is not None:
            side_col = QVBoxLayout()
            side_col.setContentsMargins(0, 0, 0, 0)
            side_col.setSpacing(12)
            side_col.addWidget(side)
            side_col.addStretch(1)
            row.addLayout(side_col)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(host)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _only(self, card):
        """Раскрыли одну карточку — остальные сворачиваются (но не во время поиска)."""
        if getattr(self, "_saved", None) is not None:
            return
        for c in self._cards:
            if c is not card and c._expanded:
                c.set_expanded(False)                     # соседние карточки сворачиваются сразу: две анимации высоты разом тормозили страницу

    def show_all(self, on):
        """Поиск: все карточки раскрыты, чтобы совпадения были видны; после поиска — как было."""
        if on:
            if getattr(self, "_saved", None) is None:
                self._saved = [c._expanded for c in self._cards]
            for c in self._cards:
                c.set_expanded(True)
        elif getattr(self, "_saved", None) is not None:
            for c, was in zip(self._cards, self._saved):
                c.set_expanded(was)
            self._saved = None

    def show_hub(self):
        pass

    def open(self, i):
        pass


class HoverRow(QWidget):
    """Строка настройки: кнопка «Сброс» появляется только при наведении — страница спокойнее."""
    hover_btn = None

    def enterEvent(self, e):
        if self.hover_btn is not None:
            self.hover_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.hover_btn is not None:
            self.hover_btn.setVisible(False)
        super().leaveEvent(e)


class SettingRow(HoverRow):
    """Строка настройки со стрелкой и кнопкой «Спросить Mico». Стрелка (или щелчок по свободному месту строки)
    плавно раскрывает пояснение; «Спросить Mico» — Mico сам объясняет в облачке, что это за настройка,
    когда она пригодится и кому лучше оставить её выключенной. Текст печатается, как живой ответ."""
    asked = pyqtSignal()
    TYPE_MS = 12

    def __init__(self, accent="#FFCFA3", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._open = False
        self._explain = None
        self._answer = None
        self._anim = None
        self.details = QFrame()
        self.details.setObjectName("rowDetails")
        self._dl = QVBoxLayout(self.details)
        self._dl.setContentsMargins(2, 6, 2, 8)
        self._dl.setSpacing(8)
        self.details.setVisible(False)
        self.chev = QPushButton()
        self.chev.setObjectName("rowChev")
        self.chev.setFixedSize(26, 26)
        self.chev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chev.setToolTip(i18n.t("Подробнее"))
        self.chev.clicked.connect(lambda: self.toggle())
        self.ask = QPushButton(i18n.t("Спросить Mico"))
        self.ask.setObjectName("askMico")
        self.ask.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ask.setToolTip(i18n.t("Mico объяснит, что это за настройка и кому она пригодится"))
        self.ask.clicked.connect(self.ask_mico)
        self.ask.setStyleSheet(f"QPushButton#askMico:hover {{ border: 1px solid {accent}; color: {accent}; }}")
        try:
            self.ask.setIcon(uiicons.icon("s_ai", accent, 14))
            self.ask.setIconSize(QSize(14, 14))
        except Exception:
            pass
        self._paint_chev()

    def add_detail(self, widget):
        self._dl.addWidget(widget)

    def set_explain(self, fn):
        """fn() -> [(заголовок, текст)] — что Mico скажет по кнопке «Спросить Mico»."""
        self._explain = fn

    def _paint_chev(self):
        self.chev.setIcon(uiicons.icon("chev_up" if self._open else "chev_down", self._accent, 14))
        self.chev.setIconSize(QSize(14, 14))

    def toggle(self, on=None, animate=True):
        """Раскрыть или свернуть пояснение: оно плавно выезжает вниз и проявляется (и так же уезжает)."""
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation
        want = (not self._open) if on is None else bool(on)
        if want == self._open and on is not None:
            return
        self._open = want
        self._paint_chev()
        if self._anim is not None:
            self._anim.stop()
        if not animate or not self.isVisible():
            self.details.setMaximumHeight(16777215)
            self.details.setVisible(self._open)
            return
        self.details.setVisible(True)
        full = max(1, self.details.sizeHint().height())
        start = self.details.height() if (not self._open and self.details.height() > 0) else (0 if self._open else full)
        anim = QPropertyAnimation(self.details, b"maximumHeight", self)
        anim.setDuration(360 if self._open else 280)
        anim.setStartValue(start)
        anim.setEndValue(full if self._open else 0)
        anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        def done():
            if not self._open:
                self.details.setVisible(False)
            self.details.setMaximumHeight(16777215)
        anim.finished.connect(done)
        self._anim = anim
        anim.start()
        if self._open:
            from ui import motion
            motion.fade_slide_in(self.details, dy=8, ms=320)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.childAt(e.position().toPoint()) is None:
            self.toggle()
            e.accept()
            return
        super().mousePressEvent(e)

    def _mark_pixmap(self, kind, size=24):
        """Значок слева от пункта в ответе Mico: аккуратная галочка (когда пригодится) или крестик (когда лучше не включать)."""
        scale = 2
        pm = QPixmap(size * scale, size * scale)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(scale, scale)
        good = kind == "check"
        col = QColor(self._accent if good else "#e5737c")
        bg = QColor(col)
        bg.setAlpha(46)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawEllipse(QRectF(1, 1, size - 2, size - 2))
        pen = QPen(col, 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        c = size / 2
        if good:
            p.drawPolyline(QPolygonF([QPointF(c - 4.6, c + 0.2), QPointF(c - 1.4, c + 3.4), QPointF(c + 4.8, c - 3.4)]))
        else:
            p.drawLine(QPointF(c - 3.6, c - 3.6), QPointF(c + 3.6, c + 3.6))
            p.drawLine(QPointF(c + 3.6, c - 3.6), QPointF(c - 3.6, c + 3.6))
        p.end()
        pm.setDevicePixelRatio(scale)
        return pm

    def ask_mico(self):
        """Mico объясняет настройку: пояснение раскрывается, слева Mico, галочка («когда пригодится») и крестик
        («кому лучше не включать»), справа печатается ответ."""
        if self._explain is None:
            return
        raw = [(h, t) for h, t in self._explain() if t]
        parts = [(i18n.t(h), i18n.t(t)) for h, t in raw]
        if self._answer is None:
            box = QFrame()
            box.setObjectName("micoSays")
            box.setStyleSheet(f"QFrame#micoSays {{ border-left: 3px solid {self._accent}; }}")
            g = QGridLayout(box)
            g.setContentsMargins(10, 9, 12, 10)
            g.setHorizontalSpacing(10)
            g.setVerticalSpacing(8)
            g.setColumnStretch(1, 1)
            self._ask_grid = g
            self._ask_widgets = []
            self._dl.addWidget(box)
            self._answer = box
            self._type_timer = QTimer(self)
            self._type_timer.setInterval(self.TYPE_MS)
            self._type_timer.timeout.connect(self._type_step)
        for w in self._ask_widgets:                       # прошлый ответ убираем и собираем новый
            self._ask_grid.removeWidget(w)
            w.deleteLater()
        self._ask_widgets = []
        self._ask_rows = []
        for i, (h, _t) in enumerate(raw):
            mark = QLabel()
            mark.setFixedSize(30, 26)
            mark.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            if h == "Что это":
                try:
                    mark.setPixmap(logo_pixmap(28))
                except Exception:
                    pass
            else:
                mark.setPixmap(self._mark_pixmap("check" if h == "Когда пригодится" else "cross"))
            text = QLabel()
            text.setObjectName("micoSaysText")
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            self._ask_grid.addWidget(mark, i, 0, Qt.AlignmentFlag.AlignTop)
            self._ask_grid.addWidget(text, i, 1)
            self._ask_widgets += [mark, text]
            self._ask_rows.append(text)
        import html as _html
        self._parts = [(_html.escape(h), _html.escape(t)) for h, t in parts]
        self._plain_len = sum(len(h) + len(t) + 2 for h, t in parts)
        self._typed = 0
        for r in self._ask_rows:
            r.setText("")
        if not self._open:
            self.details.setVisible(True)
            self.toggle(True)
        self._type_timer.start()
        self.asked.emit()

    def _render_rows(self, n):
        """Первые n символов ответа по строкам: заголовок жирным цветом Mico, под ним текст."""
        for row, (h, t) in zip(self._ask_rows, self._parts):
            if n <= 0:
                row.setText("")
                continue
            hh = h[:n]
            n -= len(h) + 2
            tt = t[:max(0, n)]
            n -= len(t)
            row.setText(f"<b style='color:{self._accent}'>{hh}</b>" + ("<br>" + tt if tt else ""))

    def _type_step(self):
        self._typed = min(self._plain_len, self._typed + 3)
        self._render_rows(self._typed)
        if self._typed >= self._plain_len:
            self._type_timer.stop()
            if self._open and self._anim is None or (self._anim is not None and self._anim.state() != self._anim.State.Running):
                self.details.setMaximumHeight(16777215)          # текст допечатан — блок занимает столько, сколько нужно


PREVIEW_BASE = 150                        # размер Mico AI в предпросмотре при масштабе 100%


class PreviewBlob(blob.Blob):
    """Живой Mico AI для предпросмотра: тот же Mico, что в чате (моргает, смотрит на курсор, меняет настроение,
    дышит), но стоит на месте: не ходит по экрану, не засыпает и не реагирует на мышь."""

    def __init__(self, cfg):
        super().__init__(cfg)
        self.locked = True                 # движением ведает Intel, а здесь движения нет
        self.keep_awake = True             # не засыпает
        self.can_sleep = lambda: False

    def _size_px(self):
        return max(1, int(PREVIEW_BASE * self.cfg["scale"] * self.size_k))

    def move(self, *args):                 # в предпросмотре окно не переезжает
        pass

    def mousePressEvent(self, e):
        e.ignore()

    def mouseMoveEvent(self, e):
        e.ignore()

    def mouseReleaseEvent(self, e):
        e.ignore()

    def mouseDoubleClickEvent(self, e):
        e.ignore()


class _PreviewStage(QWidget):
    """Место, где стоит Mico AI: держит его по центру при любом размере."""

    def __init__(self, mico, parent=None):
        super().__init__(parent)
        self.mico = mico
        self.setFixedHeight(190)

    def center_mico(self):
        """Mico по центру. Тело Mico рисуется чуть ниже середины квадрата — поднимаем его, чтобы сидел ровно."""
        s = self.mico.width()
        x = (self.width() - s) // 2
        y = (self.height() - s) // 2 - int(s * 0.04)
        QWidget.move(self.mico, QPoint(x, y))              # явно: PreviewBlob.move не двигает окно

    def resizeEvent(self, e):
        self.center_mico()
        super().resizeEvent(e)


class PreviewCard(QFrame):
    """Предпросмотр: живой Mico AI. Цвет, размер, прозрачность и тема применяются сразу,
    без «Сохранить»: карточка следит за cfg и перерисовывает Mico при любом изменении."""

    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedWidth(230)
        self.cfg = cfg
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 18)
        lay.setSpacing(8)
        title = QLabel(i18n.t("Предпросмотр"))
        title.setObjectName("cardTitle")
        lay.addWidget(title)
        self.mico = PreviewBlob(cfg)
        self.stage = _PreviewStage(self.mico)
        self.mico.setParent(self.stage, Qt.WindowType.Widget)   # внутрь карточки, а не отдельным окном
        self._fx = QGraphicsOpacityEffect(self.mico)
        self.mico.setGraphicsEffect(self._fx)
        self.mico.timer.stop()             # таймер идёт, только пока карточка видна (см. showEvent)
        lay.addWidget(self.stage)
        name = QLabel("Mico AI")
        name.setObjectName("previewName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name)
        hint = QLabel(i18n.t("Цвет и размер меняются сразу"))
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self._seen = None
        self._watch = QTimer(self)         # проверяем настройки часто: изменение видно почти сразу
        self._watch.setInterval(120)
        self._watch.timeout.connect(self._sync)
        self._sync(force=True)

    def _sync(self, force=False):
        key = (self.cfg.get("color"), self.cfg.get("scale"), self.cfg.get("opacity"), theme.is_dark(self.cfg))
        if key == self._seen and not force:
            return
        self._seen = key
        self.mico.apply_config()
        self._fx.setOpacity(max(0.3, float(self.cfg.get("opacity", 1.0))))
        self.stage.center_mico()
        self.mico.update()

    def showEvent(self, e):
        super().showEvent(e)
        self.mico.timer.start()
        self._watch.start()

    def hideEvent(self, e):
        self.mico.timer.stop()
        self._watch.stop()
        super().hideEvent(e)


def paint_glow(p, rect, color, radius=22, steps=12):
    """Свечение вокруг рамки окна: несколько контуров, каждый бледнее предыдущего.
    Рисуем сами, без эффектов Qt: эффект тени на большом окне тормозит анимации и переходы."""
    base = QColor(color)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for i in range(steps):
        c = QColor(base)
        c.setAlpha(int(90 * (1 - i / steps) ** 2))
        p.setPen(QPen(c, 1.5))
        k = i + 1
        p.drawRoundedRect(rect.adjusted(-k, -k, k, k), radius + k, radius + k)
