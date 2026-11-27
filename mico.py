"""Mico AI — ИИ-компаньон для Windows 11. Запуск: python main.py"""
import sys as _sys, os as _os, traceback as _tb

# В сборке --noconsole (Mico.exe) стандартные потоки равны None. Библиотеки (tqdm при скачивании моделей,
# torch, Hugging Face) пишут туда прогресс и падают с «NoneType object has no attribute write».
# Подменяем на пустой поток до любых других импортов.
if _sys.stdout is None:
    _sys.stdout = open(_os.devnull, "w", encoding="utf-8")
if _sys.stderr is None:
    _sys.stderr = open(_os.devnull, "w", encoding="utf-8")


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


def _trace(msg):
    """Журнал запуска: пишется сразу при старте процесса, ещё до интерфейса.
    Так видно, стартует ли Mico при входе в Windows и на каком этапе останавливается. Файл не растёт бесконечно."""
    try:
        import time as _t
        path = _os.path.join(_mico_dir(), "launch_trace.log")
        if _os.path.exists(path) and _os.path.getsize(path) > 200_000:
            _os.replace(path, path + ".old")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{_t.strftime('%d.%m.%Y %H:%M:%S')} pid {_os.getpid()} argv={_sys.argv[1:]} — {msg}\n")
    except Exception:
        pass


_trace("процесс начал работу")


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
import base64, html, json, os, subprocess, sys, threading, time, webbrowser
from ui.richtext import rich_html
from types import SimpleNamespace
from urllib.parse import unquote
from ui.controls import ClickLabel, Switch, WrapCheck      # переключатели — общие с установщиком
from ui.controls import RoundSlider                       # круглые ползунки — тоже общие с установщиком
from ui import settingslook as settings_look   # оформление окна настроек (карточки, акцент Mico AI)
from PyQt6.QtCore import QAbstractAnimation, QPoint, QRectF, QEasingCurve, QObject, QPropertyAnimation, QSize, Qt, QTime, QTimer, QUrl, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QAction, QColor, QGuiApplication, QIcon, QImage, QTextDocument
from PyQt6.QtWidgets import (QProgressBar, QAbstractButton, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGraphicsOpacityEffect, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QPlainTextEdit, QScrollArea, QSizePolicy, QSlider, QSpinBox, QTextBrowser, QTimeEdit, QToolButton, QVBoxLayout, QWidget)
import psutil
from ui import icons as uiicons
from ui import winter as winter_ui
from ui import chatlook as chat_look   # новый вид текстового чата
from core import title as chat_title   # название чата — по первому запросу пользователя
from win import actions
from setup import autostart
from assist import watch as errwatch
import i18n

i18n.EN.update({
    "Зимнее оформление: снег, сугробы, ёлки и снеговики": "Winter look: snow, snowdrifts, fir trees and snowmen",
    "Зимний Mico: красный колпак с белым помпоном": "Winter Mico: a red hat with a white pompom",
    "В настройках и в чате плавно падает снег, внизу сугробы, ёлки с огоньками и снеговик, а значки разделов становятся снежными.": "Snow falls gently in settings and in the chat, with snowdrifts, lit fir trees and a snowman at the bottom, and the section icons turn snowy.",
    "Колпак сидит на Mico, едет и качается вместе с ним, а помпон живой: болтается, когда Mico прыгает или поворачивает голову.": "The hat sits on Mico and moves and sways with him, and the pompom is alive: it swings when Mico jumps or turns his head.",
    "Скоро Новый год. Всё включается и выключается сразу, настройки перезапускать не нужно.": "New Year is coming. Everything switches on and off at once, no restart needed.",
    "Зимнее настроение": "Winter mood", "Снег, колпак и праздничный вид": "Snow, a hat and a festive look", "Зима": "Winter",
    "Облако Mico (быстро, без нагрузки на ПК)": "Mico Cloud (fast, no load on the PC)",
    "Авто: Mico сам выбирает уровень по вопросу. Искра: простые и быстрые модели. Аврора: сильные модели для сложных вопросов, текстов и кода. Полярис: самые мощные и энергозатратные модели, на них нейроны уходят быстрее всего.": "Auto: Mico picks the tier by the question. Iskra: simple, fast models. Aurora: strong models for hard questions, texts and code. Polaris: the most powerful and energy-hungry models, they use up neurons fastest.",
    "Считаю остаток нейронов…": "Counting the neurons left…", "Осталось около {n} нейронов на сегодня. Хватит примерно на запросы:": "About {n} neurons left today. Enough for roughly this many requests:", "запросов": "requests", "Осталось нейронов сегодня": "Neurons left today",
    "сам выбирает уровень": "picks the tier itself", "простые и быстрые модели": "simple, fast models", "сильные модели": "strong models", "самые мощные модели": "the most powerful models", "Режим облака": "Cloud mode",
    "В облаке Mico нет ключей. Текст чата уходит на сервер Mico AI (Cloudflare), снимки экрана не отправляются. «Авто» берёт быструю модель для простых вопросов и умную для сложных. Если дневная доля закончилась, Mico отвечает локальной моделью (если скачана) или командами для компьютера.":
        "Mico Cloud has no keys. Chat text goes to the Mico AI server (Cloudflare); screenshots are never sent. “Auto” uses a fast model for simple questions and a smart one for hard ones. If the daily share runs out, Mico answers with the local model (if downloaded) or with PC commands.",
    "Ответы идут через облако Mico: быстро и без нагрузки на процессор.": "Answers go through Mico Cloud: fast and without loading the processor.",
    "Режим «Авто» сам выбирает быструю или умную модель.": "“Auto” picks a fast or a smart model by itself.",
    "GigaChat (Сбер) — ответы в чате": "GigaChat (Sber) — answers in chat", "Авто": "Auto", "Быстро": "Fast", "Умнее": "Smarter", "Облако Mico": "Mico Cloud",
})
from ui import sidetabs
from voice import settings as voice_settings
from assist import intel
from assist import ui as intel_ui
from core import phrase
from ui import info as settings_info
from data import clipbuf
from data import schedule
from ui import menu as menu_items
from core import features
from core import uilayout                # одноразовая миграция: панель сбоку становится настройкой по умолчанию
from core import capabilities
from ui import chips
from core import habits
from win import commands
from win.screen import capture_jpeg as screen_capture
from core import custom
from ui import motion                     # общие анимации (снег ждёт, пока колонка двигается)
from core import greeting
from win import hotkeys
from data import breaks
from data import reminders
from ui import theme
from setup import updatecheck
from setup import version
from core import memview
from win import system as W
from win.actions import Reply
from ui.blob import BASE_PX, Blob
from core import brain as brain_mod   # модуль целиком: load_cfg выбирает модель и режим
from core.brain import Brain
from core.emotions import detect_emotion
from data.follow import WindowWatcher
from data.storage import APPDIR, Store
from data.tracker import Tracker, idle_seconds


DEFAULTS = {
    "user_name": "",                  # как звать пользователя (аватар, приветствие)
    "user_phone": "",                 # телефон для умных полей на сайтах (только после «да»)
    "user_email": "",                 # почта для умных полей на сайтах (только после «да»)
    "user_about": "",                 # что Mico AI должен знать о пользователе
    "user_tone": "friendly",          # выбранная манера ответов Mico AI
    "user_reply_language": "auto",    # язык ответа: язык вопроса, русский или английский
    "user_answer_length": "balanced", # краткость ответа
    "user_answer_format": "natural",  # абзацы, списки или сразу вывод
    "user_address": "name",           # обращаться по имени или на «ты»
    "user_clarify": "when_needed",    # когда задавать уточняющие вопросы
    "color": "#FFCFA3", "scale": 1.0,
    "llm_backend": "mico", "llm_temperature": 0.7, "retention_days": 30,
    "greet_on_start": True, "silent_until_asked": True, "autostart": False, "language": "en", "weather_on_start": True,
    "theme": "auto",                      # auto — как в Windows | light | dark
    "assist_style": "classic",            # classic — Mico AI в углу | intelligence — внизу по центру, с подсветкой экрана
    "placement": "manual",                # manual — стоит, где поставил мышкой | tl/tr/bl/br — всегда в этом углу экрана
    "chips_mode": "auto", "chips_count": 6, "chips_pinned": [], "chip_usage": {},   # кнопки под чатом
    "chips_hide_on_send": True,
    "chat_linked": True, "chat_scale": 1.0, "chat_ratio": 1.0,   # чат меняется вместе с Mico AI или отдельным ползунком
    "panel_side": True,                   # чат выезжает панелью у правого края (как Windows Copilot); False — окно рядом с Mico AI
    "chat_style": "balanced",             # стиль общения: creative — творческий | balanced — обычный | precise — точный
    "chat_outline": True,                 # обводка вокруг окна чата
    "button_glow": True,                  # подсветка кнопок акцентным цветом при наведении (чат, быстрые действия)
    "wi_input_outline": True,             # обводка поля ввода в чате Mico AI
    "city": "", "loc_consent": None,      # город для погоды; None — ещё не спрашивали про геопозицию
    "weather_on": True, "memory_on": True,
    "agent_mode": False,                  # режим агента (открывает программы, мессенджеры, видео) — выключен по умолчанию
    "agent_messengers": True,             # зона агента: мессенджеры MAX, WhatsApp, Teams, Discord, Telegram
    "agent_video": True,                  # зона агента: видео и сайты (YouTube, Rutube, VK Видео, Яндекс Видео)
    "agent_confirm_send": True,           # спрашивать «да» перед отправкой, лайком, комментарием и подпиской
    "agent_max_steps": 12,                # сколько шагов агент может сделать за одну задачу
    "telegram_on": False,                 # управление ПК с телефона через Telegram-бота (токен хранится в защищённом хранилище)
    "telegram_owner": None,               # подключённый телефон: {"chat": id, "user": id}; чужие чаты бот игнорирует
    "telegram_screen": True,              # команда /screen: снимок экрана в Telegram
    "telegram_proxy": "",                 # прокси для api.telegram.org, если он недоступен (http://… или socks5://…)
    "winter_ui": False, "winter_mico": False,   # зимнее оформление и колпак Mico (настройки → Зима)
    "dance_music": True, "eat_trash": True,   # Mico танцует под музыку и ест файлы из корзины
    "hotkey_chat": "f8",           # глобальная клавиша: F8 открывает чат из любого окна (нужен перезапуск)
    "hotkey_voice": "ctrl+alt+v",       # голос: нажми — говори, нажми ещё раз — отправлю (нужен перезапуск)
    "voice_wake": False,                  # голосовой чат по слову «мико!» (микрофон слушает, звук не сохраняется; по умолчанию выключено)
    "voice_mood": True, "voice_speed": 1.0, "voice_expr": 60, "voice_pause": 1.0, "voice_volume": 100,   # вкладка «Голос»
    "voice_wake_words": "мико, mico", "voice_wake_sens": 1.0, "voice_end_ms": 1000, "voice_mic": "",
    "voice_on": False, "voice_name": "irina",   # озвучка ответов (по умолчанию выключена, модель качается при включении)
    "wi_thickness": intel.THICK_DEFAULT, "wi_waves": True, "wi_glow_style": intel.GLOW_DEFAULT,
    "anim_sleep_fps": 20,                 # частота анимации Mico AI во сне, кадров в секунду (выбирается в настройках); 20 — экономно, движение плавное
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
    "block_processes": ["keepass", "bitwarden", "1password", "lastpass", "dashlane"],
    "block_titles": ["inprivate", "incognito", "инкогнито", "private browsing", "пароль", "password", "банк", "bank"],
}
CFG_PATH = os.path.join(APPDIR, "config.json")


def load_cfg():
    cfg = dict(DEFAULTS)
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    uilayout.migrate(cfg)                       # старый config.json не должен отменять панель по умолчанию
    from llm import cloud as _cloud
    cfg.pop("vision_model", None)
    cfg.pop("text_model", None)                         # локальная модель убрана: выбора модели для текста больше нет
    cfg.pop("mico_cloud_seen", None)
    cfg["llm_backend"] = "mico"                         # единственный источник ответов: GigaChat (в коде он назван «mico»)
    if cfg.get("cloud_default_ver") != 2:                # один раз: Mico-4 становится основной моделью в чате
        cfg["cloud_model"] = "mico4"
        cfg["cloud_default_ver"] = 2
    cfg["cloud_model"] = _cloud.normalize_mode(cfg.get("cloud_model"))
    if cfg.get("hotkey_chat") == "ctrl+alt+m":
        cfg["hotkey_chat"] = "f8"
    cfg["placement"], cfg["sleep_corner"] = "manual", "br"
    cfg["hotkey_chat"] = "f8"
    if cfg["color"].upper() == "#FFC94A":
        cfg["color"] = DEFAULTS["color"]
    return cfg


def save_cfg(cfg):
    """Сначала собираем текст целиком: если что-то не сериализуется, файл не трогаем.
    Пишем прямо в config.json, без переименования: на Windows переименование часто мешает
    антивирус или индексатор, который держит файл открытым, и настройки не сохранялись."""
    text = json.dumps(cfg, ensure_ascii=False, indent=2)
    with _cfg_lock:                             # два потока одновременно не перемешают файл
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            f.write(text)


PID_FILE = os.path.join(APPDIR, "mico.pid")

_cfg_lock = threading.Lock()                   # настройки пишутся из разных потоков (обновление, фоновые задачи)


def _wait_shell(max_sec=10.0):
    """При входе в Windows ждём, пока загрузится рабочий стол (панель задач), вместо паузы «на глаз».
    Раньше была пауза 10 секунд — старт из автозапуска ощутимо тормозил. Обычно хватает 1–2 секунд."""
    try:
        import ctypes
        find = ctypes.windll.user32.FindWindowW
        deadline = time.time() + max_sec
        while time.time() < deadline:
            if find("Shell_TrayWnd", None):      # панель задач появилась — рабочий стол готов
                time.sleep(0.5)
                return
            time.sleep(0.2)
    except Exception:
        time.sleep(2)


def hello(now=None):
    """Приветствие при запуске: утро, день, вечер или ночь — с эмодзи и восклицанием."""
    from core import phrase
    return phrase.greeting_text(now)


def _alive_instance():
    """Был ли Mico AI уже запущен (например, разблокировали экран) — тогда не здороваемся заново."""
    try:
        pid = int(open(PID_FILE, encoding="utf-8").read().strip())
    except (OSError, ValueError):
        return False
    if pid == os.getpid() or not psutil.pid_exists(pid):
        return False
    try:
        name = psutil.Process(pid).name().lower()
        return "python" in name or "mico" in name          # python или собранный Mico.exe
    except psutil.Error:
        return False


# =============================== Диалоги ===============================
def _confirm_wipe(store):
    """Историю удаляем только после явного «Удалить»: отменить это нельзя, поэтому по умолчанию — «Отмена»."""
    b = QMessageBox(QMessageBox.Icon.Warning, i18n.t("Удалить всю историю?"),
                    i18n.t("Вся история Mico AI будет удалена без возможности восстановить. Продолжить?"))
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
BREAK_MARK = "__break__"             # метка: это напоминание о перерыве, а не наблюдение за экраном


class Panel(QWidget):
    answered = pyqtSignal(object)
    streamed = pyqtSignal(str)       # кусочек ответа по мере генерации (живой отклик, без ожидания конца)
    reminder = pyqtSignal(str)
    initiative = pyqtSignal(object)   # напоминание о перерыве: (текст, метка)
    busy_changed = pyqtSignal(bool)   # Mico AI начал или закончил думать над запросом
    chat_shown = pyqtSignal(bool)     # чат открыли или закрыли (нужно режиму Windows Intelligence)
    answer_text = pyqtSignal(str)     # текст ответа (для строки над Mico AI в режиме Windows Intelligence)
    user_sent = pyqtSignal(str)       # вопрос ушёл Mico AI (в чат Windows Intelligence)
    mico_fx = pyqtSignal(object)      # карточка-анимация (переключатель, шкала, таймер) — для чата Mico AI
    mico_said = pyqtSignal(str)       # Mico AI написал текст в обычный чат (для чата Windows Intelligence)
    mic_requested = pyqtSignal()      # микрофон рядом с полем ввода: включить голосовой режим
    settings_requested = pyqtSignal() # «Настройки Mico AI» внизу бокового меню чата
    profile_requested = pyqtSignal()  # открыть отдельный раздел «Профиль» в настройках
    profile_changed = pyqtSignal()    # имя или «о себе» поменяли (AIChat обновит приветствие и аватар)
    title_ready = pyqtSignal()        # Mico придумал название чата — боковое меню обновит список

    def __init__(self, brain, blob, cfg):
        super().__init__()
        self.brain, self.blob, self.cfg = brain, blob, cfg
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        card = self.card = QFrame(self)
        card.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)       # контур карточки не упирается в край прозрачного окна
        outer.addWidget(card)
        body = QHBoxLayout(card)                  # слева боковое меню (всегда открыто), справа — чат
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        lay = QVBoxLayout()
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        body.addLayout(lay, 1)
        self._store = getattr(brain, "store", None)
        self.conv_id = None                       # открытый чат (None — новый, ещё не начат)
        self._rows = {}                           # id реплики в журнале → её пузырь (для перехода из поиска)
        self._pending_rid = None                  # id ответа Mico AI, который сейчас печатается
        self._reveal = None                       # ответ, который сейчас печатается по буквам
        self._reveal_timer = QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_tick)
        self._follow_on = True                    # следить за лентой: выключается, когда человек крутит сам
        self._scroll_anim = None
        self._history_anim = None                    # короткое появление при смене недавнего чата
        self._docked_blob = False                    # живой Mico AI сейчас в шапке боковой панели
        self._blob_home = None                       # где Mico AI стоял до переезда в панель
        self._dock_pos = None                        # его место в шапке панели
        self._blob_anim = None                       # полёт Mico AI в панель и обратно
        self._dock_keep = QTimer(self)               # шапка с Mico AI: его место и порядок окон проверяем сами
        self._dock_keep.setInterval(600)
        self._dock_keep.timeout.connect(self._keep_dock)
        muted = chat_look.PALETTE[bool(theme.is_dark(cfg))]["muted"]
        # шапка: три полоски (недавние чаты), поиск, закрыть; ниже — «Текущий чат» белым
        self.head_bar = QFrame()
        self.head_bar.setObjectName("chatHeadBar")
        hb = QVBoxLayout(self.head_bar)
        hb.setContentsMargins(10, 8, 10, 8)
        hb.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(6)
        self._top = top                                   # шапка: сюда позже встанет профиль
        self.menu_btn = self._icon_btn(chat_look.menu_icon(cfg["color"], 18))
        self.menu_btn.setToolTip(i18n.t("Недавние чаты"))
        self.menu_btn.clicked.connect(lambda: self._toggle_side())   # в боковой панели меню выезжает по кнопке
        self.search = QLineEdit()
        self.search.setObjectName("chatSearch")
        self.search.setPlaceholderText(i18n.t("Поиск по сообщениям"))
        self.search.setToolTip(i18n.t("Поиск по сообщениям в этом чате"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(uiicons.icon("search", chat_look.icon_ink(theme.is_dark(cfg)), 16), QLineEdit.ActionPosition.LeadingPosition)
        self.search.textChanged.connect(self._search_changed)
        close_b = self._icon_btn(chat_look.close_icon(chat_look.icon_ink(theme.is_dark(cfg)), 16))
        close_b.setToolTip(i18n.t("Закрыть"))
        close_b.clicked.connect(self.hide_smooth)
        top.addWidget(self.menu_btn)
        top.addWidget(self.search, 1)
        top.addWidget(close_b)
        hb.addLayout(top)
        self.head = QLabel(i18n.t("Текущий чат"))
        self.head.setObjectName("chatHead")
        hb.addWidget(self.head)
        lay.addWidget(self.head_bar)
        # живой Mico AI сверху панели — на месте логотипа Copilot; под ним — выбор стиля общения и чат
        self.blob_slot = QWidget()
        self.blob_slot.setObjectName("blobSlot")
        bs = QVBoxLayout(self.blob_slot)             # портрет Mico AI — пока живой Mico AI не встал в шапку
        bs.setContentsMargins(0, 0, 0, 0)
        self.dock_mico = chat_look.MicoIcon(120, cfg["color"])
        bs.addWidget(self.dock_mico, 0, Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.blob_slot)
        self.style_row = self._build_style_row()
        lay.addWidget(self.style_row)
        # лента сообщений: сверху вниз; внизу — «печатает» и пустое место
        self.msg_host = QWidget()
        self.msg_host.setObjectName("msgHost")
        self.msgs = QVBoxLayout(self.msg_host)
        self.msgs.setContentsMargins(2, 4, 6, 4)
        self.msgs.setSpacing(10)
        self.typing = chat_look.TypingRow(cfg["color"], muted)
        self.typing.hide()
        self.greeting = chat_look.Greeting(cfg["color"])  # пустой чат: Mico, приветствие и кнопки действий
        self.msgs.addWidget(self.greeting)
        self.greeting.action.connect(self.submit)          # кнопка на пустом экране — команда сразу
        self.greeting.style_picked.connect(self._set_style)
        self.greeting.settings_clicked.connect(self.settings_requested.emit)
        self.user_asked = False                             # пользователь уже что-то написал в этом сеансе
        self._deferred = []                                 # то, что Mico хотел сказать первым, но ждёт запроса
        self.msgs.addWidget(self.typing)
        self.msgs.addStretch(1)
        self.scroll = chat_look.ChatScroll()
        self.scroll.setObjectName("msgScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.msg_host)
        self.scroll.user_scrolled.connect(self._stop_follow)
        lay.addWidget(self.scroll, 1)
        self.chips_inner = QWidget()               # полоса подсказок: одна строка, листается вбок
        self.grid = QHBoxLayout(self.chips_inner)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(6)
        self.chips_box = QScrollArea()
        self.chips_box.setWidgetResizable(True)
        self.chips_box.setFrameShape(QFrame.Shape.NoFrame)
        self.chips_box.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chips_box.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chips_box.setFixedHeight(36)
        self.chips_box.setWidget(self.chips_inner)
        self.chips_inner.setObjectName("chipsInner")
        self.chips_box.horizontalScrollBar().setStyleSheet(
            "QScrollBar:horizontal { height: 4px; background: transparent; margin: 0; }"
            "QScrollBar::handle:horizontal { background: rgba(128,128,128,0.45); border-radius: 2px; min-width: 24px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }")
        self.chips_box.viewport().setAutoFillBackground(False)
        self.chips_inner.setAutoFillBackground(False)
        lay.addWidget(self.chips_box)
        self.last_pair = None
        # поле ввода: скруглённая строка и круглая кнопка отправки
        box = QFrame()
        box.setObjectName("inputBox")
        bh = QVBoxLayout(box)                              # сверху поле ввода, под ним ряд: модель, микрофон, отправка (как у Gemini)
        bh.setContentsMargins(12, 6, 10, 8)
        bh.setSpacing(4)
        self.inp = ChatInput()
        self.inp.setObjectName("chatInput")
        self.inp.setPlaceholderText(i18n.t("Напиши Mico AI…"))
        self.inp.focused.connect(self._on_input_focus)
        send_btn = QPushButton()
        send_btn.setObjectName("send")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setIcon(uiicons.send_icon("#1a1a1a"))
        send_btn.setIconSize(QSize(16, 16))
        send_btn.setFixedSize(28, 28)
        bh.addWidget(self.inp)
        self.mic_btn = QPushButton()
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setFixedSize(28, 28)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.setToolTip(i18n.t("Голосовой режим: Mico будет слушать"))
        self.mic_btn.setIcon(uiicons.icon("mic", chat_look.icon_ink(theme.is_dark(cfg)), 15))
        self.mic_btn.setIconSize(QSize(15, 15))
        self.mic_btn.clicked.connect(self.mic_requested.emit)
        btm_row = QHBoxLayout()
        btm_row.setContentsMargins(0, 0, 0, 0)
        btm_row.setSpacing(8)
        btm_row.addStretch(1)
        self.model_pill = chat_look.ModelPill(cfg, save=lambda: self.brain.save_cfg())   # быстрая смена модели GigaChat
        btm_row.addWidget(self.model_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        btm_row.addWidget(self.mic_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        btm_row.addWidget(send_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        bh.addLayout(btm_row)
        self.avatar = chat_look.AvatarButton()           # профиль — в шапке, перед крестиком; клик открывает «о себе»
        self.avatar.set_accent(cfg["color"])
        self.avatar.clicked.connect(self.edit_profile)
        self._top.insertWidget(self._top.count() - 1, self.avatar)
        gear_b = self._icon_btn(uiicons.icon("gear", chat_look.icon_ink(theme.is_dark(cfg)), 18, width=1.4))
        gear_b.setToolTip(i18n.t("Настройки"))
        gear_b.clicked.connect(self.settings_requested.emit)   # шестерёнка рядом с крестиком — настройки
        self._top.insertWidget(self._top.count() - 1, gear_b)
        lay.addWidget(box)
        self._refresh_profile()
        # результаты поиска — поверх ленты
        self.results = QListWidget(card)
        self.results.setObjectName("results")
        self.results.setWordWrap(True)
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results.setCursor(Qt.CursorShape.PointingHandCursor)
        self.results.itemClicked.connect(self._open_result)
        self.results.hide()
        # боковое меню: выезжает слева поверх ленты
        self.side = chat_look.Sidebar(cfg["color"], card, dark=theme.is_dark(cfg))
        self.side.open_chat.connect(lambda cid: self.open_chat(cid))
        self.side.new_chat.connect(self.new_chat)
        body.insertWidget(0, self.side)               # меню слева, всегда открыто
        self.side.setFixedWidth(206)
        self.title_ready.connect(self._refresh_side)
        self._refresh_side()
        self._refresh_profile()
        self.inp.returnPressed.connect(lambda: self.submit(self.inp.text()))
        send_btn.clicked.connect(lambda: self.submit(self.inp.text()))
        self.inp.textChanged.connect(self._typed)
        self.queue, self.pending, self.busy = [], "", False
        self._stream_row, self._stream_buf = None, ""   # живая строка ответа (пополняется при генерации)
        self.intel = None                 # режим Windows Intelligence (подключается в main)
        self.timer = QTimer(self)
        self.answered.connect(self.on_answer)
        self.streamed.connect(self.on_stream)
        self.reminder.connect(self.on_reminder)
        self.initiative.connect(self.on_initiative)
        self._anim = None
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
        for c in chips.pick(self.cfg):
            b = QPushButton(c.label)                 # полная подпись: в узком чате полоса листается, а не обрезает слова
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(26)
            b.setObjectName("chip")
            b.setToolTip(f"{c.label} — «{c.phrase.strip()}»")
            b.clicked.connect(lambda _, c=c: self.submit(c.phrase) if c.send else self.prefill(c.phrase))
            self.grid.addWidget(b)
        self.chips_box.setVisible(bool(chips.pick(self.cfg)) and not self._chips_hidden)
        self.refresh_welcome()

    def refresh_welcome(self):
        """Кнопки на пустом экране: свежий набор по привычкам и времени дня, когда чат пустой."""
        wc = getattr(self.intel, "aichat", None) if getattr(self, "intel", None) else None
        if wc is not None and not getattr(wc, "_has_msgs", False):
            wc.refresh_welcome()                          # тот же свежий набор и в чате Mico AI
        self.greeting.set_title("Mico")
        self.greeting.set_actions(chips.welcome(self.cfg, apps=self._habit_apps()))

    def _habit_apps(self):
        """Частые программы за две недели из локального журнала активности. Считаем не чаще раза в 10 минут."""
        now = time.time()
        cache = getattr(self, "_apps_cache", None)
        if cache is not None and now - cache[0] < 600:
            return cache[1]
        apps = {}
        try:
            if self._store is not None and self.cfg.get("habit_suggest", True):
                apps = habits.app_usage(self._store.between(now - habits.DAYS * 86400, now), now,
                                        blocked=self.cfg.get("block_processes", ()))
        except Exception:
            apps = {}
        self._apps_cache = (now, apps)
        return apps

    def may_speak(self):
        """Mico может заговорить первым: настройка выключена или пользователь уже написал запрос."""
        return self.user_asked or not self.cfg.get("silent_until_asked", True)

    def say_when_allowed(self, text):
        """То, что Mico хочет сказать сам (обновление, предупреждение). До запроса копим и покажем после него."""
        if self.may_speak():
            self.say(text)
        else:
            self._deferred.append(text)

    # ----- стиль общения (как в Windows Copilot: творческий, сбалансированный, точный) -----
    STYLE_CHOICES = chat_look.Greeting.STYLE_CHOICES      # те же кнопки, что в приветствии

    def _build_style_row(self):
        """Выбор стиля общения сразу в чате — три кнопки, как «Choose a conversation style» у Copilot."""
        row = QFrame()
        row.setObjectName("styleRow")
        v = QVBoxLayout(row)
        v.setContentsMargins(2, 0, 2, 0)
        v.setSpacing(8)
        label = QLabel(i18n.t("Выбери стиль общения"))
        label.setObjectName("styleLabel")
        v.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
        seg = QFrame()                                  # один сегментированный переключатель, как у Copilot
        seg.setObjectName("segBar")
        h = QHBoxLayout(seg)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(2)
        self.style_btns = []
        for key, title in self.STYLE_CHOICES:
            b = QPushButton(i18n.t(title))
            b.setObjectName("styleSeg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # влезают в узкую панель
            b.setMinimumWidth(0)
            b.clicked.connect(lambda _=False, k=key: self._set_style(k))
            h.addWidget(b, 1)
            self.style_btns.append(b)
        v.addWidget(seg)
        self._seg_fit = chat_look.SegFit(seg, self.style_btns)   # три кнопки одной ширины, как в приветствии
        self._sync_style()
        return row

    def _sync_style(self):
        cur = str(self.cfg.get("chat_style", "balanced"))
        for b, (key, _t) in zip(self.style_btns, self.STYLE_CHOICES):
            b.setChecked(key == cur)
        if getattr(self, "greeting", None) is not None:
            self.greeting.set_style(cur)

    def event(self, e):
        """Чат стал активным (клик по кнопке стиля, полю ввода): Windows поднимает его окно над окном Mico,
        и Mico в шапке пропадал под ним. Сразу возвращаем Mico наверх."""
        from PyQt6.QtCore import QEvent
        if e.type() in (QEvent.Type.WindowActivate, QEvent.Type.ActivationChange):
            QTimer.singleShot(0, self._lift_blob)
            QTimer.singleShot(120, self._lift_blob)
        return super().event(e)

    def _set_style(self, key):
        """Стиль общения меняется сразу, без настроек, и запоминается."""
        self.blob.touch()                                  # чат трогают — Mico AI не засыпает
        if self.blob.asleep:
            self.blob.wake(silent=True)
        self.cfg["chat_style"] = key
        self._sync_style()
        self.brain.save_cfg()
        self.inp.setFocus()
        self._keep_dock()                                  # Mico остаётся в шапке и поверх чата
        QTimer.singleShot(150, self._keep_dock)

    def _target_opacity(self):
        """Прозрачность окна чата — по ползунку «Прозрачность чатов»."""
        return intel.chat_opacity(getattr(self, "cfg", {}))

    def _fade(self, show):
        if self._anim is not None:
            self._anim.stop()
        a = QPropertyAnimation(self, b"windowOpacity", self)
        a.setDuration(260 if show else 200)
        a.setStartValue(0.0 if show else 1.0)
        a.setEndValue(self._target_opacity() if show else 0.0)
        a.setEasingCurve(QEasingCurve.Type.InOutSine)
        if not show:
            a.finished.connect(lambda: (self.hide(), self.setWindowOpacity(intel.chat_opacity(getattr(self, "cfg", {})))))
        self._anim = a
        a.start()

    def hide_smooth(self):
        if self.isVisible():
            self.chat_shown.emit(False)
            if self.side_mode():
                self._undock_blob()             # Mico AI возвращается на рабочий стол, панель уезжает вправо
                self._slide(False)
            else:
                self._fade(False)

    def chat_factor(self):
        """Во сколько раз чат больше/меньше базового размера: вместе с Mico AI или отдельным ползунком."""
        if self.cfg.get("chat_linked", True):
            return max(0.6, self.cfg.get("scale", 1.0))     # вместе с Mico AI: тот же размер, что у Mico AI
        return max(0.6, self.cfg.get("chat_scale", 1.0))

    def apply_size(self):
        k = self.chat_factor()
        if self.side_mode():
            _pos, w, h = self._dock_rect()
            self.setFixedSize(w, h)                            # панель во всю высоту у правого края экрана
            self.blob_slot.setFixedHeight(self._dock_blob_px())  # ровно под живого Mico AI — без лишних пустот
            self.dock_mico.set_size(self._dock_blob_px())      # портрет — того же размера, что живой Mico AI
            self.blob_slot.setVisible(True)
            self.side.setVisible(False)                        # недавние чаты выезжают по кнопке-полоскам
            self.menu_btn.setVisible(True)
        else:
            self.blob_slot.setVisible(False)
            self.side.setVisible(True)                         # окно чата: меню открыто всегда, как раньше
            self.menu_btn.setVisible(False)
            self.setFixedSize(round(CHAT_W * k), round(CHAT_H * k))     # стандартный размер чата (меньше, чем раньше)
        QTimer.singleShot(0, self._fit_rows)                 # перенос строк — под новую ширину ленты
        self._update_greeting()
        self._sync_dock_mico()                               # в шапке — живой Mico AI или его портрет
        self.theme()
        wc = getattr(self.intel, "aichat", None)          # чат режима Mico AI подчиняется тому же размеру
        if wc is not None:
            wc.relayout()
        if self.isVisible():
            self._dock_geometry() if self.side_mode() else self.keep_on_screen()   # не переставляем чат заново: он не должен прыгать при настройках

    def keep_on_screen(self):
        """Удерживает чат на экране, не меняя его положения, если он уже в пределах экрана."""
        scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        x = min(max(self.x(), g.left()), g.right() - self.width())
        y = min(max(self.y(), g.top()), g.bottom() - self.height())
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def _typed(self, _):
        if self.queue or self._reveal is not None:     # человек начал печатать — ответ показываем сразу целиком
            self._flush_answer()                        # (раньше остаток ответа просто терялся)
        self.blob.notify_typing()                   # Mico AI смотрит на строку ввода и интересуется
        self.blob.set_mood("curious", 3)
        self.blob.set_look(self.inp.mapToGlobal(self.inp.rect().center()))
        self._update_greeting()                     # человек пишет запрос — кнопки действий уходят

    def theme(self):
        dark = theme.is_dark(self.cfg)
        self.setStyleSheet(theme.panel_qss(self.cfg["color"], dark, self.cfg.get("chat_outline", True),
                                           self.chat_factor(), glow=intel.glow_on(self.cfg))
                           + chat_look.qss(dark, self.cfg["color"]))
        if getattr(self, "greeting", None) is not None:
            self.greeting.set_accent(self.cfg["color"])  # ссылки внизу приветствия — в цвет Mico
            self.refresh_welcome()                      # значки действий: чёрные в светлой теме, белые в тёмной

    # ----- боковая панель (как Windows Copilot) -----
    def side_mode(self):
        """Чат выезжает панелью у правого края экрана, а живой Mico AI стоит в её шапке.
        Всегда панель сбоку: выбор «Как открывать чат» убран из настроек."""
        return True

    def _screen(self):
        return QGuiApplication.screenAt(self.blob.geometry().center()) or QGuiApplication.primaryScreen()

    def _dock_blob_px(self):
        """Размер окна Mico AI, пока он в шапке панели: меньше обычного, как логотип Copilot."""
        return max(1, int(BASE_PX * self.cfg.get("scale", 1.0) * BLOB_DOCK_K))

    def _dock_rect(self):
        """Панель: у правого края экрана, во всю доступную высоту — как Windows Copilot."""
        g = self._screen().availableGeometry()
        k = self.chat_factor()
        w = max(round(SIDE_W * k), min(self._dock_blob_px(), round(g.width() * 0.45)))
        return QPoint(g.right() - w + 1, g.top()), w, g.height()

    def _dock_geometry(self):
        pos, w, h = self._dock_rect()
        self.move(pos)
        self.setFixedSize(w, h)

    def _slide(self, show):
        """Панель плавно выезжает из-за правого края экрана и уезжает обратно."""
        if self._anim is not None:
            self._anim.stop()
        pos, w, _h = self._dock_rect()
        off = QPoint(pos.x() + w + 12, pos.y())                    # за правым краем экрана
        a = QPropertyAnimation(self, b"pos", self)
        a.setDuration(360 if show else 300)
        a.setStartValue(off if show else self.pos())
        a.setEndValue(pos if show else off)
        a.setEasingCurve(QEasingCurve.Type.InOutSine)       # плавно и в начале, и в конце: без резкого торможения
        if not show:
            a.finished.connect(self.hide)
        else:
            a.finished.connect(self._lift_blob)     # когда панель доехала — Mico AI снова поверх неё
        self._anim = a
        a.start()

    def _dock_blob(self):
        """Живой Mico AI переезжает в шапку панели (место логотипа Copilot) и остаётся таким же живым."""
        if self._docked_blob:
            self._keep_dock()                  # уже в шапке — просто возвращаем его на место
            return
        self._docked_blob = True
        self._blob_home = self.blob.pos()
        self.blob.voice_k = BLOB_DOCK_K     # плавно поджимается к размеру шапки (та же механика, что в голосе)
        self.blob.locked = True             # угол экрана больше не тянет его — он в шапке панели
        self.blob.pinned = True             # и его физика тоже: привязан к шапке, пока панель открыта
        self._dock_pos = self._blob_slot_pos()
        if self._blob_anim is not None:
            self._blob_anim.stop()
        a = QPropertyAnimation(self.blob, b"pos", self)
        a.setDuration(380)
        a.setStartValue(self.blob.pos())
        a.setEndValue(self._dock_pos)
        a.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._blob_anim = a
        a.start()
        self._dock_keep.start()
        self._sync_dock_mico()
        self._lift_blob()

    def _lift_blob(self):
        """Mico AI в шапке панели должен быть ПОВЕРХ панели. Панель поднимается при активации и в конце выезда,
        поэтому поднимаем Mico AI сразу, в конце выезда и ещё раз с отсрочкой."""
        if not (self.side_mode() and self._docked_blob) or self.blob.covered():
            return
        if self.blob.isVisible():
            self.blob.raise_()
        QTimer.singleShot(150, lambda: self.blob.raise_() if (self._docked_blob and self.isVisible()) else None)

    def _keep_dock(self):
        """Пока панель открыта: Mico держится в шапке и остаётся поверх панели.
        Окно чата могли поднять кликом или вернуть из свёрнутого — шапка всегда должна быть с Mico."""
        if not self.isVisible() or self.blob is None or not self._docked_blob:
            return
        if self.blob.asleep:                          # открытая панель: Mico в шапке всегда бодрствует
            self.blob.wake(silent=True)
        if not self.blob.isVisible() or self.blob.windowOpacity() < 0.05:   # окно Mico спрятали или погасили — возвращаем
            self.blob.setWindowOpacity(1.0)
            self.blob.show()
        self._sync_dock_mico()
        anim = self._blob_anim
        if anim is None or anim.state() != QAbstractAnimation.State.Running:
            target = self._blob_slot_pos()
            if abs(self.blob.x() - target.x()) > 2 or abs(self.blob.y() - target.y()) > 2:
                self._dock_pos = target
                self.blob.move(target)
        self._lift_blob()

    def _sync_dock_mico(self):
        """В шапке панели всегда виден Mico: живой — когда встал в шапку, иначе его портрет."""
        live = self.blob is not None and self.blob.isVisible()      # пока живой Mico летит в шапку, портрета («колобка») не показываем
        self.dock_mico.setVisible(self.blob_slot.isVisible() and not live)

    def _blob_slot_pos(self):
        """Куда встаёт окно Mico AI: по центру места в шапке панели, под его будущий размер.
        Считаем от места панели у края экрана: пока панель выезжает, её окно ещё в пути."""
        d = self._dock_blob_px()
        pos, _w, _h = self._dock_rect()
        rel = self.blob_slot.mapTo(self, QPoint(0, 0))
        return QPoint(pos.x() + rel.x() + (self.blob_slot.width() - d) // 2,
                      pos.y() + rel.y() + (self.blob_slot.height() - d) // 2)

    def _undock_blob(self):
        """Панель закрывается: Mico AI сам плавно возвращается на своё место на рабочем столе."""
        if not self._docked_blob:
            return
        self._docked_blob = False
        self._dock_keep.stop()
        if self._blob_anim is not None:
            self._blob_anim.stop()
            self._blob_anim = None
        self.blob.pinned = False           # швартовка кончена
        self.blob.voice_k = None            # возвращается к обычному размеру
        self.blob.locked = False            # и к своему живому месту: его туда доведёт его же физика (_glide)
        self._sync_dock_mico()

    # ----- позиция и показ -----
    def reposition(self):
        if self.side_mode():
            self._dock_geometry()               # панель всегда у правого края: перетаскивание Mico AI её не двигает
            return
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
            self.intel.show_aichat(activate)
            return
        self.blob.touch()
        if self.blob.asleep:                        # чат открывают — Mico AI просыпается, но не повторяет «woke»
            self.blob.wake(silent=True)
        """activate=False — показать, не забирая фокус у приложения пользователя (для напоминаний и подсказок)."""
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, not activate)
        if not self.isVisible():                    # положение считаем только при открытии, чтобы чат не прыгал
            self.refresh_chips()
            if self.side_mode():
                self._dock_geometry()
                self.side.setVisible(False)                 # панель открывается чистой: чаты — по кнопке-полоскам
                self.setWindowOpacity(self._target_opacity())
                self.show()
                self.layout().activate()                # раскладка должна знать место под Mico AI
                self._slide(True)                   # панель плавно выезжает сбоку, как Windows Copilot
                self._dock_blob()                   # живой Mico AI встаёт в её шапку
            else:
                self.setWindowOpacity(0.0)
                self.reposition()
                self.show()
        elif self.side_mode():
            self._dock_blob()
        self.chat_shown.emit(True)
        self.raise_()
        if not self.side_mode() and self.windowOpacity() < self._target_opacity():
            self._fade(True)
        if activate:
            self.activateWindow()
            self.inp.setFocus()
        self._lift_blob()                           # после активации панель снова выше: Mico AI поднимаем последним

    def toggle(self):
        if self.intel and self.intel.on():
            self.intel.toggle_aichat()
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
        if not q:
            return
        if self.busy:                                       # Mico ещё отвечает: вопрос не теряем, а ставим в очередь
            self._waiting = getattr(self, "_waiting", [])
            self._waiting.append(q)
            self.inp.clear()
            return
        if self.queue or self._reveal is not None:          # прошлый ответ ещё печатается — допечатываем сразу,
            self._flush_answer()                            # иначе его хвост встанет ниже нового вопроса
        if self.cfg.get("chips_hide_on_send", True):      # кнопки скрыты, пока не нажмут в поле ввода
            self._chips_hidden = True
            self.chips_box.setVisible(False)
        if not self.user_asked:                             # первый запрос: теперь Mico может говорить сам
            self.user_asked = True
            for text in self._deferred:
                self.say(text)
            self._deferred.clear()
        self.last_pair = {"q": q, "a": ""}
        self._stream_row, self._stream_buf = None, ""   # новый вопрос — новая живая строка
        self.inp.clear()
        self._add_row("user", html.escape(q).replace("\n", "<br>"))   # пузырь вопроса — сразу, до работы с базой
        self._follow_on = True
        self._scroll_bottom(animate=True)
        self.user_sent.emit(q)
        self._ensure_conv(q)
        self._save_msg("user", q)
        self.busy = True
        self.busy_changed.emit(True)
        from assist import thinking as _thinking
        self.typing.set_steps(_thinking.steps_for(q))         # шаги раздумья — под этот запрос
        self.typing.show_typing(True)                      # Mico AI печатает: точки в пузыре
        m = detect_emotion(q)                       # Mico AI реагирует на настроение сообщения
        if m and m != "curious":
            self.blob.set_mood(m, 1.2)
            QTimer.singleShot(1250, lambda: self.busy and self.blob.set_mood("thinking"))
        else:
            self.blob.set_mood("thinking")
        self._run(q)

    def _run(self, q):
        def work():
            try:
                # on_delta: кусочки ответа летят в чат по мере генерации — человек видит текст сразу
                self.answered.emit(self.brain.ask(q, on_delta=lambda s: self.streamed.emit(s)))
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
            r = Reply(i18n.t("Ответа нет. Попробуй сказать иначе."), "worried")
        self.busy = False
        self.busy_changed.emit(False)
        self.typing.show_typing(False)
        if not r.text and not r.html and not r.image:
            r = Reply(i18n.t("Ответа нет. Попробуй сказать иначе."), "worried")
        plain = r.text or intel.plain_from_html(r.html) if r.html else r.text
        if plain:
            self.answer_text.emit(plain)                        # Mico AI: строка над Mico AI, чат — для длинного
        self.blob.touch()
        if self.last_pair is not None:
            self.last_pair["a"] = r.text or i18n.t("(ответ в виде карточек или списка)")
        if not self.blob.isVisible():
            self.blob.show()
            self.show_near()
        self.blob.set_mood(r.mood, 6)
        if r.mood in ("surprised", "happy", "love", "laugh"):
            self.blob.jump()
        if r.image and r.copy_image:
            QGuiApplication.clipboard().setImage(QImage(r.image))
        stored = (plain or "") if plain else (i18n.t("(картинка)") if r.image else "")
        self._pending_rid = self._save_msg("mico", stored)  # в журнал чата — сразу, даже если печать ещё идёт
        if plain and self.last_pair and self.conv_id is not None:
            self._schedule_title(self.conv_id, self.last_pair.get("q", ""), plain)
        if self.conv_id is not None:
            self.brain.after_turn(self.conv_id)             # иногда обновляем сводку, чтобы помнить суть
        if self._stream_row is not None and not r.html and not r.image:
            self._finish_stream(r.text or plain or "")     # живой ответ дописываем финальной версией
        else:
            self._drop_stream()                            # карточки и картинки — обычным порядком
            if r.html:
                self.queue.append(("html", "<b>Mico AI:</b><br>" + r.html))
                self.queue.append(("wi", plain))                    # тот же ответ — текстом в чат Mico AI
            else:
                self.queue.append(("text", r.text))
            if r.image:
                self.queue.append(("img", r.image))
            self._pump()
        fx = getattr(r, "fx", None)
        if fx:                                              # переключатель, ползунок или таймер — к тексту добавляется живая карточка
            self.queue.append(("fx", fx))
            self._pump()
        QTimer.singleShot(200, self._next_waiting)          # вопрос, заданный во время ответа, — следующим

    def _next_waiting(self):
        """Задаёт вопрос из очереди, когда прошлый ответ полностью показан."""
        waiting = getattr(self, "_waiting", None)
        if not waiting or self.busy:
            return
        if self.queue or self._reveal is not None:
            QTimer.singleShot(300, self._next_waiting)
            return
        self.submit(waiting.pop(0))

    def _flush_answer(self):
        """Показывает остаток ответа сразу целиком (без печати по буквам), ничего не теряя."""
        self._finish_reveal()
        self._instant = True
        try:
            self._pump()
        finally:
            self._instant = False
        self.blob.talking = False

    def on_initiative(self, payload):
        """Mico AI сам что-то увидел и говорит первым — тихо, без захвата фокуса.
        Перерыв приходит с меткой BREAK_MARK. В режиме Mico AI — полоской по краю экрана."""
        if not self.may_speak():                  # настройка «не заговаривать первым»: молчим до запроса
            return
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

    # ----- лента сообщений и печать ответа: Mico AI говорит ртом -----

    def _icon_btn(self, icon):
        b = QPushButton()
        b.setObjectName("iconBtn")
        b.setIcon(icon)
        b.setIconSize(QSize(18, 18))
        b.setFixedSize(30, 30)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _add_row(self, role, body_html, rid=None):
        row = chat_look.MessageRow(role, body_html, accent=self.cfg["color"])
        row.link.connect(self.on_link)
        self.msgs.insertWidget(self.msgs.indexOf(self.typing), row)   # всегда перед «печатает» и пустым местом
        row.fit(self.scroll.viewport().width() or self.width())
        QTimer.singleShot(0, lambda: row.fit(self.scroll.viewport().width() or self.width()))   # после раскладки — точная ширина
        if rid is not None:
            self._rows[rid] = row
        now = time.time()
        if self.isVisible() and now - getattr(self, "_last_row_t", 0) > 0.05:   # история грузится без анимаций
            from ui import motion
            motion.fade_slide_in(row, dy=10, ms=260)    # новое сообщение мягко всплывает
        self._last_row_t = now
        self._update_greeting()
        return row

    def _clear_rows(self):
        for i in reversed(range(self.msgs.count())):
            w = self.msgs.itemAt(i).widget()
            if w is not None and w is not self.typing and w is not self.greeting:
                self.msgs.takeAt(i)
                w.deleteLater()
        self._rows.clear()
        self._update_greeting()
        self.refresh_welcome()

    def _update_greeting(self):
        """Приветствие — только в пустом чате: как только появилась реплика, оно уходит.
        Пока человек пишет запрос, кнопки действий прячутся — как у Windows Copilot.
        Портрет Mico в приветствии — только в обычном окне: в панели сверху и так живой Mico AI."""
        has = any(isinstance(self.msgs.itemAt(i).widget(), chat_look.MessageRow) for i in range(self.msgs.count()))
        if has:
            self.greeting.fade_out()                   # запрос отправлен — кнопки плавно уходят
        else:
            self.greeting.show_again()
            self.greeting.set_suggest_visible(True)    # пока человек пишет, кнопки остаются
        self.greeting.set_portrait_visible(not self.side_mode())
        self.style_row.setVisible(has)     # выбор стиля живёт в приветствии; в разговоре — строкой над лентой

    def _fit_rows(self):
        """Пузыри сообщений переносятся по текущей ширине ленты (смена размера и режима чата)."""
        w = self.scroll.viewport().width()
        for i in range(self.msgs.count()):
            it = self.msgs.itemAt(i).widget()
            if isinstance(it, chat_look.MessageRow):
                it.fit(w)

    def _refresh_profile(self):
        name = self.cfg.get("user_name", "")
        self.avatar.set_name(name)
        self.greeting.set_name(name)
        if getattr(self, "side", None) is not None:
            self.side.set_profile(name)

    def edit_profile(self):
        """Профиль редактируется в отдельной вкладке настроек, а не в отдельном диалоге чата."""
        self.profile_requested.emit()

    def _scroll_bottom(self, animate=False):
        """Лента уезжает вниз, если человек за ней не следит сам. Во время печати — без анимации, ровно."""
        if not self._follow_on:
            return
        QTimer.singleShot(30, lambda: setattr(self, "_scroll_anim", chat_look.scroll_to_bottom(self.scroll, animate)))

    def _stop_follow(self):
        self._follow_on = False                                     # человек сам крутит — не мешаем
        if self._scroll_anim is not None:
            self._scroll_anim.stop()
            self._scroll_anim = None

    def _start_reveal(self, text):
        """Текст Mico AI появляется по буквам: длинный — дольше, короткий — быстрее."""
        row = self._add_row("mico", "", rid=self._pending_rid)
        self._pending_rid = None
        total_ms = min(1800, max(300, 6 * len(text)))        # быстрая печать: не дольше двух секунд
        ticks = max(1, total_ms // 22)
        self._reveal = {"row": row, "text": text, "pos": 0, "step": max(1, -(-len(text) // ticks))}
        self.blob.talking = True
        self._follow_on = True
        self._reveal_timer.start(22)

    def _reveal_tick(self):
        r = self._reveal
        if r is None:
            self._reveal_timer.stop()
            return
        r["pos"] = min(len(r["text"]), r["pos"] + r["step"])
        r["row"].label.setText(rich_html(r["text"][:r["pos"]]))
        self._scroll_bottom()
        if r["pos"] >= len(r["text"]):
            self._finish_reveal()
            QTimer.singleShot(400, self._stop_talk)
            self._pump()

    def _finish_reveal(self):
        """Допечатываем сразу (человек начал печатать или ответ закончился)."""
        r = self._reveal
        self._reveal_timer.stop()
        if r is not None:
            r["row"].label.setText(rich_html(r["text"]))
        self._reveal = None

    def say(self, text):
        self.queue.append(("text", text))
        self._pump()

    def on_stream(self, text):
        """Живой ответ: текст появляется по мере генерации — как у облачных ассистентов."""
        if self._stream_row is None:
            self.typing.show_typing(False)               # точки больше не нужны: текст уже идёт
            self._stream_row = self._add_row("mico", "")
            self.blob.talking = True
        self.blob.touch()                                # ответ идёт — Mico рядом и не засыпает
        self._stream_buf += text
        self._stream_row.label.setText(rich_html(self._stream_buf) + "▌")
        self._scroll_bottom()

    def _finish_stream(self, text):
        """Потоковый ответ закончился: показываем финальную версию (она чище предпросмотра)."""
        row, self._stream_row = self._stream_row, None
        self._stream_buf = ""
        if row is not None:
            row.label.setText(rich_html(text))
            if self._pending_rid is not None:
                self._rows[self._pending_rid] = row       # строка привязана к сообщению в журнале чата
                self._pending_rid = None
        self.mico_said.emit(text)
        QTimer.singleShot(400, self._stop_talk)
        self._pump()

    def _drop_stream(self):
        """Ответ пришёл карточками или картинкой: живую строку убираем и показываем как обычно."""
        row, self._stream_row = self._stream_row, None
        self._stream_buf = ""
        if row is not None:
            self.msgs.removeWidget(row)
            row.deleteLater()
        self._pending_rid = None

    def _pump(self):
        """Ответ появляется по очереди: текст печатается по буквам, карточки и картинки — сразу."""
        if self._reveal is not None:                                  # уже печатаем: продолжим, когда допечатаем
            return
        while self.queue:
            kind, val = self.queue.pop(0)
            if kind == "html":
                self._add_row("mico", val.replace("<b>Mico AI:</b><br>", "", 1))
                self._scroll_bottom(animate=True)
            elif kind == "img":                                      # картинку кладём в ленту, а не по ссылке
                row = self._add_row("mico", "")
                row.set_image(val)
                self._scroll_bottom(animate=True)
            elif kind == "wi":
                self.mico_said.emit(val)
            elif kind == "fx":
                self._add_fx(val)
            else:
                self.mico_said.emit(val)
                if getattr(self, "_instant", False) or not self.isVisible():   # чат скрыт — не ждём печати          # допечатать сразу: строка целиком, без анимации
                    self._add_row("mico", rich_html(val), rid=self._pending_rid)
                    self._pending_rid = None
                    continue
                self._start_reveal(val)
                return
        self._scroll_bottom(animate=True)

    def _add_fx(self, spec):
        """Карточка-анимация под ответом: что именно переключилось (ui/switchfx.py). В чат Mico AI уходит тем же сигналом."""
        self.mico_fx.emit(spec)
        if not self.isVisible():
            return
        try:
            from ui import switchfx
            row = switchfx.build_row(spec, self.cfg["color"], theme.is_dark(self.cfg))
        except Exception:
            return                                          # анимация — украшение: при сбое ответ всё равно виден
        self.msgs.insertWidget(self.msgs.indexOf(self.typing), row)
        from ui import motion
        motion.fade_slide_in(row, dy=10, ms=300)
        self._scroll_bottom(animate=True)

    def _stop_talk(self):
        if not self.blob.voice_active:            # настоящая речь сама решает, когда рот закрыть
            self.blob.talking = False

    # ----- чаты: начать, открыть, искать -----
    def _schedule_title(self, cid, question, answer):
        """Название чата придумывает сам ИИ: один раз, после первого ответа, в фоне. До тех пор — «Новый чат»."""
        done = self.__dict__.setdefault("_titled", set())
        if cid in done or self._store is None:
            return
        done.add(cid)
        prompt = ("Придумай короткое название для этого разговора: 2–4 слова, по-русски (если беседа на другом языке — "
                  "на нём). Без кавычек, точек и смайликов. Ответь только названием.\n\n"
                  f"Вопрос: {question[:300]}\nОтвет: {answer[:300]}")

        def work():
            try:
                raw = self.brain.quick_answer(prompt)
            except Exception:
                raw = ""
            title = chat_title.clean_model_title(raw, question)
            try:
                self._store.conv_set_title(cid, title)
            except Exception:
                return
            self.title_ready.emit()

        threading.Thread(target=work, daemon=True).start()

    def _ensure_conv(self, first_text):
        """Первый вопрос в новом чате — создаёт чат. Если память выключена, чат живёт только в этом окне."""
        if self.conv_id is None and self._store is not None and self.cfg.get("memory_on", True):
            title = chat_title.DEFAULT                       # название придумает сам ИИ после первого ответа
            self.conv_id = self._store.conv_new(title, time.time())
            self.brain.set_conversation(self.conv_id)
        return self.conv_id

    def _save_msg(self, role, text):
        if self.conv_id is None or self._store is None or not text:
            return None
        return self._store.conv_add_msg(self.conv_id, time.time(), role, text)

    def _refresh_side(self):
        if self._store is not None:
            items = []
            for cid, title, upd in self._store.conv_list(60):
                if "[thinking]" in title:                    # старое название от рассуждений модели: заменяем на первый запрос
                    fixed = chat_title.make_title(self._store.conv_first_question(cid))
                    self._store.conv_set_title(cid, fixed)
                    title = fixed
                items.append((cid, title, upd))
            self.side.set_chats(items, self.conv_id)

    def _toggle_side(self, on=None):
        """Недавние чаты: в боковой панели выезжают по кнопке-полоскам, в обычном окне открыто всегда."""
        if not self.side_mode():
            self.side.show()
            return
        self.side.setVisible(not self.side.isVisible() if on is None else bool(on))
        self.side.raise_()

    def _reveal_history(self):
        """Смена недавнего чата воспринимается как переход, а не как резкая подмена ленты."""
        if self._history_anim is not None:
            self._history_anim.stop()
        effect = QGraphicsOpacityEffect(self.scroll)
        effect.setOpacity(0.0)
        self.scroll.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._history_anim = anim

        def done():
            if self._history_anim is anim:
                self._history_anim = None
            self.scroll.setGraphicsEffect(None)

        anim.finished.connect(done)
        anim.start()

    def new_chat(self):
        if self.busy:
            return
        self.conv_id = None
        self._clear_rows()
        self.brain.set_conversation(None)
        self.search.clear()
        self._refresh_side()
        self._toggle_side(False)
        self._reveal_history()
        self.inp.setFocus()

    def open_chat(self, cid, focus_rid=None):
        if self.busy or self._store is None:
            return
        self.conv_id = cid
        self._clear_rows()
        for rid, ts, role, text in self._store.conv_messages(cid, limit=200):
            self._add_row("user" if role == "user" else "mico",
                                html.escape(text).replace("\n", "<br>") if role == "user" else rich_html(text), rid=rid)
        self.brain.set_conversation(cid)
        self._reveal_history()
        self.search.clear()
        self._refresh_side()                    # подсветить открытый чат в боковом меню
        self._toggle_side(False)
        QTimer.singleShot(60, lambda: self._jump_to(focus_rid) if focus_rid else self._scroll_bottom())
        self._follow_on = focus_rid is None

    def _jump_to(self, rid):
        row = self._rows.get(rid)
        if row is None:
            return
        self._follow_on = False
        self.scroll.ensureWidgetVisible(row, 0, 24)

    def _search_changed(self, text):
        q = " ".join(text.split())
        if len(q) < 2 or self._store is None:
            self.results.hide()
            return
        hits = [h for h in self._store.conv_search(q, limit=200) if h[0] == self.conv_id][:25]
        titles = {}
        self.results.clear()
        for cid, rid, ts, role, t in hits:
            self.results.addItem(chat_look.result_item(titles.get(cid, i18n.t("Чат")), t, q, cid, rid))
        if not hits:
            it = QListWidgetItem(i18n.t("Ничего не нашлось. Попробуй другое слово."))
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(it)
        h = min(240, 8 + 52 * self.results.count())
        top = self.head_bar.geometry().bottom() + 4
        self.results.setGeometry(self.head_bar.x() + 6, top, self.head_bar.width() - 12, h)
        self.results.raise_()
        self.results.show()

    def _open_result(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        cid, rid = data
        self.results.hide()
        if cid == self.conv_id:
            self._jump_to(rid)
        else:
            self.open_chat(cid, focus_rid=rid)

# =============================== Настройки ===============================
# Подсказки к настройкам: что это, стоит ли включать и когда
HELP = {
    "linked": (i18n.t("Чат меняется вместе с Mico AI"),
               i18n.t("Один ползунок меняет размер и шара, и окна чата."),
               i18n.t("включи, если хочешь всё крупнее или мельче сразу. Выключи, если нужен большой чат и маленький шар.")),
    "outline": (i18n.t("Обводка вокруг чата"),
                i18n.t("Цветная рамка вокруг окна чата. Только внешний вид."),
                i18n.t("выключи для минималистичного вида, включи, чтобы чат был заметнее на фоне.")),
    "locc": (i18n.t("Геопозиция для погоды"),
             i18n.t("Windows отдаёт Mico AI координаты, чтобы узнать погоду в твоём месте."),
             i18n.t("включи, если хочешь погоду без ввода города. Выключи — тогда укажи город вручную.")),
    "greet": (i18n.t("Здороваться при включении ПК"),
              i18n.t("При входе в Windows Mico AI говорит «Добрый день» или «Добрый вечер» и показывает пункты приветствия."),
              i18n.t("включи, если приятно видеть приветствие. Выключи для тихого запуска.")),
    "auto": (i18n.t("Запуск с Windows"),
             i18n.t("Mico AI стартует сам при входе в Windows и после разблокировки экрана."),
             i18n.t("включи, если пользуешься Mico AI каждый день. Выключи, если запускаешь его вручную.")),
    "mem": (i18n.t("Запоминать действия"),
            i18n.t("Mico AI записывает твои команды и открытые программы (зашифровано) и учится на привычках."),
            i18n.t("включи для подсказок, кнопок и «что я делал». Выключи, если не хочешь записей: тогда эти функции не работают.")),
    "pbr": (i18n.t("Напоминание о перерыве"),
            i18n.t("Mico AI напомнит отдохнуть, если работаешь без остановки дольше заданного времени."),
            i18n.t("включи, если забываешь делать перерывы.")),
    "silent": (i18n.t("Не заговаривать первым"),
               i18n.t("Mico AI молчит при запуске и не пишет в чат сам, пока ты не напишешь запрос или не нажмёшь кнопку."),
               i18n.t("включи, чтобы он не лез с приветствием и напоминаниями. Выключи, если хочешь, чтобы Mico заговаривал первым.")),
    "quiet": (i18n.t("Режим тишины"),
              i18n.t("Mico AI не здоровается, не предлагает помощь и не заговаривает первым. Напоминания, которые ты сам поставил, работают."),
              i18n.t("включи для созвона, фильма или работы без отвлечений. Выключи, когда хочешь живого компаньона.")),
}


class NoWheelSlider(RoundSlider):
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
    """О программе: логотип Mico, номер версии и что нового — карточками в прокручиваемом списке."""
    def __init__(self, parent, cfg):
        super().__init__(parent)
        from ui import appicon
        self.setWindowTitle(i18n.t("О программе Mico AI"))
        self.setMinimumWidth(480)
        accent = cfg.get("color") or "#FFCFA3"
        dark = theme.is_dark(cfg)
        bg = "#202020" if dark else "#f3f3f3"
        card = "#2b2b2b" if dark else "#ffffff"
        edge = "#3a3a3a" if dark else "#e2e2e2"
        ink = "#f2f2f2" if dark else "#1b1b1b"
        muted = "#9d9d9d" if dark else "#6b6b6b"
        self.setStyleSheet(f"""
            QDialog {{ background: {bg}; }}
            QLabel {{ background: transparent; }}
            QLabel#aboutTitle {{ color: {ink}; font-size: 24px; font-weight: 600; }}
            QLabel#aboutSub {{ color: {muted}; font-size: 13px; }}
            QLabel#aboutBadge {{ color: {accent}; border: 1px solid {accent}; border-radius: 11px;
                                 padding: 2px 12px; font-size: 12px; font-weight: 600; }}
            QLabel#aboutSection {{ color: {muted}; font-size: 11px; font-weight: 600; letter-spacing: 1px; }}
            QLabel#aboutDot {{ color: {accent}; font-size: 14px; }}
            QLabel#aboutItem {{ color: {ink}; font-size: 13px; }}
            QFrame#aboutCard {{ background: {card}; border: 1px solid {edge}; border-radius: 14px; }}
            QScrollArea {{ background: transparent; border: none; }}
            QWidget#aboutList {{ background: transparent; }}
            QPushButton#aboutClose {{ background: {accent}; color: {theme.on_accent(accent)}; border: none;
                                      border-radius: 17px; padding: 9px 26px; font-size: 13px; font-weight: 600; }}
        """)

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 26, 28, 22)
        v.setSpacing(14)

        top = QHBoxLayout()
        top.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(appicon.blob_pixmap(84, accent))
        top.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(6)
        title = QLabel("Mico AI")
        title.setObjectName("aboutTitle")
        col.addWidget(title)
        badge_row = QHBoxLayout()
        badge = QLabel(i18n.t("Версия") + " " + version.display_version())
        badge.setObjectName("aboutBadge")
        badge_row.addWidget(badge)
        badge_row.addStretch(1)
        col.addLayout(badge_row)
        sub = QLabel(i18n.t("ИИ-компаньон на рабочем столе"))
        sub.setObjectName("aboutSub")
        col.addWidget(sub)
        top.addLayout(col, 1)
        v.addLayout(top)

        section = QLabel(i18n.t("Что нового в этой версии").upper())
        section.setObjectName("aboutSection")
        v.addWidget(section)

        entry = version.CHANGELOG.get(version.APP_VERSION, {})
        changes = entry.get("changes") or [i18n.t("Исправления и мелкие улучшения.")]
        holder = QWidget()
        holder.setObjectName("aboutList")
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        for text in changes:
            box = QFrame()
            box.setObjectName("aboutCard")
            row = QHBoxLayout(box)
            row.setContentsMargins(14, 11, 16, 11)
            row.setSpacing(10)
            dot = QLabel("●")
            dot.setObjectName("aboutDot")
            dot.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.addWidget(dot)
            item = QLabel(i18n.t(text))
            item.setObjectName("aboutItem")
            item.setWordWrap(True)
            item.setTextFormat(Qt.TextFormat.PlainText)
            row.addWidget(item, 1)
            hl.addWidget(box)
        hl.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(260)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)

        foot = QHBoxLayout()
        foot.addStretch(1)
        close = QPushButton(i18n.t("Закрыть"))
        close.setObjectName("aboutClose")
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)
        foot.addWidget(close)
        v.addLayout(foot)


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


SETTINGS_SIZES = [("compact", i18n.t("Компактное"), (800, 640)), ("medium", i18n.t("Обычное"), (940, 720)),
                  ("large", i18n.t("Просторное"), (1100, 800))]


CHAT_W, CHAT_H = 560, 520      # стандартный размер чата Mico AI, px (с боковым меню, было 350×420)
SIDE_W = 480                   # ширина боковой панели чата (как Windows Copilot), px при масштабе 100%; было 430 — толще
BLOB_DOCK_K = 0.85             # доля размера Mico AI в шапке боковой панели (было 0.62 — слишком мелко)


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
        from ui import icons as uiicons
        self._arrow.setPixmap(uiicons.icon("chev_up" if opened else "chev_down", "#9a9a9a", 18).pixmap(18, 18))

    def toggle(self):
        self.setExpanded(not self._body.isVisible())

    def setExpanded(self, on):
        self._body.setVisible(bool(on))
        self._set_arrow(bool(on))

class _ExpHead(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, e):
        self.clicked.emit()
        super().mousePressEvent(e)


def _run_cb(res, cb):
    """Ответ фонового вызова передаётся в обработчик. Ошибка в нём не должна валить окно настроек: пишем в журнал."""
    try:
        cb(res)
    except Exception as e:
        from voice.log import record
        record("Настройки: ответ чата не обработан", e)


def _alive(w):
    """Виджет ещё жив (Qt мог его удалить при перестройке раздела)."""
    try:
        w.objectName()
        return True
    except RuntimeError:
        return False


class _MainCall(QObject):
    """Вызов функции в главном потоке Qt из фонового: фоновый поток ждёт, пока она выполнится."""
    run = pyqtSignal(object, object)


class _AsyncBus(QObject):
    """Ответ модели приходит из фонового потока: callback выполняется в основном потоке через сигнал."""
    done = pyqtSignal(object, object)     # (результат или исключение, функция, которую вызвать)


class SettingsDialog(QDialog):
    def __init__(self, cfg, blob, panel, hooks, parent=None, start_tab=None):
        super().__init__(parent)
        self.cfg, self.blob, self.panel, self.hooks, self.orig = cfg, blob, panel, hooks, dict(cfg)
        self._start_tab = start_tab
        self.setWindowTitle(i18n.t("Настройки Mico AI"))
        try:                                              # значок окна — настоящий Mico (как на экране), а не старая картинка
            from ui import appicon
            self.setWindowIcon(appicon.blob_icon(cfg["color"]))
        except Exception:
            pass
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)   # своя шапка в стиле макета (перетаскивается мышью)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)   # скруглённые углы и свечение рамки
        self.setObjectName("settingsWin")
        self.setMinimumSize(760, 560)
        self._apply_size("compact")                     # размер окна настроек фиксированный
        self._drag = None                               # шапку тянут мышью: здесь смещение от угла окна
        self._style_dialog()
        self._reg = {}                                  # ключ настройки → её элемент (для кнопки «Сбросить»)
        self._reg_text = {}                             # ключ настройки → подпись пункта 
        self._ai_bus = _AsyncBus()                      # ответы модели из фона приходят сюда
        self._ai_bus.done.connect(_run_cb)
        self._phrase_tab = None                         # номер раздела «Свои фразы» (чат переводит туда после «Да»)
        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setContentsMargins(16, 16, 16, 16)        # поле вокруг рамки, чтобы тень не резалась
        frame = QFrame()
        frame.setObjectName("frame")
        outer.addWidget(frame)
        root = QVBoxLayout(frame)
        root.setContentsMargins(20, 14, 20, 16)
        root.setSpacing(12)
        # шапка: логотип, название, поиск и кнопки окна — как в макете
        head = QHBoxLayout()
        head.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(settings_look.logo_pixmap(22, cfg["color"]))
        head.addWidget(logo)
        win_title = QLabel(i18n.t("Настройки Mico AI"))
        win_title.setObjectName("winTitle")
        head.addWidget(win_title)
        head.addSpacing(18)
        # поиск по настройкам: набери слово — останутся только подходящие пункты
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText(i18n.t("Поиск по настройкам"))
        self.search.setClearButtonEnabled(True)
        from ui import icons as _ui
        self.search.addAction(_ui.icon("search", settings_look.ink(cfg["color"], theme.is_dark(cfg)), 16),
                              QLineEdit.ActionPosition.LeadingPosition)
        head.addWidget(self.search, 1)
        for text, obj, handler in (("—", "winBtn", self.showMinimized),
                                   ("☐", "winBtn", self._toggle_max),
                                   ("✕", "winClose", self.accept)):      # крестик сохраняет и закрывает
            b = QPushButton(text)
            b.setObjectName(obj)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(handler)
            head.addWidget(b)
        root.addLayout(head)
        self.found_hint = QLabel(i18n.t("Ничего не нашлось. Попробуй другое слово."))
        self.found_hint.setObjectName("hint")
        self.found_hint.setVisible(False)
        root.addWidget(self.found_hint)
        self._vis = {}                                  # исходная видимость строк (чтобы поиск вернул всё как было)
        self._expanders_orig = {}                       # раскрытые блоки до поиска (после поиска возвращаем)
        tabs = self._tabs = sidetabs.SideTabs()                    # разделы слева, содержимое справа
        tabs.set_icon_color(settings_look.ink(cfg["color"], theme.is_dark(cfg)))   # значки разделов — цвет Mico
        tabs.set_accent(cfg["color"])
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(tabs, 1)
        root.addLayout(body, 1)
        self._search_timer = QTimer(self)                # поиск запускается после короткой паузы в наборе: страницы не дёргаются
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(140)
        self._search_timer.timeout.connect(lambda: self._filter_settings(self.search.text()))
        self.search.textChanged.connect(lambda _t: self._search_timer.start())

        # --- Внешний вид ---
        look = QWidget()                              # Цвет и тема
        f = QFormLayout(look)
        self.cbtn = QPushButton()
        self.cbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cbtn.clicked.connect(self.pick)
        self._paint_accent_btn()
        self._row(f, i18n.t("Цвет Mico AI"), self.cbtn, "color")
        self.cres = QPushButton(i18n.t("Вернуть стандартный цвет Mico AI"))
        self.cres.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cres.clicked.connect(self._reset_mico_color)
        f.addRow("", self._with_hint(self.cres, "Вернёт цвет Mico AI, который стоит по умолчанию."))
        self.th = NoWheelComboBox()
        for key, name in (("auto", i18n.t("Как в системе (Windows)")), ("light", i18n.t("Светлая")), ("dark", i18n.t("Тёмная"))):
            self.th.addItem(name, key)
        self.th.setCurrentIndex(max(0, self.th.findData(cfg.get("theme", "auto"))))
        self.th.currentIndexChanged.connect(self.live_theme)
        self._row(f, i18n.t("Тема чата и окон"), self.th, "theme")

        look_size = QWidget()                         # Размер и прозрачность
        f = QFormLayout(look_size)
        self.sc = NoWheelSlider(Qt.Orientation.Horizontal)
        self.sc.setRange(40, 200)
        self.sc.setValue(int(cfg["scale"] * 100))
        self.sc.valueChanged.connect(self.live)
        self._row(f, i18n.t("Размер Mico AI"), with_readout(self.sc, " %"), "scale")
        self.linked = WrapCheck(i18n.t("Чат меняется вместе с Mico AI (один ползунок)"))
        self.linked.setChecked(cfg.get("chat_linked", True))
        self.linked.toggled.connect(self.live_linked)
        f.addRow(self._hc(self.linked, "linked"))
        self.csc = NoWheelSlider(Qt.Orientation.Horizontal)
        self.csc.setRange(60, 200)
        self.csc.setValue(int(cfg.get("chat_scale", 1.0) * 100))
        self.csc.valueChanged.connect(self.live_chat)
        self.csc_lbl = QLabel(i18n.t("Размер чата"))
        self.csc_box = with_readout(self.csc, " %")
        self._chat_size_hint()
        self._row(f, self.csc_lbl, self.csc_box, "chat_scale")
        self.sleep_fps = NoWheelComboBox()
        for fps in (60, 30, 20, 15, 10):
            self.sleep_fps.addItem(f"{fps} кадров в секунду", fps)
        self.sleep_fps.setCurrentIndex(max(0, self.sleep_fps.findData(int(cfg.get("anim_sleep_fps", 20)))))
        self._row(f, i18n.t("Частота анимации во сне"), self.sleep_fps, "anim_sleep_fps")

        look_outline = QWidget()                      # Обводки и подсветка
        f = QFormLayout(look_outline)
        self.outline = WrapCheck(i18n.t("Обводка вокруг окна чата"))
        self.outline.setChecked(cfg.get("chat_outline", True))
        self.outline.toggled.connect(self.live_outline)
        self.in_outline = WrapCheck(i18n.t("Обводка поля ввода в чате Mico AI"))
        self.in_outline.setChecked(bool(cfg.get("wi_input_outline", True)))
        self.in_outline.toggled.connect(lambda on: self._set_outline("wi_input_outline", on))
        self.outline.setText(i18n.t("Обводки вокруг окна чата и поля ввода"))   # два переключателя — один
        self.outline.setChecked(bool(cfg.get("chat_outline", True)) or self.in_outline.isChecked())
        self.outline.toggled.connect(self.in_outline.setChecked)
        self.in_outline.setParent(look_outline)
        self.in_outline.hide()
        f.addRow(self._hc(self.outline, "outline"))

        # --- Профиль ---
        profile = QWidget()
        f = QFormLayout(profile)
        self.profile_name = QLineEdit(cfg.get("user_name", ""))
        self.profile_name.setPlaceholderText("Например, Сергей")
        f.addRow(i18n.t("Как к тебе обращаться"), self.profile_name)
        self.profile_phone = QLineEdit(cfg.get("user_phone", ""))   # для умных полей агента — только после «да»
        self.profile_phone.setPlaceholderText("Например, +7 900 000-00-00")
        f.addRow(i18n.t("Телефон (для форм на сайтах)"), self.profile_phone)
        self.profile_email = QLineEdit(cfg.get("user_email", ""))
        self.profile_email.setPlaceholderText("Например, serge@mail.ru")
        f.addRow(i18n.t("Почта (для форм на сайтах)"), self.profile_email)
        self.profile_style = NoWheelComboBox()
        for data, title in ((("friendly", "name"), "Дружелюбно, по имени"),
                            (("concise", "neutral"), "Коротко и по делу"),
                            (("supportive", "you"), "Спокойно и поддерживающе"),
                            (("expert", "neutral"), "Экспертно и нейтрально"),
                            (("playful", "you"), "Легко, с юмором")):
            self.profile_style.addItem(title, data)
        style = (cfg.get("user_tone", "friendly"), cfg.get("user_address", "name"))
        style_index = self.profile_style.findData(style)
        if style_index < 0:  # старый профиль: сохраняем его главную манеру, даже если обращение было другим
            style_index = {"friendly": 0, "concise": 1, "supportive": 2, "expert": 3, "playful": 4}.get(style[0], 0)
        self.profile_style.setCurrentIndex(style_index)
        self.profile_style.setParent(profile)          # стиль общения выбирается прямо в чате — в настройках его нет
        self.profile_style.hide()
        self.profile_language = NoWheelComboBox()
        for key, title in (("auto", "На языке моего вопроса"), ("ru", "Всегда по-русски"), ("en", "Always in English")):
            self.profile_language.addItem(title, key)
        self.profile_language.setCurrentIndex(max(0, self.profile_language.findData(cfg.get("user_reply_language", "auto"))))
        f.addRow(i18n.t("Язык ответов"), self.profile_language)
        self.profile_answers = NoWheelComboBox()
        for data, title in ((("brief", "answer_first", "best_effort"), "Кратко: вывод и главное"),
                            (("balanced", "natural", "when_needed"), "По делу: ясно и достаточно"),
                            (("detailed", "bullets", "ask_first"), "Подробно: структура и уточнения")):
            self.profile_answers.addItem(title, data)
        answers = (cfg.get("user_answer_length", "balanced"), cfg.get("user_answer_format", "natural"), cfg.get("user_clarify", "when_needed"))
        answers_index = self.profile_answers.findData(answers)
        if answers_index < 0:  # старые точные настройки — выбираем ближайший пресет по длине
            answers_index = {"brief": 0, "balanced": 1, "detailed": 2}.get(answers[0], 1)
        self.profile_answers.setCurrentIndex(answers_index)
        f.addRow(i18n.t("Как отвечать"), self.profile_answers)
        self.profile_about = QPlainTextEdit(cfg.get("user_about", ""))
        self.profile_about.setObjectName("profileContext")
        self.profile_about.setPlaceholderText("Например: я пишу на Python и делаю интерфейсы. Люблю конкретные ответы с примерами.")
        self.profile_about.setMinimumHeight(118)
        f.addRow(i18n.t("Контекст для Mico AI"), self.profile_about)
        profile_hint = QLabel("Эти данные используются только для того, чтобы Mico AI лучше подстраивал ответы под тебя.")
        profile_hint.setObjectName("hint")
        profile_hint.setWordWrap(True)
        f.addRow(profile_hint)

        # --- Поведение ---
        pos = QWidget()                               # Положение и сон
        f = QFormLayout(pos)
        self.sleep_min = NoWheelSpinBox()
        self.sleep_min.setRange(0, 30)
        self.sleep_min.setSuffix(i18n.t(" мин (0 — не засыпать)"))
        self.sleep_min.setValue(cfg.get("sleep_after_min", 3))
        self._row(f, i18n.t("Засыпать, если никто не обращается"), self.sleep_min, "sleep_after_min")

        start = QWidget()                             # Запуск и поведение
        f = QFormLayout(start)
        self.greet = WrapCheck(i18n.t("Здороваться при включении ПК (день/вечер, погода, что делал вчера)"))
        self.greet.setChecked(cfg["greet_on_start"])
        self.silent = WrapCheck(i18n.t("Не заговаривать первым: молчать, пока я сам не напишу"))
        self.silent.setChecked(cfg.get("silent_until_asked", True))
        self.auto = WrapCheck(i18n.t("Запускать вместе с Windows (вход в систему)"))
        self.auto.setChecked(autostart.status()[0])        # показываем то, что реально стоит в Планировщике
        f.addRow(self._hc(self.auto, "auto"))
        self.quiet = WrapCheck(i18n.t("Режим тишины: без приветствий, инициативы и подсказок"))
        self.quiet.setChecked(cfg.get("quiet_mode", False))
        # Три переключателя про одно и то же (приветствие, «не заговаривать первым», режим тишины) — один выбор.
        # Сами переключатели остаются скрытыми: они хранят значения для сохранения, ключи cfg прежние.
        for hidden in (self.greet, self.silent, self.quiet):
            hidden.setParent(start)
            hidden.hide()
        self.initiative = NoWheelComboBox()
        for label, state in ((i18n.t("Здоровается и сам подсказывает"), (True, False, False)),
                             (i18n.t("Здоровается, дальше ждёт меня"), (True, True, False)),
                             (i18n.t("Молчит, пока я не напишу"), (False, True, False)),
                             (i18n.t("Режим тишины: без подсказок"), (False, True, True))):
            self.initiative.addItem(label, state)
        if self.quiet.isChecked():
            idx = 3
        elif not self.greet.isChecked():
            idx = 2
        else:
            idx = 1 if self.silent.isChecked() else 0
        self.initiative.setCurrentIndex(idx)

        def _set_initiative(_=0):
            g, s, q = self.initiative.currentData()
            self.greet.setChecked(g)
            self.silent.setChecked(s)
            self.quiet.setChecked(q)
        self.initiative.currentIndexChanged.connect(_set_initiative)
        self._row(f, i18n.t("Когда Mico говорит первым"), self.initiative, None)
        self.lang = NoWheelComboBox()                 # язык интерфейса; применяется после перезапуска
        for code, name in i18n.LANGUAGES:
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(cfg.get("language", "en"))))
        self._row(f, i18n.t("Язык интерфейса"), self.lang, "language")
        self.lang_note = QLabel(i18n.t("Язык меняется после перезапуска Mico AI."))
        self.lang_note.setObjectName("hint")
        self.lang_note.setParent(start)
        self.lang_note.hide()                          # то же самое уже написано в подсказке к языку — дубль убран
        hist = QWidget()                              # История и поиск
        f = QFormLayout(hist)
        self.keep = NoWheelComboBox()                 # сколько хранить историю; «всегда» — без очистки
        for days, text in ((7, i18n.t("7 дней")), (30, i18n.t("30 дней")), (90, i18n.t("90 дней")), (365, i18n.t("365 дней")), (0, i18n.t("всегда"))):
            self.keep.addItem(text, days)
        if self.keep.findData(cfg["retention_days"]) < 0:      # значение из файла, которого нет в списке
            self.keep.addItem(f"{cfg['retention_days']} дн.", cfg["retention_days"])
        self.keep.setCurrentIndex(self.keep.findData(cfg["retention_days"]))
        self._row(f, i18n.t("Хранить историю"), self.keep, "retention_days")

        menu = QWidget()                              # Меню по правому щелчку
        f = QFormLayout(menu)
        f.addRow(QLabel(i18n.t("<small>Что показывать в меню по правому щелчку. «Выход» есть всегда.</small>")))
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
        f.addRow(self._with_hint(self.mlist, "Отметь пункты, которые показывать в меню по правому щелчку. Остальные скрыты."))
        self._row(f, i18n.t("Не больше пунктов"), self.mmax, "menu_max")
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
        self.city.setPlaceholderText(i18n.t("например, Москва — если геопозиция недоступна"))
        self.locc = WrapCheck(i18n.t("Разрешить геопозицию (Windows всё равно спросит подтверждение)"))
        self.locc.setChecked(cfg.get("loc_consent") is True)
        f.addRow(QLabel(theme.heading(i18n.t("Что показывать при включении ПК (до 3)"))))
        f.addRow(self._with_hint(self.gl, "Отметь, что говорить при включении ПК. Можно выбрать до трёх пунктов."))
        f.addRow(self.gcnt)
        self.wstart = WrapCheck(i18n.t("Погода при запуске Mico AI"))       # отдельно: выключить только погоду
        self.wstart.setChecked(cfg.get("weather_on_start", True))
        f.addRow(self._block(self.wstart, "weather_on_start"))
        self._row(f, i18n.t("Город"), self.city, "city")
        f.addRow(QLabel(i18n.t("<small>Город можно писать из списка крупных городов России или координатами «55.75,37.62».</small>")))
        f.addRow(self._hc(self.locc, "locc"))

        smart_b = QWidget()                           # Память и перерывы
        f = QFormLayout(smart_b)
        self.mem = WrapCheck(i18n.t("Запоминать мои команды и программы и учиться на привычках"))
        self.mem.setChecked(cfg.get("memory_on", True))
        f.addRow(self._hc(self.mem, "mem"))
        f.addRow(QLabel(i18n.t("<small>Журнал зашифрован и хранится только на этом ПК. Срок хранения задаётся выше.</small>")))
        self.pbr = WrapCheck(i18n.t("Напоминать о перерыве, если работаешь без остановки"))
        self.pbr.setChecked(cfg.get("proactive_breaks", True))
        self.pbr_min = NoWheelSpinBox()
        self.pbr_min.setRange(15, 240)
        self.pbr_min.setSuffix(i18n.t(" мин"))
        self.pbr_min.setValue(cfg.get("proactive_break_min", 60))
        f.addRow(self._hc(self.pbr, "pbr"))
        self._row(f, i18n.t("Перерыв через"), self.pbr_min, "proactive_break_min")
        # --- Свои фразы ---
        helpbox = QWidget()                           # Помощь по буферу и ошибкам
        f = QFormLayout(helpbox)
        self.wi_clip = WrapCheck(i18n.t("Помощник по буферу: предлагает объяснить текст ошибки"))
        self.wi_clip.setChecked(bool(cfg.get("wi_clip_help", True)))
        self.wi_clip.toggled.connect(lambda on: self.cfg.update(wi_clip_help=bool(on)))
        self.wi_err = WrapCheck(i18n.t("Реакция на ошибки: «программа не отвечает» и окна с ошибкой"))
        self.wi_err.setChecked(bool(cfg.get("wi_error_help", True)))
        self.wi_err.toggled.connect(lambda on: self.cfg.update(wi_error_help=bool(on)))
        self.wi_clip.setText(i18n.t("Помогать с ошибками: текст в буфере, зависшие программы и окна с ошибкой"))
        self.wi_clip.setChecked(self.wi_clip.isChecked() or self.wi_err.isChecked())   # два переключателя — один
        self.wi_clip.toggled.connect(self.wi_err.setChecked)
        self.wi_err.setParent(helpbox)
        self.wi_err.hide()
        f.addRow(self._block(self.wi_clip, "wi_clip_help"))

        ph = QWidget()
        v = QVBoxLayout(ph)
        v.addWidget(QLabel("<b>Свои фразы-команды</b>. Напиши фразу — Mico AI выполнит шаги по порядку. "
                           "Шаги разделяй «;»."))
        self._phrases = [dict(p) for p in cfg.get("custom_phrases", [])]
        self.pl = QListWidget()
        for p in self._phrases:
            self.pl.addItem(f"«{p['say']}» → {p['do']}")
        self.psay = QLineEdit()
        self.psay.setPlaceholderText(i18n.t("когда я пишу, например: работаю"))
        self.pdo = QLineEdit()
        self.pdo.setPlaceholderText(i18n.t("делай, например: включи не беспокоить; открой телеграм"))
        add_b = QPushButton(i18n.t("Добавить"))
        add_b.clicked.connect(self._phrase_add)
        del_b = QPushButton(i18n.t("Удалить выбранную"))
        del_b.clicked.connect(self._phrase_del)
        v.addWidget(self.pl)
        v.addWidget(self.psay)
        v.addWidget(self.pdo)
        self.pai = QLineEdit()                        # Mico составит фразу сам по описанию
        self.pai.setPlaceholderText(i18n.t("или опиши словами: когда я говорю работаю, включи не беспокоить"))
        self.pai.returnPressed.connect(self._phrase_ai)
        self.pai_b = QPushButton(i18n.t("Составить фразу"))
        self.pai_b.clicked.connect(self._phrase_ai)
        ai_row = QHBoxLayout()
        ai_row.addWidget(self.pai, 1)
        ai_row.addWidget(self.pai_b)
        v.addLayout(ai_row)
        row = QHBoxLayout()
        row.addWidget(add_b)
        row.addWidget(del_b)
        v.addLayout(row)

        # --- Кнопки чата ---
        btn = QWidget()
        f = QFormLayout(btn)
        self.cmode = NoWheelComboBox()
        self.cmode.addItem(i18n.t("Mico AI подбирает сам (по моим привычкам)"), "auto")
        self.cmode.addItem(i18n.t("Выбрать вручную (до 6)"), "manual")
        self.cmode.setCurrentIndex(max(0, self.cmode.findData(cfg.get("chips_mode", "auto"))))
        self.ccount = NoWheelSpinBox()
        self.ccount.setRange(0, chips.MAX_CHIPS)
        self.ccount.setSpecialValueText(i18n.t("не показывать"))
        self.ccount.setValue(cfg.get("chips_count", chips.MAX_CHIPS))
        self._row(f, i18n.t("Режим"), self.cmode, "chips_mode")
        self._row(f, i18n.t("Сколько кнопок (авто)"), self.ccount, "chips_count")
        self.chide = WrapCheck(i18n.t("Скрывать кнопки, когда отправил запрос (вернутся, когда нажмёшь в поле ввода)"))
        self.chide.setChecked(cfg.get("chips_hide_on_send", True))
        f.addRow(self._block(self.chide, "chips_hide_on_send"))
        self.cfilter = QLineEdit()
        self.cfilter.setPlaceholderText(i18n.t("поиск: например «громче» или «блютуз»"))
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
        f.addRow(self._with_hint(self.clist, "Отметь кнопки, которые показывать под ответом. Работает в режиме «Выбрать вручную»."))
        self.cnt = QLabel()
        f.addRow(self.cnt)
        self._update_cnt()
        self.habit_on = WrapCheck(i18n.t("Предлагать действия по привычкам (частые программы и команды)"))
        self.habit_on.setChecked(cfg.get("habit_suggest", True))
        f.addRow(self._block(self.habit_on, "habit_suggest"))
        reset = QPushButton(i18n.t("Сбросить привычки"))
        reset.clicked.connect(self._reset_usage)
        f.addRow(reset)
        f.addRow(QLabel("<small>Mico AI учится по тому, какие кнопки и команды ты используешь. "
                        "Вручную выбранный набор работает, пока не переключишь режим на «подбирает сам».</small>"))

        def page(*sections, side=None, title=None):
            """Раздел: заголовок и карточки одна под другой. Элемент: (виджет, название[, описание, иконка]).
            side — колонка справа (предпросмотр). Значки карточек серые: цвет Mico — только у активного."""
            ink_c = settings_look.ink(cfg["color"], theme.is_dark(cfg))   # значки карточек — в цвет Mico
            return settings_look.CardPage([(sec[0], sec[1], sec[2] if len(sec) > 2 else "", sec[3] if len(sec) > 3 else None)
                                           for sec in sections], ink_c, side=side, title=title)

        self._voice = voice_settings.VoicePage(cfg)                 # голос: озвучка, микрофон, «мико»
        from llm import cloud as cloud_api
        api_box = QWidget()
        api_form = QFormLayout(api_box)
        self.api_help_text = QLabel()
        self.api_help_text.setWordWrap(True)
        api_form.addRow(self.api_help_text)
        self.api_status = QLabel()
        self.api_status.setWordWrap(True)
        api_form.addRow(self.api_status)
        from ui.modelpicker import ModelCards
        self.api_model = ModelCards(accent=settings_look.ink(cfg["color"], theme.is_dark(cfg)), dark=theme.is_dark(cfg))
        for group_title, group_items in cloud_api.MODE_GROUPS:        # сверху «Mico-3», ниже «Mico-2»
            for mode_id, mode_name in group_items:
                self.api_model.addItem(i18n.t(mode_name), mode_id, i18n.t(cloud_api.MODE_DESC[mode_id]), group=group_title)
        self.api_model.setCurrentIndex(max(0, self.api_model.findData(cloud_api.normalize_mode(cfg.get("cloud_model")))))
        self.api_models_btn = QPushButton(i18n.t("Загрузить список моделей"))
        self.api_models_btn.hide()                         # у облака Mico нет списка моделей: режим выбирается выше
        api_form.addRow(i18n.t("Модель"), self.api_model)
        self.api_key = QLineEdit()                         # Authorization key из кабинета GigaChat: хранится зашифрованным
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText(i18n.t("Свой ключ облака (необязательно)"))
        self.api_key_status = QLabel(cloud_api.key_status())
        self.api_key_status.setObjectName("hint")
        self.api_key_status.setWordWrap(True)
        key_row = QWidget()
        key_lay = QHBoxLayout(key_row)
        key_lay.setContentsMargins(0, 0, 0, 0)
        key_lay.addWidget(self.api_key, 1)
        self.api_key_check = QPushButton(i18n.t("Проверить"))
        self.api_key_check.clicked.connect(self._check_api_key)
        key_lay.addWidget(self.api_key_check)
        api_form.addRow(i18n.t("Ключ облака"), key_row)
        api_form.addRow(self.api_key_status)
        self.ru_key = QLineEdit()                          # ключ cloud.ru для Mico-4: хранится зашифрованным
        self.ru_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ru_key.setPlaceholderText(i18n.t("Ключ cloud.ru для Mico-4 (API-ключ Foundation Models)"))
        self.ru_key_status = QLabel(cloud_api.cloudru_status())
        self.ru_key_status.setObjectName("hint")
        self.ru_key_status.setWordWrap(True)
        ru_row = QWidget()
        ru_lay = QHBoxLayout(ru_row)
        ru_lay.setContentsMargins(0, 0, 0, 0)
        ru_lay.addWidget(self.ru_key, 1)
        self.ru_key_check = QPushButton(i18n.t("Проверить"))
        self.ru_key_check.clicked.connect(self._check_ru_key)
        ru_lay.addWidget(self.ru_key_check)
        api_form.addRow(i18n.t("Ключ cloud.ru"), ru_row)
        api_form.addRow(self.ru_key_status)
        self.api_quota = QLabel()                          # сколько осталось нейронов и на сколько запросов каждого уровня хватит: пересчитывается после каждого ответа
        self.api_quota.setObjectName("hint")
        self.api_quota.setWordWrap(True)
        api_form.addRow(self.api_quota)
        api_hint = QLabel(i18n.t("Ключ хранится только на этом ПК. Текст чата уходит в GigaChat, снимки экрана не отправляются. Без ключа ответов на вопросы не будет."))
        api_hint.setWordWrap(True)
        api_form.addRow(api_hint)
        self._quota_stamp = -1.0
        self._quota_timer = QTimer(self)                   # остаток обновляется сам: после каждого ответа облака числа в окне пересчитываются
        self._quota_timer.setInterval(1500)
        self._quota_timer.timeout.connect(self._refresh_cloud_quota)
        self._quota_timer.start()
        cloud_api.ensure_quota_async()
        self._refresh_cloud_quota(force=True)
        self._refresh_api_provider()
        # Семь разделов по задачам (было 8 вкладок по технике). Ключи cfg не менялись — старые настройки не сбрасываются.
        # 1. Общение: как Mico говорит с тобой и что предлагает сам
        self._profile_tab = tabs.addTab(page((profile, i18n.t("Мой профиль"), i18n.t("Имя, контекст и манера ответов Mico AI"), "s_profile"),
                         (btn, i18n.t("Быстрые действия"), i18n.t("Кнопки под чатом и подсказки по привычкам"), "s_quick"),
                         (smart_a, i18n.t("Погода и приветствие"), i18n.t("Что рассказывать при включении ПК"), "s_sun"),
                         (helpbox, i18n.t("Помощь по буферу и ошибкам"), i18n.t("Когда Mico AI предлагает помощь сам"), "s_help"),
                         title=i18n.t("Общение")),
                    i18n.t("Общение"), "s_chat")
        # 2. Внешний вид — с живым предпросмотром справа
        tabs.addTab(page((look, i18n.t("Цвет и тема"), i18n.t("Цвет Mico AI, тема и вид чата"), "s_palette"),
                         (look_size, i18n.t("Размер и прозрачность"), i18n.t("Размер Mico AI, чата и прозрачность"), "s_size"),
                         (look_outline, i18n.t("Обводки и подсветка"), i18n.t("Линии вокруг окон и кнопок"), "s_outline"),
                         (self._wi_colors_box(cfg), i18n.t("Полоска Mico AI"), i18n.t("Полоска по краю экрана"), "s_bar"),
                         side=settings_look.PreviewCard(cfg), title=i18n.t("Внешний вид")),
                    i18n.t("Внешний вид"), "s_look")
        # 3. Mico на экране: где стоит, когда спит, как запускается, тишина
        tabs.addTab(page((pos, i18n.t("Положение и сон"), i18n.t("Где стоит Mico AI и когда он засыпает"), "s_sleep"),
                         (start, i18n.t("Запуск и поведение"), i18n.t("Автозапуск, приветствие, горячая клавиша"), "s_power"),
                         (self._wi_rhythm_box(cfg), i18n.t("Тишина и загрузка"), i18n.t("Тихий час и линия нагрузки"), "s_quiet"),
                         (menu, i18n.t("Меню по правому щелчку"), i18n.t("Какие пункты показывать"), "s_menu"),
                         (self._anim_box(cfg), i18n.t("Танцы и корзина"), i18n.t("Танец под музыку и поедание файлов из корзины"), "s_dance"),
                         title=i18n.t("Mico на экране")),
                    i18n.t("Mico на экране"), "s_screen")
        # 4. Голос
        tabs.addTab(self._voice.pages(), i18n.t("Голос"), "s_voice")
        # 5. Действия на ПК: свои фразы и агент
        self._phrase_tab = tabs.addTab(page((ph, i18n.t("Свои фразы"), i18n.t("Команды из нескольких шагов"), "s_phrase"),
                         (self._agent_box(cfg), i18n.t("Агент"), i18n.t("Программы, мессенджеры, видео и сайты"), "s_agent"),
                         title=i18n.t("Действия на ПК")),
                    i18n.t("Действия на ПК"), "s_action")
        # Зима: снег, сугробы, ёлки, снеговики и колпак на Mico (включается на ходу, видно сразу)
        winter_box = QWidget()
        wf = QFormLayout(winter_box)
        self.winter_ui_on = WrapCheck(i18n.t("Зимнее оформление: снег, сугробы, ёлки и снеговики"))
        self.winter_ui_on.setChecked(bool(cfg.get("winter_ui", False)))
        self.winter_ui_on.toggled.connect(self._winter_ui_toggle)
        wf.addRow(self._with_hint(self.winter_ui_on, i18n.t("В настройках и в чате плавно падает снег, внизу сугробы, ёлки с огоньками и снеговик, а значки разделов становятся снежными.")))
        self.winter_mico_on = WrapCheck(i18n.t("Зимний Mico: красный колпак с белым помпоном"))
        self.winter_mico_on.setChecked(bool(cfg.get("winter_mico", False)))
        self.winter_mico_on.toggled.connect(self._winter_mico_toggle)
        wf.addRow(self._with_hint(self.winter_mico_on, i18n.t("Колпак сидит на Mico, едет и качается вместе с ним, а помпон живой: болтается, когда Mico прыгает или поворачивает голову.")))
        winter_hint = QLabel(i18n.t("Скоро Новый год. Всё включается и выключается сразу, настройки перезапускать не нужно."))
        winter_hint.setObjectName("hint")
        winter_hint.setWordWrap(True)
        wf.addRow(winter_hint)
        tabs.addTab(page((winter_box, i18n.t("Зимнее настроение"), i18n.t("Снег, колпак и праздничный вид"), "s_snow"),
                         side=winter_ui.PreviewCard(), title=i18n.t("Зима")),
                    i18n.t("Зима"), "s_snow")
        # 6. Модели и ключи
        tabs.addTab(page((api_box, i18n.t("Источник ответов"), i18n.t("GigaChat (Сбер) — ответы в чате"), "s_model"),
                         title=i18n.t("Модели и ключи")),
                    i18n.t("Модели и ключи"), "s_ai")
        # 6b. Телефон: Telegram-бот (токен, код подключения, отвязка)
        from ui import tgsettings
        tg_box = tgsettings.TgBox(self.panel.brain, cfg, self._row_accent())
        tabs.addTab(page((tg_box, i18n.t("Управление с телефона"), "Telegram-бот @MicoChatBot", "s_phone"),
                         title=i18n.t("Управление с телефона")),
                    "Telegram", "s_telegram")
        # 7. Данные: память, история, что Mico знает
        tabs.addTab(page((smart_b, i18n.t("Память и перерывы"), i18n.t("Что помнить и когда напоминать"), "s_memory"),
                         (hist, i18n.t("История и поиск"), i18n.t("Сколько хранить и где искать"), "s_history"),
                         (memview.MemoryView(), i18n.t("Что Mico AI знает"), i18n.t("Заметки, команды, история и окна — можно удалить"), "s_bulb"),
                         title=i18n.t("Данные")),
                    i18n.t("Данные"), "s_data")

        if self._start_tab == "profile":
            tabs.setCurrentIndex(self._profile_tab)

        for lab in self.findChildren(QLabel):          # пояснения «<small>…» — тот же серый стиль подсказок
            t = lab.text()
            if t.startswith("<small>") and t.endswith("</small>") and not lab.objectName():
                lab.setText(t[len("<small>"):-len("</small>")])
                lab.setObjectName("hint")
                lab.setWordWrap(True)
        for form in self.findChildren(QFormLayout):
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setVerticalSpacing(6)
            form.setHorizontalSpacing(12)
        self._fit_widgets()
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        save_b = bb.button(QDialogButtonBox.StandardButton.Save)
        save_b.setText(i18n.t("Готово"))                  # сохранить и закрыть
        save_b.setObjectName("primary")
        cancel_b = bb.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_b.setText(i18n.t("Отменить изменения"))
        cancel_b.setObjectName("flat")
        reset_b = bb.addButton(i18n.t("Сбросить настройки"), QDialogButtonBox.ButtonRole.ActionRole)
        reset_b.setObjectName("flat")
        for b_ in bb.buttons():                       # кнопки крупнее: удобно нажимать, и внизу нет пустоты
            b_.setMinimumSize(96 if b_ is save_b else 0, 32)   # аккуратные кнопки одной высоты
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
        self._winter_orig = (bool(cfg.get("winter_ui")), bool(cfg.get("winter_mico")))
        self._tabs.set_winter(self._winter_orig[0], scene=False)   # зимой в меню только снежные значки
        # зима в настройках: только гирлянда и лёгкий снег (без сугробов, сосулек, подарков и ёлок)
        self._winter_snow = winter_ui.install(self, self.cfg, festive=True, gifts_x=None, scene=False,
                                              icicles=False, light=True)

    # ---------- облачные API: Groq (ключ встроен, пользователь выбирает только модель) ----------
    def _refresh_cloud_quota(self, force=False):
        """Остаток учитывает сам GigaChat: здесь только состояние ключа."""
        from llm import cloud as cloud_api
        self.api_key_status.setText(cloud_api.key_status())

    def _check_ru_key(self):
        """Кнопка «Проверить» у ключа cloud.ru: настоящий короткий запрос к Mico-4."""
        from llm import cloud as cloud_api
        key = self.ru_key.text().strip() or cloud_api.get_cloudru_key()
        if not key:
            QMessageBox.information(self, i18n.t("Ключ cloud.ru"), i18n.t("Сначала вставь ключ cloud.ru."))
            return
        self.ru_key_check.setEnabled(False)
        self.ru_key_check.setText(i18n.t("Проверяю…"))
        QApplication.processEvents()
        ok, text = cloud_api.check_cloudru_key(key)
        self.ru_key_check.setEnabled(True)
        self.ru_key_check.setText(i18n.t("Проверить"))
        QMessageBox.information(self, i18n.t("Ключ cloud.ru"), text)

    def _check_api_key(self):
        """Кнопка «Проверить»: настоящий запрос к GigaChat с ключом из поля (или сохранённым)."""
        from llm import cloud as cloud_api
        key = self.api_key.text().strip() or cloud_api.get_key(cloud_api.PROVIDER)
        if not key:
            QMessageBox.information(self, i18n.t("Ключ облака"), i18n.t("Сначала вставь ключ облака."))
            return
        self.api_key_check.setEnabled(False)
        self.api_key_check.setText(i18n.t("Проверяю…"))
        QApplication.processEvents()
        ok, text = cloud_api.check_key(key, model=self.api_model.currentData() or cloud_api.DEFAULT_MODE)
        self.api_key_check.setEnabled(True)
        self.api_key_check.setText(i18n.t("Проверить"))
        QMessageBox.information(self, i18n.t("Ключ облака"), i18n.t(text) if ok else text)

    def _refresh_api_provider(self, load=False):
        """Ответы идут через GigaChat: карточки моделей и поле ключа всегда на виду."""
        for w in (self.api_help_text, self.api_model, self.api_key, self.api_key_status, self.api_key_check,
                  self.ru_key, self.ru_key_status, self.ru_key_check):
            w.setVisible(True)
        self.api_help_text.setText(i18n.t("Ответы идут через GigaChat (Сбер). Нужен ключ из кабинета GigaChat."))
        self.api_status.hide()

    def _winter_ui_toggle(self, on):
        """Зимнее оформление: сразу и в настройках, и в чате. Пока окно не закрыто «Сохранить», можно отменить."""
        self.cfg["winter_ui"] = bool(on)
        self._tabs.set_winter(bool(on), scene=False)
        winter_ui.refresh_all()

    def _winter_mico_toggle(self, on):
        self.cfg["winter_mico"] = bool(on)                  # колпак виден на Mico сразу: он читает этот же словарь настроек

    def _wi_colors_box(self, cfg):
        """Цвета полоски Mico AI: у каждого действия свой. Занятый цвет выбрать нельзя."""
        box = QWidget()
        f = QFormLayout(box)
        self._wi_btns = {}
        cur = intel.state_colors(cfg)
        for key, name in intel.STATE_NAMES.items():
            b = QPushButton(cur[key])
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._pick_wi(k))
            self._wi_btns[key] = b
            self._paint_wi(key, cur[key])
            f.addRow(name, self._with_hint(b, self.STATE_HELP.get(key, "Цвет полоски для этого действия.")))
        reset = QPushButton(i18n.t("Вернуть цвета по умолчанию"))
        reset.clicked.connect(self._reset_wi_colors)
        f.addRow(self._with_hint(reset, "Вернёт цвета действий к стандартным."))
        self.wi_edge = NoWheelSlider(Qt.Orientation.Horizontal)           # толщина полосок по краям
        self.wi_edge.setRange(intel.EDGE_W_MIN, intel.EDGE_W_MAX)
        self.wi_edge.setValue(intel.edge_band(cfg))
        self.wi_edge_lbl = QLabel(f"{intel.edge_band(cfg)} px")
        self.wi_edge_lbl.setObjectName("readout")
        self.wi_edge.valueChanged.connect(self._wi_edge_changed)
        erow = QHBoxLayout()
        erow.addWidget(self.wi_edge, 1)
        erow.addWidget(self.wi_edge_lbl)
        ew = QWidget()
        ew.setLayout(erow)
        f.addRow(i18n.t("Толщина полосок по краям"), self._with_hint(ew, "Насколько толстой будет полоска у края экрана: тоньше — незаметнее, толще — заметнее."))
        self.wi_waves = WrapCheck(i18n.t("Свечение ярче, пока Mico AI отвечает"))
        self.wi_waves.setChecked(intel.waves_on(cfg))
        self.wi_waves.toggled.connect(self._wi_waves_changed)
        f.addRow(self._with_hint(self.wi_waves, "Полоска светится ярче, пока Mico AI отвечает на вопрос."))
        self.wi_wsrc = NoWheelComboBox()
        for key, name in intel.WAVE_SOURCES.items():
            self.wi_wsrc.addItem(name, key)
        self.wi_wsrc.setCurrentIndex(max(0, self.wi_wsrc.findData(cfg.get("wi_wave_source", "mico"))))
        self.wi_wsrc.currentIndexChanged.connect(self._wi_wave_src_changed)
        f.addRow(i18n.t("Цвет волн"), self._with_hint(self.wi_wsrc, "Откуда брать цвета волн: из самого Mico AI или из выбранного набора."))
        self.wi_wbtn = QPushButton()
        self.wi_wbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.wi_wbtn.clicked.connect(self._pick_wave)
        self._paint_wave_btn()
        f.addRow(i18n.t("Свой цвет волн"), self._with_hint(self.wi_wbtn, "Выбери свой цвет для волн. Он заменит готовый набор."))
        self.wi_theme = NoWheelComboBox()
        for key, (name, _cols, _states) in intel.WAVE_THEMES.items():
            self.wi_theme.addItem(name, key)
        self.wi_theme.setCurrentIndex(max(0, self.wi_theme.findData(cfg.get("wi_wave_theme", intel.WAVE_THEME_DEFAULT))))
        self.wi_theme.currentIndexChanged.connect(self._wi_theme_changed)
        f.addRow(i18n.t("Готовый набор волн"), self._with_hint(self.wi_theme, "Набор цветов для полоски: можно взять готовый вариант."))
        hint = QLabel("Полоска по краям экрана в режиме Mico AI. Цвета у действий не повторяются. "
                      "Волны могут быть цветом Mico AI из персонализации.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        return box

    def _exp_badge(self):
        badge = QLabel("BETA")
        badge.setStyleSheet("color:#c0392b; font-weight:600; font-size:11px;")
        return badge

    def _agent_box(self, cfg):
        """Вкладка «Агент»: Mico сам действует — программы, мессенджеры, видео и сайты.
        Агент выключен по умолчанию: включается только когда это нужно, зоны — по отдельности."""
        box = QWidget()
        f = QFormLayout(box)
        self.agent_on = WrapCheck(i18n.t("Режим агента (BETA)"))
        self.agent_on.setChecked(bool(cfg.get("agent_mode", False)))
        f.addRow(self._block(self.agent_on, "agent_mode", self._exp_badge()))
        self.agent_messengers = WrapCheck(i18n.t("Мессенджеры: MAX, WhatsApp, Teams, Discord, Telegram"))
        self.agent_messengers.setChecked(bool(cfg.get("agent_messengers", True)))
        f.addRow(self.agent_messengers)
        self.agent_video = WrapCheck(i18n.t("Видео и сайты: YouTube, Rutube, VK Видео, Яндекс Видео"))
        self.agent_video.setChecked(bool(cfg.get("agent_video", True)))
        f.addRow(self.agent_video)
        self.agent_confirm_send = WrapCheck(i18n.t("Спрашивать «да» перед отправкой, лайком, комментарием и подпиской"))
        self.agent_confirm_send.setChecked(bool(cfg.get("agent_confirm_send", True)))
        f.addRow(self.agent_confirm_send)
        self.agent_steps = NoWheelSpinBox()
        self.agent_steps.setRange(3, 24)
        self.agent_steps.setValue(int(cfg.get("agent_max_steps") or 12))
        f.addRow(i18n.t("Максимум шагов за задачу"), self.agent_steps)
        from core import telegram_bridge as tg
        self.tg_on = WrapCheck(i18n.t("Управление с телефона через Telegram"))
        self.tg_on.setChecked(bool(cfg.get("telegram_on", False)))
        f.addRow(self.tg_on)
        self.tg_token = QLineEdit()
        self.tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.tg_token.setPlaceholderText(i18n.t("Токен бота от @BotFather (пусто — не менять)"))
        f.addRow(i18n.t("Токен бота"), self.tg_token)
        self.tg_code_btn = QPushButton(i18n.t("Показать код подключения"))
        self.tg_code = QLabel("")
        self.tg_code.setWordWrap(True)
        self.tg_code.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        def show_code():
            code = tg.BRIDGE.pairing.new_code()
            self.tg_code.setText(i18n.t("Отправь боту в Telegram: /start ") + code + i18n.t(" (код действует 10 минут)"))
        self.tg_code_btn.clicked.connect(show_code)
        f.addRow(self.tg_code_btn, self.tg_code)
        self.tg_screen = WrapCheck(i18n.t("Разрешить команду /screen (снимок экрана в Telegram)"))
        self.tg_screen.setChecked(bool(cfg.get("telegram_screen", True)))
        f.addRow(self.tg_screen)
        self.tg_proxy = QLineEdit(str(cfg.get("telegram_proxy") or ""))
        self.tg_proxy.setPlaceholderText(i18n.t("Прокси, если Telegram недоступен: http://… или socks5://…"))
        f.addRow(i18n.t("Прокси"), self.tg_proxy)
        self.tg_state = QLabel(i18n.t("Состояние: ") + tg.BRIDGE.status_text())
        self.tg_state.setObjectName("hint")
        self.tg_state.setWordWrap(True)
        f.addRow(self.tg_state)
        tg_note = QLabel(i18n.t("<small>1) В Telegram откройте @BotFather, создайте бота и скопируйте токен сюда. "
                                "2) Включите галочку, сохраните, нажмите «Показать код» и отправьте боту /start КОД. "
                                "Бот отвечает только вам. Всё, что меняет компьютер, спрашивает «да» кнопками. "
                                "Кто получит доступ к вашему Telegram, сможет управлять ПК: включите защиту аккаунта.</small>"))
        tg_note.setWordWrap(True)
        f.addRow(tg_note)
        note = QLabel(i18n.t("<small>Агент сам открывает программы, пишет в мессенджерах («напиши мамуле привет»), "
                             "включает видео («открой на ютубе 1 видео в полном экране») и заполняет сайты. "
                             "Перед отправкой, лайком, комментарием, подпиской, оплатой и удалением спрашивает «да». "
                             "Пароли не вводит, окна банков и кошельков не трогает. Команды: «агент, …», «стоп агент». "
                             "Работает только на Windows.</small>"))
        note.setWordWrap(True)
        f.addRow(note)
        return box

    def _anim_box(self, cfg):
        """Танец под музыку и поедание файлов из корзины: работают только на Windows."""
        box = QWidget()
        f = QFormLayout(box)
        self.dance_on = WrapCheck(i18n.t("Танцевать под музыку"))
        self.dance_on.setChecked(bool(cfg.get("dance_music", True)))
        f.addRow(self._block(self.dance_on, "dance_music"))
        self.eat_on = WrapCheck(i18n.t("Есть файлы, когда корзину очистили"))
        self.eat_on.setChecked(bool(cfg.get("eat_trash", True)))
        f.addRow(self._block(self.eat_on, "eat_trash"))
        return box

    def _wi_rhythm_box(self, cfg):
        """Тишина по расписанию и загрузка ПК полоской: только в режиме Mico AI."""
        box = QWidget()
        f = QFormLayout(box)
        self.wi_qon = WrapCheck(i18n.t("Тихий час: в это время Mico AI не начинает разговор сам"))
        self.wi_qon.setChecked(bool(cfg.get("wi_quiet_on", False)))
        self.wi_qon.toggled.connect(lambda on: self.cfg.update(wi_quiet_on=bool(on)))
        f.addRow(self._with_hint(self.wi_qon, "Mico AI сам не начинает разговор в выбранные часы. Ответы на твои вопросы всё равно приходят."))
        self.wi_qfrom, self.wi_qto = QTimeEdit(), QTimeEdit()
        for edit, key, default, row in ((self.wi_qfrom, "wi_quiet_from", "23:00", i18n.t("С")),
                                        (self.wi_qto, "wi_quiet_to", "08:00", i18n.t("До"))):
            edit.setDisplayFormat("HH:mm")
            edit.setTime(QTime.fromString(str(cfg.get(key) or default), "HH:mm"))
            edit.timeChanged.connect(lambda t, k=key: self.cfg.update({k: t.toString("HH:mm")}))
            f.addRow(row, self._with_hint(edit, "Начало тихого часа." if row == i18n.t("С") else "Конец тихого часа."))
        hint = QLabel(i18n.t("Через полночь тоже работает: 23:00–08:00. Ответы на твои вопросы тихий час не блокирует."))
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        f.addRow(hint)
        self.wi_lbar = WrapCheck(i18n.t("Загрузка ПК тонкой линией внизу экрана"))
        self.wi_lbar.setChecked(bool(cfg.get("wi_load_bar", False)))
        self.wi_lbar.toggled.connect(lambda on: self.cfg.update(wi_load_bar=bool(on)))
        f.addRow(self._with_hint(self.wi_lbar, i18n.t("Линия растёт вместе с нагрузкой процессора. Цвет — как у волн.")))
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
        self.cfg["color"] = intel.theme_colors(self.cfg)[0]  # Mico берёт основной цвет выбранного набора
        self._apply_accent()
        for state_key, hex_color in states.items():
            self._paint_wi(state_key, hex_color)
        if self.cfg.get("wi_wave_source") != "theme":                 # выбрал набор — он и включается
            self.wi_wsrc.setCurrentIndex(self.wi_wsrc.findData("theme"))
        self._wi_preview()

    def _paint_wave_btn(self):
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg.get("wi_wave_custom"))
        self.wi_wbtn.setText(hex_color)
        self.wi_wbtn.setStyleSheet(theme.swatch_qss(hex_color))

    def _pick_wave(self):
        c = QColorDialog.getColor(QColor(*intel.hex_rgb(self.cfg.get("wi_wave_custom"))), self, i18n.t("Цвет волн"))
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
        b.setStyleSheet(theme.swatch_qss(hex_color))

    def _pick_wi(self, key):
        cur = intel.state_colors(self.cfg)
        c = QColorDialog.getColor(QColor(cur[key]), self, f"Цвет: {intel.STATE_NAMES[key]}")
        if not c.isValid():
            return
        hex_color = c.name().upper()
        clash = intel.color_clash(cur, key, hex_color)
        if clash:
            QMessageBox.information(self, i18n.t("Цвет занят"),
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

    def _style_dialog(self):
        """Оформление окна настроек по цвету Mico AI и теме (в режиме Mico AI — спокойнее, как в macOS)."""
        dark = theme.is_dark(self.cfg)
        accent = self.cfg["color"]                    # переключатели и полоска окна — цвет Mico AI (персиковый по умолчанию)
        Switch.ON = accent
        Switch.OFF = "#4a4a4a" if dark else "#d1d1d6"
        Switch.OFF_EDGE = "#a6a6a6" if dark else "#5d5d5d"   # выключенный — тонкий контур, как в Windows 11
        Switch.KNOB_ON = theme.on_accent(accent)      # кнопка контрастна любому цвету Mico
        RoundSlider.ACCENT = accent                   # ползунки — тот же цвет, что переключатели
        RoundSlider.TRACK = "#4a4a4a" if dark else "#d0d0d0"
        RoundSlider.RING = settings_look.PALETTE[bool(dark)]["card"]
        if hasattr(self, "_tabs"):
            self._tabs.set_accent(accent)
        self.setStyleSheet(settings_look.qss(dark, accent))
        self.update()                                 # свечение берёт новый цвет
        for sl in self.findChildren(RoundSlider):
            sl.update()
        for sw in self.findChildren(Switch):          # переключатели перекрашиваются сразу
            sw.update()

    def _paint_accent_btn(self):
        """Кнопка «Цвет Mico AI» показывает сам цвет."""
        hex_color = "#%02X%02X%02X" % intel.hex_rgb(self.cfg["color"])
        self.cbtn.setText(hex_color)
        self.cbtn.setStyleSheet(theme.swatch_qss(hex_color))

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
        c = QColorDialog.getColor(QColor(self.cfg["color"]), self, i18n.t("Цвет Mico AI"))
        if c.isValid():
            self.cfg["color"] = c.name()
            self._apply_accent()

    def live(self):
        self.cfg["scale"] = self.sc.value() / 100
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
            self.csc_lbl.setText(i18n.t("Размер Mico AI и чата"))
            self.csc.setToolTip(i18n.t("Меняет размер и Mico AI, и чата вместе"))
        else:
            self.csc.setRange(60, 200)
            self.csc.setValue(int(round(self.cfg.get("chat_scale", 1.0) * 100)))
            self.csc_lbl.setText(i18n.t("Размер чата"))
            self.csc.setToolTip(i18n.t("Отдельный размер чата, Mico AI не меняется"))
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
            QMessageBox.information(self, i18n.t("Фразы"), i18n.t("Заполни обе строки. Фраза — до 60 знаков, шаги — до 300."))
            return
        if len(self._phrases) >= custom.MAX_PHRASES:
            QMessageBox.information(self, i18n.t("Фразы"), f"Можно добавить не больше {custom.MAX_PHRASES} фраз.")
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
        Пустое поле возвращает всё как было. Разделы и вкладки без совпадений прячутся совсем (не серые и не пустые),
        скрытые строки не оставляют дыр в форме, а переключение вкладок во время набора идёт без анимации."""
        def norm(x):
            return " ".join(str(x).lower().replace("ё", "е").split())

        words = [w for w in norm(text).split(" ") if w]
        if words and not self._expanders_orig:
            self._expanders_orig = {ex: ex._body.isVisible() for ex in self.findChildren(Expander)}
        if words:
            for ex in self.findChildren(Expander):
                ex.setExpanded(True)                  # совпадения внутри свёрнутых блоков должны быть видны
        elif self._expanders_orig:
            for ex, was_open in self._expanders_orig.items():
                try:
                    ex.setExpanded(was_open)          # поиск очищен: блоки сворачиваются, как были
                except RuntimeError:
                    pass
            self._expanders_orig = {}
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

        def ancestor_of(w, cls):
            p = w.parentWidget()
            while p is not None and not isinstance(p, cls):
                p = p.parentWidget()
            return p

        hit_tabs, hit_groups, hit_panels, any_hit = set(), set(), set(), False
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
                show = matched and any(self._vis[w] for w in widgets)
                for w in widgets:
                    w.setVisible(matched and self._vis[w])
                try:
                    form.setRowVisible(r, show)          # строка пропадает вместе с отступами, без пустых «дыр»
                except (AttributeError, TypeError):
                    pass
                if words and matched:
                    any_hit = True
                    t = tab_of(widgets[0])
                    if t is not None:
                        hit_tabs.add(t)
                    g = ancestor_of(widgets[0], QGroupBox)
                    if g is not None:
                        hit_groups.add(g)
                    pn = ancestor_of(widgets[0], settings_look.SectionPanel)
                    if pn is not None:
                        hit_panels.add(pn)

        for g in self.findChildren(QGroupBox):
            self._vis.setdefault(g, not g.isHidden())
            g.setVisible(self._vis[g] and (not words or g in hit_groups))
        for i in range(tabs.count()):                  # вкладки без совпадений прячем, а не оставляем серыми
            tabs.setTabEnabled(i, not words or i in hit_tabs)
            pg = tabs.widget(i)
            if hasattr(pg, "filter_panels"):
                pg.filter_panels(hit_panels if words else None)
        if words and hit_tabs and tabs.currentIndex() not in hit_tabs:
            tabs.setCurrentIndex(min(hit_tabs), animate=False)
        self.found_hint.setVisible(bool(words) and not any_hit)
        lay = self.layout()
        if lay is not None:
            lay.activate()

    def _greet_ids(self):
        out = []
        for i in range(self.gl.count()):
            it = self.gl.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    NAME2KEY = {"outline": "chat_outline", "linked": "chat_linked", "greet": "greet_on_start", "silent": "silent_until_asked",
                "auto": "autostart", "quiet": "quiet_mode", "locc": "loc_consent", "mem": "memory_on",
                "pbr": "proactive_breaks"}

    def _row_accent(self):
        return settings_look.ink(self.cfg["color"], theme.is_dark(self.cfg))

    def _block(self, widget, key=None, badge=None):
        """Одна настройка: сам элемент, «Сброс» (виден при наведении), «Спросить Mico» и стрелка. Стрелка плавно
        раскрывает пояснение; «Спросить Mico» — под строкой появляется Mico и объясняет настройку."""
        w = settings_look.SettingRow(self._row_accent())
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
            if hasattr(widget, "text") and widget.text():
                self._reg_text.setdefault(key, widget.text())
            rb = QPushButton(i18n.t("Сброс"))
            rb.setObjectName("resetRow")
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setToolTip(i18n.t("Вернуть эту настройку к значению по умолчанию"))
            rb.clicked.connect(lambda _=False, k=key: self._reset_key(k))
            sp = rb.sizePolicy()
            sp.setRetainSizeWhenHidden(True)              # строка не прыгает, когда кнопка появляется
            rb.setSizePolicy(sp)
            rb.setVisible(False)
            w.hover_btn = rb
            line.addWidget(rb)
        raw_hint = settings_info.CFG_HINTS.get(key) if key else None
        hint = i18n.t(raw_hint) if raw_hint else None
        if hint:
            hl = QLabel(hint)
            hl.setObjectName("settingDesc")
            hl.setWordWrap(True)
            w.add_detail(hl)                              # пояснение — в раскрывающемся блоке под строкой
            w.set_explain(lambda k=key, h=raw_hint: settings_info.ask_mico(k, h))
            line.addWidget(w.ask)                         # «Спросить Mico»: под настройкой плавно появляется Mico и рассказывает о ней
            line.addWidget(w.chev)
        v.addLayout(line)
        v.addWidget(w.details)
        return w

    STATE_HELP = {
        "listen": "Цвет полоски, пока Mico AI ждёт твоей команды.",
        "think": "Цвет полоски, пока Mico AI готовит ответ.",
        "break": "Цвет полоски, когда Mico AI напоминает отдохнуть.",
        "watch": "Цвет полоски, когда Mico AI наблюдает за работой на экране.",
        "tip": "Цвет полоски, когда Mico AI предлагает полезный совет.",
        "warn": "Цвет полоски, когда Mico AI предупреждает о проблеме или опасной команде.",
    }

    def _with_hint(self, widget, text):
        """Элемент без своей настройки (кнопка, список, цвет): та же стрелка с пояснением."""
        w = settings_look.SettingRow(self._row_accent())
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(widget, 1)
        hl = QLabel(text)
        hl.setObjectName("settingDesc")
        hl.setWordWrap(True)
        w.add_detail(hl)
        w.set_explain(lambda h=text: settings_info.ask_mico(None, h))
        line.addWidget(w.ask)
        line.addWidget(w.chev)
        v.addLayout(line)
        v.addWidget(w.details)
        return w

    def _row(self, f, label, widget, key):
        block = self._block(widget, key)
        if key and isinstance(label, str):
            self._reg_text[key] = label                 # подпись строки — 
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
            badge.setStyleSheet("color:#c0392b; font-weight:600; font-size:11px;")
            if not features.enabled(feat, self.cfg):
                box.setEnabled(False)
                box.setToolTip(i18n.t("Доступно в программе предварительной оценки (⚙ Настройки → Бета)"))
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
        if isinstance(w, QSlider) and isinstance(default, float):     # ползунки в процентах: 1.0 → 100
            w.setValue(int(round(default * 100)))
            return
        _set_widget_value(w, default)

    # ---------- «Свои фразы» через ИИ ----------
    def _model_ask(self):
        """Функция «промпт → ответ модели» для фоновых запросов. Помощник настроек — GigaChat Lite, если ключ задан;
        иначе поиск работает по словам и своему понимающему слою."""
        from llm import cloud as cloud_api
        key = cloud_api.get_key(cloud_api.PROVIDER)
        if key:
            return lambda p: cloud_api.generate(cloud_api.PROVIDER, key, [
                {"role": "system", "content": "Ты помогаешь найти настройку в программе Mico. Отвечай только JSON."},
                {"role": "user", "content": p}], model="lite3", temperature=0.2)
        brain = getattr(self.panel, "brain", None)
        if brain is None:
            return None
        return lambda p: brain._chat(p, use_history=False)

    def _run_async(self, fn, on_done):
        """Тяжёлый вызов (модель) — в фоне. Результат или ошибка уходит в on_done в основном потоке."""
        bus = self._ai_bus

        def work():
            try:
                res = fn()
            except Exception as e:
                res = e
            bus.done.emit(res, on_done)
        threading.Thread(target=work, daemon=True).start()

    def _phrase_ai(self):
        """«Свои фразы»: описываешь словами — Mico составляет фразу и шаги, показывает и спрашивает «добавить?»."""
        q = self.pai.text().strip()
        if not q:
            return
        self.pai_b.setEnabled(False)
        self.pai_b.setText(i18n.t("Думаю…"))
        ask, phrases = self._model_ask(), list(self._phrases)
        self._run_async(lambda: custom.draft(q, ask, phrases), self._phrase_ai_done)

    def _phrase_ai_done(self, res):
        self.pai_b.setEnabled(True)
        self.pai_b.setText(i18n.t("Составить фразу"))
        if isinstance(res, ValueError):                      # понятная причина от custom.draft
            QMessageBox.information(self, i18n.t("Фразы"), str(res))
            return
        if isinstance(res, Exception):
            QMessageBox.information(self, i18n.t("Фразы"), i18n.t("Не получилось составить фразу. Опиши проще или запиши её ниже."))
            return
        d = res
        warn = ""
        if d["danger"]:
            warn = ("\n\nВнимание: в фразе опасное действие («" + "», «".join(d["danger"]) +
                    "»). Mico будет спрашивать «да» перед ним.")
        ans = QMessageBox.question(self, i18n.t("Фразы"),
                                   f"Составил фразу:\n«{d['say']}» → {d['do']}{warn}\n\nДобавить?")
        if ans == QMessageBox.StandardButton.Yes:
            self._phrases = self._phrases + [{"say": d["say"], "do": d["do"]}]
            self.pl.addItem(f"«{d['say']}» → {d['do']}")
            self.pai.clear()
        else:                                                # не добавили — кладём в поля, можно поправить руками
            self.psay.setText(d["say"])
            self.pdo.setText(d["do"])

    def _greet_count(self):
        self.gcnt.setText(f"Выбрано: {len(self._greet_ids())} из {greeting.MAX_ITEMS}")

    def _greet_changed(self, item):
        if item.checkState() == Qt.CheckState.Checked and len(self._greet_ids()) > greeting.MAX_ITEMS:
            self.gl.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.gl.blockSignals(False)
            QMessageBox.information(self, i18n.t("Приветствие"), f"Можно выбрать не больше {greeting.MAX_ITEMS} пунктов.")
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
            QMessageBox.information(self, i18n.t("Кнопки"), f"Можно выбрать не больше {chips.MAX_CHIPS} кнопок.")
        self._update_cnt()

    def _filter_chips(self, text):
        t = text.strip().lower()
        for i in range(self.clist.count()):
            it = self.clist.item(i)
            it.setHidden(bool(t) and t not in it.text().lower())

    def _reset_usage(self):
        chips.reset(self.cfg)
        save_cfg(self.cfg)
        QMessageBox.information(self, i18n.t("Кнопки"), i18n.t("Привычки сброшены. Mico AI начнёт учиться заново."))

    def _save_chips(self):
        self.cfg.update(chips_mode=self.cmode.currentData(), chips_count=self.ccount.value(),
                        chips_hide_on_send=self.chide.isChecked(),
                        anim_sleep_fps=self.sleep_fps.currentData() or 20,
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
        QMessageBox.information(self, "Mico AI", i18n.t("Настройки сброшены. Перезапусти Mico AI, чтобы всё применилось."))
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

    def paintEvent(self, e):
        """Свечение рамки: рисуем здесь, а не эффектом тени. В развёрнутом окне рамка во весь экран — свечения нет."""
        if self.isMaximized():
            return
        if QRectF(self.rect()).adjusted(16, 16, -16, -16).contains(QRectF(e.rect())):
            return                                         # перерисовка не задевает край окна: тень не нужна (раньше рисовалась на каждый кадр снега)
        p = QPainter(self)
        settings_look.paint_glow(p, QRectF(self.rect()).adjusted(16, 16, -16, -16), QColor(0, 0, 0), radius=12, steps=10)   # мягкая тень вместо цветного свечения
        p.end()

    def changeEvent(self, e):
        """Развёрнутое окно — без прозрачного поля под тень: иначе по краям просвечивал рабочий стол."""
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.WindowStateChange and getattr(self, "_outer", None) is not None:
            m = 0 if self.isMaximized() else 16
            self._outer.setContentsMargins(m, m, m, m)
        super().changeEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        if getattr(self, "_outer", None) is not None and self.isMaximized():
            self._outer.setContentsMargins(0, 0, 0, 0)
        if not getattr(self, "_faded", False):
            self._faded = True
            from ui import motion
            motion.window_fade_in(self, 220)               # настройки мягко проявляются

    def _toggle_max(self):
        """Кнопка «во весь экран» в шапке: переключает обычный и развёрнутый вид."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, e):
        """Окно без системной шапки: тянем его за верхнюю полосу (кнопки и поиск работают как обычно)."""
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 72 and not self.isMaximized():
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag = None
        super().mouseReleaseEvent(e)

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
            QMessageBox.warning(self, i18n.t("Настройки"), f"Не получилось сохранить настройки: {e}\n\n"
                                "Подробности записаны в crash.log в папке Mico AI (%APPDATA%\\Mico).")
            return
        if done:
            super().accept()

    def _apply(self):
        self._save_chips()
        self.cfg["habit_suggest"] = self.habit_on.isChecked()   # быстрые действия по привычкам
        self.panel._apps_cache = None                          # при следующем открытии чата — свежий набор
        self._voice.apply(self.cfg)                       # вкладка «Голос»
        from llm import cloud as cloud_api                 # выбранная модель GigaChat и ключ
        self.cfg.update(cloud_model=cloud_api.normalize_mode(self.api_model.currentData()))
        key_text = self.api_key.text().strip()
        if key_text:
            try:
                cloud_api.set_key(cloud_api.PROVIDER, key_text)
                self.api_key.clear()
            except Exception as e:
                QMessageBox.warning(self, i18n.t("Ключ облака"), str(e))
        ru_text = self.ru_key.text().strip()
        if ru_text:
            try:
                cloud_api.set_key("cloudru", ru_text)
                self.ru_key.clear()
            except Exception as e:
                QMessageBox.warning(self, i18n.t("Ключ cloud.ru"), str(e))
        self.cfg["llm_backend"] = "mico"
        self.cfg["llm_temperature"] = 0.7                  # «характер ответов» из настроек убран: стиль выбирается в чате
        self.cfg.update(menu_items=self._menu_ids(), menu_max=self.mmax.value())
        self.cfg.update(quiet_mode=self.quiet.isChecked())
        self.cfg.update(sleep_after_min=self.sleep_min.value())
        self.cfg.update(proactive_breaks=self.pbr.isChecked(),
                        proactive_break_min=self.pbr_min.value())
        self.cfg.update(winter_ui=self.winter_ui_on.isChecked(), winter_mico=self.winter_mico_on.isChecked())
        self._winter_orig = (self.cfg["winter_ui"], self.cfg["winter_mico"])
        self.cfg.update(agent_mode=self.agent_on.isChecked(), dance_music=self.dance_on.isChecked(),
                        eat_trash=self.eat_on.isChecked())
        from core import telegram_bridge as tg
        if self.tg_token.text().strip():
            tg.save_token(self.tg_token.text())      # неверный токен — понятная ошибка и ничего не сохраняется
            self.tg_token.clear()
        self.cfg.update(telegram_on=self.tg_on.isChecked(), telegram_screen=self.tg_screen.isChecked(),
                        telegram_proxy=self.tg_proxy.text().strip())
        tg.BRIDGE.cfg = self.cfg
        tg.BRIDGE.reconfigure()                      # включить, выключить или перезапустить мост с новыми настройками
        self.cfg.update(agent_messengers=self.agent_messengers.isChecked(),
                        agent_video=self.agent_video.isChecked(),
                        agent_confirm_send=self.agent_confirm_send.isChecked(),
                        agent_max_steps=self.agent_steps.value())
        self.cfg.update(custom_phrases=list(self._phrases))
        self.cfg.update(greet_on_start=self.greet.isChecked(), silent_until_asked=self.silent.isChecked(),
                        retention_days=self.keep.currentData())
        self.cfg.update(language=self.lang.currentData() or "en")
        tone, address = self.profile_style.currentData() or ("friendly", "name")
        length, answer_format, clarify = self.profile_answers.currentData() or ("balanced", "natural", "when_needed")
        self.cfg.update(user_name=self.profile_name.text().strip()[:80],
                        user_phone=self.profile_phone.text().strip()[:40],
                        user_email=self.profile_email.text().strip()[:80],
                        user_tone=tone, user_address=address,
                        user_reply_language=self.profile_language.currentData() or "auto",
                        user_answer_length=length, user_answer_format=answer_format,
                        user_clarify=clarify,
                        user_about=self.profile_about.toPlainText().strip()[:2000])
        self.cfg.update(chat_outline=self.outline.isChecked(), chat_linked=self.linked.isChecked(),
                        panel_side=True,
                        chat_scale=self.cfg.get("chat_scale", 1.0), chat_ratio=self.cfg.get("chat_ratio", 1.0),
                        weather_on="weather" in self._greet_ids() and self.wstart.isChecked(),
                        weather_on_start=self.wstart.isChecked(), greet_items=self._greet_ids(),
                        city=self.city.text().strip(), memory_on=self.mem.isChecked(),
                        loc_consent=True if self.locc.isChecked() else (False if self.cfg.get("loc_consent") is not None else None))
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
            QMessageBox.warning(self, i18n.t("Настройки"), f"Не удалось записать настройки: {e}")
            return False
        if not ok:
            QMessageBox.warning(self, i18n.t("Автозапуск"), msg)
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
    update_required = pyqtSignal(object)   # на сайте вышла новая версия: чат закрывается просьбой обновить Mico
    update_found = pyqtSignal(object)   # найдена новая версия Mico AI (словарь с номером и адресом страницы)
    playing = pyqtSignal(bool)          # звук играет (или стих): Mico танцует — из фонового потока soundwatch
    emptied = pyqtSignal()              # корзину очистили: Mico ест файлы — из фонового потока soundwatch


def main():
    _trace("main() начат")
    if "--autostart" in sys.argv:                # при входе в Windows ждём рабочий стол (обычно пару секунд)
        _wait_shell()
    try:                                       # 1 мс точность таймеров Windows — плавные кадры
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
    app = QApplication(sys.argv)
    theme.load_fonts()                       # основной текст Segoe UI Variable, заголовки Nunito Bold
    app.setFont(theme.app_font())
    app.setStyleSheet(theme.FONT_QSS)        # и в стилях тоже: иначе виджеты берут системный шрифт
    from PyQt6.QtCore import QLibraryInfo, QLocale, QTranslator
    _qt_ru = QTranslator()                             # стандартные кнопки Qt (Да, Нет, ОК, Отмена) — по-русски
    if _qt_ru.load(QLocale("ru_RU"), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(_qt_ru)
    app._qt_ru = _qt_ru                                # не даём сборщику мусора удалить перевод
    from setup import installer as _ic
    _icon = _ic._asset("mico.ico")
    if _icon:
        app.setWindowIcon(QIcon(_icon))       # значок Mico AI во всех окнах программы
    from setup import installer
    if installer.is_uninstall_request():   # «Параметры → Приложения» или пункт меню запускают удаление
        # Язык ставим до окна: раньше он оставался английским по умолчанию, потому что настройки читались позже
        lang = None
        try:                                   # язык берём из файла настроек: в load_cfg() по умолчанию стоит английский
            with open(CFG_PATH, encoding="utf-8") as f:
                lang = json.load(f).get("language")
        except Exception:
            pass
        i18n.set_language(lang if lang in ("ru", "en") else installer._system_language())
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
    i18n.set_language(cfg.get("language", "en"))   # язык из настроек: английский по умолчанию
    try:                                              # значок Mico во всех окнах и на панели задач — настоящий, как у Mico на экране
        from ui import appicon
        appicon.set_color(cfg["color"])
        app.setWindowIcon(appicon.blob_icon(cfg["color"]))
        installer.refresh_icon(cfg["color"])          # и файл значка в «Приложениях» и ярлыках
    except Exception:
        pass
    if version.BUILD_CHANNEL == "stable" and cfg.get("update_channel") != "stable":
        cfg["update_channel"] = "stable"                 # стабильная сборка всегда на стабильном канале
        save_cfg(cfg)
    _stage("настройки и хранилище готовы")
    wi_notice = intel.enforce_mode(cfg, intel_ui.total_ram_gb(), intel_ui.free_disk_gb())   # слабый ПК: предупреждаем
    try:                                                                                      # проверка при запуске: только то, что не в порядке
        problems = [l for l in intel.checkup_lines(cfg, intel_ui.total_ram_gb(), intel_ui.free_disk_gb())
                    if not l.startswith("✅")]
    except Exception:
        problems = []
    if problems:
        wi_notice = "\n".join(filter(None, [wi_notice] + problems))
    store.purge(cfg["retention_days"])
    commands.warmup()                           # заранее читаем список приложений из «Пуска»
    tracker = Tracker(store, cfg)
    tracker.start()
    brain = Brain(cfg, store, tracker)
    try:                                        # Telegram: управление ПК с телефона, если бот уже подключён
        from win import tgbot as _tgbot
        brain.tgbot = _tgbot.start(brain)
    except Exception:
        brain.tgbot = None                      # сбой Telegram не должен мешать запуску Mico
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
        QTimer.singleShot(4000, lambda: panel.say_when_allowed(wi_notice))
    _wi_chat = getattr(getattr(panel, "intel", None), "aichat", None)
    if _wi_chat is not None:
        _wi_chat.on_draft = lambda _t: save_cfg(cfg)      # черновик чата Mico AI сохраняется в настройках
    _stage("окно чата готово")
    watcher = WindowWatcher()
    _stage("наблюдатель окон готов")
    bus = Bus()                              # сигналы между фоновыми потоками и окном
    from voice import sound as soundwatch
    bus.playing.connect(blob.set_dancing)    # музыка играет — Mico танцует
    bus.emptied.connect(blob.eat_files)      # корзину очистили — Mico ест файлы
    sound = soundwatch.Watcher(lambda: (bool(cfg.get("dance_music", True)), bool(cfg.get("eat_trash", True))),
                               bus.playing.emit, bus.emptied.emit)
    sound.start()
    bus.info.connect(panel.say)              # погода и сообщения из фоновых потоков
    brain.notify = panel.reminder.emit
    brain.say = bus.info.emit                # сообщения агента — обычным текстом в чат (без ⏰ и звука)
    brain.save_cfg = lambda: save_cfg(cfg)

    from core import telegram_bridge as _tg      # Telegram: тот же мозг, что и в чате; владелец — только подключённый телефон

    def _tg_ask(text):
        brain.channel = "telegram"
        try:
            r = brain.ask(text)
        finally:
            brain.channel = "chat"
        return (r.text if r and r.text else "Готово.")

    def _tg_stop():
        run = getattr(brain, "_agent_run", None)
        if run is not None:
            run.stop()
    _tg.BRIDGE.configure(cfg, save_cfg=brain.save_cfg, handler=_tg_ask, screen=screen_capture, on_stop=_tg_stop, harness=brain.harness)
    reminders.bind(store)                    # напоминания — в зашифрованном хранилище
    memview.bind(store)                      # экран «Что Mico AI знает»

    def on_hotkey(hid):
        if intel_ctl is not None and getattr(intel_ctl, "update_locked", False):
            intel_ctl.show_aichat()                          # нужно обновление: любая горячая клавиша ведёт к просьбе обновить Mico
            return
        if hid == 1:                                         # F8: открывает обычный чат Mico AI
            if intel_ctl is not None and intel_ctl.on():
                intel_ctl.toggle_aichat()                    # режим Mico AI: чат Mico AI
            else:
                panel.toggle()                               # обычный режим: чат рядом с Mico AI
        elif hid == 2 and intel_ctl is not None:             # скриншот: Mico AI рассказывает, что на экране
            intel_ctl.screen_hotkey()
        elif hid == 3 and intel_ctl is not None:             # помочь с программой, которой пользуются сейчас
            intel_ctl.window_hotkey(active_title())
        elif hid == 4 and intel_ctl is not None:             # голос: начать или закончить запись
            intel_ctl.voice.toggle_listen()
        elif hid == 5:                                       # переписать выделенное короче
            rewrite_selection()
    bus.hotkey.connect(on_hotkey)

    def offer_update(info):
        """Новая версия найдена: открываем страницу загрузки; программа ничего не скачивает сама."""
        webbrowser.open("https://serdzh29.github.io/Mico-AI/")
        bus.info.emit(i18n.t("Найдена новая версия Mico AI: ") + info["version"] + ". Открыл страницу загрузки.")
    bus.update_found.connect(offer_update)

    def apply_update_gate(info):
        """На сайте версия новее: чат закрывается просьбой обновить Mico, ответы и голос не работают."""
        intel_ctl.update_locked = True
        brain.locked_reply = i18n.t("Нужно обновить Mico: без обновления я не буду работать. Скачай новую версию на сайте.")
        intel_ctl.aichat.set_update_gate(info)
        if panel.isVisible():
            panel.hide_smooth()
    bus.update_required.connect(apply_update_gate)

    def start_update_check():
        """При каждом запуске спрашиваем сайт, какая версия последняя. Фоновый запрос: интерфейс не ждёт, без сети
        или при ошибке сайта Mico работает как обычно."""
        def work():
            try:
                from setup import sitecheck
                info = sitecheck.check()
            except Exception:
                return
            if info:
                bus.update_required.emit(info)
        threading.Thread(target=work, daemon=True).start()
    def active_title():
        """Название программы, которой пользуешься (не Mico AI). Пусто — если узнать не получилось."""
        try:
            import win32gui
            hwnd = watcher.last_hwnd or tracker.last_hwnd
            return win32gui.GetWindowText(hwnd) if hwnd else ""
        except Exception:
            return ""
    # --- вызовы в главном потоке: окна и буфер обмена трогаем только там ---
    main_call = _MainCall()
    main_call.run.connect(lambda fn, box: box.append(fn()), Qt.ConnectionType.BlockingQueuedConnection)

    def on_main(fn):
        if threading.current_thread() is threading.main_thread():
            return fn()
        box = []
        main_call.run.emit(fn, box)
        return box[0] if box else None

    # --- скриншот без Mico: прячем окна на время снимка и возвращаем их ---
    def hide_mico():
        hidden = []
        for w in (blob, panel):
            try:
                if w is not None and w.isVisible():
                    w.hide()
                    hidden.append(w)
            except RuntimeError:
                pass
        return hidden

    def show_mico(hidden):
        for w in hidden or []:
            try:
                w.show()
            except RuntimeError:
                pass

    from win import capture_guard
    capture_guard.set_handlers(lambda: on_main(hide_mico) or [],
                               lambda hidden: on_main(lambda: show_mico(hidden)))

    # --- память экрана (выключена по умолчанию: включается настройкой screen_memory_on) ---
    from core import memory_hub
    from data import screenmem
    from win import ocr as winocr
    memory_hub.set_store(store)
    memory_hub.set_ask(lambda p: panel.brain._chat(p, use_history=False))
    mem_policy = screenmem.Policy(enabled=cfg.get("screen_memory_on", False),
                                  retention_days=cfg.get("screen_memory_days", screenmem.DEFAULT_RETENTION_DAYS),
                                  extra_apps=cfg.get("screen_memory_skip_apps", []),
                                  extra_words=cfg.get("screen_memory_skip_words", []))

    def active_app():
        """Программа и заголовок окна, которым пользуешься. Пусто — если не получилось."""
        try:
            import win32gui
            import win32process
            hwnd = watcher.last_hwnd or tracker.last_hwnd
            if not hwnd:
                return "", ""
            _tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower(), win32gui.GetWindowText(hwnd)
        except Exception:
            return "", ""

    def memory_tick_work():
        try:
            app, title = active_app()
            if not mem_policy.allowed(app, title):
                return
            shot = capture_guard.around(capture_guard.grab_all)
            text = winocr.ocr_png(winocr.shot_to_png(shot))
            rec = screenmem.make_record(time.time(), app, title, text)
            if rec:
                store.add_screen(rec)
            store.purge_screen(screenmem.expired_before(time.time(), mem_policy.retention_days))
        except Exception as e:
            from voice.log import record
            record("Память экрана: кадр пропущен", e)

    def memory_tick():
        if mem_policy.enabled:
            threading.Thread(target=memory_tick_work, daemon=True).start()

    mem_timer = QTimer(panel)
    mem_timer.timeout.connect(memory_tick)
    mem_timer.start(int(cfg.get("screen_memory_sec", screenmem.DEFAULT_INTERVAL_SEC)) * 1000)

    # --- переписывание выделенного (горячая клавиша): короче; буфер обмена — только по нажатию ---
    def rewrite_selection():
        def work():
            from core import rewrite
            from win import selection
            try:
                import pyautogui
                text = selection.grab(
                    send_copy=lambda: pyautogui.hotkey("ctrl", "c"),
                    read_clip=lambda: on_main(lambda: QGuiApplication.clipboard().text()),
                    write_clip=lambda t: on_main(lambda: QGuiApplication.clipboard().setText(t)))
                if not text:
                    bus.info.emit(i18n.t("Выдели текст и нажми горячую клавишу ещё раз."))
                    return
                out = rewrite.rewrite_text(text, "short", lambda p: panel.brain._chat(
                    p, use_history=False))
                on_main(lambda: QGuiApplication.clipboard().setText(out))
                bus.info.emit(i18n.t("Готово: текст стал короче и лежит в буфере обмена. Вставь его Ctrl+V."))
            except ValueError as e:
                bus.info.emit(str(e))
            except Exception as e:
                from voice.log import record
                bus.info.emit(record("Переписать выделенное не получилось", e))
        threading.Thread(target=work, daemon=True).start()

    hk = hotkeys.HotkeyThread({1: "f8", 2: cfg.get("hotkey_screen", "ctrl+alt+s"),
                               3: cfg.get("hotkey_window", "ctrl+alt+h"),
                               4: cfg.get("hotkey_voice", "ctrl+alt+v"),
                               5: cfg.get("hotkey_rewrite", "ctrl+alt+r")}, bus.hotkey.emit)
    hk.start()

    hk.ready.wait(3)
    if hk.failed:
        bus.info.emit(i18n.t("Не получилось назначить горячую клавишу: ") + ", ".join(hk.failed) +
                      i18n.t(". Проверь сочетание в ⚙ Настройки → Поведение или его уже занимает другая программа."))
    reminders.restore(brain.notify)          # напоминания, поставленные до перезапуска
    brain.last_hwnd = lambda: watcher.last_hwnd or tracker.last_hwnd
    brain.clip_text = lambda: QGuiApplication.clipboard().text()
    brain.on_command = lambda q: (chips.record(q, cfg), save_cfg(cfg))     # учимся на кнопках и командах
    onboarding_open = [False]                                   # знакомство сейчас на экране (см. show_onboarding)

    def _blob_clicked():
        if onboarding_open[0]:
            return                                              # пока идёт первая настройка, чат не открываем: знакомство поверх
        if intel_ctl is not None and intel_ctl.voice_mode:      # в голосовом режиме чат не открываем
            return
        if intel_ctl is not None and getattr(intel_ctl, "update_locked", False):
            intel_ctl.toggle_aichat()                           # нужно обновление: чат открывается, но только с просьбой обновить Mico
            return
        if intel_ctl is not None and intel_ctl.on():            # режим Mico AI: единственный чат — чат Mico AI
            intel_ctl.toggle_aichat()
        else:
            panel.toggle()
    blob.clicked.connect(_blob_clicked)

    # Значок Mico в области уведомлений, справа у часов: нажал — открылся чат (правый щелчок — меню)
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon
        if QSystemTrayIcon.isSystemTrayAvailable():
            from ui import appicon
            tray = QSystemTrayIcon(appicon.blob_icon(cfg["color"]), app)
            tray.setToolTip("Mico AI")
            tray_menu = QMenu()
            tray_menu.addAction(i18n.t("Открыть чат"), _blob_clicked)
            tray_menu.addAction(i18n.t("Настройки"), lambda: blob.settings_requested.emit())
            tray_menu.addSeparator()
            tray_menu.addAction(i18n.t("Выйти"), app.quit)
            tray.setContextMenu(tray_menu)
            tray.activated.connect(lambda reason: _blob_clicked() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
            tray.show()
            app._tray, app._tray_menu = tray, tray_menu             # держим ссылки, иначе значок исчезнет
    except Exception:
        pass
    blob.slept.connect(lambda: None if (intel_ctl is not None and intel_ctl.on()) else panel.hide_smooth())   # заснул — обычный чат прячется
    # проснулся — чат возвращается, но не раньше, чем Mico AI приземлится после прыжка (иначе чат налезает на него)
    def _blob_woke():
        if intel_ctl is None or not intel_ctl.on():             # обычный чат возвращается только вне режима Mico AI
            QTimer.singleShot(blob.WAKE_SETTLE_MS, panel.show_near)
    blob.woke.connect(_blob_woke)
    blob.can_sleep = lambda: not (panel.busy or panel.inp.hasFocus() or panel.inp.text()
                                  or panel.isVisible()            # чат открыт (даже без мыши над ним) — Mico не засыпает и не уходит
                                  or (intel_ctl is not None and intel_ctl.aichat.isVisible()))
                                  # открыт чат Mico AI или голосовой режим — не спим
    intel_ctl = intel_ui.Intel(cfg, blob, panel)              # режим Windows Intelligence (по умолчанию выключен)
    panel.intel = intel_ctl
    panel.busy_changed.connect(intel_ctl.busy)
    panel.answer_text.connect(intel_ctl.answer)
    panel.streamed.connect(intel_ctl.voice.speak_feed)   # живая озвучка: фразы говорятся по мере готовности
    brain.speak_step = lambda t: intel_ctl.voice.speak(t)  # шаги агента — тоже вслух
    panel.user_sent.connect(intel_ctl.wi_user)
    panel.mic_requested.connect(lambda: intel_ctl.voice.toggle_listen())   # микрофон в чате
    panel.mico_fx.connect(intel_ctl.wi_fx)          # карточки-анимации переключателей — и в чат Mico AI
    panel.mico_said.connect(intel_ctl.wi_mico)
    panel.streamed.connect(intel_ctl.wi_stream)     # ответ в чат Mico AI печатается сразу, по кускам

    # Mico AI: помощник по буферу обмена и реакция на ошибки — раз в 2 секунды, только в режиме Mico AI
    help_t = QTimer()

    def help_tick():
        if not intel_ctl.on():
            return
        now = time.time()
        intel_ctl.clip_seen(QGuiApplication.clipboard().text(), now)
        intel_ctl.watch_errors(errwatch.probe(os.getpid(), W.process_of), now)
        if cfg.get("wi_load_bar"):
            try:
                import psutil
                intel_ctl.set_load(psutil.cpu_percent(interval=None))
            except Exception:
                pass
    help_t.timeout.connect(help_tick)
    help_t.start(intel.ERROR_CHECK_MS)
    blob.slept.connect(lambda: intel_ctl.glow.set_muted(True))            # во сне волны внизу гаснут
    blob.awake.connect(lambda: intel_ctl.glow.set_muted(False))           # проснулся — волны возвращаются
    blob.slept.connect(intel_ctl.on_sleep)               # в Intelligence Mico AI во сне исчезает, а не уходит в угол
    blob.moved.connect(lambda: panel.isVisible() and panel.reposition())   # чат всегда рядом с Mico AI, где бы он ни стоял

    # Сторож: Mico не должен пропадать с экрана. Раз в 3 с проверяем, что окно Mico видно и стоит на каком-то мониторе
    # (после смены разрешения, отключения монитора или «Свернуть всё» окно могло уйти за край или скрыться).
    def _keep_mico():
        try:
            if QApplication.activePopupWidget() is not None:
                return                                   # открыт выпадающий список: поднятие окон закрывало его через несколько секунд
            if intel_ctl.voice_mode or getattr(intel_ctl, "_mico_hidden", False):
                return                                   # голосовой режим сам управляет окном Mico
            if not blob.isVisible():
                blob.setWindowOpacity(1.0)
                blob.show()
            if QGuiApplication.screenAt(blob.geometry().center()) is None:
                g = QGuiApplication.primaryScreen().availableGeometry()
                blob.move(g.right() - blob.width() - 6, g.bottom() - blob.height() - 6)
            if not blob.covered():
                blob.raise_()
            else:
                for w in QApplication.topLevelWidgets():  # открытое окно Mico — всегда над ним
                    if isinstance(w, QDialog) and w.isVisible() and not w.isActiveWindow():   # уже активное не трогаем
                        w.raise_()
        except Exception:
            pass
    keep_mico_t = QTimer()
    keep_mico_t.timeout.connect(_keep_mico)
    keep_mico_t.start(3000)

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

    def open_settings(start_tab=None):
        """Открывает настройки во весь доступный экран, поверх голосовой полоски."""
        dock = intel_ctl.voice_dock if (intel_ctl is not None and intel_ctl.voice_mode) else None
        try:
            blob.settings_open = True                   # пока настройки открыты, Mico не поднимается над ними
            dlg = SettingsDialog(cfg, blob, panel, hooks, start_tab=start_tab)
            dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)   # иначе окно уходит под полоску Mico
            dlg.showMaximized()
            dlg.raise_()
            dlg.activateWindow()
            if dock is not None:
                dock.squeeze_to_mic()               # в голосовом режиме остаются только кнопки; Mico скрыт за настройками
            saved = dlg.exec() == QDialog.DialogCode.Accepted
            panel.refresh_chips()                   # новые кнопки видны сразу, даже если чат открыт
            if saved:
                panel._refresh_profile()
                panel.profile_changed.emit()
        except Exception as e:
            from voice.log import record
            QMessageBox.warning(None, "Mico AI", record("Настройки не открылись", e))
        finally:
            blob.settings_open = False
            if dock is not None:
                dock.restore_from_squeeze()         # настройки закрыты — полоска возвращается как была

    blob.settings_requested.connect(lambda: None if (intel_ctl is not None and intel_ctl.voice_mode) else open_settings())
    intel_ctl.voice_dock.all_settings.connect(open_settings)      # «Все настройки Mico AI» в голосовом режиме   # двойной щелчок — настройки, но не в голосовом режиме
    panel.settings_requested.connect(open_settings)              # «Настройки Mico AI» внизу бокового меню чата
    panel.profile_requested.connect(lambda: open_settings("profile"))

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
            a.triggered.connect(lambda *_: QMessageBox.information(None, i18n.t("Окружение"), brain.environment()))
        elif item == "about":
            ch = cfg.get("update_channel", "stable")
            a.setText(f"Mico AI {version.display_version(ch)}")
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
        allowed = not cfg.get("quiet_mode") and cfg.get("proactive_breaks", True) and panel.may_speak()
        msg = brk.tick(time.time(), idle_seconds(), allowed)
        if msg:
            panel.initiative.emit((msg, BREAK_MARK))
    brk_t = QTimer()
    brk_t.timeout.connect(breaks_tick)
    brk_t.start(30000)


    def greet():
        if cfg.get("silent_until_asked", True):    # не заговаривать первым: приветствие ждёт запроса
            return
        blob.set_mood("happy", 5)
        blob.jump()
        if intel_ctl.on():                                   # Mico AI: приветствие строкой над Mico AI
            intel_ctl.greet(hello(), "")
        else:
            panel.show_near(activate=False)
            panel.say(hello())
        ids = cfg.get("greet_items", [])
        if not cfg.get("weather_on_start", True):                    # погоду при запуске выключили в настройках
            ids = [i for i in ids if i != "weather"]
        if "weather" in ids and cfg.get("loc_consent") is None:      # спрашиваем один раз
            ok = _box(QMessageBox.Icon.Question, i18n.t("Геопозиция для погоды"),
                      "Mico AI может узнать твою геопозицию, чтобы сообщать погоду.\n\n"
                      "Windows сама покажет запрос доступа. Данные используются только для погоды. "
                      "Если откажешься — возьму город из настроек.", i18n.t("Разрешить"), i18n.t("Не сейчас"))
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
            if panel.may_speak():
                panel.show_near(activate=False)
                blob.set_mood("happy", 6)
                blob.jump()
            panel.say_when_allowed(text)

    QTimer.singleShot(8000, brain.start_digests)                                                 # пересказ прошлых дней, в фоне
    # Первый запуск: начальная настройка сама объясняет всё, поэтому ни приветствие, ни чат поверх неё не открываем.
    first_run = not cfg.get("tour_done")
    if cfg["greet_on_start"] and not relaunch and not cfg.get("quiet_mode") and not first_run:
        QTimer.singleShot(700, greet)
    def open_chat_on_start():
        """При запуске Mico AI сразу открывает чат только в обычном режиме.
        В режиме Intelligence текстовый чат открывает контроллер режима."""
        if intel_ctl.on():
            return
        panel.show_near(activate=False)
    if not relaunch and not first_run:
        QTimer.singleShot(900, open_chat_on_start)
    QTimer.singleShot(2600, whats_new)
    QTimer.singleShot(1500, start_update_check)     # сразу после запуска, в фоне

    def show_tour():
        panel.show_near(activate=False)
        panel.show_html(capabilities.html_tour())

    def recolor(hex_color):
        """Цвет Mico AI и его чата меняется сразу, пока пользователь выбирает (предпросмотр в начальной настройке)."""
        cfg["color"] = hex_color
        try:
            from ui import appicon
            appicon.set_color(hex_color)
            app.setWindowIcon(appicon.blob_icon(hex_color))
            if getattr(app, "_tray", None) is not None:
                app._tray.setIcon(appicon.blob_icon(hex_color))
        except Exception:
            pass
        blob.update()
        panel.theme()
        if panel.intel:
            panel.intel.restyle()

    # цвет из палитры: Mico уже покрутился и сменил цвет — сохраняем и перекрашиваем чат
    blob.color_set.connect(lambda hex_color: (recolor(hex_color), save_cfg(cfg)))

    def show_onboarding():
        """Первый запуск: коротко, что умеет Mico AI, и выбор цвета. Один раз."""
        from ui import onboarding
        dlg = onboarding.OnboardingDialog(cfg, on_color=recolor, desktop=blob)
        try:
            dlg.home = blob.frameGeometry().center()     # в конце знакомства Mico улетает туда, где живёт на рабочем столе
        except Exception:
            pass
        onboarding_open[0] = True
        try:
            dlg.exec()
        finally:
            onboarding_open[0] = False
        recolor(dlg.color)
        try:                                              # модель GigaChat могла смениться в знакомстве — кнопки модели обновляем
            for ref in list(chat_look.ModelPill._all):
                w = ref()
                if w is not None:
                    w.refresh()
        except Exception:
            pass
        cfg["tour_done"] = True
        save_cfg(cfg)
        if intel_ctl is not None and intel_ctl.on():
            intel_ctl._text_default()       # после знакомства открываем обычный текстовый чат

    def maybe_tour():
        """Знакомство один раз при первом запуске (если не режим тишины)."""
        if cfg.get("tour_done") or cfg.get("quiet_mode") or relaunch:
            return
        show_onboarding()
    # первый запуск: сразу открываем первую настройку (знакомство), а не чат; потом — обычная пауза
    QTimer.singleShot(9000 if cfg.get("tour_done") else 1500, maybe_tour)
    _stage("цикл событий запущен")
    code = app.exec()
    try:
        store.db.close()                # всё уже записано (commit после каждой записи) — закрываем базу аккуратно
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except Exception:
            pass
    # Выход сразу, без очистки интерпретатора: фоновые потоки (экран, горячие клавиши, звук) при обычном выходе
    # ещё работают во время очистки и держат файлы распакованной программы — отсюда «Failed to remove temporary directory _MEI…».
    os._exit(code)


if __name__ == "__main__":
    main()
