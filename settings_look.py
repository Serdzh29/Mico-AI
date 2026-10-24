"""Оформление окна настроек Mico AI в стиле макета: тёмная панель, карточки с иконками,
персиковый акцент (это цвет Mico AI), переключатели-пилюли, рамка с мягким свечением.
Здесь только внешний вид. Что сохраняется и как работает — в main.py (SettingsDialog).

Модуль не зависит от других модулей Mico, кроме theme, uiicons и i18n."""
import hashlib
import os
import string
import sys
import tempfile

from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QGroupBox, QHBoxLayout, QLabel, QScrollArea,
                             QVBoxLayout, QWidget)

import blob
import i18n
import theme
import uiicons

# Палитра. Акцент берётся из цвета Mico AI, поэтому по умолчанию это персиковый #FFCFA3 из макета.
PALETTE = {
    True: {"bg": "#1e1a18", "card": "#2a2422", "field": "#342d2a", "stroke": "#453c37",
           "text": "#f7efe9", "muted": "#b09d93", "hover": "#3a312e", "track": "#50443e"},
    False: {"bg": "#f8f2ed", "card": "#fffaf6", "field": "#f3ebe4", "stroke": "#e4d8ce",
            "text": "#2a201c", "muted": "#7d6e66", "hover": "#efe5dd", "track": "#dccfc5"},
}

QSS = string.Template("""
QDialog#settingsWin { background: transparent; }
QFrame#frame { background: $bg; border: 2px solid $accent; border-radius: 22px; }
QLabel#winTitle { color: $ink; font-size: 17px; font-weight: 600; background: transparent; }
QLabel#pageTitle { color: $text; font-size: 24px; font-weight: 700; background: transparent; }
QLabel#cardTitle { color: $text; font-size: 14px; font-weight: 600; background: transparent; }
QLabel#previewName { color: $text; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#hint, QLabel#settingDesc { color: $muted; font-family: "$family"; font-size: 12px; font-style: normal;
    font-weight: 400; border: none; padding: 0px; background: transparent; }
QLabel { color: $text; background: transparent; }
QWidget#cardHost, QWidget#cardHost > QWidget { background: transparent; }
QScrollArea { background: transparent; border: none; }
QGroupBox#card, QFrame#card {
    background: $card; border: 1px solid $stroke; border-radius: 16px; margin: 0px; padding: 0px; }
QLineEdit#search {
    background: $field; border: 1px solid $stroke; border-radius: 12px; padding: 7px 12px; color: $text; }
QLineEdit#search:focus { border: 1px solid $accent; }
QPushButton#winBtn { background: transparent; border: none; color: $muted; font-size: 14px;
    padding: 4px 10px; border-radius: 8px; min-width: 22px; }
QPushButton#winBtn:hover { background: $hover; color: $text; }
QPushButton#winClose:hover { background: #e81123; color: #ffffff; }
QListWidget#sideNav { background: transparent; border: none; outline: 0; padding: 6px 0; }
QListWidget#sideNav::item { color: $text; padding: 10px 14px; margin: 2px 8px; border-radius: 12px; }
QListWidget#sideNav::item:hover:!selected { background: $hover; }
QListWidget#sideNav::item:selected { background: $accent; color: $on_accent; font-weight: 600; }
QPushButton { background: $field; border: 1px solid $stroke; border-radius: 10px; padding: 7px 16px; color: $text; }
QPushButton:hover { border: 1px solid $accent; }
QPushButton#primary { background: $accent; border: 1px solid $accent; color: $on_accent; font-weight: 700; }
QPushButton#primary:hover { background: $accent_hi; border: 1px solid $accent_hi; }
QPushButton#flat { background: transparent; border: none; color: $muted; padding: 2px 4px; }
QPushButton#flat:hover { color: $text; }
QComboBox, QLineEdit, QSpinBox, QAbstractSpinBox {
    background: $field; border: 1px solid $stroke; border-radius: 9px; padding: 5px 10px; color: $text;
    selection-background-color: $accent; selection-color: $on_accent; }
QComboBox:focus, QLineEdit:focus, QSpinBox:focus { border: 1px solid $accent; }
QComboBox QAbstractItemView { background: $card; color: $text; border: 1px solid $stroke;
    selection-background-color: $tint; selection-color: $text; outline: 0; }
QListWidget { background: $field; border: 1px solid $stroke; border-radius: 12px; color: $text; outline: 0; }
QListWidget::item { padding: 5px 6px; }
QListWidget::indicator { width: 38px; height: 22px; border: none; background: transparent; image: url($ind_off); }
QListWidget::indicator:checked { image: url($ind_on); }
QCheckBox { color: $text; spacing: 8px; background: transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px; border: 1px solid $stroke; background: $field; }
QCheckBox::indicator:checked { background: $accent; border: 1px solid $accent; }
QCheckBox::indicator:hover { border: 1px solid $accent; }
QProgressBar { background: $track; border: none; border-radius: 4px; }
QProgressBar::chunk { background: $accent; border-radius: 4px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: $track; border-radius: 4px; min-height: 36px; }
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
    if not dark:
        p["bg"] = _mix(p["bg"], accent, 0.04)
    # полупрозрачность: окно, карточки и поля чуть просвечивают — интерфейс мягче
    p["bg"] = _rgba(p["bg"], 0.97 if dark else 0.98)
    p["card"] = _rgba(p["card"], 0.95 if dark else 0.97)
    p["field"] = _rgba(p["field"], 0.97 if dark else 0.98)
    p["accent"] = accent
    p["ink"] = ink(accent, dark)
    p["accent_hi"] = _mix(accent, "#ffffff", 0.22)
    p["on_accent"] = theme.on_accent(accent)
    p["tint"] = _rgba(accent, 0.20 if dark else 0.28)
    p["family"] = theme.FONT_FAMILY
    p["ind_on"], p["ind_off"] = indicator_pictures(accent, dark)
    # общий стиль приложения идёт раньше, наши правила — последними, чтобы перекрыть его подсказки
    return theme.FONT_QSS + theme.RESET_QSS + QSS.substitute(p)


def _asset(name):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "assets", name)


def logo_pixmap(size, color=None):
    """Иконка Mico. С color — окрашена в цвет Mico AI (тот же, что у его тела и палитры)."""
    pm = QPixmap(_asset("mico.png")).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
    if not color:
        return pm
    tinted = QPixmap(pm.size())
    tinted.fill(Qt.GlobalColor.transparent)
    p = QPainter(tinted)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    p.fillRect(tinted.rect(), QColor(color))
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    p.drawPixmap(0, 0, pm)                                  # прозрачные края остаются прозрачными
    p.end()
    return tinted


class Card(QGroupBox):
    """Карточка раздела: иконка, название, пояснение сверху, содержимое ниже."""

    def __init__(self, title, desc, icon, body, accent, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(12)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(12)
        if icon:
            ic = QLabel()
            ic.setFixedSize(22, 22)
            ic.setPixmap(uiicons.icon(icon, accent, 22).pixmap(22, 22))
            head.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
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
        lay.addLayout(head)
        lay.addWidget(body)


class CardPage(QWidget):
    """Страница раздела: все карточки одна под другой, прокрутка. Вместо плиток с переходами.
    sections: [(виджет настроек, название, описание[, имя иконки])] — тот же вид, что раньше у SubPages.
    side: необязательная колонка справа (например, предпросмотр). Методы show_all/show_hub/open
    оставлены для совместимости с поиском: здесь всё и так видно сразу."""

    def __init__(self, sections, accent, side=None, parent=None):
        super().__init__(parent)
        self._cards = []
        host = QWidget()
        host.setObjectName("cardHost")
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 12, 0)
        row.setSpacing(14)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        for widget, title, desc, *rest in sections:
            card = Card(title, desc, rest[0] if rest else None, widget, accent)
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

    def show_all(self, on):
        pass

    def show_hub(self):
        pass

    def open(self, i):
        pass


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
