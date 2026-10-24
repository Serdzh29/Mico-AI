"""Мастер установки и удаление Mico. Работает только в собранном Mico.exe.
Оформление в духе Mico AI: тёмная тема, персиковый акцент, без лишнего текста.
Тексты — через i18n.t(): мастер и удаление показываются на английском (см. i18n_installer_en.py)."""
import json, os, random, shutil, subprocess, sys, time

from PyQt6.QtCore import QRectF, QEasingCurve, QThread, QVariantAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMessageBox,
                             QProgressBar, QPushButton, QStackedWidget, QVBoxLayout, QWidget)
import i18n
import theme
from switch_ui import Switch, WrapCheck    # переключатели — как в настройках Mico AI
from theme import FONT_FAMILY, FONT_DISPLAY

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
    ("Если попросишь, посмотрю на экран: «что у меня на экране?».", "surprised"),
    ("Опасные команды, например выключение компьютера, я сначала спрошу «да или нет».", "worried"),
    ("Отвечаю на вопросы прямо на этом компьютере.", "curious"),
    ("В голосовом режиме нажми на меня, и я обрадуюсь.", "happy"),
    ("Ответы считаются прямо на твоём компьютере, без облака.", "thinking"),
    ("Ты можешь сказать «запомни», и я сохраню заметку. Потом спросишь — и я вспомню.", "love"),
    ("Скоро установка закончится. В меню Mico AI, по правому щелчку, есть всё, что я умею.", "happy"),
]
FACT_MS = 4800                       # сколько показывается один факт


class MicoAvatar(QLabel):
    """Mico AI в мастере установки и удаления. Рисуется программой, живой: моргает, дышит, и настроение
    меняется плавно — старое лицо растворяется в новое за FADE_MS, а не прыгает."""
    SIZE = 150
    FRAME_MS = 33
    FADE_MS = 520

    def __init__(self, mood="happy", color="#FFCFA3"):
        super().__init__()
        from blob import Blob, BASE_PX
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
    """Страница из элементов по вертикали (виджеты и отступы числом)."""
    w = QWidget()
    lay = QVBoxLayout(w)
    for it in items:
        if isinstance(it, int):
            lay.addSpacing(it)
        else:
            lay.addWidget(it)
    lay.addStretch()
    return w


# Палитры в стиле Windows 11 (Fluent): нейтральные поверхности, акцент Windows, фон Mica там, где он есть.
# Тёмная и светлая: какая нужна, решает тема Windows на этом ПК.
_DARK = {
    "bg": "#202020", "text": "#ffffff", "title": "#ffffff", "sub": "#c5c5c5", "step": "#8a8a8a",
    "brand": "#ffffff", "accent": "#60cdff", "accent_text": "#000000", "accent_hover": "#7dd8ff",
    "accent_off_bg": "rgba(255,255,255,0.06)", "accent_off_text": "#6e6e6e",
    "ok": "#6ccb5f", "warn": "#fce100", "check": "#ffffff",
    "box": "rgba(255,255,255,0.06)", "box_edge": "#8a8a8a",
    "btn_bg": "rgba(255,255,255,0.06)", "btn_edge": "rgba(255,255,255,0.08)", "btn_text": "#ffffff",
    "btn_hover": "rgba(255,255,255,0.09)", "btn_press": "rgba(255,255,255,0.04)",
    "btn_off": "#6e6e6e", "bar": "rgba(255,255,255,0.12)", "side_edge": "rgba(255,255,255,0.06)",
}
_LIGHT = {
    "bg": "#f3f3f3", "text": "#1a1a1a", "title": "#1a1a1a", "sub": "#5c5c5c", "step": "#7a7a7a",
    "brand": "#1a1a1a", "accent": "#005fb8", "accent_text": "#ffffff", "accent_hover": "#0067c0",
    "accent_off_bg": "rgba(0,0,0,0.06)", "accent_off_text": "#9a9a9a",
    "ok": "#0f7b0f", "warn": "#9d5d00", "check": "#1a1a1a",
    "box": "#ffffff", "box_edge": "#8a8a8a",
    "btn_bg": "#fbfbfb", "btn_edge": "#e5e5e5", "btn_text": "#1a1a1a",
    "btn_hover": "#f6f6f6", "btn_press": "#f0f0f0",
    "btn_off": "#a0a0a0", "bar": "rgba(0,0,0,0.10)", "side_edge": "rgba(0,0,0,0.06)",
}


def qss(dark=None):
    """Стиль мастера установки и удаления. dark=None — как в Windows на этом ПК."""
    if dark is None:
        dark = theme.system_dark()
    c = _DARK if dark else _LIGHT
    Switch.ON, Switch.OFF = c["accent"], ("#4a4a4a" if dark else "#d1d1d6")   # переключатели — цвет установщика
    # С Mica окно прозрачное: фон дорисовывает Windows. Без Mica (Windows 10) — сплошной цвет.
    wizard_bg = "transparent" if theme.mica_supported() else c["bg"]
    return f"""
QDialog#wizard {{ background: {wizard_bg}; }}
QFrame#side {{ background: transparent; border-right: 1px solid {c['side_edge']}; }}
QLabel {{ color: {c['text']}; font-family: "{FONT_FAMILY}"; font-size: 13px; background: transparent; }}
QLabel#title {{ font-family: "{FONT_DISPLAY}"; font-size: 26px; font-weight: 700; color: {c['title']}; }}
QLabel#sub {{ color: {c['sub']}; font-size: 13px; }}
QLabel#step {{ color: {c['step']}; font-size: 12px; }}
QLabel#brand {{ font-family: "{FONT_DISPLAY}"; color: {c['brand']}; font-size: 16px; font-weight: 700; }}
QLabel#percent {{ font-family: "{FONT_DISPLAY}"; font-size: 44px; font-weight: 700; color: {c['title']}; }}
QLabel#ok {{ color: {c['ok']}; font-size: 13px; }}
QLabel#warn {{ color: {c['warn']}; font-size: 13px; }}
QCheckBox {{ color: {c['check']}; font-size: 13px; spacing: 12px; padding: 6px 0; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {c['box_edge']}; background: {c['box']}; }}
QCheckBox::indicator:checked {{ background: {c['accent']}; border: 1px solid {c['accent']}; }}
QPushButton {{ font-family: "{FONT_FAMILY}"; font-size: 13px; padding: 7px 20px; border-radius: 4px;
              background: {c['btn_bg']}; color: {c['btn_text']}; border: 1px solid {c['btn_edge']}; }}
QPushButton:hover {{ background: {c['btn_hover']}; }}
QPushButton:pressed {{ background: {c['btn_press']}; }}
QPushButton:disabled {{ color: {c['btn_off']}; }}
QPushButton#primary {{ font-family: "{FONT_FAMILY}"; background: {c['accent']}; color: {c['accent_text']};
                      border: 1px solid {c['accent']}; font-weight: 700; }}
QPushButton#primary:hover {{ background: {c['accent_hover']}; }}
QPushButton#primary:disabled {{ background: {c['accent_off_bg']}; color: {c['accent_off_text']}; border: none; }}
QProgressBar {{ background: {c['bar']}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 2px; }}
"""


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
        c = _DARK if dark else _LIGHT
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


class Wizard(QDialog):
    PAGE_STEP = {0: "", 1: "Шаг 1 из 2", 2: "Установка", 3: ""}     # переводятся в _go()
    PAGE_MOOD = {0: "happy", 1: "curious", 2: "thinking", 3: "love"}

    def __init__(self):
        super().__init__()
        self.setObjectName("wizard")
        self.setWindowTitle(i18n.t("Установка Mico AI"))
        self.setFixedSize(700, 480)              # третий вариант модели не должен обрезаться
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowIcon(QIcon(_asset("mico.ico") or ""))
        self.setStyleSheet(qss())
        if theme.mica_supported():
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ollama_ok = _ollama_present()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # левая панель: Mico AI и название
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 36)
        sv.addStretch()
        self.avatar = MicoAvatar(self.PAGE_MOOD[0])
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(self.avatar)
        sv.addSpacing(10)
        sv.addWidget(brand)
        sv.addStretch()
        root.addWidget(side)

        # правая часть: шаг, страница, кнопки
        right = QVBoxLayout()
        right.setContentsMargins(40, 34, 40, 30)
        right.setSpacing(0)
        self.step_lbl = StepDots(4)                      # точки шагов: 4 экрана
        right.addWidget(self.step_lbl)
        right.addSpacing(22)
        self.pages = QStackedWidget()
        for page in (self._page_welcome(), self._page_options(), self._page_install(), self._page_finish()):
            self.pages.addWidget(page)
        right.addWidget(self.pages, 1)

        row = QHBoxLayout()
        self.cancel_b = QPushButton(i18n.t("Отмена"))
        self.back_b = QPushButton(i18n.t("Назад"))
        self.next_b = QPushButton(i18n.t("Далее"))
        self.next_b.setObjectName("primary")
        self.cancel_b.clicked.connect(self.reject)
        self.back_b.clicked.connect(lambda: self._go(self.pages.currentIndex() - 1))
        self.next_b.clicked.connect(self._next)
        row.addWidget(self.cancel_b)
        row.addStretch()
        row.addWidget(self.back_b)
        row.addSpacing(8)
        row.addWidget(self.next_b)
        right.addLayout(row)
        root.addLayout(right, 1)
        self._go(0)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_mica_done", False):
            self._mica_done = True
            theme.apply_mica(self)

    # ---------- страницы ----------
    def _title(self, text):
        t = QLabel(i18n.t(text))
        t.setObjectName("title")
        return t

    def _sub(self, text):
        s = QLabel(i18n.t(text))
        s.setObjectName("sub")
        s.setWordWrap(True)
        return s

    def _page_welcome(self):
        return column(self._title("Установка Mico AI"),
                      10,
                      self._sub("Компаньон на рабочем столе. Понимает текст, управляет Windows "
                                "и отвечает на вопросы. Всё работает на твоём ПК."),
                      10,
                      self._sub("Займёт около минуты."))

    def _page_options(self):
        self.opt_auto = WrapCheck(i18n.t("Запускать вместе с Windows"))
        self.opt_auto.setChecked(True)
        self.opt_short = WrapCheck(i18n.t("Ярлык на рабочем столе"))
        self.opt_short.setChecked(True)
        self.model_entry, self.ollama_model = None, None
        builtin = self._builtin_available()
        light, heavy = self._model_pair(builtin)
        rows = [self._title("Параметры"), 14, self.opt_auto, self.opt_short]
        self.opt_model = None
        if builtin:                                  # встроенный движок: модель можно скачать прямо сейчас
            self.opt_model = WrapCheck(i18n.t("Скачать выбранную модель для ответов сейчас"))
            self.opt_model.setChecked(True)
            rows.append(self.opt_model)
        rows += [18, self._model_choice(builtin, light, heavy)]
        return column(*rows)

    @staticmethod
    def _builtin_available():
        """Встроенный движок (llama-cpp) установлен: модели Mico работают без Ollama."""
        try:
            import local_llm
            return local_llm.available()
        except Exception:
            return False

    @staticmethod
    def _model_pair(builtin):
        """Лёгкая и мощная модель под память этого ПК."""
        import model_catalog
        try:
            import psutil
            ram = psutil.virtual_memory().total / (1024 ** 3)
        except Exception:
            ram = 8.0
        return model_catalog.pair_for(ram, None if builtin else model_catalog.OLLAMA_TIERS)

    def _model_choice(self, builtin, light, heavy):
        """Два варианта: мощная и лёгкая. Рекомендованная для памяти выбрана сразу, второй можно выбрать вместо неё."""
        from PyQt6.QtWidgets import QButtonGroup, QRadioButton
        import model_catalog
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        head = QLabel(i18n.t("Какую модель использовать для ответов?"))
        head.setWordWrap(True)
        v.addWidget(head)
        v.addSpacing(6)
        group = QButtonGroup(box)
        options = [(heavy, True)] + ([(light, False)] if light["id"] != heavy["id"] else [])
        alt = model_catalog.by_id("gemma-3-4b-q4") if builtin else None   # ручной вариант: не подбирается сам
        if alt is not None and alt["id"] not in (heavy["id"], light["id"]):
            options.append((alt, None))
        for entry, is_heavy in options:
            if is_heavy is None:
                kind = i18n.t("Альтернатива")
            else:
                kind = i18n.t("Мощная") if is_heavy else i18n.t("Лёгкая")
            is_heavy = bool(is_heavy)
            # название коротким — в одну строку; пояснение — отдельной строкой под ним, с переносом, без обрезки
            rb = QRadioButton(f"{kind}: {entry['title']} ({entry['quant']}, около {entry['size_gb']} ГБ)")
            rb.setChecked(is_heavy)
            rb.toggled.connect(lambda on, e=entry: on and self._choose_model(e, builtin))
            group.addButton(rb)
            v.addWidget(rb)
            hint = QLabel(i18n.t(entry.get("hint") or entry["note"]))
            hint.setObjectName("sub")
            hint.setWordWrap(True)
            hint.setContentsMargins(24, 0, 0, 8)
            v.addWidget(hint)
        if not builtin:
            tail = QLabel(i18n.t("Модель скачается через Ollama после установки: ⚙ Настройки → Модели."))
            tail.setObjectName("hint")
            tail.setWordWrap(True)
            v.addWidget(tail)
        self._choose_model(heavy, builtin)
        return box

    def _choose_model(self, entry, builtin):
        if builtin:
            self.model_entry, self.ollama_model = entry, None
        else:
            self.model_entry, self.ollama_model = None, entry["id"]

    def _page_install(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.status = QLabel(i18n.t("Готовлюсь…"))
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        self.dl = QLabel("")                                   # счётчик скачивания модели: всегда виден, пока качается
        self.dl.setObjectName("sub")
        self.dl.setWordWrap(True)
        self.dl.setVisible(False)
        self.talk = QLabel("")                                 # Mico рассказывает о себе
        self.talk.setObjectName("sub")
        self.talk.setWordWrap(True)
        self.talk.setMinimumHeight(56)
        self._talk_order = list(range(len(FACTS)))
        random.shuffle(self._talk_order)                       # каждый раз в другом порядке
        self._talk_i = 0
        self._talk_timer = QTimer(self)
        self._talk_timer.setInterval(FACT_MS)
        self._talk_timer.timeout.connect(self._say_next)
        return column(self._title("Устанавливаю"), 18, self.percent, 12, self.bar, 8, self.dl, 14, self.status, 8, self.talk)

    def _say_next(self):
        """Следующий факт о Mico AI: текст и лицо меняются вместе."""
        text, mood = FACTS[self._talk_order[self._talk_i % len(FACTS)]]
        self._talk_i += 1
        self.talk.setText(i18n.t(text))
        self.avatar.set_mood(mood)

    def _page_finish(self):
        self.run_cb = WrapCheck(i18n.t("Запустить Mico AI"))
        self.run_cb.setChecked(True)
        return column(self._title("Готово"), 10,
                      self._sub("Mico AI установлен и готов к работе."), 20,
                      self.run_cb)

    # ---------- переходы ----------
    def _go(self, i):
        self.pages.setCurrentIndex(i)
        self.step_lbl.set_current(i)
        self.back_b.setVisible(i == 1)
        self.next_b.setText({0: i18n.t("Далее"), 1: i18n.t("Установить"), 2: "…", 3: i18n.t("Закрыть")}[i])
        self.next_b.setEnabled(i != 2)
        self.cancel_b.setVisible(i != 3)
        self.avatar.set_mood(self.PAGE_MOOD[i])

    def _next(self):
        i = self.pages.currentIndex()
        if i == 0:
            self._go(1)
        elif i == 1:
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
        anim.valueChanged.connect(show)
        if after is not None:
            anim.finished.connect(after)
        self._bar_anim = anim
        anim.start()

    def _fade_pages(self):
        """Смена страницы: содержимое плавно проявляется, а не появляется рывком."""
        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(340)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: effect.setOpacity(float(v)))
        anim.finished.connect(lambda: self.pages.setGraphicsEffect(None))   # без эффекта текст чёткий
        self._fade_anim = anim
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
    import autostart
    os.makedirs(INSTALL_DIR, exist_ok=True)
    report(0)
    shutil.copy2(sys.executable, INSTALL_EXE)
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
    entry = getattr(wizard, "model_entry", None)             # модель под память ПК, если встроенный движок есть
    _save_settings(auto_on, model_entry=entry, ollama_model=getattr(wizard, "ollama_model", None))               # записываем то, что реально получилось, а не то, что выбрали
    if entry is not None and getattr(wizard, "opt_model", None) is not None and wizard.opt_model.isChecked():
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
            vision = _vision_entry_for(entry)
            if vision is not None:                           # модель для экрана — тоже без Ollama, с полоской
                _download_model(vision, make_show(92, 99, vision["title"]), retries=2, timeout=15)
    else:
        report(5)


def _builtin_entry():
    """Модель под память этого ПК для встроенного движка (без Ollama). None — движок не установлен."""
    try:
        import local_llm, model_catalog
        if not local_llm.available():
            return None
        import psutil
        return model_catalog.recommend(psutil.virtual_memory().total / (1024 ** 3))
    except Exception:
        return None


def _vision_entry_for(text_entry):
    """Модель для экрана под эту машину; None — не нужна (памяти мало)."""
    try:
        import model_catalog, psutil
        return model_catalog.recommend_vision(psutil.virtual_memory().total / (1024 ** 3))
    except Exception:
        return None


def _download_model(entry, show=None, retries=3, timeout=30):
    """Скачивает модель из каталога. True — файл на месте. Ошибка сети не валит установку.
    show(скачано_байт, всего_байт) — вызывается с прогрессом, чтобы окно не висело молча."""
    try:
        import model_store
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
    import winctl
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


def _register_uninstall():
    """Регистрирует Mico AI в «Параметры → Приложения», чтобы его можно было удалить штатным способом."""
    import winreg
    uninstall_cmd = f'"{INSTALL_EXE}" --uninstall'          # удаление через наш мастер, а не консольный скрипт
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE)
    values = {"DisplayName": "Mico AI", "DisplayVersion": _version(), "Publisher": "Mico AI",
              "InstallLocation": INSTALL_DIR,
              "DisplayIcon": ICON_PATH if os.path.exists(ICON_PATH) else INSTALL_EXE,
              "UninstallString": uninstall_cmd}
    for name, value in values.items():
        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, value)
    winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(k)


def refresh_uninstall_entry():
    """Старые установки прописывали удаление консольным скриптом (remove_mico.cmd). При каждом запуске
    установленного Mico AI запись в «Приложениях» приводится к мастеру, а старый скрипт удаляется."""
    if not FROZEN or os.path.normcase(sys.executable) != os.path.normcase(INSTALL_EXE):
        return
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
    if os.path.exists(REMOVER_PATH):
        try:
            os.remove(REMOVER_PATH)
        except OSError:
            pass


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


def _ollama_present():
    local = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if os.path.exists(local) or shutil.which("ollama"):
        return True
    try:
        import requests
        return requests.get("http://127.0.0.1:11434/api/tags", timeout=1).ok
    except Exception:
        return False


def _save_settings(autostart_on, model_entry=None, ollama_model=None):
    """Минимальные настройки для первого запуска. Остальное — значения по умолчанию в программе."""
    os.makedirs(APPDIR, exist_ok=True)
    path = os.path.join(APPDIR, "config.json")
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    import version
    cfg.update(autostart=autostart_on, greet_on_start=True, update_channel=version.BUILD_CHANNEL,
               language=i18n.LANG)                # язык, выбранный в мастере, становится языком программы
    if model_entry is not None:                   # встроенный движок: ответы без Ollama, модель под память ПК
        cfg.update(llm_backend="builtin", text_model=model_entry["id"])
    elif ollama_model:                            # Ollama: модель, которую выбрал человек, докачивается в настройках
        cfg.update(llm_backend="ollama", text_model=ollama_model)
    cfg.setdefault("last_version", _version())            # не показывать «что нового» сразу после установки
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _version():
    import version
    return version.APP_VERSION


# ============================ Мастер установки ============================
def pick_language(default):
    """Окно выбора языка перед мастером: English или Русский. Возвращает код языка или None, если закрыли окно."""
    dlg = QDialog()
    dlg.setObjectName("wizard")
    dlg.setWindowTitle("Mico AI")
    dlg.setFixedSize(420, 220)
    dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    dlg.setWindowIcon(QIcon(_asset("mico.ico") or ""))
    dlg.setStyleSheet(qss())
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(36, 34, 36, 30)
    title = QLabel("Choose your language")
    title.setObjectName("title")
    lay.addWidget(title)
    lay.addWidget(QLabel("Выберите язык"))
    lay.addSpacing(22)
    row = QHBoxLayout()
    chosen = {"code": None}
    for code, label in (("en", "English"), ("ru", "Русский")):
        b = QPushButton(label)
        if code == default:
            b.setObjectName("primary")       # язык, который уже выбран в программе, подсвечен
        b.clicked.connect(lambda _=False, c=code: (chosen.update(code=c), dlg.accept()))
        row.addWidget(b)
    lay.addLayout(row)
    dlg.exec()
    return chosen["code"]


def run():
    """Мастер установки. Возвращает после закрытия; установленная копия запускается сама."""
    code = pick_language("en")               # сначала выбор языка, потом весь мастер на нём
    if not code:
        return
    i18n.set_language(code)
    dlg = Wizard()
    dlg.exec()


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


def _mico_ollama_models():
    """Модели, которые Mico AI использует (из его настроек). Удаляются только по галочке: их могут брать другие программы."""
    names = []
    try:
        with open(os.path.join(APPDIR, "config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("text_model", "vision_model"):
            name = cfg.get(key)
            if name and name not in names:
                names.append(name)
    except Exception:
        pass
    return names


class _Remover(QThread):
    """Шаги удаления, которые можно сделать, пока Mico AI работает. Файлы программы и данных удаляет отдельный скрипт после выхода."""
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str)

    def __init__(self, choices, ollama_names):
        super().__init__()
        self.choices = choices
        self.ollama_names = ollama_names
        self.errors = []          # понятные сообщения о том, что не удалось
        self.failed = set()       # ключи шагов, которые не выполнились: такие не попадают в «удалено»

    def _steps(self):
        steps = []
        if self.choices.get("autostart"):
            steps.append(("autostart", "Снимаю автозапуск", self._autostart))
        if self.choices.get("shortcut"):
            steps.append(("shortcut", "Удаляю ярлык на рабочем столе", self._shortcut))
        if self.choices.get("ollama") and self.ollama_names:
            steps.append(("ollama", "Удаляю модели Mico AI", self._ollama))
        steps.append(("program", "Убираю запись из «Приложений» Windows", _unregister_uninstall))
        return steps

    def _autostart(self):
        import autostart
        autostart.remove()

    def _shortcut(self):
        _desktop_shortcut(create=False)

    def _ollama(self):
        bad = []
        for name in self.ollama_names:
            try:
                r = subprocess.run(["ollama", "rm", name], capture_output=True, timeout=180,
                                   creationflags=_NOWIN)
                if r.returncode != 0:
                    bad.append(name)
            except FileNotFoundError:
                raise RuntimeError(i18n.t("Движок не найден, модели не тронуты"))
            except Exception:
                bad.append(name)
        if bad:
            raise RuntimeError(i18n.t("не удалось удалить {names}").format(names=", ".join(bad)))

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


class Uninstaller(QDialog):
    """Мастер удаления в стиле установщика: сначала выбор, что удалить, потом плавный прогресс и итог."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.removed = False
        self.worker = None
        self.ollama_names = _mico_ollama_models()
        self.setObjectName("wizard")
        self.setWindowTitle(i18n.t("Удаление Mico AI"))
        self.setFixedSize(700, 480)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(qss())
        if theme.mica_supported():
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(230)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 36)
        sv.addStretch()
        self.avatar = MicoAvatar("worried")
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("Mico AI")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sv.addWidget(self.avatar)
        sv.addSpacing(10)
        sv.addWidget(brand)
        sv.addStretch()
        root.addWidget(side)

        right = QVBoxLayout()
        right.setContentsMargins(40, 34, 40, 30)
        right.setSpacing(0)
        self.step_lbl = StepDots(3)                      # точки шагов: выбор, прогресс, итог
        right.addWidget(self.step_lbl)
        right.addSpacing(22)
        right.addSpacing(10)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._page_choose())
        self.pages.addWidget(self._page_progress())
        self.pages.addWidget(self._page_done())
        right.addWidget(self.pages, 1)

        row = QHBoxLayout()
        self.cancel_b = QPushButton(i18n.t("Отмена"))
        self.cancel_b.clicked.connect(self.reject)
        self.next_b = QPushButton(i18n.t("Удалить"))
        self.next_b.setObjectName("primary")
        self.next_b.clicked.connect(self._start)
        row.addWidget(self.cancel_b)
        row.addStretch()
        row.addWidget(self.next_b)
        right.addLayout(row)
        self.btn_row_widget = row
        root.addLayout(right, 1)
        self._go(0)

    # ---------- страницы ----------
    def _choice(self, key, title, hint, checked):
        box = WrapCheck(i18n.t(title))
        box.setChecked(checked)
        self.choices[key] = box
        hint_lbl = QLabel(i18n.t(hint))
        hint_lbl.setObjectName("sub")
        hint_lbl.setWordWrap(True)
        hint_lbl.setContentsMargins(0, 0, 0, 6)     # подсказка под подписью: галочки больше нет, отступ не нужен
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
            theme.apply_mica(self)

    def _page_choose(self):
        self.choices = {}
        items = [self._title("Удалить Mico AI?"), 6,
                 self._sub("Программу удалим в любом случае. Остальное выбираешь сам."), 14]
        items.append(self._choice("shortcut", "Ярлык на рабочем столе",
                                  "Запись в «Приложениях» Windows удалится в любом случае.", True))
        items.append(self._choice("autostart", "Автозапуск с Windows",
                                  "Mico AI перестанет запускаться при входе в систему.", True))
        items.append(self._choice("data", "История, настройки и напоминания",
                                  "Чат, память и напоминания. Оставь, если переустановишь Mico AI с прежними данными.",
                                  False))
        if self.ollama_names:
            items.append(self._choice("ollama", "Модели, которые скачал Mico AI",
                                      "Их могут использовать другие программы. Удаление освобождает место на диске.",
                                      False))
        size = _dir_size_mb(INSTALL_DIR) if os.path.isdir(INSTALL_DIR) else 0
        size_lbl = self._sub("Программа Mico AI · {size} МБ")
        size_lbl.setText(size_lbl.text().format(size=size))
        items += [14, size_lbl]
        return column(*items)

    def _page_progress(self):
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.status = QLabel(i18n.t("Готовлюсь…"))
        self.status.setObjectName("sub")
        self.status.setWordWrap(True)
        return column(self._title("Удаляю"), 18, self.percent, 12, self.bar, 14, self.status)

    def _page_done(self):
        self.done_text = QLabel("")
        self.done_text.setObjectName("sub")
        self.done_text.setWordWrap(True)
        return column(self._title("Mico AI удалён"), 10, self.done_text)

    def _title(self, text):
        t = QLabel(i18n.t(text))
        t.setObjectName("title")
        return t

    def _sub(self, text):
        s = QLabel(i18n.t(text))
        s.setObjectName("sub")
        s.setWordWrap(True)
        return s

    # ---------- переходы ----------
    def _go(self, i):
        self.pages.setCurrentIndex(i)
        self.step_lbl.set_current(i)
        self.cancel_b.setVisible(i == 0)
        self.next_b.setVisible(i != 2)
        self.next_b.setText({0: i18n.t("Удалить"), 1: "…"}[i] if i != 2 else "")
        self.next_b.setEnabled(i != 1)
        self.avatar.set_mood({0: "worried", 1: "sad", 2: "sad"}[i])     # при удалении Mico грустит

    def _fade_pages(self):
        effect = QGraphicsOpacityEffect(self.pages)
        self.pages.setGraphicsEffect(effect)
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(340)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.valueChanged.connect(lambda v: effect.setOpacity(float(v)))
        anim.finished.connect(lambda: self.pages.setGraphicsEffect(None))
        self._fade_anim = anim
        anim.start()

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
        self.worker = _Remover(picked, self.ollama_names if picked.get("ollama") else [])
        self.worker.progress.connect(self._on_progress)
        self.worker.done.connect(self._on_done)
        self.worker.start()

    def _on_progress(self, pct, text):
        self.status.setText(text)
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
        if picked.get("ollama") and "ollama" not in failed:
            removed.append("модели Mico AI")
        kept = []
        if not picked.get("data"):
            kept.append("история и настройки в папке Mico AI (AppData)")
        if not picked.get("ollama") and self.ollama_names:
            kept.append("модели Mico AI")
        text = i18n.t("Удалено") + ": " + ", ".join(i18n.t(x) for x in removed) + "."
        if kept:
            text += "\n\n" + i18n.t("Осталось по твоему выбору") + ": " + ", ".join(i18n.t(x) for x in kept) + "."
        if self.worker and self.worker.errors:
            text += ("\n\n" + i18n.t("Не получилось") + ": " + "; ".join(self.worker.errors) + ". "
                     + i18n.t("Можно повторить позже."))
        self.done_text.setText(text)
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
    previous = i18n.LANG
    code = pick_language(previous)
    if not code:
        return False
    i18n.set_language(code)                  # мастер удаления на выбранном языке; язык запущенной программы вернём после
    try:
        dlg = Uninstaller(app)
        dlg.exec()
        return dlg.removed
    finally:
        i18n.set_language(previous)


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
    subprocess.Popen(["cmd", "/c", script], creationflags=_NOWIN | _DETACHED)     # без окна, отдельно
