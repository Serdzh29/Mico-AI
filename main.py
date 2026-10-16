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
from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, QTime, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QGuiApplication, QIcon, QImage
from PyQt6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                             QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMenu,
                             QFileDialog, QInputDialog, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSlider, QSpinBox, QTabWidget, QTextBrowser, QToolButton,
                             QVBoxLayout, QScrollArea, QSizePolicy, QTimeEdit,
                             QWidget)
import psutil
import actions, autostart, betaprogram, errwatch, intel, intel_ui, phrase, settings_info, voice, voicemodel, sleep_island, clipbuf, daysum, ghreport, schedule, menu_items, features, capabilities, chips, commands, custom, feedback, greeting, hotkeys, breaks, initiative, mailreport, report, reminders, sleepmode, theme, updatecheck, version, windows_info
import winctl as W
from actions import Reply
from blob import Blob
from brain import SUGGEST_TEXT, SUGGEST_VISION, Brain, list_models, pull_model
from emotions import detect_emotion
from follow import WindowWatcher
from storage import APPDIR, Store
from tracker import Tracker, idle_seconds

SEARCH_ENGINES = {"Google": "https://www.google.com/search?q=", "Яндекс": "https://yandex.ru/search/?text=",
                  "Bing": "https://www.bing.com/search?q=", "DuckDuckGo": "https://duckduckgo.com/?q="}

DEFAULTS = {
    "color": "#FFCFA3", "scale": 1.0, "opacity": 1.0,
    "text_model": "qwen2.5:7b", "vision_model": "qwen2.5vl:7b", "retention_days": 30,
    "greet_on_start": True, "autostart": False,
    "theme": "auto",                      # auto — как в Windows | light | dark
    "assist_style": "classic",            # classic — Mico в углу | intelligence — внизу по центру, с подсветкой экрана
    "placement": "manual",                # manual — стоит, где поставил мышкой | tl/tr/bl/br — всегда в этом углу экрана
    "chips_mode": "auto", "chips_count": 6, "chips_pinned": [], "chip_usage": {},   # кнопки под чатом
    "chips_hide_on_send": True,
    "voice_listen": True,
    "voice_wake": False, "wave_opacity": 85, "wake_words": "мико", "vosk_model_name": voicemodel.DEFAULT_MODEL,
    "conversation_sec": 12, "min_confidence": 55, "vosk_model_dir": "",                                                           # слушать «Мико» в фоне (микрофон)                                                         # кнопка микрофона в чате                                                   # скрывать после отправки запроса
    "chat_linked": True, "chat_scale": 1.0, "chat_ratio": 1.0,   # чат меняется вместе с Mico или отдельным ползунком
    "chat_outline": True,                 # обводка вокруг окна чата
    "city": "", "loc_consent": None,      # город для погоды; None — ещё не спрашивали про геопозицию
    "weather_on": True, "memory_on": True,
    "hotkey_chat": "ctrl+alt+m",   # глобальное сочетание (нужен перезапуск)
    "hotkey_screen": "ctrl+alt+s", "hotkey_window": "ctrl+alt+h",   # только для Mico WI (нужен перезапуск)
    "wi_thickness": intel.THICK_DEFAULT, "wi_waves": True, "wi_glow_style": intel.GLOW_DEFAULT,
    "wi_wave_height": intel.WAVE_HEIGHT_DEFAULT, "wi_edge_width": intel.EDGE_W_DEFAULT,            # толщина полоски и волны при ответе (WI)
    "wi_wave_source": "mico", "wi_wave_custom": intel.WAVE_DEFAULT_CUSTOM,   # откуда цвет волн: Mico, действие, свой, набор
    "wi_wave_theme": intel.WAVE_THEME_DEFAULT,                 # готовый набор волн (если выбран «Готовый набор»)
    "wi_quiet_on": False, "wi_quiet_from": "23:00", "wi_quiet_to": "08:00", "wi_load_bar": False,   # тихий час, загрузка (WI)
    "wi_clip_help": True, "wi_error_help": True,            # помощник по буферу и реакция на ошибки (WI)
    "wi_colors": dict(intel.DEFAULT_COLORS),   # цвет полоски для каждого действия WI; у действий цвета не совпадают
    "proactive_breaks": True, "proactive_break_min": 60,   # напоминание о перерыве
    "quiet_mode": False,                  # режим тишины
    "day_summary_at": "20:00", "day_summary_last": "",   # итог дня (бета): время и дата последней отправки
    "workspace": {},                     # рабочее место (бета): запомненные программы
    "update_check": True, "update_checked_at": 0,   # проверка новой версии раз в сутки (только сообщает)
    "custom_phrases": [],                          # свои фразы-команды: [{"say": "...", "do": "...; ..."}]
    "greet_items": ["recap", "weather"],           # что показывать при входе (до 3), см. greeting.py
    "initiative_on": False, "initiative_min": 15,   # Mico сам начинает разговор
    "sleep_after_min": 3,                          # через сколько минут без внимания Mico засыпает (0 — не засыпать)
    "sleep_corner": "br",                          # угол экрана, где Mico спит (tl/tr/bl/br)
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
    """Был ли Mico уже запущен (например, разблокировали экран) — тогда не здороваемся заново."""
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
                    "Вся история Mico будет удалена без возможности восстановить. Продолжить?")
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


# =============================== Чат под Mico ===============================
class ChatLog(QTextBrowser):
    """Текст чата. Если человек сам крутит колёсиком, плавная прокрутка Mico останавливается."""
    user_scrolled = pyqtSignal()

    def wheelEvent(self, e):
        self.user_scrolled.emit()
        super().wheelEvent(e)


BREAK_MARK = "__break__"             # метка: это напоминание о перерыве, а не наблюдение за экраном


class Panel(QWidget):
    answered = pyqtSignal(object)
    heard = pyqtSignal(str)
    mic_error = pyqtSignal(str)             # почему микрофон не сработал (показываем в чате)
    voice_status = pyqtSignal(str)          # статус голоса: модель грузится, голос готов (тоже в чате)
    phrase_in = pyqtSignal(str, float)      # фраза из фонового прослушивания (с уверенностью)                 # распознанная фраза с микрофона
    wake_in = pyqtSignal(float)             # услышали слово «Мико» отдельно (с уверенностью) — из фона
    wake_requested = pyqtSignal()           # Mico спит, а его позвали голосом — пора проснуться
    reminder = pyqtSignal(str)
    initiative = pyqtSignal(object)   # Mico заговорил первым: (текст, эмоция)
    busy_changed = pyqtSignal(bool)   # Mico начал или закончил думать над запросом
    chat_shown = pyqtSignal(bool)     # чат открыли или закрыли (нужно режиму Windows Intelligence)
    answer_text = pyqtSignal(str)     # текст ответа (для строки над Mico в режиме Windows Intelligence)
    user_sent = pyqtSignal(str)       # вопрос ушёл Mico (в чат Windows Intelligence)
    mico_said = pyqtSignal(str)       # Mico написал текст в обычный чат (для чата Windows Intelligence)

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
        self.fb_box = QWidget()
        fb = QHBoxLayout(self.fb_box)
        fb.setContentsMargins(0, 0, 0, 0)
        fb.addStretch()
        for text, tip, slot in (("👍", "Ответ полезен", lambda: self._vote("up")),
                                ("👎", "Ответ не помог", lambda: self._vote("down")),
                                ("⚠ Что-то не так", "Расскажи, что пошло не так", self._problem)):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            fb.addWidget(b)
        fb.addStretch()
        self.fb_box.setVisible(False)
        lay.addWidget(self.fb_box)
        self.last_pair = None                     # последний вопрос и ответ — для отзыва
        self.feedback_save = None                 # main.py: сохранить отзыв в хранилище
        self.report_with_feedback = None          # main.py: собрать отчёт с отзывами
        row = QHBoxLayout()
        self.inp = ChatInput()
        self.inp.setPlaceholderText("Напиши Mico…")
        self.inp.focused.connect(self._on_input_focus)
        send_btn = QPushButton("➤")
        send_btn.setFixedWidth(36)
        mic_btn = QPushButton("🎤")
        mic_btn.setFixedWidth(36)
        mic_btn.setToolTip("Сказать голосом")
        mic_btn.setVisible(bool(cfg.get("voice_listen", True)))
        mic_btn.clicked.connect(self.listen)
        self.mic_btn = mic_btn
        row.addWidget(self.inp)
        row.addWidget(mic_btn)
        row.addWidget(send_btn)
        lay.addLayout(row)
        self.inp.returnPressed.connect(lambda: self.submit(self.inp.text()))
        send_btn.clicked.connect(lambda: self.submit(self.inp.text()))
        self.heard.connect(self._on_heard)
        self.mic_error.connect(self.say)
        self.voice_status.connect(self.say)
        self._mic_error = ""
        self.phrase_in.connect(self._on_wake_phrase)
        self.wake_in.connect(self._on_wake_heard)
        self.listener = None                       # создаётся по настройкам (apply_voice)
        self._engine_key = None                    # (движок, модель, слова пробуждения) — при смене слушатель пересоздаётся
        self.gate = voice.ConversationGate()
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

    def _fade(self, show):
        if self._anim is not None:
            self._anim.stop()
        a = QPropertyAnimation(self, b"windowOpacity", self)
        a.setDuration(200 if show else 160)
        a.setStartValue(0.0 if show else 1.0)
        a.setEndValue(1.0 if show else 0.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic if show else QEasingCurve.Type.InCubic)
        if not show:
            a.finished.connect(lambda: (self.hide(), self.setWindowOpacity(1.0)))
        self._anim = a
        a.start()

    def hide_smooth(self):
        if self.isVisible():
            self.chat_shown.emit(False)
            self._fade(False)

    def chat_factor(self):
        """Во сколько раз чат больше/меньше базового размера: вместе с Mico или отдельным ползунком."""
        if self.cfg.get("chat_linked", True):
            return max(0.6, self.cfg.get("scale", 1.0))     # вместе с Mico: тот же размер, что у Mico
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
        self.blob.notify_typing()                   # Mico смотрит на строку ввода и интересуется
        self.blob.set_mood("curious", 3)
        self.blob.set_look(self.inp.mapToGlobal(self.inp.rect().center()))

    def theme(self):
        dark = theme.is_dark(self.cfg)
        self.setStyleSheet(theme.panel_qss(self.cfg["color"], dark, self.cfg.get("chat_outline", True),
                                           self.chat_factor()))
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
        self.move(max(g.left(), min(x, g.right() - self.width())), max(g.top(), y))

    def show_near(self, activate=True):
        if self.intel and self.intel.on():          # в Windows Intelligence открывается свой чат, не этот
            self.intel.show_wichat(activate)
            return
        self.blob.touch()
        if self.blob.asleep:                        # чат открывают — Mico просыпается, но не повторяет «woke»
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
        if self.windowOpacity() < 1.0:
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
        self.fb_box.setVisible(False)
        if self.cfg.get("chips_hide_on_send", True):      # кнопки скрыты, пока не нажмут в поле ввода
            self._chips_hidden = True
            self.chips_box.setVisible(False)
        self.last_pair = {"q": q, "a": ""}
        self.inp.clear()
        self.log.append(f"<p align='right'><b>Вы:</b> {html.escape(q)}</p>")
        self.user_sent.emit(q)
        self.busy = True
        self.busy_changed.emit(True)
        m = detect_emotion(q)                       # Mico реагирует на настроение сообщения
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
                    time.sleep(0.45)                # дать Mico и чату исчезнуть с экрана
                self.answered.emit(self.brain.ask(q))
            except Exception as e:
                self.answered.emit(Reply(f"Ой, что-то пошло не так: {e}", "worried"))
        threading.Thread(target=work, daemon=True).start()

    def _vote(self, kind):
        lp = self.last_pair or {"q": "", "a": ""}
        if self.feedback_save:
            self.feedback_save(kind, "", lp["q"], lp["a"])
        self.fb_box.setVisible(False)
        self.say("Спасибо за отзыв 🙏")

    def _problem(self):
        text, ok = QInputDialog.getMultiLineText(self, "Что-то не так", "Что ты ожидал и что получилось?")
        if not ok or not text.strip():
            return
        lp = self.last_pair or {"q": "", "a": ""}
        if self.feedback_save:
            self.feedback_save("problem", text, lp["q"], lp["a"])
        self.fb_box.setVisible(False)
        if self.report_with_feedback and QMessageBox.question(
                self, "Журналы", "Сохранить отчёт на рабочий стол, чтобы отправить его разработчику?\n\n"
                "Он содержит журналы (в них могут быть пути к файлам) и твой отзыв. Сам Mico ничего не отправляет.") \
                == QMessageBox.StandardButton.Yes:
            self.report_with_feedback(text)
        else:
            QMessageBox.information(self, "Спасибо", "Отзыв сохранён на твоём ПК.")

    def explain(self, text):
        """Mico сам говорит пояснение в чате (без отдельных окон)."""
        self.show_near(activate=False)
        self.say(text)

    def show_html(self, html_text):
        """Показать готовый блок (знакомство, список возможностей) без вопроса пользователя."""
        self.queue.append(("html", html_text))
        self._pump()

    def apply_voice(self):
        """Включает и выключает прослушивание по настройкам (при запуске и после «Сохранить»). Только Vosk."""
        want = bool(self.cfg.get("voice_wake")) and bool(self.cfg.get("voice_listen", True))
        self.gate.window = int(self.cfg.get("conversation_sec", 12))
        model = self.cfg.get("vosk_model_dir") or ""
        words = tuple(voice.wake_words_from(self.cfg.get("wake_words")))
        key = (model, words)
        try:
            if self.listener is not None and (not want or self._engine_key != key):
                self.listener.stop()
                self.listener = None
            if want and self.listener is None:
                problem = voice.vosk_problem(model)
                if problem:
                    self.mic_error.emit(problem)
                    return
                self.listener = voice.VoskListener(model, self._emit_phrase, on_wake=self._emit_wake,
                                                   wake_words=words, on_error=self.mic_error.emit,
                                                   on_status=self.voice_status.emit)
                self._engine_key = key
                self.listener.start()
        except Exception as e:                       # не молчим: причину показываем в чате
            self.mic_error.emit(f"Голос не запустился: {e}")

    def _emit_phrase(self, text, conf):
        self.phrase_in.emit(text, float(conf))

    def _emit_wake(self, conf):
        self.wake_in.emit(float(conf))

    def _on_wake_heard(self, conf):
        """Слово «Мико» услышано отдельно: спящего будим, а дальше понимаем команду в окне разговора."""
        if conf < voice.WAKE_MIN_CONFIDENCE or self.busy:
            return
        if self.blob.asleep:
            self.wake_requested.emit()
        self.gate.open(time.time())
        self.say("Слушаю 🎤")

    def _on_wake_phrase(self, text, conf):
        """Фраза из фона. «Мико, …» — команда; без «Мико» — только в окне разговора (после слова «Мико»).
        Слово «Мико» в чат не попадает: в запрос идёт только команда. Спит — слушаем только «Мико».
        Пока Mico занят ответом, его собственный голос не слушаем (речи нет, но ответ может обрабатываться)."""
        words = voice.wake_words_from(self.cfg.get("wake_words"))
        minimum = int(self.cfg.get("min_confidence", 55)) / 100.0
        now = time.time()
        in_window = self.gate.is_open(now)
        # В окне разговора принимаем и искажённые варианты «Мико» («ником», «никакой»): они только в начале фразы.
        wake, cmd = voice.parse_wake(text, words, loose=in_window)
        if wake and not cmd:                       # одно слово «Мико» распознаётся неуверенно — порог ниже
            minimum = min(minimum, voice.WAKE_MIN_CONFIDENCE)
        if not voice.accept_phrase(text, conf, minimum):
            return
        if self.busy:
            return
        if self.blob.asleep and not wake:          # спит: без слова «Мико» ничего не делаем
            return
        if wake:
            if self.blob.asleep:
                self.wake_requested.emit()
            if not cmd:                            # сказали только «Мико» — ждём команду, в чат ничего не пишем
                self.gate.open(now)
                self.say("Слушаю 🎤")
                return
        elif in_window:
            cmd = text
        else:
            return
        self.gate.open(now)
        cmd = voice.normalize_dictation(cmd)
        if cmd:
            self.submit(cmd)

    def listen(self):
        """Кнопка микрофона: слушаем одну фразу в фоне, распознанный текст уходит в чат как запрос."""
        if not self.cfg.get("voice_listen", True):
            return
        self.inp.setPlaceholderText("Слушаю…")
        self.mic_btn.setEnabled(False)

        def work():
            try:
                text, err = voice.listen_once(self.cfg, 8)
                text = voice.strip_wake(text, voice.wake_words_from(self.cfg.get("wake_words")))
            except Exception as e:
                text, err = "", f"Микрофон не запустился: {e}"
            self._mic_error = err
            self.heard.emit(text)
        threading.Thread(target=work, daemon=True).start()

    def _on_heard(self, text):
        self.inp.setPlaceholderText("Напиши Mico…")
        self.mic_btn.setEnabled(True)
        if text:
            self.submit(text)
        else:
            self.say(self._mic_error or "Не расслышал. Нажми 🎤 и скажи ещё раз.")
        self._mic_error = ""

    def on_answer(self, r):
        if r is None:                                           # модель ничего не вернула — не молчим
            r = Reply("Ответа нет. Попробуй сказать иначе.", "worried")
        self.busy = False
        self.busy_changed.emit(False)
        if not r.text and not r.html and not r.image:
            r = Reply("Ответа нет. Попробуй сказать иначе.", "worried")
        plain = r.text or intel.plain_from_html(r.html) if r.html else r.text
        if plain:
            self.answer_text.emit(plain)                        # Mico WI: строка над Mico, чат — для длинного
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
            self.queue.append(("html", "<b>Mico:</b><br>" + r.html))
            self.queue.append(("wi", plain))                    # тот же ответ — текстом в чат WI
        else:
            self.queue.append(("text", r.text))
        if r.image:
            self.queue.append(("html", f'<img src="{QUrl.fromLocalFile(r.image).toString()}" width="300">'))
        self._pump()
        if self.last_pair is not None and not r.image:
            self.fb_box.setVisible(True)

    def on_initiative(self, payload):
        """Mico сам что-то увидел и говорит первым — тихо, без захвата фокуса.
        Перерыв приходит с меткой BREAK_MARK. В режиме Mico WI — полоской по краю экрана."""
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
        self.blob.wake(silent=True)                 # уведомление будит спящего Mico, но чат сам не открывает
        self.blob.set_mood("surprised", 8)
        self.blob.jump()
        self.say("⏰ " + text[:1].upper() + text[1:])

    def on_link(self, url):
        scheme, _, rest = url.toString().partition(":")
        path = unquote(rest)
        try:
            if scheme == "mico-do":                 # нажали пример из списка возможностей — выполняем его
                self.submit(path)
            elif scheme == "mico-info":             # «?» у бета-функции — Mico объясняет в чате
                self.explain(features.explain(path))
            elif scheme == "mico-open":
                os.startfile(path)
            elif scheme == "mico-dir":
                subprocess.Popen(["explorer", f"/select,{path}"])
        except Exception:
            pass

    # ----- «печатающий» ответ: Mico говорит ртом -----
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
                self.log.append("<b>Mico:</b><br>" + html.escape(val).replace("\n", "<br>") + "<br>")
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
    "linked": ("Чат меняется вместе с Mico",
               "Один ползунок меняет размер и шара, и окна чата.",
               "включи, если хочешь всё крупнее или мельче сразу. Выключи, если нужен большой чат и маленький шар."),
    "outline": ("Обводка вокруг чата",
                "Цветная рамка вокруг окна чата. Только внешний вид.",
                "выключи для минималистичного вида, включи, чтобы чат был заметнее на фоне."),
    "locc": ("Геопозиция для погоды",
             "Windows отдаёт Mico координаты, чтобы узнать погоду в твоём месте.",
             "включи, если хочешь погоду без ввода города. Выключи — тогда укажи город вручную."),
    "greet": ("Здороваться при включении ПК",
              "При входе в Windows Mico говорит «Добрый день» или «Добрый вечер» и показывает пункты приветствия.",
              "включи, если приятно видеть приветствие. Выключи для тихого запуска."),
    "auto": ("Запуск с Windows",
             "Mico стартует сам при входе в Windows и после разблокировки экрана.",
             "включи, если пользуешься Mico каждый день. Выключи, если запускаешь его вручную."),
    "mem": ("Запоминать действия",
            "Mico записывает твои команды и открытые программы (зашифровано) и учится на привычках.",
            "включи для подсказок, кнопок и «что я делал». Выключи, если не хочешь записей: тогда эти функции не работают."),
    "ini": ("Инициатива",
            "Mico сам заговаривает, если на экране что-то интересное. Для этого раз в несколько минут смотрит на экран локальной моделью.",
            "включи, если нравится живой компаньон. Выключи на слабом ПК или если отвлекает."),
    "pbr": ("Напоминание о перерыве",
            "Mico напомнит отдохнуть, если работаешь без остановки дольше заданного времени.",
            "включи, если забываешь делать перерывы."),
    "quiet": ("Режим тишины",
              "Mico не здоровается, не предлагает помощь и не заговаривает первым. Напоминания, которые ты сам поставил, работают.",
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
        self.setWindowTitle("О программе Mico")
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        channel = "бета-канал" if cfg.get("update_channel") == "beta" else "стабильный канал"
        head = QLabel(f"<b style='font-size:16px'>Mico {version.display_version(cfg.get('update_channel', 'stable'))}</b>"
                      f"<br><span style='color:#8f8f8f'>{channel}</span>")
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


class WrapCheck(QWidget):
    """Галочка с переносимым текстом. Длинная подпись переносится на новую строку, а не растягивает окно."""
    toggled = pyqtSignal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self._cb = QCheckBox()
        self._lbl = ClickLabel(text)
        self._lbl.setWordWrap(True)
        self._lbl.clicked.connect(self._cb.toggle)
        lay.addWidget(self._cb, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self._lbl, 1)
        self._cb.toggled.connect(self.toggled)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def isChecked(self):
        return self._cb.isChecked()

    def setChecked(self, on):
        self._cb.setChecked(on)

    def setToolTip(self, text):
        super().setToolTip(text)
        self._cb.setToolTip(text)
        self._lbl.setToolTip(text)


SETTINGS_SIZES = [("compact", "Компактное", (560, 600)), ("medium", "Обычное", (660, 740)),
                  ("large", "Просторное", (820, 880))]


def ask_beta_consent(parent):
    """Бета-канал включается только после согласия. Возвращает True, если человек согласился."""
    return QMessageBox.question(parent, "Бета-канал", features.BETA_CONSENT_TEXT + "\n\nСогласен?") \
        == QMessageBox.StandardButton.Yes


class BetaReportDialog(QDialog):
    """Отзыв бета-тестера на GitHub. Текст показываем целиком: его можно поправить, и ничего не уходит,
    пока человек не нажмёт «Открыть GitHub». Обсуждения на GitHub публичны — это написано прямо в окне."""

    def __init__(self, parent, cfg):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Отзыв о бете")
        self.resize(580, 480)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("<b>Что отправляем</b>"))
        self.kind = QComboBox()
        self.kind.addItem("Ошибка или сбой", "bug")
        self.kind.addItem("Как я пользуюсь бетой", "usage")
        self.kind.currentIndexChanged.connect(self.rebuild)
        v.addWidget(self.kind)
        self.log = QCheckBox("Приложить последние строки журнала ошибок (пути к файлам будут скрыты)")
        self.log.toggled.connect(self.rebuild)
        v.addWidget(self.log)
        self.text = QPlainTextEdit()
        v.addWidget(self.text)
        self.warn = QLabel("")
        self.warn.setWordWrap(True)
        v.addWidget(self.warn)
        hint = QLabel("Отзыв публичен: его увидят все на GitHub. Проверь текст и поправь, что нужно. "
                      "Ничего не отправится, пока ты не нажмёшь «Открыть GitHub».")
        hint.setWordWrap(True)
        v.addWidget(hint)
        row = QHBoxLayout()
        copy_btn = QPushButton("Скопировать текст")
        copy_btn.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.text.toPlainText()))
        open_btn = QPushButton("Открыть GitHub")
        open_btn.clicked.connect(self.open_github)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(copy_btn)
        row.addStretch(1)
        row.addWidget(cancel_btn)
        row.addWidget(open_btn)
        v.addLayout(row)
        self.rebuild()

    def _log_tail(self):
        for name in ("crash.log", "startup.log"):
            try:
                lines = open(_os.path.join(_mico_dir(), name), encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            if lines:
                return "\n".join(lines[-30:])
        return ""

    def rebuild(self):
        import platform
        kind = self.kind.currentData()
        body = ghreport.build_body(kind, version.APP_VERSION, version.BUILD_CHANNEL,
                                   f"Windows, сборка {platform.version()}", self.cfg.get("beta_usage", {}),
                                   self._log_tail() if (kind == "bug" and self.log.isChecked()) else "")
        self.text.setPlainText(body)
        self.warn.setText("Текст длинный: в ссылку войдёт только начало. Лучше нажми «Скопировать текст» "
                          "и вставь его в обсуждение вручную." if ghreport.is_too_long(body) else "")

    def open_github(self):
        body = self.text.toPlainText()
        webbrowser.open(ghreport.issue_url(version.ISSUES_REPO, self.kind.currentData(), body))
        self.accept()


class SettingsDialog(QDialog):
    status = pyqtSignal(str)
    model_msg = pyqtSignal(str)            # статус скачивания голосовой модели (из фонового потока)
    pulled = pyqtSignal(str)

    def __init__(self, cfg, blob, panel, hooks, parent=None):
        super().__init__(parent)
        self.cfg, self.blob, self.panel, self.hooks, self.orig = cfg, blob, panel, hooks, dict(cfg)
        self.join_request = False                       # после «Сохранить» — установить бету (см. open_settings)
        self.setWindowTitle("Настройки Mico")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(520, 420)
        self._apply_size(cfg.get("settings_size", "medium"))
        wi_on = intel.style_of(cfg.get("assist_style")) == intel.INTELLIGENCE
        self._style_dialog()
        self._reg = {}                                  # ключ настройки → её элемент (для кнопки «Сбросить»)
        root = QVBoxLayout(self)
        if wi_on:
            root.addWidget(self._wi_header())
        tabs = QTabWidget()
        root.addWidget(tabs)

        # --- Внешний вид ---
        look = QWidget()
        f = QFormLayout(look)
        self.assist = NoWheelComboBox()
        self.assist.addItem("Обычный — Mico в углу", intel.CLASSIC)
        self.assist.addItem("Mico · WI (BETA) — внизу, с подсветкой", intel.INTELLIGENCE)
        self.assist.setCurrentIndex(max(0, self.assist.findData(intel.style_of(cfg.get("assist_style")))))
        self.assist.currentIndexChanged.connect(self.live_assist)
        self._row(f, "Режим", self.assist, "assist_style")
        self.cbtn = QPushButton()
        self.cbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cbtn.clicked.connect(self.pick)
        self._paint_accent_btn()
        self._row(f, "Цвет Mico", self.cbtn, "color")
        self.sc = NoWheelSlider(Qt.Orientation.Horizontal)
        self.sc.setRange(40, 200)
        self.sc.setValue(int(cfg["scale"] * 100))
        self.op = NoWheelSlider(Qt.Orientation.Horizontal)
        self.op.setRange(30, 100)
        self.op.setValue(int(cfg["opacity"] * 100))
        for s in (self.sc, self.op):
            s.valueChanged.connect(self.live)
        self._row(f, "Размер Mico", with_readout(self.sc, " %"), "scale")
        self.linked = WrapCheck("Чат меняется вместе с Mico (один ползунок)")
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
        self.th = NoWheelComboBox()
        for key, name in (("auto", "Как в системе (Windows)"), ("light", "Светлая"), ("dark", "Тёмная")):
            self.th.addItem(name, key)
        self.th.setCurrentIndex(max(0, self.th.findData(cfg.get("theme", "auto"))))
        self.th.currentIndexChanged.connect(self.live_theme)
        self._row(f, "Тема чата и окон", self.th, "theme")
        self.size_pick = NoWheelComboBox()
        for key, title, _ in SETTINGS_SIZES:
            self.size_pick.addItem(title, key)
        self.size_pick.setCurrentIndex(max(0, self.size_pick.findData(cfg.get("settings_size", "medium"))))
        self.size_pick.currentIndexChanged.connect(lambda _: self._apply_size(self.size_pick.currentData()))
        self._row(f, "Размер окна настроек", self.size_pick, "settings_size")
        self.outline = WrapCheck("Обводка вокруг окна чата")
        self.outline.setChecked(cfg.get("chat_outline", True))
        self.outline.toggled.connect(self.live_outline)
        f.addRow(self._hc(self.outline, "outline"))

        # --- Поведение ---
        beh = QWidget()
        f = QFormLayout(beh)
        self.plc = NoWheelComboBox()
        self.plc.addItem("Сам перетаскиваю — стоит, где поставил", "manual")
        for k, name in sleepmode.CORNERS.items():
            self.plc.addItem(name + " угол экрана", k)
        self.plc.setCurrentIndex(max(0, self.plc.findData(cfg.get("placement", "manual"))))
        self.plc.currentIndexChanged.connect(self.live_placement)
        self._row(f, "Положение", self.plc, "placement")
        self.plc.setEnabled(intel.style_of(cfg.get("assist_style")) != intel.INTELLIGENCE)   # в Intelligence место задано режимом
        f.addRow(QLabel("<small>В выбранном углу Mico всегда возвращается туда, даже если его потащить мышкой.</small>"))
        self.se = NoWheelComboBox()
        self.se.addItems(list(SEARCH_ENGINES))
        cur = next((n for n, u in SEARCH_ENGINES.items() if u == cfg.get("search_url")), "Google")
        self.se.setCurrentText(cur)
        self._row(f, "Поиск в интернете", self.se, "search_url")
        self.greet = WrapCheck("Здороваться при включении ПК (день/вечер, погода, что делал вчера)")
        self.greet.setChecked(cfg["greet_on_start"])
        self.auto = WrapCheck("Запускать вместе с Windows (вход в систему)")
        self.auto.setChecked(autostart.status()[0])        # показываем то, что реально стоит в Планировщике
        self.keep = NoWheelComboBox()                     # сколько хранить историю; «всегда» — без очистки
        for days, text in ((7, "7 дней"), (30, "30 дней"), (90, "90 дней"), (365, "365 дней"), (0, "всегда")):
            self.keep.addItem(text, days)
        if self.keep.findData(cfg["retention_days"]) < 0:      # значение из файла, которого нет в списке
            self.keep.addItem(f"{cfg['retention_days']} дн.", cfg["retention_days"])
        self.keep.setCurrentIndex(self.keep.findData(cfg["retention_days"]))
        f.addRow(self._hc(self.greet, "greet"))
        f.addRow(self._hc(self.auto, "auto"))
        self._row(f, "Хранить историю", self.keep, "retention_days")
        self.sleep_min = NoWheelSpinBox()
        self.sleep_min.setRange(0, 30)
        self.sleep_min.setSuffix(" мин (0 — не засыпать)")
        self.sleep_min.setValue(cfg.get("sleep_after_min", 3))
        self._row(f, "Засыпать, если никто не обращается", self.sleep_min, "sleep_after_min")
        self.slc = NoWheelComboBox()
        for k, name in sleepmode.CORNERS.items():
            self.slc.addItem(name + " угол экрана", k)
        self.slc.setCurrentIndex(max(0, self.slc.findData(cfg.get("sleep_corner", "br"))))
        self.slc.currentIndexChanged.connect(self.live_placement)
        self._row(f, "Во сне прячется", self.slc, "sleep_corner")
        pp = QWidget()                                  # отдельная вкладка: программа предварительной оценки
        self._beta_page = pp                            # держим ссылку: в стабильной сборке вкладки нет,
                                                        # и без ссылки pp удалялся бы вместе с beta_pick
        fp = QFormLayout(pp)
        self.beta_pick = WrapCheck("Участвовать в программе: бета-канал (новые функции раньше, возможны сбои)")
        self.beta_pick.setChecked(cfg.get("update_channel") == "beta")
        fp.addRow(self.beta_pick)
        pp_info = QLabel("Включив бету, Mico скачает бета-сборку с новыми функциями и переустановится — "
                         "Mico возьмёт бета-сборку с адреса разработчика. Перед этим попросим согласие: "
                         "ошибки и отзывы о бета-функциях уходят разработчику только по твоему действию. "
                         "Выключить можно в любой момент — вернёшься на стабильный канал.")
        pp_info.setWordWrap(True)
        fp.addRow(pp_info)
        now_ch = "бета" if cfg.get("update_channel") == "beta" else "стабильный"
        self.beta_now = QLabel(f"Сейчас: {now_ch} канал · Mico {version.display_version(cfg.get('update_channel', 'stable'))}")
        fp.addRow(self.beta_now)
        report_btn = QPushButton("Отправить отзыв на GitHub…")
        report_btn.clicked.connect(lambda: BetaReportDialog(self, cfg).exec())
        fp.addRow(report_btn)
        self.quiet = WrapCheck("Режим тишины: без приветствий, инициативы и подсказок")
        self.quiet.setChecked(cfg.get("quiet_mode", False))
        f.addRow(self._hc(self.quiet, "quiet"))
        self.updchk = WrapCheck("Проверять новые версии Mico при запуске (раз в сутки, без скачивания)")
        self.updchk.setChecked(cfg.get("update_check", True))
        f.addRow(self._block(self.updchk, "update_check"))
        f.addRow(QLabel("<b>Меню по правому щелчку</b>"))
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
        self.hk_chat = QLineEdit(cfg.get("hotkey_chat", "ctrl+alt+m"))
        self._row(f, "Горячая клавиша: открыть чат", self.hk_chat, "hotkey_chat")
        f.addRow(QLabel("<small>Например ctrl+alt+m. Нужно сочетание с Ctrl, Alt, Shift или Win. "
                        "Применится после перезапуска Mico.</small>"))

        # --- Умное: погода, память, инициатива ---
        smart = QWidget()
        f = QFormLayout(smart)
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
        self.mem = WrapCheck("Запоминать мои команды и программы и учиться на привычках")
        self.mem.setChecked(cfg.get("memory_on", True))
        f.addRow(self._hc(self.mem, "mem"))
        f.addRow(QLabel("<small>Журнал зашифрован и хранится только на этом ПК. «Удалить всю историю» — в меню Mico.</small>"))
        self.ini = WrapCheck("Mico сам начинает разговор, если увидит на экране что прокомментировать")
        self.ini.setChecked(cfg.get("initiative_on", False))
        self.ini_min = NoWheelSpinBox()
        self.ini_min.setRange(5, 240)
        self.ini_min.setSuffix(" мин")
        self.ini_min.setValue(cfg.get("initiative_min", 15))
        if features.enabled("initiative", cfg):         # инициатива — бета-функция: на стабильном канале её нет
            f.addRow(self._hc(self.ini, "ini"))
            self._row(f, "Как часто проверять экран", self.ini_min, "initiative_min")
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
        ph = QWidget()
        v = QVBoxLayout(ph)
        v.addWidget(QLabel("<b>Свои фразы-команды</b>. Напиши фразу — Mico выполнит шаги по порядку. "
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
        self.cmode.addItem("Mico подбирает сам (по моим привычкам)", "auto")
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
        f.addRow(QLabel("<small>Mico учится по тому, какие кнопки и команды ты используешь. "
                        "Вручную выбранный набор работает, пока не переключишь режим на «подбирает сам».</small>"))

        # --- Модели ---
        mod = QWidget()
        f = QFormLayout(mod)
        installed = list_models()
        self.tm = self._combo(installed, SUGGEST_TEXT, cfg["text_model"])
        self.vm = self._combo(installed, SUGGEST_VISION, cfg["vision_model"])
        self._row(f, "Модель для общения", self.tm, "text_model")
        self._row(f, "Модель для экрана (VLM)", self.vm, "vision_model")
        f.addRow(QLabel("<small>Сверху — установленные модели, ниже — рекомендуемые (их нужно скачать). "
                        "Можно вписать любое имя из ollama.com/library.</small>"))
        self.pull_edit = QLineEdit()
        self.pull_edit.setPlaceholderText("например qwen2.5:14b")
        pb = QPushButton("Скачать модель")
        pb.clicked.connect(self.pull)
        row = QHBoxLayout()
        row.addWidget(self.pull_edit)
        row.addWidget(pb)
        f.addRow("Скачать", row)
        self.stat = QLabel("")
        f.addRow(self.stat)

        def page(*sections):
            """Страница вкладки из карточек: каждая секция — группа с заголовком."""
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(6, 6, 6, 6)
            v.setSpacing(8)
            for widget, title in sections:
                gb = QGroupBox(title)
                lay = QVBoxLayout(gb)
                lay.addWidget(widget)
                v.addWidget(gb)
            v.addStretch()
            sc = QScrollArea()                       # при уменьшении окна содержимое прокручивается
            sc.setWidgetResizable(True)
            sc.setFrameShape(QFrame.Shape.NoFrame)
            sc.setWidget(w)
            return sc

        tabs.addTab(page((look, "Mico и чат"), (self._wi_colors_box(cfg), "Полоска Mico WI")), "Вид")
        if wi_on:                                       # только для WI: тишина, загрузка и то, что нового в WI
            tabs.insertTab(0, page((self._wi_rhythm_box(cfg), "Тишина и загрузка")), "Mico · WI (BETA)")
            tabs.addTab(self._news_page(), "Что нового")
        tabs.addTab(page((beh, "Поведение и запуск")), "Основные")
        tabs.addTab(page((self._voice_box(cfg), "Голос и речь")), "Голос")
        tabs.addTab(page((ph, "Свои фразы"), (btn, "Кнопки под чатом"),
                         (smart, "Погода, память, приветствие")), "Функции")
        if version.BUILD_CHANNEL == "beta":                 # в стабильной сборке вкладки беты нет
            tabs.addTab(page((pp, betaprogram.TITLE)), "Бета")
        tabs.addTab(page((mod, "Модели Ollama")), "Модели")

        for form in self.findChildren(QFormLayout):
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setVerticalSpacing(6)
            form.setHorizontalSpacing(12)
        self._fit_widgets()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_b = bb.button(QDialogButtonBox.StandardButton.Save)
        save_b.setText("Сохранить")
        save_b.setObjectName("primary")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        reset_b = bb.addButton("Сбросить настройки", QDialogButtonBox.ButtonRole.ActionRole)
        reset_b.clicked.connect(self.reset_settings)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        # два ряда: сверху версия и «О программе», снизу кнопки — так при компактном окне ничего не обрезается
        ver = QLabel(f"Mico {version.display_version(cfg.get('update_channel', 'stable'))}")
        ver.setObjectName("hint")
        about_b = QPushButton("О программе")
        about_b.setObjectName("flat")
        about_b.setCursor(Qt.CursorShape.PointingHandCursor)
        about_b.clicked.connect(lambda: AboutDialog(self, self.cfg).exec())
        top = QHBoxLayout()
        top.addWidget(ver)
        top.addStretch()
        top.addWidget(about_b)
        root.addLayout(top)
        root.addWidget(bb)
        self.status.connect(self.stat.setText)
        self.pulled.connect(self.on_pulled)
        self.live_placement()

    def _live_wave(self, value):
        """Ползунок двигается — волны меняются сразу, без «Сохранить»."""
        self.cfg["wave_opacity"] = int(value)
        glow = getattr(getattr(self.panel, "intel", None), "glow", None)
        if glow is not None:
            glow.update()

    def _voice_box(self, cfg):
        """Голос: что Mico слушает, как говорит и как распознаёт. Модель Vosk можно скачать или выбрать вручную."""
        box = QWidget()
        f = QFormLayout(box)
        self.vlisten = WrapCheck("Голос включён (кнопка 🎤 и голосовые команды)")
        self.vlisten.setChecked(bool(cfg.get("voice_listen", True)))
        f.addRow(self._block(self.vlisten, "voice_listen"))
        self.vwake = WrapCheck("Слушать «Мико» в фоне (микрофон включён)")
        self.vwake.setChecked(bool(cfg.get("voice_wake", False)))
        f.addRow(self._block(self.vwake, "voice_wake"))
        self.vconv = NoWheelSpinBox()
        self.vconv.setRange(0, 60)
        self.vconv.setSuffix(" сек")
        self.vconv.setSpecialValueText("выключено")
        self.vconv.setValue(int(cfg.get("conversation_sec", 12)))
        self._row(f, "Окно разговора без «Мико»", self.vconv, "conversation_sec")
        self.vconf = NoWheelSpinBox()
        self.vconf.setRange(0, 100)
        self.vconf.setSuffix(" %")
        self.vconf.setValue(int(cfg.get("min_confidence", 55)))
        self._row(f, "Насколько уверен, чтобы выполнить", self.vconf, "min_confidence")
        # модель Vosk: несколько размеров, от лёгкой до самой точной
        self.model_dir_value = cfg.get("vosk_model_dir", "") or ""
        self.model_name_value = voicemodel.model_name_of(cfg.get("vosk_model_name", ""))
        self.model_pick = NoWheelComboBox()
        for name, info in voicemodel.MODELS.items():
            size = info["size_mb"]
            size_txt = f"~{size / 1000:.1f} ГБ" if size >= 1000 else f"~{size} МБ"
            self.model_pick.addItem(f"{info['title']} · {size_txt}", name)
        self.model_pick.setCurrentIndex(max(0, self.model_pick.findData(self.model_name_value)))
        self.model_pick.currentIndexChanged.connect(self._model_pick_changed)
        status = QLabel("")
        status.setWordWrap(True)
        self.model_status = status
        self._refresh_model_status()
        self.model_msg.connect(self._model_msg_show)
        btns = QWidget()
        bl = QHBoxLayout(btns)
        bl.setContentsMargins(0, 0, 0, 0)
        b_dl = QPushButton("Скачать модель")
        b_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        b_dl.clicked.connect(self._download_model)
        b_file = QPushButton("Выбрать файл вручную…")
        b_file.setCursor(Qt.CursorShape.PointingHandCursor)
        b_file.clicked.connect(self._pick_model)
        bl.addWidget(b_dl)
        bl.addWidget(b_file)
        hint = QLabel("Точнее — значит больше места на диске и памяти. После смены модели нажми «Сохранить».")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow("Модель Vosk", self.model_pick)
        f.addRow("", hint)
        f.addRow("", btns)
        f.addRow("", status)
        return box

    def _model_pick_changed(self, _=None):
        """Выбрали другую модель: если она уже на диске — сразу указываем её; если нет — покажем, что надо скачать."""
        self.model_name_value = self.model_pick.currentData() or voicemodel.DEFAULT_MODEL
        self.model_dir_value = voicemodel.default_dir(APPDIR, self.model_name_value)
        self._refresh_model_status()

    def _refresh_model_status(self):
        if voicemodel.is_installed(self.model_dir_value):
            self.model_status.setText(f"✓ Модель установлена: {self.model_dir_value}")
        else:
            self.model_status.setText("Модель не установлена. Нажми «Скачать модель» или выбери файл вручную.")

    def _model_msg_show(self, text):
        self.model_status.setText(text)

    def _download_model(self):
        """Скачивание в фоне. Если не вышло — пишем конкретную причину и предлагаем файл вручную."""
        self.model_msg.emit("Скачиваю модель с alphacephei.com…")

        def prog(done, total):
            mb = done // (1024 * 1024)
            self.model_msg.emit(f"Скачиваю модель: {mb} МБ" + (f" из {total // (1024 * 1024)} МБ" if total else ""))

        name = self.model_name_value

        def work():
            ok, res = voicemodel.fetch_model(APPDIR, progress=prog, name=name)
            if ok:
                self.model_dir_value = res
                self.model_msg.emit(f"✓ Модель установлена: {res}")
            else:
                self.model_msg.emit(f"✗ Не получилось скачать: {res}. Можно выбрать файл вручную.")
        threading.Thread(target=work, daemon=True).start()

    def _pick_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбери архив модели Vosk", "", "Архив модели (*.zip)")
        if not path:
            return
        ok, res = voicemodel.install_from_file(path, APPDIR)
        if ok:
            self.model_dir_value = res
            self.model_msg.emit(f"✓ Модель установлена: {res}")
        else:
            self.model_msg.emit(f"✗ Не получилось установить: {res}")

    def _wi_colors_box(self, cfg):
        """Цвета полоски Mico WI: у каждого действия свой. Занятый цвет выбрать нельзя."""
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
        self.wi_wh = NoWheelSlider(Qt.Orientation.Horizontal)              # толщина самих волн
        self.wi_wh.setRange(intel.WAVE_HEIGHT_MIN, intel.WAVE_HEIGHT_MAX)
        self.wi_wh.setValue(intel.wave_height(cfg))
        self.wi_wh_lbl = QLabel(f"{intel.wave_height(cfg)} %")
        self.wi_wh_lbl.setObjectName("readout")
        self.wi_wh.valueChanged.connect(self._wi_wave_height_changed)
        wrow = QHBoxLayout()
        wrow.addWidget(self.wi_wh, 1)
        wrow.addWidget(self.wi_wh_lbl)
        f.addRow("Толщина волн", wrow)
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
        self.wi_thick = NoWheelSlider(Qt.Orientation.Horizontal)
        self.wi_thick.setRange(intel.THICK_MIN, intel.THICK_MAX)
        self.wi_thick.setValue(intel.thickness(cfg))
        self.wi_thick_lbl = QLabel(f"{intel.thickness(cfg)} px")
        self.wi_thick_lbl.setObjectName("readout")
        self.wi_thick.valueChanged.connect(self._wi_thick_changed)
        trow = QHBoxLayout()
        trow.addWidget(self.wi_thick, 1)
        trow.addWidget(self.wi_thick_lbl)
        f.addRow("Высота свечения внизу (волны)", trow)
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
        self.wi_clip = QCheckBox("Помощник по буферу: предлагает объяснить текст ошибки")
        self.wi_clip.setChecked(bool(cfg.get("wi_clip_help", True)))
        self.wi_clip.toggled.connect(lambda on: self.cfg.update(wi_clip_help=bool(on)))
        f.addRow(self.wi_clip)
        self.wi_err = QCheckBox("Реакция на ошибки: «программа не отвечает» и окна с ошибкой")
        self.wi_err.setChecked(bool(cfg.get("wi_error_help", True)))
        self.wi_err.toggled.connect(lambda on: self.cfg.update(wi_error_help=bool(on)))
        f.addRow(self.wi_err)
        self.wi_glow = NoWheelComboBox()                      # вид подсветки по краю экрана
        self.wi_glow.addItem("Волны внизу экрана", intel.GLOW_WAVES)
        self.wi_glow.addItem("Нежные полоски по краям", intel.GLOW_EDGES)
        self.wi_glow.setCurrentIndex(max(0, self.wi_glow.findData(intel.glow_style(cfg))))
        self.wi_glow.currentIndexChanged.connect(self._wi_glow_changed)
        f.addRow("Вид подсветки", self.wi_glow)
        self.wi_waves = QCheckBox("Свечение ярче, пока Mico отвечает")
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
        for key, (name, _cols) in intel.WAVE_THEMES.items():
            self.wi_theme.addItem(name, key)
        self.wi_theme.setCurrentIndex(max(0, self.wi_theme.findData(cfg.get("wi_wave_theme", intel.WAVE_THEME_DEFAULT))))
        self.wi_theme.currentIndexChanged.connect(self._wi_theme_changed)
        f.addRow("Готовый набор волн", self.wi_theme)
        hint = QLabel("Полоска по краям экрана в режиме Mico · WI (BETA). Цвета у действий не повторяются. "
                      "Волны могут быть цветом Mico из персонализации.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        return box

    def _wi_header(self):
        head = QFrame()
        head.setObjectName("wiHead")
        v = QVBoxLayout(head)
        v.setContentsMargins(18, 14, 18, 14)
        t = QLabel("Mico · WI (BETA)")
        t.setObjectName("wiTitle")
        sub = QLabel("Внизу по центру, полоска по краю, чат WI. Настройки только для этого режима.")
        sub.setObjectName("wiSub")
        sub.setWordWrap(True)
        v.addWidget(t)
        v.addWidget(sub)
        return head

    def _wi_rhythm_box(self, cfg):
        """Тишина по расписанию и загрузка ПК полоской: только в режиме WI."""
        box = QWidget()
        f = QFormLayout(box)
        self.wi_qon = QCheckBox("Тихий час: в это время Mico не начинает разговор сам")
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
        self.wi_lbar = QCheckBox("Загрузка ПК тонкой линией внизу экрана")
        self.wi_lbar.setChecked(bool(cfg.get("wi_load_bar", False)))
        self.wi_lbar.toggled.connect(lambda on: self.cfg.update(wi_load_bar=bool(on)))
        f.addRow(self.wi_lbar)
        hint2 = QLabel("Линия растёт вместе с нагрузкой процессора. Цвет — как у волн.")
        hint2.setObjectName("hint")
        hint2.setWordWrap(True)
        f.addRow(hint2)
        return box

    def _news_page(self):
        """Что нового в Mico WI — только строки про WI, от свежих к старым."""
        w = QWidget()
        v = QVBoxLayout(w)
        items = version.wi_changes()
        if not items:
            v.addWidget(QLabel("Пока нет записей про WI."))
        last = None
        for key, line in items:
            if key != last:
                head = QLabel(f"<b>Mico {key}</b>")
                v.addWidget(head)
                last = key
            lab = QLabel("•  " + line)
            lab.setWordWrap(True)
            v.addWidget(lab)
        v.addStretch()
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(w)
        return sc

    def _wi_wave_height_changed(self, v):
        self.cfg["wi_wave_height"] = int(v)
        self.wi_wh_lbl.setText(f"{int(v)} %")
        self._wi_preview()

    def _wi_edge_changed(self, v):
        self.cfg["wi_edge_width"] = int(v)
        self.wi_edge_lbl.setText(f"{int(v)} px")
        self._wi_preview()

    def _wi_thick_changed(self, v):
        self.cfg["wi_thickness"] = int(v)
        self.wi_thick_lbl.setText(f"{int(v)} px")
        self._wi_preview()

    def _wi_waves_changed(self, on):
        self.cfg["wi_waves"] = bool(on)
        self._wi_preview()

    def _wi_glow_changed(self, _=None):
        self.cfg["wi_glow_style"] = self.wi_glow.currentData() or intel.GLOW_DEFAULT
        self._wi_preview()

    def _wi_wave_src_changed(self, _=None):
        self.cfg["wi_wave_source"] = self.wi_wsrc.currentData()
        self._wi_preview()

    def _wi_theme_changed(self, _=None):
        self.cfg["wi_wave_theme"] = self.wi_theme.currentData()
        if self.cfg.get("wi_wave_source") != "theme":                 # выбрал набор — он и включается
            self.wi_wsrc.setCurrentIndex(self.wi_wsrc.findData("theme"))
        self._wi_preview()

    def _paint_wave_btn(self):
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg.get("wi_wave_custom"))
        self.wi_wbtn.setText(hex_color)
        self.wi_wbtn.setStyleSheet(f"background:{hex_color}; color:#201a14; border:1px solid #8a7d6a; "
                                   "border-radius:8px; padding:4px 12px;")

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
                        "border-radius:8px; padding:4px 12px;")

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
        c = NoWheelComboBox()
        c.setEditable(True)
        c.addItems(installed)
        if installed:
            c.insertSeparator(c.count())
        c.addItems([s for s in suggest if s not in installed])
        c.setCurrentText(cur)
        return c

    def _style_dialog(self):
        """Оформление окна настроек по цвету Mico и теме (в режиме WI — спокойнее, как в macOS)."""
        dark = theme.is_dark(self.cfg)
        if intel.style_of(self.cfg.get("assist_style")) == intel.INTELLIGENCE:
            self.setStyleSheet(theme.wi_settings_qss(self.cfg["color"], dark) + theme.RESET_QSS)
        else:
            self.setStyleSheet(theme.settings_qss(self.cfg["color"], dark) + theme.RESET_QSS)

    def _paint_accent_btn(self):
        """Кнопка «Цвет Mico» показывает сам цвет."""
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg["color"])
        self.cbtn.setText(hex_color)
        self.cbtn.setStyleSheet(f"background:{hex_color}; color:#201a14; border:1px solid #8a7d6a; "
                                "border-radius:8px; padding:4px 12px;")

    def _apply_accent(self):
        """Цвет Mico сменили: окно настроек, кнопка цвета, чат, строка WI и волны перекрашиваются сразу,
        без перезапуска. Все кнопки берут цвет из одного места — cfg["color"]."""
        self._style_dialog()
        self._paint_accent_btn()
        self.blob.update()
        self.panel.theme()
        if self.panel.intel:
            self.panel.intel.restyle()
            self._wi_preview()

    def pick(self):
        c = QColorDialog.getColor(QColor(self.cfg["color"]), self, "Цвет Mico")
        if c.isValid():
            self.cfg["color"] = c.name()
            self._apply_accent()

    def live(self):
        self.cfg["scale"], self.cfg["opacity"] = self.sc.value() / 100, self.op.value() / 100
        self.blob.apply_config()
        if self.linked.isChecked() and self.csc.value() != self.sc.value():
            self.csc.blockSignals(True)                 # ползунок чата следует за размером Mico
            self.csc.setValue(self.sc.value())
            self.csc.blockSignals(False)
        self.panel.apply_size()

    def _chat_size_hint(self):
        """Ползунок размера чата: при связке меняет размер и Mico, и чата; без связки — только чат."""
        linked = self.linked.isChecked()
        self.csc.blockSignals(True)
        if linked:
            self.csc.setRange(self.sc.minimum(), self.sc.maximum())
            self.csc.setValue(self.sc.value())
            self.csc_lbl.setText("Размер Mico и чата")
            self.csc.setToolTip("Меняет размер и Mico, и чата вместе")
        else:
            self.csc.setRange(60, 200)
            self.csc.setValue(int(round(self.cfg.get("chat_scale", 1.0) * 100)))
            self.csc_lbl.setText("Размер чата")
            self.csc.setToolTip("Отдельный размер чата, Mico не меняется")
        self.csc.setEnabled(True)
        self.csc.blockSignals(False)
        self.csc_box.refresh()                      # подпись значения, пока сигналы были выключены

    def live_linked(self, on):
        self.cfg["chat_linked"] = on
        self._chat_size_hint()
        self.panel.apply_size()

    def live_chat(self, v):
        if self.linked.isChecked():                 # вместе: двигаем общий размер Mico и чата
            self.sc.setValue(v)                     # ползунок Mico обновит и Mico, и чат
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

    def _greet_ids(self):
        out = []
        for i in range(self.gl.count()):
            it = self.gl.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    NAME2KEY = {"outline": "chat_outline", "linked": "chat_linked", "greet": "greet_on_start",
                "auto": "autostart", "quiet": "quiet_mode", "locc": "loc_consent", "mem": "memory_on",
                "ini": "initiative_on", "pbr": "proactive_breaks"}

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
        hint = settings_info.CFG_HINTS.get(key) if key else None
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
            self.cfg["color"] = DEFAULTS["color"]
            self.cbtn.setText(DEFAULTS["color"])
            self.blob.update()
            self.panel.theme()
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
        QMessageBox.information(self, "Кнопки", "Привычки сброшены. Mico начнёт учиться заново.")

    def _save_chips(self):
        self.cfg.update(chips_mode=self.cmode.currentData(), chips_count=self.ccount.value(),
                        chips_hide_on_send=self.chide.isChecked(),
                        voice_wake=self.vwake.isChecked(),
                        voice_listen=self.vlisten.isChecked(),
                        conversation_sec=self.vconv.value(), min_confidence=self.vconf.value(),
                        vosk_model_dir=self.model_dir_value,
                        vosk_model_name=self.model_name_value,
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
        QMessageBox.information(self, "Mico", "Настройки сброшены. Перезапусти Mico, чтобы всё применилось.")
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
            w.setSizePolicy(ignore, w.sizePolicy().verticalPolicy())
        for w in self.findChildren(QPushButton):
            w.setSizePolicy(ignore, w.sizePolicy().verticalPolicy())
        for w in self.findChildren(QLineEdit):
            w.setSizePolicy(ignore, w.sizePolicy().verticalPolicy())

    def _apply_size(self, key):
        """Окно настроек — выбранного размера, но не больше экрана (не на весь экран по умолчанию)."""
        w, h = next(((w, h) for k, _, (w, h) in SETTINGS_SIZES if k == key), (640, 720))
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(w, scr.width() - 40), min(h, scr.height() - 80))

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

    def live_theme(self):
        self.cfg["theme"] = self.th.currentData()
        self.hooks.apply_theme()

    def live_assist(self):
        """Режим только выбирают здесь: переход (Mico выезжает вниз, полоска расходится) случится после «Сохранить»."""
        on = self.assist.currentData() == intel.INTELLIGENCE
        self.plc.setEnabled(not on)
        self.plc.setToolTip("В режиме Mico · WI (BETA) Mico всегда внизу по центру" if on else "")

    def _switch_mode(self):
        """Вызывается после сохранения: если режим сменился — Mico переходит (WI) или возвращается в угол."""
        was_on = intel.style_of(self.orig.get("assist_style")) == intel.INTELLIGENCE
        now_on = intel.style_of(self.cfg.get("assist_style")) == intel.INTELLIGENCE
        if was_on == now_on or not self.panel.intel:
            return
        tips = intel.checkup_lines(self.cfg, list_models(), intel_ui.total_ram_gb(), intel_ui.free_disk_gb()) \
            if now_on else ()
        self.panel.intel.switch(now_on, tips)

    def live_placement(self):
        self.cfg["placement"], self.cfg["sleep_corner"] = self.plc.currentData(), self.slc.currentData()

    # ----- модели Ollama -----
    def pull(self):
        name = self.pull_edit.text().strip() or self.tm.currentText().strip()
        if not name:
            return

        def work():
            ok = pull_model(name, self.status.emit)
            if ok:
                self.status.emit(f"✓ Готово: {name}")
                self.pulled.emit(name)
        threading.Thread(target=work, daemon=True).start()
        self.status.emit(f"Скачиваю {name}…")

    def on_pulled(self, name):
        for c in (self.tm, self.vm):
            if c.findText(name) < 0:
                c.insertItem(0, name)

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
                                "Подробности записаны в crash.log в папке Mico (%APPDATA%\\Mico).")
            return
        if done:
            self.panel.apply_voice()
            self._switch_mode()
            super().accept()

    def _apply(self):
        self._save_chips()
        self.cfg["assist_style"] = self.assist.currentData() or intel.CLASSIC
        self.cfg.update(settings_size=self.size_pick.currentData(),
                        menu_items=self._menu_ids(), menu_max=self.mmax.value())
        want_beta = self.beta_pick.isChecked()
        was_beta = self.orig.get("update_channel") == "beta"
        if want_beta and not was_beta:
            if not betaprogram.consent_given(self.cfg):
                if ask_beta_consent(self):
                    self.cfg["beta_consent_version"] = features.BETA_CONSENT_VERSION
                else:
                    want_beta = False
                    self.beta_pick.setChecked(False)
            # канал меняется только после того, как бета-сборка поставлена: иначе останемся на стабильном
            self.join_request = want_beta
        elif was_beta and not want_beta:
            self.cfg["update_channel"] = "stable"       # бету выключили — дальше обычный стабильный канал
        self.cfg.update(quiet_mode=self.quiet.isChecked(), update_check=self.updchk.isChecked())
        self.cfg.update(sleep_after_min=self.sleep_min.value())
        self.cfg.update(proactive_breaks=self.pbr.isChecked(),
                        proactive_break_min=self.pbr_min.value())
        self.cfg.update(custom_phrases=list(self._phrases), hotkey_chat=self.hk_chat.text().strip().lower())
        self.cfg.update(text_model=self.tm.currentText().strip(), vision_model=self.vm.currentText().strip(),
                        greet_on_start=self.greet.isChecked(), retention_days=self.keep.currentData(),
                        search_url=SEARCH_ENGINES.get(self.se.currentText(), SEARCH_ENGINES["Google"]))
        self.cfg.update(chat_outline=self.outline.isChecked(), chat_linked=self.linked.isChecked(),
                        chat_scale=self.cfg.get("chat_scale", 1.0), chat_ratio=self.cfg.get("chat_ratio", 1.0),
                        weather_on="weather" in self._greet_ids(), greet_items=self._greet_ids(),
                        city=self.city.text().strip(), memory_on=self.mem.isChecked(),
                        initiative_on=self.ini.isChecked(), initiative_min=self.ini_min.value(),
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
    update_found = pyqtSignal(object)   # найдена новая версия Mico (словарь с номером и адресом страницы)


def main():
    if "--autostart" in sys.argv:                # при входе в Windows даём рабочему столу загрузиться
        time.sleep(10)
    try:                                       # 1 мс точность таймеров Windows — плавные кадры
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    app = QApplication(sys.argv)
    theme.load_fonts()                       # Inter из assets/fonts — один шрифт на всё Mico
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
        app.setWindowIcon(QIcon(_icon))       # значок Mico во всех окнах программы
    import installer
    if betaprogram.is_join_request(sys.argv):    # временная копия бета-версии: ставит себя на место старой
        if not installer.finish_beta_join():
            QMessageBox.warning(None, betaprogram.TITLE, "Бету не получилось поставить: старая программа ещё занята. "
                                                         "Закрой Mico (в трее — «Выход») и попробуй снова из настроек.")
        return
    if installer.is_uninstall_request():        # «Параметры → Приложения» или пункт меню запускают удаление
        installer.uninstall(app)
        return
    if installer.should_run():                  # собранный Mico.exe запущен не из папки установки — мастер
        installer.run()
        return
    app.setQuitOnLastWindowClosed(False)
    existed = os.path.exists(CFG_PATH)           # была ли уже установка (для «что нового»)
    _stage("запуск main()")
    cfg, store = load_cfg(), Store()
    if version.BUILD_CHANNEL == "stable" and cfg.get("update_channel") != "stable":
        cfg["update_channel"] = "stable"                 # стабильная сборка всегда на стабильном канале
        save_cfg(cfg)
    _stage("настройки и хранилище готовы")
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
    panel.apply_voice()
    _stage("окно чата готово")
    watcher = WindowWatcher()
    _stage("наблюдатель окон готов")
    bus = Bus()                              # сигналы между фоновыми потоками и окном
    bus.info.connect(panel.say)              # погода и сообщения из фоновых потоков
    brain.notify = panel.reminder.emit
    brain.save_cfg = lambda: save_cfg(cfg)
    reminders.bind(store)                    # напоминания — в зашифрованном хранилище
    panel.feedback_save = lambda kind, text, q, a: store.add_feedback(feedback.make_entry(kind, text, q, a))
    panel.report_with_feedback = lambda text: save_report()

    def ask_idea():
        text, ok = QInputDialog.getMultiLineText(None, "Идея", "Что бы ты хотел, чтобы Mico умел?")
        if ok and text.strip():
            store.add_feedback(feedback.make_entry("idea", text))
            QMessageBox.information(None, "Спасибо", "Идея сохранена. Она попадёт к разработчику вместе с отчётом.")

    def on_hotkey(hid):
        if hid == 1:
            panel.toggle()
        elif hid == 2:                                       # Mico WI: «Что на экране?»
            intel_ctl.screen_hotkey()
        elif hid == 3:                                       # Mico WI: «Помочь с окном»
            intel_ctl.window_hotkey(active_title())
    bus.hotkey.connect(on_hotkey)

    def offer_update(info):
        """Новая версия: спрашиваем один раз за запуск. Mico только открывает страницу, скачивать — тебе."""
        if cfg.get("quiet_mode"):
            return
        if _box(QMessageBox.Icon.Information, "Новая версия Mico", updatecheck.offer_text(info),
                "Открыть страницу", "Позже"):
            webbrowser.open(info["url"])
    bus.update_found.connect(offer_update)

    def start_update_check():
        """Фоновый запрос к GitHub: интерфейс не ждёт, без сети тихо пропускаем."""
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
        """Название программы, которой пользуешься (не Mico). Пусто — если узнать не получилось."""
        try:
            import win32gui
            hwnd = watcher.last_hwnd or tracker.last_hwnd
            return win32gui.GetWindowText(hwnd) if hwnd else ""
        except Exception:
            return ""
    hk = hotkeys.HotkeyThread({1: cfg.get("hotkey_chat", "ctrl+alt+m"),
                               2: cfg.get("hotkey_screen", intel.SCREEN_KEY),
                               3: cfg.get("hotkey_window", intel.WINDOW_KEY)}, bus.hotkey.emit)
    hk.start()
    hk.ready.wait(3)
    if hk.failed:
        bus.info.emit("Не получилось назначить горячую клавишу: " + ", ".join(hk.failed) +
                      ". Проверь сочетание в ⚙ Настройки → Поведение или его уже занимает другая программа.")
    reminders.restore(brain.notify)          # напоминания, поставленные до перезапуска
    brain.last_hwnd = lambda: watcher.last_hwnd or tracker.last_hwnd
    brain.on_command = lambda q: (chips.record(q, cfg), save_cfg(cfg))     # учимся на кнопках и командах
    blob.clicked.connect(panel.toggle)
    blob.slept.connect(panel.hide_smooth)                    # заснул — чат прячется
    # проснулся — чат возвращается, но не раньше, чем Mico приземлится после прыжка (иначе чат налезает на него)
    blob.woke.connect(lambda: QTimer.singleShot(blob.WAKE_SETTLE_MS, panel.show_near))
    blob.can_sleep = lambda: not (panel.busy or panel.inp.hasFocus() or panel.inp.text()
                                  or (panel.isVisible() and panel.underMouse())
                                  or (intel_ctl is not None and intel_ctl.wichat.isVisible()))   # открыт чат WI — не спим
    intel_ctl = intel_ui.Intel(cfg, blob, panel)              # режим Windows Intelligence (по умолчанию выключен)
    panel.intel = intel_ctl
    panel.busy_changed.connect(intel_ctl.busy)
    panel.answer_text.connect(intel_ctl.answer)
    panel.user_sent.connect(intel_ctl.wi_user)
    panel.mico_said.connect(intel_ctl.wi_mico)
    blob.dropped.connect(intel_ctl.file_dropped)          # файл на Mico — WI его читает и пересказывает

    # Mico WI: помощник по буферу обмена и реакция на ошибки — раз в 2 секунды, только в режиме WI
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
    sleep_isl = sleep_island.SleepIsland(cfg)                # спящий Mico — островок сверху по центру, по нажатию просыпается
    intel_ctl.sub.set_island(sleep_isl)                      # во сне строки WI выплывают из этого островка
    blob.slept.connect(lambda: (sleep_isl.show_from(blob), blob.hide()))   # во сне — чёрный остров сверху по центру
    sleep_isl.wake.connect(lambda: (blob.show(), blob.wake()))
    panel.wake_requested.connect(lambda: sleep_isl.wake.emit())   # голосом «Мико» — то же, что тап по острову
    blob.awake.connect(lambda: sleep_isl.retract_to(blob))                # проснулся по любой причине — остров втягивается
    blob.slept.connect(lambda: intel_ctl.glow.set_muted(True))            # во сне волны внизу гаснут
    blob.awake.connect(lambda: intel_ctl.glow.set_muted(False))           # проснулся — волны возвращаются
    blob.slept.connect(intel_ctl.on_sleep)               # в Intelligence Mico во сне исчезает, а не уходит в угол
    blob.moved.connect(lambda: panel.isVisible() and panel.reposition())   # чат всегда рядом с Mico, где бы он ни стоял

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

    def mail_allowed():
        """Письмо разработчику — только в бете, после согласия и когда адрес задан."""
        return (cfg.get("update_channel") == "beta" and cfg.get("beta_consent_version") == features.BETA_CONSENT_VERSION
                and bool(version.FEEDBACK_EMAIL))

    def offer_mail(path, windows_build):
        """Открывает письмо с готовым текстом. Zip прикрепляет сам человек: программа ничего не отправляет."""
        if QMessageBox.question(None, "Отправить разработчику",
                                "Открыть письмо с готовым текстом?\n\nZip-файл откроется в папке — прикрепи его к письму сам."
                                ) != QMessageBox.StandardButton.Yes:
            return
        from PyQt6.QtGui import QDesktopServices
        counts = feedback.summary(store.list_feedback(500))
        body = mailreport.build_body(version.APP_VERSION, windows_build, counts)
        link = mailreport.mailto_link(version.FEEDBACK_EMAIL, "Отчёт Mico (бета)", body)
        if link:
            QDesktopServices.openUrl(QUrl(link))
        subprocess.Popen(["explorer", f"/select,{path}"])

    def save_report(extra=None):
        """Отчёт для баг-репорта на рабочем столе: журналы, настройки без секретов, отзывы. Ничего не отправляется."""
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        dest = desk if os.path.isdir(desk) else os.path.expanduser("~")
        try:
            wb = windows_info.current_build()[0]
        except Exception:
            wb = None
        files = {"feedback.json": feedback.export_json(store.list_feedback(50))}
        files.update(extra or {})
        path, included = report.build_report(_mico_dir(), dest, version.APP_VERSION, cfg, wb, files)
        logs = ", ".join(included) if included else "журналов пока нет"
        QMessageBox.information(None, "Отчёт сохранён", f"Файл: {path}\nЖурналы: {logs}\n\n"
                                "Проверь файлы перед отправкой: в журналах могут быть пути к файлам.")
        if mail_allowed():
            offer_mail(path, wb)

    joins = []                                       # держим ссылки на фоновую загрузку бета-версии

    def join_beta():
        """Переход на бету: качаем бета-сборку в фоне, сверяем контрольную сумму и ставим её поверх Mico."""
        if not installer.FROZEN:
            QMessageBox.information(None, betaprogram.TITLE, "Бета ставится в установленную программу Mico.exe. "
                                                             "Канал не меняю.")
            return
        if not version.BETA_INFO_URL:
            QMessageBox.information(None, betaprogram.TITLE, "Бета-сборка пока не опубликована. Попробуй позже.")
            return
        wait = QMessageBox(None)
        wait.setWindowTitle(betaprogram.TITLE)
        wait.setText("Скачиваю бета-версию. Mico переустановится и сам расскажет, что в ней нового.")
        cancel_b = wait.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
        wait.show()
        worker = installer.BetaJoin(version.BETA_INFO_URL)
        joins.append(worker)
        cancel_b.clicked.connect(lambda *_: worker.cancel())

        def finished(path, err):
            wait.close()
            if err == installer.BetaJoin.CANCELLED:
                return                                  # отменили сами: канал не меняем
            if err:
                QMessageBox.warning(None, betaprogram.TITLE, f"Бету не поставил: {err}.\n"
                                                             "Канал не изменился, Mico остаётся стабильным.")
                return
            betaprogram.launch(path, [betaprogram.JOIN_FLAG])   # новая копия сама поставит себя на место
            app.quit()
        worker.done.connect(finished)
        worker.start()

    def open_settings():
        """Настройки открываются по центру экрана. Чат и Mico не двигаются: они остаются там, где стоят."""
        dlg = SettingsDialog(cfg, blob, panel, hooks)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        w, h = dlg.width(), dlg.height()
        dlg.move(scr.left() + max(10, (scr.width() - w) // 2), scr.top() + max(10, (scr.height() - h) // 2))
        dlg.exec()
        panel.refresh_chips()                       # новые кнопки видны сразу, даже если чат открыт
        if dlg.join_request:
            join_beta()

    blob.settings_requested.connect(open_settings)       # двойной щелчок по Mico — настройки

    def menu_action(item, m):
        """Один пункт меню. Пункты с галочкой отражают текущее состояние."""
        a = QAction(menu_items.LABELS[item], m)
        if item == "chat":
            a.triggered.connect(lambda *_: panel.show_near())
        elif item == "settings":
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
        elif item == "report":
            a.triggered.connect(lambda *_: save_report())
        elif item == "idea":
            a.triggered.connect(lambda *_: ask_idea())
        elif item == "tour":
            a.triggered.connect(lambda *_: show_tour())
        elif item == "whatsnew":
            a.triggered.connect(lambda *_: QMessageBox.information(None, "Что нового", version.recent_changes(3)))
        elif item == "env":
            a.triggered.connect(lambda *_: QMessageBox.information(None, "Окружение", brain.environment()))
        elif item == "about":
            ch = cfg.get("update_channel", "stable")
            a.setText(f"ℹ Mico {version.display_version(ch)}")
            a.triggered.connect(lambda *_: QMessageBox.information(
                None, "Mico", f"Версия {version.display_version(ch)}.\n\nИстория изменений: CHANGELOG.md\n"
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

    relaunch = _alive_instance()                # Mico уже работал: это разблокировка или повторный запуск
    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    try:                                        # журнал последнего запуска: откуда и когда стартовал Mico
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

    # итог дня (бета): раз в минуту проверяем, не пора ли прислать сводку за сегодня
    sum_t = QTimer()
    def day_tick():
        if not features.enabled("day_summary", cfg) or cfg.get("quiet_mode"):
            return
        now = time.time()
        if daysum.due(now, cfg):
            save_cfg(cfg)
            bus.info.emit("🌙 " + daysum.build(store, now))
    sum_t.timeout.connect(day_tick)
    sum_t.start(60000)

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

    # инициатива (бета): Mico смотрит на экран, когда сменилось окно, и может сам что-то сказать
    ini_gate = initiative.Gate()

    def initiative_tick():
        wi = intel_ctl.on()                                  # Mico WI наблюдает за экраном сам
        if not ((cfg.get("initiative_on") or wi) and (features.enabled("initiative", cfg) or wi)):
            return
        ini_gate.min_gap = max(5, cfg.get("initiative_min", 15)) * 60
        now, win = time.time(), watcher.last_hwnd
        busy = panel.busy or panel.inp.hasFocus() or bool(panel.inp.text())
        paused = bool(cfg.get("quiet_mode")) or blob.asleep or not blob.isVisible() or intel_ctl.hushed()
        if not ini_gate.should_look(now, win, busy, tracker.last_blocked, paused):
            return
        ini_gate.looked(now, win)

        def work():
            try:
                text = brain.glance(recent=ini_gate.recent)
            except Exception:
                text = None
            if text and not ini_gate.is_repeat(text[0]):
                ini_gate.remember(text[0])
                panel.initiative.emit(text)
        threading.Thread(target=work, daemon=True).start()
    ini_t = QTimer()
    ini_t.timeout.connect(initiative_tick)
    ini_t.start(20000)

    # напоминание о перерыве: следит и когда Mico спит — тогда он просто покажется и посоветует отдохнуть
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

    def ensure_beta_consent():
        """Тем, кто уже в бете без согласия, текст показываем один раз при запуске."""
        if cfg.get("update_channel") != "beta" or cfg.get("beta_consent_version") == features.BETA_CONSENT_VERSION:
            return
        if ask_beta_consent(None):
            cfg["beta_consent_version"] = features.BETA_CONSENT_VERSION
        else:
            cfg["update_channel"] = "stable"
        save_cfg(cfg)
    QTimer.singleShot(5000, ensure_beta_consent)


    def greet():
        blob.set_mood("happy", 5)
        blob.jump()
        if intel_ctl.on():                                   # Mico WI: приветствие и итог дня строкой над Mico
            intel_ctl.greet(hello(), daysum.build(store, time.time()))
        else:
            panel.show_near(activate=False)
            panel.say(hello())
        ids = cfg.get("greet_items", [])
        if "weather" in ids and cfg.get("loc_consent") is None:      # спрашиваем один раз
            ok = _box(QMessageBox.Icon.Question, "Геопозиция для погоды",
                      "Mico может узнать твою геопозицию, чтобы сообщать погоду.\n\n"
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
    if not cfg.get("first_run"):
        cfg["first_run"] = time.time()          # от этой даты считается опрос через неделю
        save_cfg(cfg)

    def maybe_survey():
        if cfg.get("quiet_mode") or not feedback.should_show_survey(cfg):
            return
        text, ok = QInputDialog.getMultiLineText(None, "Опрос Mico",
                                                 "Ответь коротко на три вопроса:\n" + feedback.survey_prompt())
        if ok and text.strip():
            store.add_feedback(feedback.make_entry("survey", text))
        cfg["survey_done"] = True
        save_cfg(cfg)
    QTimer.singleShot(60000, maybe_survey)

    def whats_new():
        """Один раз после обновления: что изменилось и что проверить."""
        prev = cfg.get("last_version") or (version.BASE_VERSION if existed else None)
        if prev == version.APP_VERSION:
            return
        cfg["last_version"] = version.APP_VERSION
        save_cfg(cfg)
        text = version.whats_new(prev) if prev else ""
        if text and not cfg.get("quiet_mode") and not welcome_now:
            panel.show_near(activate=False)
            blob.set_mood("happy", 6)
            blob.jump()
            panel.say(text)

    def beta_welcome():
        """Первая запуск бета-версии: Mico радуется, крутится и рассказывает, что есть и что делает."""
        cfg["beta_welcome_version"] = features.BETA_WELCOME_VERSION
        save_cfg(cfg)
        panel.show_near(activate=False)
        blob.wake(silent=True)
        blob.set_mood("happy", 8)
        blob.start_anim("spin")
        for i, line in enumerate(betaprogram.welcome_lines(version.APP_VERSION)):
            QTimer.singleShot(1200 + i * 3200, lambda t=line: panel.say(t))

    welcome_now = betaprogram.needs_welcome(cfg) and not relaunch and not cfg.get("quiet_mode")
    QTimer.singleShot(8000, lambda: threading.Thread(target=brain.warm_up, daemon=True).start())   # прогрев модели
    QTimer.singleShot(8000, brain.start_digests)                                                 # пересказ прошлых дней, в фоне
    if welcome_now:
        QTimer.singleShot(900, beta_welcome)
    elif cfg["greet_on_start"] and not relaunch and not cfg.get("quiet_mode"):
        QTimer.singleShot(700, greet)
    QTimer.singleShot(2600, whats_new)
    QTimer.singleShot(7000, start_update_check)     # после приветствия, в фоне

    def show_tour():
        panel.show_near(activate=False)
        panel.show_html(capabilities.html_tour())

    def maybe_tour():
        """Знакомство один раз при первом запуске (если не режим тишины)."""
        if cfg.get("tour_done") or cfg.get("quiet_mode") or relaunch or welcome_now:
            return
        cfg["tour_done"] = True
        save_cfg(cfg)
        show_tour()
    QTimer.singleShot(9000, maybe_tour)
    _stage("цикл событий запущен")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
