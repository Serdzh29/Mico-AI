"""Mico AI — локальный ИИ-компаньон для Windows 11. Запуск: python main.py"""
import sys as _sys, os as _os, traceback as _tb


def _log_crash(exc_type, exc, tb):
    """Любая необработанная ошибка пишется в %APPDATA%\\Mico\\crash.log — даже если окно не открылось."""
    text = "".join(_tb.format_exception(exc_type, exc, tb))
    try:
        folder = _os.path.join(_os.environ.get("APPDATA", _os.path.expanduser("~")), "Mico")
        _os.makedirs(folder, exist_ok=True)
        with open(_os.path.join(folder, "crash.log"), "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except OSError:
        pass
    _sys.__excepthook__(exc_type, exc, tb)


_sys.excepthook = _log_crash


def _mico_dir():
    folder = _os.path.join(_os.environ.get("APPDATA", _os.path.expanduser("~")), "Mico")
    _os.makedirs(folder, exist_ok=True)
    return folder


def _stage(name):
    """Метка этапа запуска: в startup.log видно, на каком шаге программа упала."""
    try:
        with open(_os.path.join(_mico_dir(), "startup.log"), "a", encoding="utf-8") as f:
            f.write(f"{_time_now()} {name}\n")
    except OSError:
        pass


def _time_now():
    import time as _t
    return _t.strftime("%Y-%m-%d %H:%M:%S")


# нативные сбои (нарушение доступа и т.п.) тоже попадают в журнал
try:
    import faulthandler as _fh
    _native = open(_os.path.join(_mico_dir(), "native_crash.log"), "a", encoding="utf-8")
    _fh.enable(file=_native, all_threads=True)
except Exception:
    pass
_stage("модуль main загружен")
import html, json, os, subprocess, sys, threading, time, webbrowser
from types import SimpleNamespace
from urllib.parse import unquote
from PyQt6.QtCore import QRectF, QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTime, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QAction, QColor, QGuiApplication, QIcon, QImage
from PyQt6.QtWidgets import (QProgressBar, QAbstractButton, QAbstractButton, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QTabWidget, QTextBrowser, QTimeEdit, QToolButton, QVBoxLayout, QWidget)
import psutil
import actions, autostart, errwatch, i18n, sidetabs, subpages, intel, intel_ui, phrase, settings_info, sleep_island, clipbuf, schedule, menu_items, features, capabilities, chips, commands, custom, greeting, hotkeys, breaks, reminders, sleepmode, theme, updatecheck, version, windows_info
import winctl as W
from actions import Reply
from blob import Blob
from brain import SUGGEST_TEXT, SUGGEST_VISION, VISION_MODEL, Brain, is_vision_model, list_models, pull_model, delete_model as delete_ollama_model
from emotions import detect_emotion
from follow import WindowWatcher
from storage import APPDIR, Store
from tracker import Tracker, idle_seconds

SEARCH_ENGINES = {"Google": "https://www.google.com/search?q=", "Яндекс": "https://yandex.ru/search/?text=",
                  "Bing": "https://www.bing.com/search?q=", "DuckDuckGo": "https://duckduckgo.com/?q="}

DEFAULTS = {
    "color": "#FFCFA3", "scale": 1.0, "opacity": 1.0, "chat_opacity": 1.0,
    "text_model": "qwen2.5:7b", "vision_model": "qwen2.5vl:7b", "retention_days": 30,
    "greet_on_start": True, "autostart": False, "language": "ru",
    "theme": "auto",                      # auto — как в Windows | light | dark
    "assist_style": "classic",            # classic — Mico AI в углу | intelligence — внизу по центру, с подсветкой экрана
    "placement": "manual",                # manual — стоит, где поставил мышкой | tl/tr/bl/br — всегда в этом углу экрана
    "chips_mode": "auto", "chips_count": 6, "chips_pinned": [], "chip_usage": {},   # кнопки под чатом
    "chips_hide_on_send": True,
    "wave_opacity": 85,
    "chat_linked": True, "chat_scale": 1.0, "chat_ratio": 1.0,   # чат меняется вместе с Mico AI или отдельным ползунком
    "chat_outline": True,                 # обводка вокруг окна чата
    "button_glow": True,                  # подсветка кнопок акцентным цветом при наведении (чат, быстрые действия)
    "wi_input_outline": True,             # обводка поля ввода в чате Mico AI
    "city": "", "loc_consent": None,      # город для погоды; None — ещё не спрашивали про геопозицию
    "weather_on": True, "memory_on": True,
    "hotkey_chat": "f8",           # глобальная клавиша: F8 открывает чат из любого окна (нужен перезапуск)
    "hotkey_screen": "ctrl+alt+s", "hotkey_window": "ctrl+alt+h",   # только для Mico AI (нужен перезапуск)
    "wi_thickness": intel.THICK_DEFAULT, "wi_waves": True, "wi_glow_style": intel.GLOW_DEFAULT,
    "anim_sleep_fps": 60,                 # частота анимации Mico AI во сне, кадров в секунду (выбирается в настройках)
    "wi_wave_height": intel.WAVE_HEIGHT_DEFAULT, "wi_edge_width": intel.EDGE_W_DEFAULT,
    "wi_draft": "",                         # черновик из чата Mico AI — восстанавливается при следующем открытии            # толщина полоски и волны при ответе (Mico AI)
    "wi_wave_source": "mico", "wi_wave_custom": intel.WAVE_DEFAULT_CUSTOM,   # откуда цвет волн: Mico AI, действие, свой, набор
    "wi_wave_theme": intel.WAVE_THEME_DEFAULT,                 # готовый набор волн (если выбран «Готовый набор»)
    "wi_quiet_on": False, "wi_quiet_from": "23:00", "wi_quiet_to": "08:00", "wi_load_bar": False,   # тихий час, загрузка (Mico AI)
    "wi_clip_help": True, "wi_error_help": True,            # помощник по буферу и реакция на ошибки (Mico AI)
    "wi_colors": dict(intel.DEFAULT_COLORS),   # цвет полоски для каждого действия Mico AI; у действий цвета не совпадают
    "proactive_breaks": True, "proactive_break_min": 60,   # напоминание о перерыве
    "quiet_mode": False,                  # режим тишины
    "workspace": {},                     # рабочее место (бета): запомненные программы
    "update_check": True, "update_checked_at": 0,   # проверка новой версии раз в сутки (только сообщает)
    "custom_phrases": [],                          # свои фразы-команды: [{"say": "...", "do": "...; ..."}]
    "greet_items": ["recap", "weather"],           # что показывать при входе (до 3), см. greeting.py
    "sleep_after_min": 3,                          # через сколько минут без внимания Mico AI засыпает (0 — не засыпать)
    "sleep_corner": "br",                          # угол экрана, где Mico AI спит (tl/tr/bl/br)
    "search_url": SEARCH_ENGINES["Google"],
    "block_processes": ["keepass", "bitwarden", "1password", "lastpass", "dashlane"],
    "block_titles": ["inprivate", "incognito", "инкогнито", "private browsing", "пароль", "password", "банк", "bank"],
}
CFG_PATH = os.path.join(APPDIR, "config.json")


def load_cfg():
    cfg = dict(DEFAULTS)
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    if cfg.get("hotkey_chat") == "ctrl+alt+m":  # старое значение по умолчанию -> одна клавиша F8
        cfg["hotkey_chat"] = "f8"
    cfg["placement"], cfg["sleep_corner"] = "manual", "br"   # положение и угол сна — не настраиваются
    cfg["hotkey_chat"] = "f8"                                # клавиша фиксированная: чат — F8
    if cfg.get("vision_model") not in SUGGEST_VISION:        # выбранная в настройках модель для экрана сохраняется
        cfg["vision_model"] = VISION_MODEL
    if cfg["color"].upper() == "#FFC94A":      # старый жёлтый -> новый персиковый
        cfg["color"] = DEFAULTS["color"]
    return cfg


def save_cfg(cfg):
    """Сначала собираем текст целиком: если что-то не сериализуется, файл не трогаем.
    Пишем прямо в config.json, без переименования: на Windows переименование часто мешает
    антивирус или индексатор, который держит файл открытым, и настройки не сохранялись."""
    text = json.dumps(cfg, ensure_ascii=False, indent=2)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        f.write(text)


PID_FILE = os.path.join(APPDIR, "mico.pid")


def hello(now=None):
    """Приветствие при запуске: утро, день, вечер или ночь — с эмодзи и восклицанием."""
    import phrase
    return phrase.greeting_text(now)


def _alive_instance():
    """Был ли Mico AI уже запущен (например, разблокировали экран) — тогда не здороваемся заново."""
    try:
        pid = int(open(PID_FILE, encoding="utf-8").read().strip())
    except (OSError, ValueError):
        return False
    if pid == os.getpid():
        return False
    try:
        name = psutil.Process(pid).name().lower()
        return psutil.pid_exists(pid) and ("python" in name or "mico" in name)     # python или собранный Mico.exe
    except psutil.Error:
        return False


# =============================== Диалоги ===============================
def _confirm_wipe(store):
    """Историю удаляем только после явного «Удалить»: отменить это нельзя, поэтому по умолчанию — «Отмена»."""
    b = QMessageBox(QMessageBox.Icon.Warning, "Удалить всю историю?",
                    "Вся история Mico AI будет удалена без возможности восстановить. Продолжить?")
    yes = b.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
    no = b.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    b.setDefaultButton(no)
    b.exec()
    if b.clickedButton() is yes:
        store.wipe()


def _box(icon, title, text, yes="OK", no=None):
    """Модальное окошко поверх всех окон. Возвращает True, если нажата кнопка «yes»."""
    b = QMessageBox(icon, title, text)
    b.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    ybtn = b.addButton(yes, QMessageBox.ButtonRole.AcceptRole)
    if no:
        b.addButton(no, QMessageBox.ButtonRole.RejectRole)
    b.exec()
    return b.clickedButton() is ybtn


# =============================== Чат под Mico AI ===============================
class ChatLog(QTextBrowser):
    """Текст чата. Если человек сам крутит колёсиком, плавная прокрутка Mico AI останавливается."""
    user_scrolled = pyqtSignal()

    def wheelEvent(self, e):
        self.user_scrolled.emit()
        super().wheelEvent(e)


BREAK_MARK = "__break__"             # метка: это напоминание о перерыве, а не наблюдение за экраном


class Panel(QWidget):
    answered = pyqtSignal(object)
    reminder = pyqtSignal(str)
    initiative = pyqtSignal(object)   # напоминание о перерыве: (текст, метка)
    busy_changed = pyqtSignal(bool)   # Mico AI начал или закончил думать над запросом
    chat_shown = pyqtSignal(bool)     # чат открыли или закрыли (нужно режиму Windows Intelligence)
    answer_text = pyqtSignal(str)     # текст ответа (для строки над Mico AI в режиме Windows Intelligence)
    user_sent = pyqtSignal(str)       # вопрос ушёл Mico AI (в чат Windows Intelligence)
    mico_said = pyqtSignal(str)       # Mico AI написал текст в обычный чат (для чата Windows Intelligence)

    def __init__(self, brain, blob, cfg):
        super().__init__()
        self.brain, self.blob, self.cfg = brain, blob, cfg
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        card = QFrame(self)
        card.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(card)
        lay = QVBoxLayout(card)
        self.log = ChatLog()
        self.log.setOpenLinks(False)
        self.log.anchorClicked.connect(self.on_link)
        self.log.user_scrolled.connect(self._stop_follow)
        lay.addWidget(self.log)
        self.grid = QGridLayout()
        self.chips_box = QWidget()                 # ряд кнопок целиком — его можно скрыть или убрать
        self.chips_box.setLayout(self.grid)
        lay.addWidget(self.chips_box)
        self.last_pair = None                     # последний вопрос и ответ — для «короче» и «подробнее»
        row = QHBoxLayout()
        self.inp = ChatInput()
        self.inp.setPlaceholderText("Напиши Mico AI…")
        self.inp.focused.connect(self._on_input_focus)
        send_btn = QPushButton("➤")
        send_btn.setFixedWidth(36)
        row.addWidget(self.inp)
        row.addWidget(send_btn)
        lay.addLayout(row)
        self.inp.returnPressed.connect(lambda: self.submit(self.inp.text()))
        send_btn.clicked.connect(lambda: self.submit(self.inp.text()))
        self.inp.textChanged.connect(self._typed)
        self.queue, self.pending, self.busy = [], "", False
        self.intel = None                 # режим Windows Intelligence (подключается в main)
        self.timer = QTimer(self)
        self.answered.connect(self.on_answer)
        self.reminder.connect(self.on_reminder)
        self.initiative.connect(self.on_initiative)
        self._anim = None
        self._scroll_anim = None                 # плавная прокрутка чата
        self._chips_hidden = False               # кнопки скрыты после отправки запроса
        self.refresh_chips()
        self.apply_size()

    def _on_input_focus(self):
        """Поле ввода снова активно: если кнопки скрыли после отправки, возвращаем их."""
        if self._chips_hidden:
            self._chips_hidden = False
            self.refresh_chips()

    def refresh_chips(self):
        """Кнопки под чатом: в авто-режиме каждый раз свой набор, в ручном — выбранные."""
        while self.grid.count():
            it = self.grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i, c in enumerate(chips.pick(self.cfg)):
            text = c.label if len(c.label) <= 20 else c.label[:19] + "…"     # полное имя — в подсказке
            b = QPushButton(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(f"{c.label} — «{c.phrase.strip()}»")
            b.clicked.connect(lambda _, c=c: self.submit(c.phrase) if c.send else self.prefill(c.phrase))
            self.grid.addWidget(b, i // 3, i % 3)
        self.chips_box.setVisible(bool(chips.pick(self.cfg)) and not self._chips_hidden)

    def _target_opacity(self):
        """Прозрачность окна чата — по ползунку «Прозрачность чатов»."""
        return intel.chat_opacity(getattr(self, "cfg", {}))

    def _fade(self, show):
        if self._anim is not None:
            self._anim.stop()
        a = QPropertyAnimation(self, b"windowOpacity", self)
        a.setDuration(200 if show else 160)
        a.setStartValue(0.0 if show else 1.0)
        a.setEndValue(self._target_opacity() if show else 0.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)
        if not show:
            a.finished.connect(lambda: (self.hide(), self.setWindowOpacity(intel.chat_opacity(getattr(self, "cfg", {})))))
        self._anim = a
        a.start()

    def hide_smooth(self):
        if self.isVisible():
            self.chat_shown.emit(False)
            self._fade(False)

    def chat_factor(self):
        """Во сколько раз чат больше/меньше базового размера: вместе с Mico AI или отдельным ползунком."""
        if self.cfg.get("chat_linked", True):
            return max(0.6, self.cfg.get("scale", 1.0))     # вместе с Mico AI: тот же размер, что у Mico AI
        return max(0.6, self.cfg.get("chat_scale", 1.0))

    def apply_size(self):
        k = self.chat_factor()
        self.setFixedSize(round(360 * k), round(430 * k))
        self.theme()
        if self.isVisible():
            self.keep_on_screen()                   # не переставляем чат заново: он не должен прыгать при настройках

    def keep_on_screen(self):
        """Удерживает чат на экране, не меняя его положения, если он уже в пределах экрана."""
        scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = min(max(self.x(), g.left()), g.right() - self.width())
        y = min(max(self.y(), g.top()), g.bottom() - self.height())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def _typed(self, _):
        if self.queue:                                 # человек начал печатать — не дочитываем ответ
            self.queue.clear()
            self.blob.talking = False
        self.blob.notify_typing()                   # Mico AI смотрит на строку ввода и интересуется
        self.blob.set_mood("curious", 3)
        self.blob.set_look(self.inp.mapToGlobal(self.inp.rect().center()))

    def theme(self):
        dark = theme.is_dark(self.cfg)
        self.setStyleSheet(theme.panel_qss(self.cfg["color"], dark, self.cfg.get("chat_outline", True),
                                           self.chat_factor(), glow=intel.glow_on(self.cfg)))
        self.log.document().setDefaultStyleSheet(theme.LINK_DARK if dark else theme.LINK_LIGHT)

    # ----- позиция и показ -----
    def reposition(self):
        b = self.blob
        scr = QGuiApplication.screenAt(b.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = b.x() + b.width() // 2 - self.width() // 2
        y = b.y() + int(b.height() * 0.80)
        if y + self.height() > g.bottom():
            y = b.y() + int(b.height() * 0.22) - self.height()
        nx, ny = max(g.left(), min(x, g.right() - self.width())), max(g.top(), y)
        if nx != self.x() or ny != self.y():             # без лишних перемещений окна
            self.move(nx, ny)

    def show_near(self, activate=True):
        if self.intel and self.intel.on():          # в Windows Intelligence открывается свой чат, не этот
            self.intel.show_wichat(activate)
            return
        self.blob.touch()
        if self.blob.asleep:                        # чат открывают — Mico AI просыпается, но не повторяет «woke»
            self.blob.wake(silent=True)
        """activate=False — показать, не забирая фокус у приложения пользователя (для напоминаний и подсказок)."""
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not activate)
        if not self.isVisible():                    # положение считаем только при открытии, чтобы чат не прыгал
            self.refresh_chips()
            self.setWindowOpacity(0.0)
            self.reposition()
        self.show()
        self.chat_shown.emit(True)
        self.raise_()
        if self.windowOpacity() < self._target_opacity():
            self._fade(True)
        if activate:
            self.activateWindow()
            self.inp.setFocus()

    def toggle(self):
        if self.intel and self.intel.on():
            self.intel.toggle_wichat()
            return
        self.hide_smooth() if self.isVisible() else self.show_near()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.hide_smooth()
        super().keyPressEvent(e)

    def prefill(self, text):
        self.inp.setText(text)
        self.inp.setFocus()

    # ----- отправка -----
    def submit(self, q):
        self.blob.touch()
        q = q.strip()
        if not q or self.busy:
            return
        if self.cfg.get("chips_hide_on_send", True):      # кнопки скрыты, пока не нажмут в поле ввода
            self._chips_hidden = True
            self.chips_box.setVisible(False)
        self.last_pair = {"q": q, "a": ""}
        self.inp.clear()
        self.log.append(f"<p align='right'><b>Вы:</b> {html.escape(q)}</p>")
        self.user_sent.emit(q)
        self.busy = True
        self.busy_changed.emit(True)
        m = detect_emotion(q)                       # Mico AI реагирует на настроение сообщения
        if m and m != "curious":
            self.blob.set_mood(m, 1.2)
            QTimer.singleShot(1250, lambda: self.busy and self.blob.set_mood("thinking"))
        else:
            self.blob.set_mood("thinking")
        if self.brain.is_screenshot(q):
            self.blob.hide()
            self.hide()
        self._run(q)

    def _run(self, q):
        shot = self.brain.is_screenshot(q)

        def work():
            try:
                if shot:
                    time.sleep(0.45)                # дать Mico AI и чату исчезнуть с экрана
                self.answered.emit(self.brain.ask(q))
            except Exception as e:
                self.answered.emit(Reply(f"Ой, что-то пошло не так: {e}", "worried"))
        threading.Thread(target=work, daemon=True).start()

    def explain(self, text):
        """Mico AI сам говорит пояснение в чате (без отдельных окон)."""
        self.show_near(activate=False)
        self.say(text)

    def show_html(self, html_text):
        """Показать готовый блок (знакомство, список возможностей) без вопроса пользователя."""
        self.queue.append(("html", html_text))
        self._pump()

    def on_answer(self, r):
        if r is None:                                           # модель ничего не вернула — не молчим
            r = Reply("Ответа нет. Попробуй сказать иначе.", "worried")
        self.busy = False
        self.busy_changed.emit(False)
        if not r.text and not r.html and not r.image:
            r = Reply("Ответа нет. Попробуй сказать иначе.", "worried")
        plain = r.text or intel.plain_from_html(r.html) if r.html else r.text
        if plain:
            self.answer_text.emit(plain)                        # Mico AI: строка над Mico AI, чат — для длинного
        self.blob.touch()
        if self.last_pair is not None:
            self.last_pair["a"] = r.text or "(ответ в виде карточек или списка)"
        if not self.blob.isVisible():
            self.blob.show()
            self.show_near()
        self.blob.set_mood(r.mood, 6)
        if r.mood in ("surprised", "happy", "love", "laugh"):
            self.blob.jump()
        if r.image:
            QGuiApplication.clipboard().setImage(QImage(r.image))
        if r.html:
            self.queue.append(("html", "<b>Mico AI:</b><br>" + r.html))
            self.queue.append(("wi", plain))                    # тот же ответ — текстом в чат Mico AI
        else:
            self.queue.append(("text", r.text))
        if r.image:
            self.queue.append(("html", f'<img src="{QUrl.fromLocalFile(r.image).toString()}" width="300">'))
        self._pump()

    def on_initiative(self, payload):
        """Mico AI сам что-то увидел и говорит первым — тихо, без захвата фокуса.
        Перерыв приходит с меткой BREAK_MARK. В режиме Mico AI — полоской по краю экрана."""
        text, mood = payload
        is_break = mood == BREAK_MARK
        if is_break:
            mood = "happy"
        if self.busy or self.inp.text():
            return
        if self.intel and self.intel.on():
            if is_break:
                self.intel.break_note(text)              # перед перерывом — сводка за последний час
            else:
                self.intel.notify(text, "watch")
            return
        if not self.blob.isVisible():
            self.blob.show()
        self.show_near(activate=False)
        self.blob.set_mood(mood or "curious", 6)
        self.blob.jump(120)
        self.say("👀 " + text)

    def on_reminder(self, text):
        QApplication.beep()
        if not self.blob.isVisible():
            self.blob.show()
        self.show_near(activate=False)
        self.blob.wake(silent=True)                 # уведомление будит спящего Mico AI, но чат сам не открывает
        self.blob.set_mood("surprised", 8)
        self.blob.jump()
        self.say("⏰ " + text[:1].upper() + text[1:])

    def on_link(self, url):
        scheme, _, rest = url.toString().partition(":")
        path = unquote(rest)
        try:
            if scheme == "mico-do":                 # нажали пример из списка возможностей — выполняем его
                self.submit(path)
            elif scheme == "mico-info":             # «?» у бета-функции — Mico AI объясняет в чате
                self.explain(features.explain(path))
            elif scheme == "mico-open":
                os.startfile(path)
            elif scheme == "mico-dir":
                subprocess.Popen(["explorer", f"/select,{path}"])
        except Exception:
            pass

    # ----- «печатающий» ответ: Mico AI говорит ртом -----
    def say(self, text):
        self.queue.append(("text", text))
        self._pump()

    def _pump(self):
        """Ответ появляется целиком. Чат прокручивается вниз: короткий — сразу, длинный — плавно, по мере ответа."""
        sb = self.log.verticalScrollBar()
        top = sb.maximum() + self.log.viewport().height()     # высота текста до ответа
        talk = 0
        while self.queue:
            kind, val = self.queue.pop(0)
            if kind == "html":
                self.log.append(val)
            elif kind == "wi":
                self.mico_said.emit(val)
            else:
                self.log.append("<b>Mico AI:</b><br>" + html.escape(val).replace("\n", "<br>") + "<br>")
                self.mico_said.emit(val)
                self.blob.talking = True
                talk = max(talk, min(12000, max(1500, 28 * len(val))))
                QTimer.singleShot(min(2500, 300 + 25 * len(val)), self._stop_talk)
        self._follow(top, talk)

    def _stop_talk(self):
        self.blob.talking = False

    def _follow(self, top, talk_ms):
        """top — высота текста до нового ответа. Ответ помещается в окно — чат быстро едет в конец.
        Не помещается — сначала показываем начало ответа, потом чат плавно спускается вниз."""
        def go():
            sb = self.log.verticalScrollBar()
            end = sb.maximum()                                   # конец текста (после layout)
            long_ = end > top                                    # ответ выше окна
            self._stop_follow()
            if long_:
                sb.setValue(int(top))                            # начало нового ответа — наверху окна
            a = QPropertyAnimation(sb, b"value", self)
            a.setDuration(int(talk_ms or 2000) if long_ else 250)
            a.setStartValue(sb.value())
            a.setEndValue(end)
            a.setEasingCurve(QEasingCurve.Type.Linear if long_ else QEasingCurve.Type.OutCubic)
            a.start()
            self._scroll_anim = a
        QTimer.singleShot(60, go)                                # даём Qt пересчитать высоту текста

    def _stop_follow(self):
        if self._scroll_anim is not None:
            self._scroll_anim.stop()
            self._scroll_anim = None

# =============================== Настройки ===============================
# Подсказки к настройкам: что это, стоит ли включать и когда
HELP = {
    "linked": ("Чат меняется вместе с Mico AI",
               "Один ползунок меняет размер и шара, и окна чата.",
               "включи, если хочешь всё крупнее или мельче сразу. Выключи, если нужен большой чат и маленький шар."),
    "outline": ("Обводка вокруг чата",
                "Цветная рамка вокруг окна чата. Только внешний вид.",
                "выключи для минималистичного вида, включи, чтобы чат был заметнее на фоне."),
    "locc": ("Геопозиция для погоды",
             "Windows отдаёт Mico AI координаты, чтобы узнать погоду в твоём месте.",
             "включи, если хочешь погоду без ввода города. Выключи — тогда укажи город вручную."),
    "greet": ("Здороваться при включении ПК",
              "При входе в Windows Mico AI говорит «Добрый день» или «Добрый вечер» и показывает пункты приветствия.",
              "включи, если приятно видеть приветствие. Выключи для тихого запуска."),
    "auto": ("Запуск с Windows",
             "Mico AI стартует сам при входе в Windows и после разблокировки экрана.",
             "включи, если пользуешься Mico AI каждый день. Выключи, если запускаешь его вручную."),
    "mem": ("Запоминать действия",
            "Mico AI записывает твои команды и открытые программы (зашифровано) и учится на привычках.",
            "включи для подсказок, кнопок и «что я делал». Выключи, если не хочешь записей: тогда эти функции не работают."),
    "pbr": ("Напоминание о перерыве",
            "Mico AI напомнит отдохнуть, если работаешь без остановки дольше заданного времени.",
            "включи, если забываешь делать перерывы."),
    "quiet": ("Режим тишины",
              "Mico AI не здоровается, не предлагает помощь и не заговаривает первым. Напоминания, которые ты сам поставил, работают.",
              "включи для созвона, фильма или работы без отвлечений. Выключи, когда хочешь живого компаньона."),
}


class NoWheelSlider(QSlider):
    """Колесо мыши листает окно настроек, а не меняет ползунок. Двигать ползунок можно мышью и клавишами."""
    def wheelEvent(self, e):
        e.ignore()


def with_readout(slider, suffix):
    """Ползунок и справа его значение («100 %»), чтобы не гадать по положению. Настройку сбрасывает сам ползунок."""
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    lbl = QLabel()
    lbl.setObjectName("readout")
    lbl.setMinimumWidth(52)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def show(_=None):
        lbl.setText(f"{slider.value()}{suffix}")
    show()
    slider.valueChanged.connect(show)
    lay.addWidget(slider, 1)
    lay.addWidget(lbl)
    box.inner, box.refresh = slider, show          # сюда смотрят «Сбросить» и обновление при смене диапазона
    return box


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, e):
        e.ignore()


class _OpenOnClick(QObject):
    """Нажатие на текст поля выбора открывает список, повторное — закрывает.
    Qt закрывает список сам при нажатии, поэтому помним момент закрытия и не открываем его обратно тем же кликом."""
    def __init__(self, combo):
        super().__init__(combo)
        self.combo = combo
        self._hidden_at = 0.0
        combo.view().installEventFilter(self)

    def eventFilter(self, obj, ev):
        import time
        if obj is self.combo.view():
            if ev.type() == QEvent.Type.Hide:
                self._hidden_at = time.monotonic()
            return False
        if ev.type() == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
            if self.combo.view().isVisible():
                self.combo.hidePopup()
            elif time.monotonic() - self._hidden_at > 0.3:
                self.combo.showPopup()
        return False


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, e):
        e.ignore()


class ChatInput(QLineEdit):
    """Поле ввода: при фокусе сообщает чату, что скрытые кнопки можно вернуть."""
    focused = pyqtSignal()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.focused.emit()


class AboutDialog(QDialog):
    """О программе: версия, канал и что нового в этой сборке."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.setWindowTitle("О программе Mico AI")
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        head = QLabel(f"<b style='font-size:16px'>Mico AI {version.display_version(cfg.get('update_channel', 'stable'))}</b>")
        head.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(head)
        entry = version.CHANGELOG.get(version.APP_VERSION, {})
        items = "".join(f"<li>{html.escape(c)}</li>" for c in entry.get("changes", [])) \
            or "<li>Исправления и мелкие улучшения.</li>"
        body = QTextBrowser()
        body.setHtml(f"<b>Что нового в этой сборке</b><ul>{items}</ul>")
        v.addWidget(body)
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        v.addWidget(close)


def _set_widget_value(w, value):
    """Ставит элементу значение по умолчанию. Сигналы срабатывают как обычно, поэтому эффект виден сразу."""
    if isinstance(w, (QCheckBox, WrapCheck)):
        w.setChecked(bool(value))
    elif isinstance(w, QComboBox):
        if w.isEditable():
            w.setCurrentText("" if value is None else str(value))
        else:
            i = w.findData(value)
            w.setCurrentIndex(i if i >= 0 else 0)
    elif isinstance(w, (QSpinBox, QSlider)):
        if value is not None:
            w.setValue(int(value))
    elif isinstance(w, QLineEdit):
        w.setText("" if value is None else str(value))


class ClickLabel(QLabel):
    """Подпись, по которой можно кликнуть: нажатие переключает галочку рядом."""
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


SETTINGS_SIZES = [("compact", "Компактное", (560, 600)), ("medium", "Обычное", (660, 740)),
                  ("large", "Просторное", (820, 880))]


class Switch(QAbstractButton):
    """Переключатель-пилюля: дорожка и белая кнопка. Включён — цвет акцента Windows."""
    ON = "#4cc2c4"
    OFF = "#4a4a4a"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(40, 22)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.ON if self.isChecked() else self.OFF))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), self.height() / 2, self.height() / 2)
        d = self.height() - 6
        x = self.width() - 3 - d if self.isChecked() else 3
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()


class Expander(QFrame):
    """Раскрывающийся блок: заголовок с подписью и стрелкой. По нажатию снизу открываются доп. настройки."""

    def __init__(self, title, subtitle="", body=None, open_=False, parent=None):
        super().__init__(parent)
        self.setObjectName("expander")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        head = _ExpHead()
        head.setCursor(Qt.CursorShape.PointingHandCursor)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 8, 4, 8)
        text = QVBoxLayout()
        text.setSpacing(1)
        t = QLabel(title)
        t.setObjectName("expTitle")
        text.addWidget(t)
        if subtitle:
            st = QLabel(subtitle)
            st.setObjectName("hint")
            st.setWordWrap(True)
            text.addWidget(st)
        hl.addLayout(text, 1)
        self._arrow = QLabel()
        self._arrow.setFixedSize(18, 18)
        hl.addWidget(self._arrow, 0, Qt.AlignmentFlag.AlignVCenter)
        self._body = QWidget()
        bl = QVBoxLayout(self._body)
        bl.setContentsMargins(0, 2, 0, 6)
        bl.setSpacing(4)
        if body is not None:
            bl.addWidget(body)
        self._body.setVisible(open_)
        head.clicked.connect(self.toggle)
        v.addWidget(head)
        v.addWidget(self._body)
        self._set_arrow(open_)

    def _set_arrow(self, opened):
        import uiicons
        self._arrow.setPixmap(uiicons.icon("chev_up" if opened else "chev_down", "#9a9a9a", 18).pixmap(18, 18))

    def toggle(self):
        self.setExpanded(not self._body.isVisible())

    def setExpanded(self, on):
        self._body.setVisible(bool(on))
        self._set_arrow(bool(on))

    def isExpanded(self):
        return self._body.isVisible()


class _ExpHead(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


class WrapCheck(QWidget):
    """Пункт настройки: подпись слева (переносится), переключатель справа. Интерфейс тот же, что у галочки."""
    toggled = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        self._sw = Switch()
        self._lbl = ClickLabel(text)
        self._lbl.setWordWrap(True)
        self._lbl.clicked.connect(self._sw.toggle)
        lay.addWidget(self._lbl, 1)
        lay.addWidget(self._sw, 0, Qt.AlignmentFlag.AlignVCenter)
        self._sw.toggled.connect(self.toggled)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def isChecked(self):
        return self._sw.isChecked()

    def setChecked(self, on):
        self._sw.setChecked(bool(on))

    def setToolTip(self, text):
        super().setToolTip(text)
        self._lbl.setToolTip(text)
        self._sw.setToolTip(text)

    def setText(self, text):
        self._lbl.setText(text)

    def text(self):
        return self._lbl.text()

class SettingsDialog(QDialog):
    status = pyqtSignal(str)
    pulled = pyqtSignal(str)
    pull_progress = pyqtSignal(int, int)   # скачано и всего байт; (0, 0) — скачивание закончилось
    deleted = pyqtSignal(str)              # модель Ollama удалена (имя)
    models_ready = pyqtSignal(object)      # список установленных моделей Ollama, посчитан в фоне

    def __init__(self, cfg, blob, panel, hooks, parent=None):
        super().__init__(parent)
        self.cfg, self.blob, self.panel, self.hooks, self.orig = cfg, blob, panel, hooks, dict(cfg)
        self.setWindowTitle("Настройки Mico AI")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(520, 420)
        self._apply_size("compact")                     # размер окна настроек фиксированный
        self._style_dialog()
        self._reg = {}                                  # ключ настройки → её элемент (для кнопки «Сбросить»)
        root = QVBoxLayout(self)
        # поиск по настройкам: набери слово — останутся только подходящие пункты
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Поиск по настройкам")
        self.search.setClearButtonEnabled(True)
        import uiicons as _ui
        self.search.addAction(_ui.icon("search", "#8e8e93", 16), QLineEdit.ActionPosition.LeadingPosition)
        root.addWidget(self.search)
        self.found_hint = QLabel("Ничего не нашлось. Попробуй другое слово.")
        self.found_hint.setObjectName("hint")
        self.found_hint.setVisible(False)
        root.addWidget(self.found_hint)
        self._vis = {}                                  # исходная видимость строк (чтобы поиск вернул всё как было)
        tabs = self._tabs = sidetabs.SideTabs()                    # разделы слева, содержимое справа
        tabs.set_icon_color("#8e8e93")
        tabs.set_accent(theme.windows_accent())
        root.addWidget(tabs)
        self.search.textChanged.connect(self._filter_settings)

        # --- Внешний вид ---
        look = QWidget()                              # Цвет и тема
        f = QFormLayout(look)
        self.cbtn = QPushButton()
        self.cbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cbtn.clicked.connect(self.pick)
        self._paint_accent_btn()
        self._row(f, "Цвет Mico AI", self.cbtn, "color")
        self.cres = QPushButton("Вернуть стандартный цвет Mico AI")
        self.cres.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cres.clicked.connect(self._reset_mico_color)
        f.addRow("", self.cres)
        self.th = NoWheelComboBox()
        for key, name in (("auto", "Как в системе (Windows)"), ("light", "Светлая"), ("dark", "Тёмная")):
            self.th.addItem(name, key)
        self.th.setCurrentIndex(max(0, self.th.findData(cfg.get("theme", "auto"))))
        self.th.currentIndexChanged.connect(self.live_theme)
        self._row(f, "Тема чата и окон", self.th, "theme")

        look_size = QWidget()                         # Размер и прозрачность
        f = QFormLayout(look_size)
        self.sc = NoWheelSlider(Qt.Orientation.Horizontal)
        self.sc.setRange(40, 200)
        self.sc.setValue(int(cfg["scale"] * 100))
        self.op = NoWheelSlider(Qt.Orientation.Horizontal)
        self.op.setRange(30, 100)
        self.op.setValue(int(cfg["opacity"] * 100))
        for s_ in (self.sc, self.op):
            s_.valueChanged.connect(self.live)
        self._row(f, "Размер Mico AI", with_readout(self.sc, " %"), "scale")
        self.linked = WrapCheck("Чат меняется вместе с Mico AI (один ползунок)")
        self.linked.setChecked(cfg.get("chat_linked", True))
        self.linked.toggled.connect(self.live_linked)
        f.addRow(self._hc(self.linked, "linked"))
        self.csc = NoWheelSlider(Qt.Orientation.Horizontal)
        self.csc.setRange(60, 200)
        self.csc.setValue(int(cfg.get("chat_scale", 1.0) * 100))
        self.csc.valueChanged.connect(self.live_chat)
        self.csc_lbl = QLabel("Размер чата")
        self.csc_box = with_readout(self.csc, " %")
        self._chat_size_hint()
        self._row(f, self.csc_lbl, self.csc_box, "chat_scale")
        self._row(f, "Прозрачность", with_readout(self.op, " %"), "opacity")
        self.chop = NoWheelSlider(Qt.Orientation.Horizontal)
        self.chop.setRange(30, 100)
        self.chop.setValue(int(round(intel.chat_opacity(cfg) * 100)))
        self._row(f, "Прозрачность чатов", with_readout(self.chop, " %"), "chat_opacity")
        self.sleep_fps = NoWheelComboBox()
        for fps in (60, 30, 15, 10):
            self.sleep_fps.addItem(f"{fps} кадров в секунду", fps)
        self.sleep_fps.setCurrentIndex(max(0, self.sleep_fps.findData(int(cfg.get("anim_sleep_fps", 60)))))
        f.addRow("Частота анимации во сне", self.sleep_fps)

        look_outline = QWidget()                      # Обводки и подсветка
        f = QFormLayout(look_outline)
        self.outline = WrapCheck("Обводка вокруг окна чата")
        self.outline.setChecked(cfg.get("chat_outline", True))
        self.outline.toggled.connect(self.live_outline)
        f.addRow(self._hc(self.outline, "outline"))
        self.in_outline = WrapCheck("Обводка поля ввода в чате Mico AI")
        self.in_outline.setChecked(bool(cfg.get("wi_input_outline", True)))
        self.in_outline.toggled.connect(lambda on: self._set_outline("wi_input_outline", on))
        f.addRow(self._block(self.in_outline, "wi_input_outline"))

        # --- Поведение ---
        pos = QWidget()                               # Положение и сон
        f = QFormLayout(pos)
        self.sleep_min = NoWheelSpinBox()
        self.sleep_min.setRange(0, 30)
        self.sleep_min.setSuffix(" мин (0 — не засыпать)")
        self.sleep_min.setValue(cfg.get("sleep_after_min", 3))
        self._row(f, "Засыпать, если никто не обращается", self.sleep_min, "sleep_after_min")

        start = QWidget()                             # Запуск и поведение
        f = QFormLayout(start)
        self.greet = WrapCheck("Здороваться при включении ПК (день/вечер, погода, что делал вчера)")
        self.greet.setChecked(cfg["greet_on_start"])
        self.auto = WrapCheck("Запускать вместе с Windows (вход в систему)")
        self.auto.setChecked(autostart.status()[0])        # показываем то, что реально стоит в Планировщике
        self.lang = NoWheelComboBox()
        for code, name in i18n.LANGUAGES:
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("language", "ru"))))
        lang_row = QWidget()
        lh = QHBoxLayout(lang_row)
        lh.setContentsMargins(0, 0, 0, 0)
        lh.addWidget(self.lang, 1)
        f.addRow(i18n.t("Язык"), lang_row)
        lang_hint = QLabel(i18n.t("Язык меняется после перезапуска Mico AI."))
        lang_hint.setObjectName("hint")
        f.addRow(lang_hint)
        f.addRow(self._hc(self.greet, "greet"))
        f.addRow(self._hc(self.auto, "auto"))
        self.quiet = WrapCheck("Режим тишины: без приветствий, инициативы и подсказок")
        self.quiet.setChecked(cfg.get("quiet_mode", False))
        f.addRow(self._hc(self.quiet, "quiet"))
        self.updchk = WrapCheck("Проверять новые версии Mico AI при запуске (раз в сутки, без скачивания)")
        self.updchk.setChecked(cfg.get("update_check", True))
        f.addRow(self._block(self.updchk, "update_check"))

        hist = QWidget()                              # История и поиск
        f = QFormLayout(hist)
        self.se = NoWheelComboBox()
        self.se.addItems(list(SEARCH_ENGINES))
        cur = next((n for n, u in SEARCH_ENGINES.items() if u == cfg.get("search_url")), "Google")
        self.se.setCurrentText(cur)
        self._row(f, "Поиск в интернете", self.se, "search_url")
        self.keep = NoWheelComboBox()                 # сколько хранить историю; «всегда» — без очистки
        for days, text in ((7, "7 дней"), (30, "30 дней"), (90, "90 дней"), (365, "365 дней"), (0, "всегда")):
            self.keep.addItem(text, days)
        if self.keep.findData(cfg["retention_days"]) < 0:      # значение из файла, которого нет в списке
            self.keep.addItem(f"{cfg['retention_days']} дн.", cfg["retention_days"])
        self.keep.setCurrentIndex(self.keep.findData(cfg["retention_days"]))
        self._row(f, "Хранить историю", self.keep, "retention_days")

        menu = QWidget()                              # Меню по правому щелчку
        f = QFormLayout(menu)
        f.addRow(QLabel("<small>Что показывать в меню по правому щелчку. «Выход» есть всегда.</small>"))
        chosen = [i for i in cfg.get("menu_items", menu_items.DEFAULT_ON) if i in menu_items.LABELS]
        self.mlist = QListWidget()
        for key in list(chosen) + [i for i in menu_items.LABELS if i not in chosen]:
            it = QListWidgetItem(menu_items.LABELS[key])
            it.setData(Qt.ItemDataRole.UserRole, key)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if key in chosen else Qt.CheckState.Unchecked)
            self.mlist.addItem(it)
        self.mlist.setMinimumHeight(180)
        self.mmax = NoWheelSpinBox()
        self.mmax.setRange(menu_items.MIN_MAX, menu_items.MAX_MAX)
        self.mmax.setValue(max(menu_items.MIN_MAX, min(menu_items.MAX_MAX, cfg.get("menu_max", menu_items.DEFAULT_MAX))))
        self.mcnt = QLabel()
        self.mlist.itemChanged.connect(self._menu_changed)
        self.mmax.valueChanged.connect(self._menu_changed)
        f.addRow(self.mlist)
        self._row(f, "Не больше пунктов", self.mmax, "menu_max")
        f.addRow(self.mcnt)
        self._menu_changed()

        # --- Умное: погода, память, инициатива ---
        smart_a = QWidget()                           # Погода и приветствие
        f = QFormLayout(smart_a)
        self.gl = QListWidget()
        chosen = set(cfg.get("greet_items", ["recap", "weather"]))
        for key, label in greeting.ITEMS:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, key)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if key in chosen else Qt.CheckState.Unchecked)
            self.gl.addItem(it)
        self.gcnt = QLabel()
        self._greet_count()
        self.gl.itemChanged.connect(self._greet_changed)
        self.city = QLineEdit(cfg.get("city", ""))
        self.city.setPlaceholderText("например, Москва — если геопозиция недоступна")
        self.locc = WrapCheck("Разрешить геопозицию (Windows всё равно спросит подтверждение)")
        self.locc.setChecked(cfg.get("loc_consent") is True)
        f.addRow(QLabel("<b>Что показывать при включении ПК (до 3)</b>"))
        f.addRow(self.gl)
        f.addRow(self.gcnt)
        self._row(f, "Город", self.city, "city")
        f.addRow(QLabel("<small>Город можно писать из списка крупных городов России или координатами «55.75,37.62».</small>"))
        f.addRow(self._hc(self.locc, "locc"))

        smart_b = QWidget()                           # Память и перерывы
        f = QFormLayout(smart_b)
        self.mem = WrapCheck("Запоминать мои команды и программы и учиться на привычках")
        self.mem.setChecked(cfg.get("memory_on", True))
        f.addRow(self._hc(self.mem, "mem"))
        f.addRow(QLabel("<small>Журнал зашифрован и хранится только на этом ПК. Срок хранения задаётся выше.</small>"))
        self.pbr = WrapCheck("Напоминать о перерыве, если работаешь без остановки")
        self.pbr.setChecked(cfg.get("proactive_breaks", True))
        self.pbr_min = NoWheelSpinBox()
        self.pbr_min.setRange(15, 240)
        self.pbr_min.setSuffix(" мин")
        self.pbr_min.setValue(cfg.get("proactive_break_min", 60))
        f.addRow(self._hc(self.pbr, "pbr"))
        self._row(f, "Перерыв через", self.pbr_min, "proactive_break_min")
        f.addRow(QLabel("<small>Экран смотрит только локальная модель (VLM), картинка никуда не отправляется.</small>"))

        # --- Свои фразы ---
        helpbox = QWidget()                           # Помощь по буферу и ошибкам
        f = QFormLayout(helpbox)
        self.wi_clip = WrapCheck("Помощник по буферу: предлагает объяснить текст ошибки")
        self.wi_clip.setChecked(bool(cfg.get("wi_clip_help", True)))
        self.wi_clip.toggled.connect(lambda on: self.cfg.update(wi_clip_help=bool(on)))
        f.addRow(self.wi_clip)
        self.wi_err = WrapCheck("Реакция на ошибки: «программа не отвечает» и окна с ошибкой")
        self.wi_err.setChecked(bool(cfg.get("wi_error_help", True)))
        self.wi_err.toggled.connect(lambda on: self.cfg.update(wi_error_help=bool(on)))
        f.addRow(self.wi_err)

        ph = QWidget()
        v = QVBoxLayout(ph)
        v.addWidget(QLabel("<b>Свои фразы-команды</b>. Напиши фразу — Mico AI выполнит шаги по порядку. "
                           "Шаги разделяй «;»."))
        self._phrases = [dict(p) for p in cfg.get("custom_phrases", [])]
        self.pl = QListWidget()
        for p in self._phrases:
            self.pl.addItem(f"«{p['say']}» → {p['do']}")
        self.psay = QLineEdit()
        self.psay.setPlaceholderText("когда я пишу, например: работаю")
        self.pdo = QLineEdit()
        self.pdo.setPlaceholderText("делай, например: включи не беспокоить; открой телеграм")
        add_b = QPushButton("Добавить")
        add_b.clicked.connect(self._phrase_add)
        del_b = QPushButton("Удалить выбранную")
        del_b.clicked.connect(self._phrase_del)
        v.addWidget(self.pl)
        v.addWidget(self.psay)
        v.addWidget(self.pdo)
        row = QHBoxLayout()
        row.addWidget(add_b)
        row.addWidget(del_b)
        v.addLayout(row)

        # --- Кнопки чата ---
        btn = QWidget()
        f = QFormLayout(btn)
        self.cmode = NoWheelComboBox()
        self.cmode.addItem("Mico AI подбирает сам (по моим привычкам)", "auto")
        self.cmode.addItem("Выбрать вручную (до 6)", "manual")
        self.cmode.setCurrentIndex(max(0, self.cmode.findData(cfg.get("chips_mode", "auto"))))
        self.ccount = NoWheelSpinBox()
        self.ccount.setRange(0, chips.MAX_CHIPS)
        self.ccount.setSpecialValueText("не показывать")
        self.ccount.setValue(cfg.get("chips_count", chips.MAX_CHIPS))
        self._row(f, "Режим", self.cmode, "chips_mode")
        self._row(f, "Сколько кнопок (авто)", self.ccount, "chips_count")
        self.chide = WrapCheck("Скрывать кнопки, когда отправил запрос (вернутся, когда нажмёшь в поле ввода)")
        self.chide.setChecked(cfg.get("chips_hide_on_send", True))
        f.addRow(self._block(self.chide, "chips_hide_on_send"))
        self.cfilter = QLineEdit()
        self.cfilter.setPlaceholderText("поиск: например «громче» или «блютуз»")
        self.cfilter.textChanged.connect(self._filter_chips)
        f.addRow(self.cfilter)
        self.clist = QListWidget()
        pinned = set(cfg.get("chips_pinned", []))
        for c in chips.CATALOG:
            it = QListWidgetItem(f"{c.label}  —  «{c.phrase.strip()}»")
            it.setData(Qt.ItemDataRole.UserRole, c.id)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if c.id in pinned else Qt.CheckState.Unchecked)
            self.clist.addItem(it)
        self.clist.itemChanged.connect(self._chip_checked)
        f.addRow(self.clist)
        self.cnt = QLabel()
        f.addRow(self.cnt)
        self._update_cnt()
        reset = QPushButton("Сбросить привычки")
        reset.clicked.connect(self._reset_usage)
        f.addRow(reset)
        f.addRow(QLabel("<small>Mico AI учится по тому, какие кнопки и команды ты используешь. "
                        "Вручную выбранный набор работает, пока не переключишь режим на «подбирает сам».</small>"))

        # --- Модели ---
        mod = QWidget()
        f = QFormLayout(mod)
        # Список установленных моделей приходит из фонового потока (_refresh_ollama_lists): Ollama может быть занята,
        # и окно настроек не должно из-за этого зависать. Пока — только модель из настроек.
        self.ollama_hint = QLabel("<small>⚠️ Установленные модели не найдены. Проверь, что Ollama запущен (значок в трее), "
                                  "и открой настройки снова. Пока ниже показаны только рекомендованные модели.</small>")
        self.ollama_hint.hide()
        f.addRow(self.ollama_hint)
        self.tm = self._combo([], SUGGEST_TEXT, cfg["text_model"])
        self._row(f, "Модель для общения", self.tm, "text_model")
        self.vm = self._combo([], SUGGEST_VISION, cfg["vision_model"])
        self._row(f, "Модель для экрана", self.vm, "vision_model")
        f.addRow(QLabel("<small>В списках только модели, которые уже скачаны на этот ПК. "
                        "Нужной нет — скачай её в разделе «Скачивание и удаление».</small>"))
        mod2 = QWidget()                              # скачивание и удаление
        f = QFormLayout(mod2)
        self.pull_pick = NoWheelComboBox()            # только выбор из списка: вписать имя нельзя
        self.pull_pick.setMinimumWidth(260)
        self.pull_btn = QPushButton("Скачать")
        self.pull_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pull_btn.clicked.connect(self.pull)
        dl_row = QWidget()
        dl_l = QHBoxLayout(dl_row)
        dl_l.setContentsMargins(0, 0, 0, 0)
        dl_l.addWidget(self.pull_pick, 1)
        dl_l.addWidget(self.pull_btn)
        f.addRow("Скачать модель", dl_row)
        self.pull_bar = QProgressBar()                # прогресс скачивания: скрыт, пока ничего не качается
        self.pull_bar.setRange(0, 100)
        self.pull_bar.setTextVisible(False)
        self.pull_bar.setFixedHeight(8)
        self.pull_bar.hide()
        self.pull_lbl = QLabel("")
        self.pull_lbl.setObjectName("hint")
        self.pull_lbl.hide()
        f.addRow(self.pull_bar)
        f.addRow(self.pull_lbl)
        f.addRow(QLabel("<small>Здесь только рекомендованные модели, которых ещё нет на этом ПК. "
                        "Уже скачанные в список не попадают.</small>"))
        self.del_pick = NoWheelComboBox()             # удаление: выбираешь модель из списка установленных
        self.del_pick.setMinimumWidth(260)
        d_ref = QPushButton("Обновить список")
        d_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        d_ref.clicked.connect(lambda: self._refresh_ollama_lists())
        d_btn = QPushButton("Удалить")
        d_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        d_btn.clicked.connect(lambda: self._delete_ollama(self.del_pick.currentText() if self.del_pick.isEnabled() else ""))
        del_row = QWidget()
        del_l = QHBoxLayout(del_row)
        del_l.setContentsMargins(0, 0, 0, 0)
        del_l.addWidget(self.del_pick, 1)
        del_l.addWidget(d_ref)
        del_l.addWidget(d_btn)
        f.addRow("Удалить модель", del_row)
        f.addRow(QLabel("<small>Выбери модель из списка установленных и нажми «Удалить». "
                        "Список берётся из Ollama: если он пуст, запусти Ollama и нажми «Обновить список».</small>"))
        self.stat = QLabel("")
        f.addRow(self.stat)

        def page(*sections):
            """Раздел: плитки подразделов. Нажал плитку — открылись её настройки. Элемент: (виджет, название[, описание])."""
            return subpages.SubPages([(sec[0], sec[1], sec[2] if len(sec) > 2 else "", sec[3] if len(sec) > 3 else None)
                                      for sec in sections])

        tabs.addTab(page((look, i18n.t("Цвет и тема"), "Цвет Mico AI, тема и размер окна настроек", "drop"),
                         (look_size, i18n.t("Размер и прозрачность"), "Размер Mico AI, чата и прозрачность", "resize"),
                         (look_outline, i18n.t("Обводки и подсветка"), "Линии вокруг окон и кнопок", "frame"),
                         (self._wi_colors_box(cfg), i18n.t("Полоска Mico AI"), "Полоска по краю экрана", "bar")), i18n.t("Вид"), "look")
        tabs.addTab(page((pos, i18n.t("Положение и сон"), "Где стоит Mico AI и когда он засыпает", "moon"),
                         (start, i18n.t("Запуск и поведение"), "Автозапуск, приветствие, горячая клавиша", "power"),
                         (hist, i18n.t("История и поиск"), "Сколько хранить и где искать", "history"),
                         (menu, i18n.t("Меню по правому щелчку"), "Какие пункты показывать", "menu"),
                         (self._wi_rhythm_box(cfg), i18n.t("Тишина и загрузка"), "Тихий час и линия нагрузки", "pulse")), i18n.t("Основные"), "general")
        tabs.addTab(page((ph, i18n.t("Свои фразы"), "Команды из нескольких шагов", "chat"),
                         (btn, i18n.t("Кнопки под чатом"), "Что показывать под ответом", "buttons"),
                         (smart_a, i18n.t("Погода и приветствие"), "Что рассказывать при включении ПК", "sun"),
                         (smart_b, i18n.t("Память и перерывы"), "Что помнить и когда напоминать", "layers"),
                         (helpbox, i18n.t("Помощь по буферу и ошибкам"), "Когда Mico AI предлагает помощь сам", "bolt")), i18n.t("Функции"), "functions")
        tabs.addTab(page((mod, i18n.t("Модели для общения и экрана"), i18n.t("Какие модели отвечают"), "models"),
                         (mod2, i18n.t("Скачивание и удаление"), "Загрузить или освободить место", "download")), i18n.t("Модели"), "models")

        for form in self.findChildren(QFormLayout):
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setVerticalSpacing(6)
            form.setHorizontalSpacing(12)
        self._fit_widgets()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_b = bb.button(QDialogButtonBox.StandardButton.Save)
        save_b.setText(i18n.t("Сохранить"))
        save_b.setObjectName("primary")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(i18n.t("Отмена"))
        reset_b = bb.addButton(i18n.t("Сбросить настройки"), QDialogButtonBox.ButtonRole.ActionRole)
        for b_ in bb.buttons():                       # кнопки крупнее: удобно нажимать, и внизу нет пустоты
            b_.setMinimumSize(150, 40)
            b_.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_b.clicked.connect(self.reset_settings)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        # одна нижняя строка: версия и «О программе» в левом углу, кнопки справа
        ver = QLabel(f"Mico AI {version.display_version(cfg.get('update_channel', 'stable'))}")
        ver.setObjectName("hint")
        about_b = QPushButton(i18n.t("О программе"))
        about_b.setObjectName("flat")
        about_b.setCursor(Qt.CursorShape.PointingHandCursor)
        about_b.clicked.connect(lambda: AboutDialog(self, self.cfg).exec())
        foot = QHBoxLayout()
        foot.setContentsMargins(0, 0, 0, 0)
        foot.addWidget(ver, 0, Qt.AlignmentFlag.AlignVCenter)
        foot.addSpacing(10)
        foot.addWidget(about_b, 0, Qt.AlignmentFlag.AlignVCenter)
        foot.addStretch(1)
        foot.addWidget(bb)
        root.addLayout(foot)
        self.status.connect(self.stat.setText)
        self.pulled.connect(self.on_pulled)
        self.pull_progress.connect(self._on_pull_progress)
        self.deleted.connect(self.on_deleted)
        self.models_ready.connect(self._on_models_ready)
        self._refresh_ollama_lists()

    def _live_wave(self, value):
        """Ползунок двигается — волны меняются сразу, без «Сохранить»."""
        self.cfg["wave_opacity"] = int(value)
        glow = getattr(getattr(self.panel, "intel", None), "glow", None)
        if glow is not None:
            glow.update()

    def _wi_colors_box(self, cfg):
        """Цвета полоски Mico AI: у каждого действия свой. Занятый цвет выбрать нельзя."""
        box = QWidget()
        f = QFormLayout(box)
        self._wi_btns = {}
        self.wave_op = NoWheelSlider(Qt.Orientation.Horizontal)
        self.wave_op.setRange(0, 100)
        self.wave_op.setValue(int(cfg.get("wave_opacity", 85)))
        self.wave_op.valueChanged.connect(self._live_wave)
        f.addRow("Прозрачность волн и полосок", self._block(self.wave_op, "wave_opacity"))
        presets = QWidget()
        pl = QHBoxLayout(presets)
        pl.setContentsMargins(0, 0, 0, 0)
        b_clear = QPushButton("Максимально прозрачные")
        b_clear.clicked.connect(lambda: self.wave_op.setValue(0))
        b_solid = QPushButton("Непрозрачные")
        b_solid.clicked.connect(lambda: self.wave_op.setValue(100))
        pl.addWidget(b_clear)
        pl.addWidget(b_solid)
        f.addRow("", presets)
        cur = intel.state_colors(cfg)
        for key, name in intel.STATE_NAMES.items():
            b = QPushButton(cur[key])
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._pick_wi(k))
            self._wi_btns[key] = b
            self._paint_wi(key, cur[key])
            f.addRow(name, b)
        reset = QPushButton("Вернуть цвета по умолчанию")
        reset.clicked.connect(self._reset_wi_colors)
        f.addRow(reset)
        self.wi_edge = NoWheelSlider(Qt.Orientation.Horizontal)           # толщина полосок по краям
        self.wi_edge.setRange(intel.EDGE_W_MIN, intel.EDGE_W_MAX)
        self.wi_edge.setValue(intel.edge_band(cfg))
        self.wi_edge_lbl = QLabel(f"{intel.edge_band(cfg)} px")
        self.wi_edge_lbl.setObjectName("readout")
        self.wi_edge.valueChanged.connect(self._wi_edge_changed)
        erow = QHBoxLayout()
        erow.addWidget(self.wi_edge, 1)
        erow.addWidget(self.wi_edge_lbl)
        f.addRow("Толщина полосок по краям", erow)
        self.wi_waves = WrapCheck("Свечение ярче, пока Mico AI отвечает")
        self.wi_waves.setChecked(intel.waves_on(cfg))
        self.wi_waves.toggled.connect(self._wi_waves_changed)
        f.addRow(self.wi_waves)
        self.wi_wsrc = NoWheelComboBox()
        for key, name in intel.WAVE_SOURCES.items():
            self.wi_wsrc.addItem(name, key)
        self.wi_wsrc.setCurrentIndex(max(0, self.wi_wsrc.findData(cfg.get("wi_wave_source", "mico"))))
        self.wi_wsrc.currentIndexChanged.connect(self._wi_wave_src_changed)
        f.addRow("Цвет волн", self.wi_wsrc)
        self.wi_wbtn = QPushButton()
        self.wi_wbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wi_wbtn.clicked.connect(self._pick_wave)
        self._paint_wave_btn()
        f.addRow("Свой цвет волн", self.wi_wbtn)
        self.wi_theme = NoWheelComboBox()
        for key, (name, _cols, _states) in intel.WAVE_THEMES.items():
            self.wi_theme.addItem(name, key)
        self.wi_theme.setCurrentIndex(max(0, self.wi_theme.findData(cfg.get("wi_wave_theme", intel.WAVE_THEME_DEFAULT))))
        self.wi_theme.currentIndexChanged.connect(self._wi_theme_changed)
        f.addRow("Готовый набор волн", self.wi_theme)
        hint = QLabel("Полоска по краям экрана в режиме Mico AI. Цвета у действий не повторяются. "
                      "Волны могут быть цветом Mico AI из персонализации.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        return box

    def _wi_rhythm_box(self, cfg):
        """Тишина по расписанию и загрузка ПК полоской: только в режиме Mico AI."""
        box = QWidget()
        f = QFormLayout(box)
        self.wi_qon = WrapCheck("Тихий час: в это время Mico AI не начинает разговор сам")
        self.wi_qon.setChecked(bool(cfg.get("wi_quiet_on", False)))
        self.wi_qon.toggled.connect(lambda on: self.cfg.update(wi_quiet_on=bool(on)))
        f.addRow(self.wi_qon)
        self.wi_qfrom, self.wi_qto = QTimeEdit(), QTimeEdit()
        for edit, key, default, row in ((self.wi_qfrom, "wi_quiet_from", "23:00", "С"),
                                        (self.wi_qto, "wi_quiet_to", "08:00", "До")):
            edit.setDisplayFormat("HH:mm")
            edit.setTime(QTime.fromString(str(cfg.get(key) or default), "HH:mm"))
            edit.timeChanged.connect(lambda t, k=key: self.cfg.update({k: t.toString("HH:mm")}))
            f.addRow(row, edit)
        hint = QLabel("Через полночь тоже работает: 23:00–08:00. Ответы на твои вопросы тихий час не блокирует.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        self.wi_lbar = WrapCheck("Загрузка ПК тонкой линией внизу экрана")
        self.wi_lbar.setChecked(bool(cfg.get("wi_load_bar", False)))
        self.wi_lbar.toggled.connect(lambda on: self.cfg.update(wi_load_bar=bool(on)))
        f.addRow(self.wi_lbar)
        hint2 = QLabel("Линия растёт вместе с нагрузкой процессора. Цвет — как у волн.")
        hint2.setObjectName("hint")
        hint2.setWordWrap(True)
        f.addRow(hint2)
        return box

    def _wi_edge_changed(self, v):
        self.cfg["wi_edge_width"] = int(v)
        self.wi_edge_lbl.setText(f"{int(v)} px")
        self._wi_preview()

    def _wi_waves_changed(self, on):
        self.cfg["wi_waves"] = bool(on)
        self._wi_preview()

    def _wi_wave_src_changed(self, _=None):
        self.cfg["wi_wave_source"] = self.wi_wsrc.currentData()
        self._wi_preview()

    def _wi_theme_changed(self, _=None):
        key = self.wi_theme.currentData()
        self.cfg["wi_wave_theme"] = key
        states = intel.theme_states(key)              # цвета действий под набор
        self.cfg["wi_colors"] = dict(states)
        for state_key, hex_color in states.items():
            self._paint_wi(state_key, hex_color)
        if self.cfg.get("wi_wave_source") != "theme":                 # выбрал набор — он и включается
            self.wi_wsrc.setCurrentIndex(self.wi_wsrc.findData("theme"))
        self._wi_preview()

    def _paint_wave_btn(self):
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg.get("wi_wave_custom"))
        self.wi_wbtn.setText(hex_color)
        self.wi_wbtn.setStyleSheet(f"background:{hex_color}; color:#201a14; border:1px solid #8a7d6a; "
                                   "border-radius:10px; padding:4px 12px;")

    def _pick_wave(self):
        c = QColorDialog.getColor(QColor(*intel.hex_rgb(self.cfg.get("wi_wave_custom"))), self, "Цвет волн")
        if not c.isValid():
            return
        self.cfg["wi_wave_custom"] = c.name().upper()
        self._paint_wave_btn()
        self.wi_wsrc.setCurrentIndex(self.wi_wsrc.findData("custom"))    # выбрал свой цвет — он и включается

    def _wi_preview(self):
        """Настройку меняют: полоска и волны показываются сразу, чтобы увидеть результат."""
        if self.panel.intel:
            self.panel.intel.preview()

    def _paint_wi(self, key, hex_color):
        b = self._wi_btns[key]
        b.setText(hex_color)
        b.setStyleSheet(f"background:{hex_color}; color:#201a14; border:1px solid #8a7d6a; "
                        "border-radius:10px; padding:4px 12px;")

    def _pick_wi(self, key):
        cur = intel.state_colors(self.cfg)
        c = QColorDialog.getColor(QColor(cur[key]), self, f"Цвет: {intel.STATE_NAMES[key]}")
        if not c.isValid():
            return
        hex_color = c.name().upper()
        clash = intel.color_clash(cur, key, hex_color)
        if clash:
            QMessageBox.information(self, "Цвет занят",
                                    f"Этот цвет уже у действия «{intel.STATE_NAMES[clash]}». "
                                    "Выбери другой: у каждого действия свой цвет.")
            return
        cur[key] = hex_color
        self.cfg["wi_colors"] = cur
        self._paint_wi(key, hex_color)

    def _reset_wi_colors(self):
        self.cfg["wi_colors"] = dict(intel.DEFAULT_COLORS)
        for key, hex_color in intel.DEFAULT_COLORS.items():
            self._paint_wi(key, hex_color)

    @staticmethod
    def _combo(installed, suggest, cur):
        """Выбор модели только из установленных. Модель из настроек показываем, даже если её сейчас нет в списке.
        Вписать имя руками нельзя: чтобы скачать новую модель, есть список «Скачать модель» в разделе «Модели»."""
        c = NoWheelComboBox()
        c.setEditable(False)
        names = list(installed)
        if cur and cur not in names:                  # настроенной модели нет на ПК — покажем с пометкой
            names.insert(0, cur + "  (не скачана)")
        c.addItems(names)
        if cur:
            i = c.findText(cur) if cur in names else c.findText(cur + "  (не скачана)")
            if i >= 0:
                c.setCurrentIndex(i)
        c.setEnabled(bool(names))
        return c

    def _style_dialog(self):
        """Оформление окна настроек по цвету Mico AI и теме (в режиме Mico AI — спокойнее, как в macOS)."""
        dark = theme.is_dark(self.cfg)
        accent_win = theme.windows_accent()
        Switch.ON = accent_win
        Switch.OFF = "#4a4a4a" if dark else "#d1d1d6"
        if hasattr(self, "_tabs"):
            self._tabs.set_accent(accent_win)
        if intel.style_of(self.cfg.get("assist_style")) == intel.INTELLIGENCE:
            self.setStyleSheet(theme.wi_settings_qss(self.cfg["color"], dark) + theme.RESET_QSS)
        else:
            self.setStyleSheet(theme.settings_qss(self.cfg["color"], dark) + theme.RESET_QSS)

    def _paint_accent_btn(self):
        """Кнопка «Цвет Mico AI» показывает сам цвет."""
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg["color"])
        self.cbtn.setText(hex_color)
        self.cbtn.setStyleSheet(f"background:{hex_color}; color:#201a14; border:1px solid #8a7d6a; "
                                "border-radius:10px; padding:4px 12px;")

    def _apply_accent(self):
        """Цвет Mico AI сменили: окно настроек, кнопка цвета, чат, строка Mico AI и волны перекрашиваются сразу,
        без перезапуска. Все кнопки берут цвет из одного места — cfg["color"]."""
        self._style_dialog()
        self._paint_accent_btn()
        self.blob.update()
        self.panel.theme()
        if self.panel.intel:
            self.panel.intel.restyle()
            self._wi_preview()

    def pick(self):
        c = QColorDialog.getColor(QColor(self.cfg["color"]), self, "Цвет Mico AI")
        if c.isValid():
            self.cfg["color"] = c.name()
            self._apply_accent()

    def live(self):
        self.cfg["scale"], self.cfg["opacity"] = self.sc.value() / 100, self.op.value() / 100
        self.cfg["chat_opacity"] = self.chop.value() / 100
        self.blob.apply_config()
        if self.linked.isChecked() and self.csc.value() != self.sc.value():
            self.csc.blockSignals(True)                 # ползунок чата следует за размером Mico AI
            self.csc.setValue(self.sc.value())
            self.csc.blockSignals(False)
        self.panel.apply_size()

    def _chat_size_hint(self):
        """Ползунок размера чата: при связке меняет размер и Mico AI, и чата; без связки — только чат."""
        linked = self.linked.isChecked()
        self.csc.blockSignals(True)
        if linked:
            self.csc.setRange(self.sc.minimum(), self.sc.maximum())
            self.csc.setValue(self.sc.value())
            self.csc_lbl.setText("Размер Mico AI и чата")
            self.csc.setToolTip("Меняет размер и Mico AI, и чата вместе")
        else:
            self.csc.setRange(60, 200)
            self.csc.setValue(int(round(self.cfg.get("chat_scale", 1.0) * 100)))
            self.csc_lbl.setText("Размер чата")
            self.csc.setToolTip("Отдельный размер чата, Mico AI не меняется")
        self.csc.setEnabled(True)
        self.csc.blockSignals(False)
        self.csc_box.refresh()                      # подпись значения, пока сигналы были выключены

    def live_linked(self, on):
        self.cfg["chat_linked"] = on
        self._chat_size_hint()
        self.panel.apply_size()

    def live_chat(self, v):
        if self.linked.isChecked():                 # вместе: двигаем общий размер Mico AI и чата
            self.sc.setValue(v)                     # ползунок Mico AI обновит и Mico AI, и чат
            return
        self.cfg["chat_scale"] = v / 100
        self.panel.apply_size()

    def _phrase_add(self):
        say, do = self.psay.text().strip(), self.pdo.text().strip()
        if not custom.valid(say, do):
            QMessageBox.information(self, "Фразы", "Заполни обе строки. Фраза — до 60 знаков, шаги — до 300.")
            return
        if len(self._phrases) >= custom.MAX_PHRASES:
            QMessageBox.information(self, "Фразы", f"Можно добавить не больше {custom.MAX_PHRASES} фраз.")
            return
        self._phrases = self._phrases + [{"say": say, "do": do}]
        self.pl.addItem(f"«{say}» → {do}")
        self.psay.clear()
        self.pdo.clear()

    def _phrase_del(self):
        row = self.pl.currentRow()
        if row >= 0:
            self._phrases = self._phrases[:row] + self._phrases[row + 1:]
            self.pl.takeItem(row)

    def _filter_settings(self, text):
        """Поиск по настройкам: оставляет строки, в которых есть все слова из поля (название, подсказка, варианты).
        Пустое поле возвращает всё как было. Вкладки без совпадений выключаются."""
        def norm(x):
            return " ".join(str(x).lower().replace("ё", "е").split())

        words = [w for w in norm(text).split(" ") if w]
        if words:
            for ex in self.findChildren(Expander):
                ex.setExpanded(True)                  # совпадения внутри свёрнутых блоков должны быть видны
        tabs = self._tabs
        for i in range(tabs.count()):                  # во время поиска все подразделы — одним списком
            pg = tabs.widget(i)
            if hasattr(pg, "show_all"):
                pg.show_all(bool(words))

        def text_of(w):
            parts = []
            for c in [w] + w.findChildren(QWidget):
                if isinstance(c, (QLabel, QCheckBox)):
                    parts.append(c.text())
                elif isinstance(c, QComboBox):
                    parts += [c.itemText(i) for i in range(c.count())]
                elif isinstance(c, QLineEdit):
                    parts.append(c.placeholderText())
            return norm(" ".join(parts))

        def tab_of(w):
            return next((i for i in range(tabs.count()) if tabs.widget(i).isAncestorOf(w)), None)

        def group_of(w):
            p = w.parentWidget()
            while p is not None and not isinstance(p, QGroupBox):
                p = p.parentWidget()
            return p

        hit_tabs, hit_groups, any_hit = set(), set(), False
        for form in self.findChildren(QFormLayout):
            for r in range(form.rowCount()):
                widgets = []
                for role in (QFormLayout.ItemRole.LabelRole, QFormLayout.ItemRole.FieldRole,
                             QFormLayout.ItemRole.SpanningRole):
                    item = form.itemAt(r, role)
                    if item is not None and item.widget() is not None and item.widget() not in widgets:
                        widgets.append(item.widget())
                if not widgets:
                    continue
                for w in widgets:
                    self._vis.setdefault(w, not w.isHidden())
                haystack = " ".join(text_of(w) for w in widgets)
                matched = all(word in haystack for word in words) if words else True
                for w in widgets:
                    w.setVisible(matched and self._vis[w])
                if words and matched:
                    any_hit = True
                    t = tab_of(widgets[0])
                    if t is not None:
                        hit_tabs.add(t)
                    g = group_of(widgets[0])
                    if g is not None:
                        hit_groups.add(g)

        for g in self.findChildren(QGroupBox):
            g.setVisible(not words or g in hit_groups)
        for i in range(tabs.count()):
            tabs.setTabEnabled(i, not words or i in hit_tabs)
        if words and hit_tabs and tabs.currentIndex() not in hit_tabs:
            tabs.setCurrentIndex(min(hit_tabs))
        self.found_hint.setVisible(bool(words) and not any_hit)

    def _greet_ids(self):
        out = []
        for i in range(self.gl.count()):
            it = self.gl.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    NAME2KEY = {"outline": "chat_outline", "linked": "chat_linked", "greet": "greet_on_start",
                "auto": "autostart", "quiet": "quiet_mode", "locc": "loc_consent", "mem": "memory_on",
                "pbr": "proactive_breaks"}

    def _block(self, widget, key=None, badge=None):
        """Одна настройка: сам элемент, кнопка «Сбросить» в конце строки и серая подсказка под ней."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(widget, 1)
        if badge is not None:
            line.addWidget(badge)
        if key:
            self._reg[key] = getattr(widget, "inner", widget)
            rb = QPushButton("Сброс")
            rb.setObjectName("resetRow")
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setToolTip("Вернуть эту настройку к значению по умолчанию")
            rb.clicked.connect(lambda _=False, k=key: self._reset_key(k))
            line.addWidget(rb)
        v.addLayout(line)
        raw_hint = settings_info.CFG_HINTS.get(key) if key else None
        hint = i18n.t(raw_hint) if raw_hint else None
        if hint:
            hl = QLabel(hint)
            hl.setObjectName("hint")
            hl.setWordWrap(True)
            v.addWidget(hl)
        return w

    def _row(self, f, label, widget, key):
        block = self._block(widget, key)
        if label is None:
            f.addRow(block)
        else:
            f.addRow(label, block)

    def _hc(self, box, name):
        """Галочка с подсказкой и кнопкой «Сбросить». Для бета-функций рядом пишется BETA;
        вне бета-канала пункт недоступен."""
        feat = features.SETTING_FEATURE.get(name)
        badge = None
        if feat and features.is_beta(feat):
            badge = QLabel("BETA")
            badge.setStyleSheet("color:#c0392b; font-weight:bold; font-size:11px;")
            if not features.enabled(feat, self.cfg):
                box.setEnabled(False)
                box.setToolTip("Доступно в программе предварительной оценки (⚙ Настройки → Бета)")
        return self._block(box, self.NAME2KEY.get(name), badge)

    def _reset_key(self, key):
        """Возвращает одну настройку к значению по умолчанию — только ту, у которой нажали «Сбросить»."""
        w = self._reg.get(key)
        if w is None:
            return
        default = DEFAULTS.get(key)
        if key == "color":
            self._reset_mico_color()
            return
        if key == "search_url":
            name = next((n for n, u in SEARCH_ENGINES.items() if u == default), None)
            if name:
                self.se.setCurrentText(name)
            return
        if isinstance(w, QSlider) and isinstance(default, float):     # ползунки в процентах: 1.0 → 100
            w.setValue(int(round(default * 100)))
            return
        _set_widget_value(w, default)

    def _greet_count(self):
        self.gcnt.setText(f"Выбрано: {len(self._greet_ids())} из {greeting.MAX_ITEMS}")

    def _greet_changed(self, item):
        if item.checkState() == Qt.CheckState.Checked and len(self._greet_ids()) > greeting.MAX_ITEMS:
            self.gl.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.gl.blockSignals(False)
            QMessageBox.information(self, "Приветствие", f"Можно выбрать не больше {greeting.MAX_ITEMS} пунктов.")
        self._greet_count()

    def _checked_ids(self):
        out = []
        for i in range(self.clist.count()):
            it = self.clist.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def _update_cnt(self):
        n = len(self._checked_ids())
        self.cnt.setText(f"Выбрано: {n} из {chips.MAX_CHIPS}")

    def _chip_checked(self, item):
        if item.checkState() == Qt.CheckState.Checked:
            self.cmode.setCurrentIndex(self.cmode.findData("manual"))     # выбрал кнопки — значит, вручную
        if item.checkState() == Qt.CheckState.Checked and len(self._checked_ids()) > chips.MAX_CHIPS:
            self.clist.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.clist.blockSignals(False)
            QMessageBox.information(self, "Кнопки", f"Можно выбрать не больше {chips.MAX_CHIPS} кнопок.")
        self._update_cnt()

    def _filter_chips(self, text):
        t = text.strip().lower()
        for i in range(self.clist.count()):
            it = self.clist.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def _reset_usage(self):
        chips.reset(self.cfg)
        save_cfg(self.cfg)
        QMessageBox.information(self, "Кнопки", "Привычки сброшены. Mico AI начнёт учиться заново.")

    def _save_chips(self):
        self.cfg.update(chips_mode=self.cmode.currentData(), chips_count=self.ccount.value(),
                        chips_hide_on_send=self.chide.isChecked(),
                        anim_sleep_fps=self.sleep_fps.currentData() or 60,
                        wave_opacity=self.wave_op.value(),
                        chips_pinned=self._checked_ids()[:chips.MAX_CHIPS])

    def reset_settings(self):
        """Возврат всех настроек к значениям по умолчанию. История, напоминания и словарь сохраняются."""
        if QMessageBox.question(self, "Сбросить настройки",
                                "Вернуть все настройки к значениям по умолчанию?\n\n"
                                "История, напоминания, словарь и счётчики кнопок сохранятся. "
                                "Согласие на геопозицию придётся дать заново.") \
                != QMessageBox.StandardButton.Yes:
            return
        keep = {k: self.cfg[k] for k in ("last_version", "chip_usage") if k in self.cfg}
        self.cfg.clear()
        self.cfg.update(DEFAULTS)
        self.cfg.update(keep)
        save_cfg(self.cfg)
        self.orig = dict(self.cfg)                   # reject() не должен откатить сброс
        QMessageBox.information(self, "Mico AI", "Настройки сброшены. Перезапусти Mico AI, чтобы всё применилось.")
        super().reject()

    def _fit_widgets(self):
        """Чтобы при уменьшении окна всё переносилось, а не выходило за края: подписи переносятся,
        выпадающие списки, кнопки и поля не требуют ширины по самому длинному тексту."""
        ignore = QSizePolicy.Policy.Ignored
        for w in self.findChildren(QLabel):
            w.setWordWrap(True)
        for w in self.findChildren(QComboBox):
            w.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            w.setMinimumContentsLength(6)
            w.setSizePolicy(QSizePolicy.Policy.Preferred, w.sizePolicy().verticalPolicy())   # растягивается, но не ноль
        for w in self.findChildren(QPushButton):
            w.setSizePolicy(QSizePolicy.Policy.Minimum, w.sizePolicy().verticalPolicy())      # кнопка не сжимается в ноль
        for w in self.findChildren(QLineEdit):
            w.setSizePolicy(ignore, w.sizePolicy().verticalPolicy())

    def _apply_size(self, key):
        """Окно настроек — выбранного размера, но не больше экрана (не на весь экран по умолчанию)."""
        w, h = next(((w, h) for k, _, (w, h) in SETTINGS_SIZES if k == key), (640, 720))
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(w, scr.width() - 40), min(h, scr.height() - 80))
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)   # на весь экран

    def _menu_changed(self, _item=None):
        self.mcnt.setText(f"Показано: {min(len(self._menu_ids()), self.mmax.value())} из {self.mmax.value()} "
                          "(выход — всегда)")

    def _menu_ids(self):
        out = []
        for i in range(self.mlist.count()):
            it = self.mlist.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def live_outline(self, on):
        self.cfg["chat_outline"] = on
        self.panel.theme()
        if self.panel.intel:                              # режим Mico AI рисует окно чата сам
            self.panel.intel.restyle()

    def _set_outline(self, key, on):
        """Обводка поля ввода в чате Mico AI. Применяется сразу, без перезапуска."""
        self.cfg[key] = bool(on)
        if self.panel.intel:
            self.panel.intel.restyle()

    def _reset_mico_color(self):
        """Возвращает Mico AI стандартную окраску. Только цвет Mico AI: полоска Mico AI и её цвета не трогаются."""
        self.cfg["color"] = DEFAULTS["color"]
        self._apply_accent()

    def live_theme(self):
        self.cfg["theme"] = self.th.currentData()
        self.hooks.apply_theme()

    # ----- модели Ollama -----
    def pull(self):
        name = self.pull_pick.currentText().strip() if self.pull_pick.isEnabled() else ""
        if not name or name.startswith("──"):          # заголовок раздела выбрать нельзя
            return
        self.pull_btn.setEnabled(False)

        def work():
            try:
                ok = pull_model(name, self.status.emit, self.pull_progress.emit)
            finally:
                self.pull_progress.emit(0, 0)            # прячем полоску даже при ошибке
            if ok:
                self.status.emit(f"✓ Готово: {name}")
                self.pulled.emit(name)
        threading.Thread(target=work, daemon=True).start()
        self.status.emit(f"Скачиваю {name}…")

    def _on_pull_progress(self, done, total):
        """Полоска: сколько скачано из скольких мегабайт и сколько процентов."""
        if total <= 0:
            self.pull_bar.hide()
            self.pull_lbl.hide()
            self.pull_btn.setEnabled(True)
            return
        done = max(0, min(done, total))               # скачано не может быть больше размера модели и отрицательным
        pct = 100 if done >= total else done * 100 // total   # 99.9% не показываем как 99
        self.pull_bar.setValue(pct)
        text = f"{done / 1e6:.0f} из {total / 1e6:.0f} МБ · {pct}%"
        if pct >= 100:                                # всё скачано: Ollama проверяет и ставит модель
            text += " · проверяю…"
        self.pull_lbl.setText(text)
        self.pull_bar.show()
        self.pull_lbl.show()

    def _delete_ollama(self, name):
        """Удаление модели Ollama с подтверждением: место на диске освобождается, скачать снова можно в любой момент."""
        name = (name or "").strip()
        if not name:
            return
        if QMessageBox.question(self, "Удалить модель",
                                f"Удалить «{name}» с компьютера? Скачать её снова можно в любой момент.") \
                != QMessageBox.StandardButton.Yes:
            return
        self.status.emit(f"Удаляю {name}…")

        def work():
            ok = delete_ollama_model(name)
            if ok:
                self.status.emit(f"✓ Удалена: {name}")
                self.deleted.emit(name)
            else:
                self.status.emit(f"Не получилось удалить «{name}». Проверь, что Ollama запущена.")
        threading.Thread(target=work, daemon=True).start()

    def _refresh_ollama_lists(self):
        """Список установленных моделей Ollama — в фоновом потоке, результат придёт сигналом models_ready.
        Раньше это делалось прямо в окне: пока Ollama занята (например, грузит модель), настройки висели."""
        def work():
            self.models_ready.emit(list_models())
        threading.Thread(target=work, daemon=True).start()

    def _on_models_ready(self, installed):
        """Список пришёл: обновляем выбор моделей для чата и скачивание/удаление. Выбор пользователя сохраняем."""
        self.ollama_hint.setVisible(not installed)
        self._set_model_items(self.tm, [m for m in installed if not is_vision_model(m)], self.tm.currentText())
        self._set_model_items(self.vm, [m for m in installed if is_vision_model(m)], self.vm.currentText())
        self._fill_pull_pick(installed)
        self._fill_del_pick(installed)

    @staticmethod
    def _set_model_items(c, installed, current):
        """Заполняет список установленных моделей, сохраняя выбранную. Если её нет на ПК — помечаем «(не скачана)»."""
        cur = (current or "").replace("  (не скачана)", "").strip()
        names = list(installed)
        if cur and cur not in names:
            names.insert(0, cur + "  (не скачана)")
        c.blockSignals(True)
        c.clear()
        c.addItems(names)
        if cur:
            i = c.findText(cur) if cur in names else c.findText(cur + "  (не скачана)")
            if i >= 0:
                c.setCurrentIndex(i)
        c.setEnabled(bool(names))
        c.blockSignals(False)

    def _fill_pull_pick(self, installed):
        """Список для скачивания: отдельно модели для чата и отдельно для экрана; установленные не показываем."""
        if not hasattr(self, "pull_pick"):
            return
        import brain as _brain
        have = set(installed)
        groups = (("Для чата", _brain.SUGGEST_TEXT), ("Для экрана", _brain.SUGGEST_VISION))
        self.pull_pick.blockSignals(True)
        self.pull_pick.clear()
        model = self.pull_pick.model()
        first = None
        for title, names in groups:
            todo = [n for n in names if n not in have]
            if not todo:
                continue
            self.pull_pick.addItem(f"── {title} ──")
            model.item(self.pull_pick.count() - 1).setEnabled(False)   # заголовок видно, но не выбирается
            for n in todo:
                self.pull_pick.addItem(n)
                if first is None:
                    first = self.pull_pick.count() - 1
        self.pull_pick.setEnabled(first is not None)
        if first is not None:
            self.pull_pick.setCurrentIndex(first)
        self.pull_pick.blockSignals(False)

    def _fill_del_pick(self, names):
        """Список установленных моделей для удаления. Пусто — Ollama не запущена или моделей ещё нет."""
        if not hasattr(self, "del_pick"):
            return
        self.del_pick.blockSignals(True)
        self.del_pick.clear()
        self.del_pick.addItems(list(names))
        self.del_pick.setEnabled(bool(names))
        self.del_pick.blockSignals(False)

    def on_deleted(self, name):
        self._refresh_ollama_lists()
        for c in (self.tm, self.vm):
            i = c.findText(name)
            if i >= 0:
                c.removeItem(i)

    def on_pulled(self, name):
        for c in (self.tm, self.vm):
            if c.findText(name) < 0:
                c.insertItem(0, name)
        self._refresh_ollama_lists()

    def accept(self):
        """Сохранение: любая ошибка показывается человеку с причиной и пишется в crash.log — не молчаливый отказ."""
        try:
            done = self._apply()
        except Exception as e:
            import traceback
            try:
                folder = os.path.join(APPDIR)
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, "crash.log"), "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc() + "\n")
            except OSError:
                pass
            QMessageBox.warning(self, "Настройки", f"Не получилось сохранить настройки: {e}\n\n"
                                "Подробности записаны в crash.log в папке Mico AI (%APPDATA%\\Mico).")
            return
        if done:
            super().accept()

    def _apply(self):
        self._save_chips()
        self.cfg.update(menu_items=self._menu_ids(), menu_max=self.mmax.value())
        self.cfg.update(language=self.lang.currentData() or "ru")
        self.cfg.update(quiet_mode=self.quiet.isChecked(), update_check=self.updchk.isChecked())
        self.cfg.update(sleep_after_min=self.sleep_min.value())
        self.cfg["chat_opacity"] = self.chop.value() / 100          # ползунок сохраняем всегда, не только при движении других
        self.cfg.update(proactive_breaks=self.pbr.isChecked(),
                        proactive_break_min=self.pbr_min.value())
        self.cfg.update(custom_phrases=list(self._phrases))
        self.cfg.update(text_model=self.tm.currentText().strip(), vision_model=self.vm.currentText().strip() or VISION_MODEL,
                        greet_on_start=self.greet.isChecked(), retention_days=self.keep.currentData(),
                        search_url=SEARCH_ENGINES.get(self.se.currentText(), SEARCH_ENGINES["Google"]))
        self.cfg.update(chat_outline=self.outline.isChecked(), chat_linked=self.linked.isChecked(),
                        chat_scale=self.cfg.get("chat_scale", 1.0), chat_ratio=self.cfg.get("chat_ratio", 1.0),
                        weather_on="weather" in self._greet_ids(), greet_items=self._greet_ids(),
                        city=self.city.text().strip(), memory_on=self.mem.isChecked(),
                        loc_consent=True if self.locc.isChecked() else (False if self.cfg.get("loc_consent") is not None else None))
        commands.SEARCH_URL = self.cfg["search_url"]
        # включённый флажок всегда переписываем задачу: так чинится и отсутствующая, и устаревшая (старый путь)
        # ошибка автозапуска не должна мешать сохранить остальные настройки: сохраняем сначала, сообщаем потом
        try:
            ok, msg = autostart.install() if self.auto.isChecked() else autostart.remove()
        except Exception as e:
            ok, msg = False, f"не получилось: {e}"
        if ok:
            self.cfg["autostart"] = self.auto.isChecked()
        try:
            save_cfg(self.cfg)
        except OSError as e:                       # не записали — окно не закрываем, чтобы пользователь увидел причину
            QMessageBox.warning(self, "Настройки", f"Не удалось записать настройки: {e}")
            return False
        if not ok:
            QMessageBox.warning(self, "Автозапуск", msg)
        return True

    def reject(self):
        self.cfg.update(self.orig)
        self.blob.apply_config()
        self.panel.apply_size()
        self.hooks.apply_theme()
        super().reject()


# =============================== Запуск ===============================
class Bus(QObject):
    hotkey = pyqtSignal(int)            # нажата глобальная горячая клавиша (из фонового потока)
    info = pyqtSignal(str)              # погода и прочие сообщения из фоновых потоков
    update_found = pyqtSignal(object)   # найдена новая версия Mico AI (словарь с номером и адресом страницы)


def main():
    if "--autostart" in sys.argv:                # при входе в Windows даём рабочему столу загрузиться
        time.sleep(10)
    try:                                       # 1 мс точность таймеров Windows — плавные кадры
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    app = QApplication(sys.argv)
    theme.load_fonts()                       # Inter из assets/fonts — один шрифт на всё Mico AI
    app.setFont(theme.app_font())
    app.setStyleSheet(theme.FONT_QSS)        # и в стилях тоже: иначе виджеты берут системный шрифт
    from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
    _qt_ru = QTranslator()                             # стандартные кнопки Qt (Да, Нет, ОК, Отмена) — по-русски
    if _qt_ru.load(QLocale("ru_RU"), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(_qt_ru)
    app._qt_ru = _qt_ru                                # не даём сборщику мусора удалить перевод
    import installer as _ic
    _icon = _ic._asset("mico.ico")
    if _icon:
        app.setWindowIcon(QIcon(_icon))       # значок Mico AI во всех окнах программы
    import installer
    if installer.is_uninstall_request():   # «Параметры → Приложения» или пункт меню запускают удаление
        installer.uninstall(app)
        return
    try:
        installer.refresh_uninstall_entry()     # старая запись в «Приложениях» ведёт на консольный скрипт — исправляем
    except Exception:
        pass
    if installer.should_run():                  # собранный Mico.exe запущен не из папки установки — мастер
        installer.run()
        return
    app.setQuitOnLastWindowClosed(False)
    existed = os.path.exists(CFG_PATH)           # была ли уже установка (для «что нового»)
    _stage("запуск main()")
    cfg, store = load_cfg(), Store()
    i18n.set_language(cfg.get("language", "ru"))           # язык интерфейса из настроек
    if version.BUILD_CHANNEL == "stable" and cfg.get("update_channel") != "stable":
        cfg["update_channel"] = "stable"                 # стабильная сборка всегда на стабильном канале
        save_cfg(cfg)
    _stage("настройки и хранилище готовы")
    wi_notice = intel.enforce_mode(cfg, intel_ui.total_ram_gb(), intel_ui.free_disk_gb())   # слабый ПК: предупреждаем
    try:                                                                                      # проверка при запуске: только то, что не в порядке
        problems = [l for l in intel.checkup_lines(cfg, list_models(), intel_ui.total_ram_gb(), intel_ui.free_disk_gb())
                    if not l.startswith("✅")]
    except Exception:
        problems = []
    if problems:
        wi_notice = "\n".join(filter(None, [wi_notice] + problems))
    store.purge(cfg["retention_days"])
    commands.SEARCH_URL = cfg["search_url"]
    commands.warmup()                           # заранее читаем список приложений из «Пуска»
    tracker = Tracker(store, cfg)
    tracker.start()
    brain = Brain(cfg, store, tracker)
    _stage("мозг готов")
    blob = Blob(cfg)
    fresh_start = not _alive_instance()          # первый запуск (включение ПК) — по центру экрана
    if fresh_start:
        g = QGuiApplication.primaryScreen().availableGeometry()
        blob.move(g.center().x() - blob.width() // 2, g.center().y() - blob.height() // 2)
    else:
        blob.move(300, 160)
    blob.show()
    panel = Panel(brain, blob, cfg)
    if wi_notice:
        QTimer.singleShot(4000, lambda: panel.say(wi_notice))
    _wi_chat = getattr(getattr(panel, "intel", None), "wichat", None)
    if _wi_chat is not None:
        _wi_chat.on_draft = lambda _t: save_cfg(cfg)      # черновик чата Mico AI сохраняется в настройках
    _stage("окно чата готово")
    watcher = WindowWatcher()
    _stage("наблюдатель окон готов")
    bus = Bus()                              # сигналы между фоновыми потоками и окном
    bus.info.connect(panel.say)              # погода и сообщения из фоновых потоков
    brain.notify = panel.reminder.emit
    brain.save_cfg = lambda: save_cfg(cfg)
    reminders.bind(store)                    # напоминания — в зашифрованном хранилище

    def on_hotkey(hid):
        if hid == 1:                                         # F8: открывает обычный чат Mico AI
            if intel_ctl is not None and intel_ctl.on():
                intel_ctl.toggle_wichat()                    # режим Mico AI: чат Mico AI
            else:
                panel.toggle()                               # обычный режим: чат рядом с Mico AI
        elif hid == 2:                                       # Mico AI: «Что на экране?»
            intel_ctl.screen_hotkey()
        elif hid == 3:                                       # Mico AI: «Помочь с окном»
            intel_ctl.window_hotkey(active_title())
    bus.hotkey.connect(on_hotkey)

    def offer_update(info):
        """Новая версия: спрашиваем один раз за запуск. Mico AI только открывает страницу, скачивать — тебе."""
        if cfg.get("quiet_mode"):
            return
        if _box(QMessageBox.Icon.Information, "Новая версия Mico AI", updatecheck.offer_text(info),
                "Открыть страницу", "Позже"):
            webbrowser.open(info["url"])
    bus.update_found.connect(offer_update)

    def start_update_check():
        """Фоновый запрос к GitHub: интерфейс не ждёт, без сети тихо пропускаем. В версии из Store не нужна."""
        def work():
            try:
                info = updatecheck.check(cfg)
                save_cfg(cfg)
            except Exception:
                return
            if info:
                bus.update_found.emit(info)
        threading.Thread(target=work, daemon=True).start()
    def active_title():
        """Название программы, которой пользуешься (не Mico AI). Пусто — если узнать не получилось."""
        try:
            import win32gui
            hwnd = watcher.last_hwnd or tracker.last_hwnd
            return win32gui.GetWindowText(hwnd) if hwnd else ""
        except Exception:
            return ""
    hk = hotkeys.HotkeyThread({1: "f8",
                               2: cfg.get("hotkey_screen", intel.SCREEN_KEY),
                               3: cfg.get("hotkey_window", intel.WINDOW_KEY)}, bus.hotkey.emit)
    hk.start()

    hk.ready.wait(3)
    if hk.failed:
        bus.info.emit("Не получилось назначить горячую клавишу: " + ", ".join(hk.failed) +
                      ". Проверь сочетание в ⚙ Настройки → Поведение или его уже занимает другая программа.")
    reminders.restore(brain.notify)          # напоминания, поставленные до перезапуска
    brain.last_hwnd = lambda: watcher.last_hwnd or tracker.last_hwnd
    brain.clip_text = lambda: QGuiApplication.clipboard().text()
    brain.on_command = lambda q: (chips.record(q, cfg), save_cfg(cfg))     # учимся на кнопках и командах
    blob.clicked.connect(panel.toggle)
    blob.slept.connect(panel.hide_smooth)                    # заснул — чат прячется
    # проснулся — чат возвращается, но не раньше, чем Mico AI приземлится после прыжка (иначе чат налезает на него)
    blob.woke.connect(lambda: QTimer.singleShot(blob.WAKE_SETTLE_MS, panel.show_near))
    blob.can_sleep = lambda: not (panel.busy or panel.inp.hasFocus() or panel.inp.text()
                                  or (panel.isVisible() and panel.underMouse())
                                  or (intel_ctl is not None and intel_ctl.wichat.isVisible()))   # открыт чат Mico AI — не спим
    intel_ctl = intel_ui.Intel(cfg, blob, panel)              # режим Windows Intelligence (по умолчанию выключен)
    panel.intel = intel_ctl
    panel.busy_changed.connect(intel_ctl.busy)
    panel.answer_text.connect(intel_ctl.answer)
    panel.user_sent.connect(intel_ctl.wi_user)
    panel.mico_said.connect(intel_ctl.wi_mico)
    blob.dropped.connect(intel_ctl.file_dropped)          # файл на Mico AI — Mico AI его читает и пересказывает

    # Mico AI: помощник по буферу обмена и реакция на ошибки — раз в 2 секунды, только в режиме Mico AI
    help_t = QTimer()

    def help_tick():
        if not intel_ctl.on():
            return
        now = time.time()
        intel_ctl.clip_seen(QGuiApplication.clipboard().text(), now)
        intel_ctl.watch_errors(errwatch.probe(os.getpid(), W.process_of), now)
        intel_ctl.expire_file(now)
        if cfg.get("wi_load_bar"):
            try:
                import psutil
                intel_ctl.set_load(psutil.cpu_percent(interval=None))
            except Exception:
                pass
    help_t.timeout.connect(help_tick)
    help_t.start(intel.ERROR_CHECK_MS)
    sleep_isl = sleep_island.SleepIsland(cfg)                # спящий Mico AI — островок сверху по центру, по нажатию просыпается
    blob.slept.connect(lambda: (sleep_isl.show_from(blob), blob.hide()))   # во сне — чёрный остров сверху по центру
    sleep_isl.wake.connect(lambda: (blob.show(), blob.wake()))
    blob.awake.connect(lambda: sleep_isl.retract_to(blob))                # проснулся по любой причине — остров втягивается
    blob.slept.connect(lambda: intel_ctl.glow.set_muted(True))            # во сне волны внизу гаснут
    blob.awake.connect(lambda: intel_ctl.glow.set_muted(False))           # проснулся — волны возвращаются
    blob.slept.connect(intel_ctl.on_sleep)               # в Intelligence Mico AI во сне исчезает, а не уходит в угол
    blob.moved.connect(lambda: panel.isVisible() and panel.reposition())   # чат всегда рядом с Mico AI, где бы он ни стоял

    # ---------- тема ----------
    state = {"dark": None}

    def apply_theme():
        dark = theme.is_dark(cfg)
        state["dark"] = dark
        app.setStyleSheet(theme.app_qss(dark))
        panel.theme()
    apply_theme()
    poll = QTimer()
    poll.timeout.connect(lambda: cfg.get("theme", "auto") == "auto" and theme.system_dark() != state["dark"]
                         and apply_theme())
    poll.start(3000)
    try:
        app.styleHints().colorSchemeChanged.connect(lambda *_: apply_theme())
    except Exception:
        pass

    hooks = SimpleNamespace(apply_theme=apply_theme)

    def open_settings():
        """Настройки открываются по центру экрана. Чат и Mico AI не двигаются: они остаются там, где стоят."""
        dlg = SettingsDialog(cfg, blob, panel, hooks)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        w, h = dlg.width(), dlg.height()
        dlg.move(scr.left() + max(10, (scr.width() - w) // 2), scr.top() + max(10, (scr.height() - h) // 2))
        dlg.exec()
        panel.refresh_chips()                       # новые кнопки видны сразу, даже если чат открыт

    blob.settings_requested.connect(open_settings)       # двойной щелчок по Mico AI — настройки

    def menu_action(item, m):
        """Один пункт меню. Пункты с галочкой отражают текущее состояние."""
        a = QAction(menu_items.LABELS[item], m)
        if item == "settings":
            a.triggered.connect(lambda *_: open_settings())
        elif item == "capabilities":
            a.triggered.connect(lambda *_: (panel.show_near(), panel.submit("что ты умеешь?")))
        elif item == "pause":
            a.setCheckable(True)
            a.setChecked(tracker.paused)
            a.toggled.connect(lambda on: setattr(tracker, "paused", on))
        elif item == "forget_hour":
            a.triggered.connect(lambda *_: store.forget(3600))
        elif item == "wipe":
            a.triggered.connect(lambda *_: _confirm_wipe(store))
        elif item == "quiet":
            a.setCheckable(True)
            a.setChecked(bool(cfg.get("quiet_mode")))
            a.toggled.connect(lambda on: (cfg.update(quiet_mode=on), save_cfg(cfg)))
        elif item == "tour":
            a.triggered.connect(lambda *_: show_tour())
        elif item == "env":
            a.triggered.connect(lambda *_: QMessageBox.information(None, "Окружение", brain.environment()))
        elif item == "about":
            ch = cfg.get("update_channel", "stable")
            a.setText(f"ℹ Mico AI {version.display_version(ch)}")
            a.triggered.connect(lambda *_: QMessageBox.information(
                None, "Mico AI", f"Версия {version.display_version(ch)}.\n\nИстория изменений: CHANGELOG.md\n"
                              f"Политика приватности: PRIVACY.md"))
        elif item == "uninstall":
            a.triggered.connect(lambda *_: installer.uninstall(app))
        elif item == "exit":
            a.triggered.connect(lambda *_: app.quit())
        return a

    def menu(pos):
        m = QMenu()
        prev_group = None
        for item in menu_items.visible(cfg):
            if item == "uninstall" and not installer.FROZEN:
                continue
            group = menu_items.GROUP[item]
            if prev_group is not None and group != prev_group:
                m.addSeparator()
            prev_group = group
            m.addAction(menu_action(item, m))
        m.exec(pos)

    blob.menu_requested.connect(menu)
    app.aboutToQuit.connect(tracker._flush)

    relaunch = _alive_instance()                # Mico AI уже работал: это разблокировка или повторный запуск
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    try:                                        # журнал последнего запуска: откуда и когда стартовал Mico AI
        with open(os.path.join(APPDIR, "start.log"), "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%d.%m.%Y %H:%M:%S')} запуск: "
                    f"{'из автозапуска' if '--autostart' in sys.argv else 'вручную'}, pid {os.getpid()}\n")
    except OSError:
        pass
    QTimer.singleShot(4000, lambda: autostart.repair_if_outdated())   # старая задача Планировщика → ключ Run

    def takeover_check():                       # если запустился новый экземпляр — этот уходит
        try:
            cur = int(open(PID_FILE, encoding="utf-8").read().strip())
        except (OSError, ValueError):
            return
        if cur != os.getpid():
            app.quit()
    pid_t = QTimer()
    pid_t.timeout.connect(takeover_check)
    pid_t.start(2000)

    def cleanup_pid():
        try:
            if int(open(PID_FILE, encoding="utf-8").read().strip()) == os.getpid():
                os.remove(PID_FILE)
        except (OSError, ValueError):
            pass
    app.aboutToQuit.connect(cleanup_pid)

    # история копирования (бета): запоминаем новые тексты из буфера; пароли и менеджеры паролей пропускаем
    clip_rec = clipbuf.Recorder(store)
    clip_t = QTimer()
    def clip_tick():
        if not features.enabled("clipboard_search", cfg):
            return
        proc = W.process_of(watcher.last_hwnd) if watcher.last_hwnd else ""
        clip_rec.offer(QGuiApplication.clipboard().text(), proc)
    clip_t.timeout.connect(clip_tick)
    clip_t.start(2000)


    # расписание переключателей (бета): раз в минуту выполняем правила, которые пора выполнить
    sched_t = QTimer()
    def sched_tick():
        if not features.enabled("schedule", cfg) or not cfg.get("schedules"):
            return
        due_rules = schedule.due(cfg["schedules"], time.time())
        if not due_rules:
            return
        save_cfg(cfg)
        for r in due_rules:
            try:
                rep = commands.handle(r["action"], lambda t: None, lambda: None)
            except Exception:
                continue
            if rep and getattr(rep, "text", ""):
                bus.info.emit(f"⏰ {rep.text}")
    sched_t.timeout.connect(sched_tick)
    sched_t.start(60000)

    # напоминание о перерыве: следит и когда Mico AI спит — тогда он просто покажется и посоветует отдохнуть
    brk = breaks.BreakWatch(start=time.time())

    def breaks_tick():
        brk.set_minutes(cfg.get("proactive_break_min", 60))
        allowed = not cfg.get("quiet_mode") and cfg.get("proactive_breaks", True)
        msg = brk.tick(time.time(), idle_seconds(), allowed)
        if msg:
            panel.initiative.emit((msg, BREAK_MARK))
    brk_t = QTimer()
    brk_t.timeout.connect(breaks_tick)
    brk_t.start(30000)


    def greet():
        blob.set_mood("happy", 5)
        blob.jump()
        if intel_ctl.on():                                   # Mico AI: приветствие строкой над Mico AI
            intel_ctl.greet(hello(), "")
        else:
            panel.show_near(activate=False)
            panel.say(hello())
        ids = cfg.get("greet_items", [])
        if "weather" in ids and cfg.get("loc_consent") is None:      # спрашиваем один раз
            ok = _box(QMessageBox.Icon.Question, "Геопозиция для погоды",
                      "Mico AI может узнать твою геопозицию, чтобы сообщать погоду.\n\n"
                      "Windows сама покажет запрос доступа. Данные используются только для погоды. "
                      "Если откажешься — возьму город из настроек.", "Разрешить", "Не сейчас")
            cfg["loc_consent"] = bool(ok)
            save_cfg(cfg)
        sync, jobs = greeting.plan(ids, cfg, store)
        for text in sync:
            panel.say(text)
        for job in jobs:
            def run(j=job):
                try:
                    text = j()
                except Exception:
                    text = None
                if text:
                    bus.info.emit(text)
            threading.Thread(target=run, daemon=True).start()

    def whats_new():
        """Один раз после обновления: что изменилось и что проверить."""
        prev = cfg.get("last_version") or (version.BASE_VERSION if existed else None)
        if prev == version.APP_VERSION:
            return
        cfg["last_version"] = version.APP_VERSION
        save_cfg(cfg)
        text = version.whats_new(prev) if prev else ""
        if text and not cfg.get("quiet_mode"):
            panel.show_near(activate=False)
            blob.set_mood("happy", 6)
            blob.jump()
            panel.say(text)

    QTimer.singleShot(8000, brain.start_digests)                                                 # пересказ прошлых дней, в фоне
    if cfg["greet_on_start"] and not relaunch and not cfg.get("quiet_mode"):
        QTimer.singleShot(700, greet)
    def open_chat_on_start():
        """При запуске Mico AI сразу открывает чат: и в обычном режиме, и в режиме Intelligence."""
        if intel_ctl.on():
            intel_ctl.show_wichat(activate=False)
        else:
            panel.show_near(activate=False)
    if not relaunch:
        QTimer.singleShot(900, open_chat_on_start)
    QTimer.singleShot(2600, whats_new)
    QTimer.singleShot(7000, start_update_check)     # после приветствия, в фоне

    def show_tour():
        panel.show_near(activate=False)
        panel.show_html(capabilities.html_tour())

    def show_onboarding():
        """Первый запуск: коротко, что умеет Mico AI, и выбор цвета. Один раз."""
        import onboarding
        dlg = onboarding.OnboardingDialog(cfg)
        dlg.exec()
        cfg["color"] = dlg.color
        cfg["tour_done"] = True
        save_cfg(cfg)
        blob.update()
        panel.theme()
        if panel.intel:
            panel.intel.restyle()

    def maybe_tour():
        """Знакомство один раз при первом запуске (если не режим тишины)."""
        if cfg.get("tour_done") or cfg.get("quiet_mode") or relaunch:
            return
        show_onboarding()
    QTimer.singleShot(9000, maybe_tour)
    _stage("цикл событий запущен")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
