"""Первый запуск Mico AI: коротко, что умеет программа, и выбор цвета. Показывается один раз."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

COLORS = [("#FFCFA3", "Персиковый"), ("#FFB3C6", "Розовый"), ("#B8C0FF", "Лавандовый"),
          ("#9FD3FF", "Небесный"), ("#A8E6CF", "Мятный"), ("#F6D365", "Солнечный")]

ABILITIES = [
    ("Разговор", "Спрашивай что угодно. Ответ появится рядом со мной."),
    ("Экран", "Скажи «что на экране?» — посмотрю на окно и подскажу, что делать дальше."),
    ("Компьютер", "Открою программу, найду файл, включу тёмную тему — если попросишь."),
    ("Напоминания", "Напомню о делах, таймере и перерыве. Можно одной фразой."),
]


class OnboardingDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добро пожаловать в Mico AI")
        self.setMinimumWidth(460)
        self.color = cfg.get("color") or COLORS[0][0]
        self._swatches = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(14)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._intro_page())
        self.pages.addWidget(self._color_page())
        root.addWidget(self.pages)

        row = QHBoxLayout()
        self.back = QPushButton("Назад")
        self.back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        self.next = QPushButton("Дальше")
        self.next.setObjectName("primary")
        self.next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next.clicked.connect(self._next)
        row.addWidget(self.back)
        row.addStretch(1)
        row.addWidget(self.next)
        root.addLayout(row)
        self._sync()

    def _intro_page(self):
        w = QLabel()
        w.setTextFormat(Qt.TextFormat.RichText)
        items = "".join(f"<p style='margin:10px 0'><b>{t}</b><br>"
                        f"<span style='color:#8a8a8e'>{d}</span></p>" for t, d in ABILITIES)
        w.setText("<div style='font-size:20px;font-weight:600'>Привет, я Mico AI</div>"
                  "<p style='color:#8a8a8e;margin-top:6px'>Живу на твоём компьютере и работаю офлайн.</p>"
                  + items)
        w.setWordWrap(True)
        return w

    def _color_page(self):
        w = QLabel()
        w.setTextFormat(Qt.TextFormat.RichText)
        w.setText("<div style='font-size:20px;font-weight:600'>Выбери цвет</div>"
                  "<p style='color:#8a8a8e;margin-top:6px'>Им окрасятся Mico AI и его чат. "
                  "Поменять можно в настройках в любой момент.</p>")
        w.setWordWrap(True)
        box = QVBoxLayout()
        box.addWidget(w)
        row = QHBoxLayout()
        for hex_color, name in COLORS:
            b = QPushButton()
            b.setToolTip(name)
            b.setFixedSize(54, 54)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=hex_color: self._pick(c))
            self._swatches[hex_color] = b
            row.addWidget(b)
        box.addLayout(row)
        self.color_name = QLabel()
        self.color_name.setObjectName("hint")
        box.addWidget(self.color_name)
        holder = QWidget()
        holder.setLayout(box)
        return holder

    def _pick(self, hex_color):
        self.color = hex_color
        self._sync()

    def _sync(self):
        for c, b in self._swatches.items():
            ring = "3px solid #2b2b2b" if c == self.color else "1px solid rgba(0,0,0,0.12)"
            b.setStyleSheet(f"QPushButton {{ background:{c}; border:{ring}; border-radius:27px; }}")
        names = dict(COLORS)
        if hasattr(self, "color_name"):
            self.color_name.setText(names.get(self.color, ""))
        last = self.pages.currentIndex() == 1
        self.back.setVisible(last)
        self.next.setText("Готово" if last else "Дальше")

    def _next(self):
        if self.pages.currentIndex() == 0:
            self.pages.setCurrentIndex(1)
            self._sync()
        else:
            self.accept()
