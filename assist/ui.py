"""Окна Mico AI (Windows Intelligence): полоса по краю экрана, волны при ответе, строка ответа над Mico AI,
кнопки под ней и переходы Mico. Все окна не забирают фокус (кроме собственного чата Mico AI). Полоса пропускает клики.
Расчёты — в intel.py; здесь рисование, анимации и связь с чатом. В полноэкранном режиме Mico AI молчит."""
from ui.energy import GLOW_MS, LOAD_MS
import base64
import math
import os
import threading
import time

from PyQt6.QtCore import (QAbstractAnimation, QObject, Qt, QTimer, QRectF, QPoint, QPointF, QPropertyAnimation, QVariantAnimation,
                          QEasingCurve, pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QGuiApplication, QLinearGradient, QPainter, QPainterPath)
from PyQt6.QtWidgets import QFileDialog, QWidget

from data import clipbuf
from core import emotions
from assist import help as errhelp
from assist import watch as errwatch
from assist import intel
from win import power as sleepmode
from ui import theme
from voice.dock import VoiceDock
from assist.chat import AIChat
from voice import control as voice_ctl


def _window_flags():
    """Окно без рамки, поверх других, без кнопки на панели задач. Вычисляется при создании, не при импорте."""
    return Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool


def fullscreen_now():
    """Активное окно занимает весь монитор (игра, видео, презентация). Если узнать не получилось — нет."""
    try:
        import win32api
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False
        win = win32gui.GetWindowRect(hwnd)
        mon = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd, 2))["Monitor"]   # 2 — ближайший монитор
        return intel.is_fullscreen(win, mon)
    except Exception:
        return False


def system_readings():
    """Свободное место, память и батарея для проверок Mico AI. Что не удалось прочитать — None."""
    disk = mem = batt = plugged = None
    try:
        import shutil
        disk = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\").free / 1e9
    except Exception:
        pass
    try:
        import psutil
        mem = psutil.virtual_memory().percent
        b = psutil.sensors_battery()
        if b is not None:
            batt, plugged = b.percent, bool(b.power_plugged)
    except Exception:
        pass
    return disk, mem, batt, plugged


def total_ram_gb():
    """Установленная оперативная память в гигабайтах. None — если не удалось прочитать."""
    try:
        import psutil
        return psutil.virtual_memory().total / 1024 ** 3
    except Exception:
        return None


def free_disk_gb():
    """Свободное место на системном диске (где Windows и по умолчанию модели) в гигабайтах."""
    try:
        import shutil
        return shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\").free / 1e9
    except Exception:
        return None


class EdgeGlow(QWidget):
    """Полоса у нижнего края экрана, на всю ширину: постоянные волны, которые плавно пульсируют,
    а при ответе Mico AI поднимаются в нескольких местах. Цвет показывает действие и плавно меняется.
    Рядом с Mico AI — Island."""
    IDLE = 0.55                                  # уровень волн, когда Mico AI ничего не делает — они видны всегда

    def __init__(self, cfg):
        super().__init__(None, _window_flags() | Qt.WindowType.WindowTransparentForInput)
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.state = "listen"
        self.rgb = intel.hex_rgb(intel.state_color(cfg, "listen"))
        self.target_rgb = self.rgb
        self.level, self.target, self.phase = 0.0, 0.0, 0.0
        self.idle = False                                                  # волны видны постоянно (режим Mico AI)
        self.wave, self.wave_until = 0.0, 0.0                              # 0..1: свечение ярче, пока Mico AI говорит
        self.keep = False                                                  # True — Mico AI думает: гасить нельзя
        self.muted = False                                                 # True — Mico AI спит: волны и свечение гаснут
        self.island = None                                                 # капсула рядом с Mico AI (Island)
        self._last = time.time()
        self.timer = QTimer(self)
        self.timer.setInterval(GLOW_MS)
        self.timer.timeout.connect(self._tick)
        self.hold = QTimer(self)                  # «вспышка» на время ответа, потом гаснет сама
        self.hold.setSingleShot(True)
        self.hold.timeout.connect(lambda: self.set_on(False))

    def set_idle(self, on):
        """Волны внизу видны постоянно, пока включён режим Mico AI (но не в полноэкранном режиме — там Mico AI молчит)."""
        self.idle = bool(on) and intel.glow_visible(self.cfg)
        if self.idle:
            self.setGeometry(QGuiApplication.primaryScreen().geometry())
            if not self.isVisible():
                self.show()
            self.target = max(self.target, self.IDLE)
            self.timer.start()
        else:
            self.set_on(False)

    def set_muted(self, on):
        """Mico AI уснул — волны и свечение плавно гаснут; проснулся — возвращаются (если режим Mico AI включён)."""
        self.muted = bool(on)
        if not self.muted and (self.idle or self.target > 0):
            self.setGeometry(QGuiApplication.primaryScreen().geometry())
            if not self.isVisible():
                self.show()
            self.timer.start()

    def set_on(self, on, state="listen", label=None):
        if not on and self.keep:                              # Mico AI ещё думает — свечение не гаснет
            return
        self.target = 1.0 if on else (self.IDLE if self.idle else 0.0)
        if on:
            self.state = state
            self.target_rgb = intel.hex_rgb(intel.state_color(self.cfg, state))
            self.setGeometry(QGuiApplication.primaryScreen().geometry())
            if not self.isVisible():
                self.show()
            self.timer.start()
        if self.island is not None:
            if on:
                self.island.show_state(state, label)
            else:
                self.island.hide_state()
        self.hold.stop()

    def pulse(self, secs, state="think", label=None):
        self.set_on(True, state, label)
        self.hold.start(int(secs * 1000))

    def sweep(self, secs, state, goal):
        """Совместимость: появление и уход теперь — плавное проявление и затухание свечения."""
        self.set_on(goal >= 1.0, state)

    def wave_for(self, secs):
        """Свечение дышит ярче на время ответа. Работает, только если в настройках волны включены."""
        self.wave_until = max(self.wave_until, time.time() + secs)

    def _tick(self):
        now = time.time()
        dt = min(0.1, max(0.001, now - self._last))
        self._last = now
        self.phase += 0.05
        goal = 0.0 if self.muted else self.target          # во сне всё гаснет, не меняя цели
        self.level = intel.approach(self.level, goal)
        if self.muted and self.level < 0.02:                # во сне полоски полностью пропадают
            self.level = 0.0
            self.timer.stop()
            self.hide()
            return
        self.rgb = intel.lerp_rgb(self.rgb, self.target_rgb, 1 - math.exp(-dt * 6))   # цвет плавно сменяется
        want_wave = now < self.wave_until and intel.waves_on(self.cfg)
        self.wave = intel.approach(self.wave, 1.0 if want_wave else 0.0, 0.1)
        if self.level <= 0.0 and goal <= 0.0:
            self.timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, e):
        if self.level <= 0.0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.level)
        w, h = float(self.width()), float(self.height())
        breathe = 0.85 + 0.15 * math.sin(self.phase)              # дыхание: едва заметно
        # Цвет подсветки всегда такой, как выбран в «Цвет волн»: Mico AI из персонализации, свой, готовый набор.
        # Цвет действия (ждёт, думает…) используется только если выбрано «Цвет действия».
        if self.cfg.get("wi_wave_source", "mico") == "state":
            r, g, b = (int(c) for c in self.rgb)                                # плавный переход между действиями
        else:
            r, g, b = intel.hex_rgb(intel.wave_base(self.cfg, self.state, self.phase))
        if intel.glow_style(self.cfg) == intel.GLOW_EDGES:
            edge_strength = (0.55 + 0.25 * self.wave) * breathe                 # полоски заметно ярче волн
            self._draw_edges(p, w, h, (r, g, b), edge_strength * intel.edge_alpha(self.cfg))   # полоски по краям, без волн
        p.end()

    def _draw_edges(self, p, w, h, rgb, strength):
        """Нежные полоски вдоль низа, верха и боков: мягкий градиент, который гаснет к центру экрана.
        Два слоя разной ширины дают мягкий край без резкой линии. Цвет медленно переливается
        к светлому оттенку, как у Apple Intelligence. Толщина — из настроек, но полоски всегда тонкие."""
        band = float(intel.edge_band(self.cfg))
        r, g, b = rgb
        shift = 0.5 + 0.5 * math.sin(self.phase * 0.6)                        # медленное переливание
        tint = (int(r + (255 - r) * 0.30 * shift), int(g + (255 - g) * 0.30 * shift),
                int(b + (255 - b) * 0.30 * shift))

        def fade(rect, x0, y0, x1, y1, col, amp):
            grad = QLinearGradient(QPointF(x0, y0), QPointF(x1, y1))
            a = int(255 * strength * amp)
            grad.setColorAt(0.0, QColor(col[0], col[1], col[2], a))
            grad.setColorAt(0.55, QColor(col[0], col[1], col[2], int(a * 0.3)))
            grad.setColorAt(1.0, QColor(col[0], col[1], col[2], 0))
            p.fillRect(rect, QBrush(grad))

        for col, scale, amp in (((r, g, b), 1.0, 0.55), (tint, 0.45, 0.45)):   # внешний слой мягче и шире
            bw = band * scale
            fade(QRectF(0, h - bw, w, bw), 0, h, 0, h - bw, col, amp)           # низ — основная полоска
            fade(QRectF(0, 0, w, bw * 0.6), 0, 0, 0, bw * 0.6, col, amp * 0.6)  # верх — тише
            fade(QRectF(0, 0, bw, h), 0, 0, bw, 0, col, amp * 0.8)              # левый край
            fade(QRectF(w - bw, 0, bw, h), w, 0, w - bw, 0, col, amp * 0.8)     # правый край

class LoadBar(QWidget):
    """Загрузка процессора тонкой линией внизу экрана. Плавно растёт и падает; цвет — цвет волн."""

    def __init__(self, cfg):
        super().__init__(None, _window_flags() | Qt.WindowType.WindowTransparentForInput)
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.target, self.level = 0.0, 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(LOAD_MS)
        self.timer.timeout.connect(self._tick)

    def set_target(self, percent):
        self.target = intel.load_percent(percent)
        if not self.isVisible():
            g = QGuiApplication.primaryScreen().geometry()
            self.setGeometry(g.left(), g.bottom() - 2, g.width(), 3)
            self.show()
        self.timer.start()

    def hide_bar(self):
        self.timer.stop()
        self.target = self.level = 0.0
        self.hide()

    def _tick(self):
        self.level += (self.target - self.level) * 0.15
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        r, g, b = intel.hex_rgb(intel.wave_color(self.cfg, "listen"))
        p.fillRect(QRectF(0, 0, self.width() * self.level / 100.0, self.height()), QColor(r, g, b, 220))
        p.end()


class _Bridge(QObject):
    """Ответ модели приходит из фонового потока: сигнал переносит его в главный поток Qt."""
    done = pyqtSignal(str)


class Intel:
    """Связывает режим Mico AI с Mico AI и своим чатом: что показывать, когда и что делать."""

    def __init__(self, cfg, blob, panel):
        self.cfg, self.blob, self.panel = cfg, blob, panel
        self._live = []                        # идущие анимации Mico AI и строки (храним, чтобы их не удалил сборщик)
        self._move = None
        self._fade_out = None
        self._drop = None
        self._labels = {}                      # вопрос для ИИ → короткая подпись в чате Mico AI
        self._warned = {}                      # когда последний раз напоминали о проблеме (ключ → время)
        self.glow = EdgeGlow(cfg)
        self.island = None                      # плашка «жду» убрана: Mico AI внизу сам показывает состояние
        self.glow.island = None
        self.aichat = AIChat(cfg)
        self.aichat.send.connect(self._on_send)
        self.aichat.closed.connect(self._aichat_closed)
        self.aichat.dnd.connect(self.set_dnd)
        self.aichat.rewrite.connect(self.rewrite)
        self.aichat.activity.connect(self._chat_activity)
        self.aichat.color_pick.connect(self.blob.pick_color)     # палитра чата: Mico крутится и меняет цвет
        # недавние чаты, поиск и история — те же, что в обычном чате Mico AI
        self.aichat.attach(self.panel._store, lambda: self.panel.conv_id, self._wi_open_conv, self._wi_new_conv)
        self.aichat.settings_all.connect(self.blob.settings_requested.emit)   # «Все настройки» из бокового меню
        self.aichat.profile_requested.connect(self.panel.edit_profile)        # аватар: профиль общий
        self.aichat.apps_fn = self.panel._habit_apps            # быстрые действия по частым программам
        self.aichat.save_cfg = self._save                       # смена стиля общения в чате сохраняет настройки
        self.panel.title_ready.connect(self.aichat.refresh_side)             # название чата придумано — обновить список
        self.panel.profile_changed.connect(self.aichat.refresh_profile)
        self.voice = voice_ctl.shared(cfg)                        # голос: озвучка и голосовой ввод, всё локально (один на всё)
        self.voice.heard.connect(self._voice_heard)               # что услышал Mico (для «почему не реагирует»)
        self.voice.said.connect(self._on_voice_said)              # распознанная фраза — вопрос как из чата (или «хватит»)
        self.voice.speaking.connect(self.blob.set_speaking)       # рот и речь
        self.voice.level.connect(self.blob.set_voice_level)
        self.voice.status.connect(self._voice_status)
        self.voice.listening.connect(self._voice_listening)
        self.aichat.voice_toggle.connect(self._voice_toggle)
        self.aichat.voice_pick.connect(self._voice_pick)
        self.aichat.listen.connect(self.enter_voice_mode)       # микрофон в чате: голосовой режим
        self.aichat.voice_mute.connect(self._voice_mute_toggle)   # кнопки голосового режима внутри чата
        self.aichat.voice_speed.connect(self._voice_speed_pick)
        self.aichat.voice_color.connect(self.blob.pick_color)
        self.aichat.voice_subs.connect(self._voice_chat_subs_toggle)
        self.aichat.voice_exit.connect(self.exit_voice_mode)
        self.voice.woke.connect(self._on_wake)                    # «мико» услышан: сразу открываем голосовой чат
        self.blob.slept.connect(self.voice.arm_wake)              # во сне «мико» продолжаем слушать
        self.blob.awake.connect(self.voice.arm_wake)
        self.voice.speaking.connect(self._on_voice_speaking)      # закончил говорить — снова слушаем (голосовой режим)
        self.voice.ready.connect(self._voice_rearm)               # модель распознавания загрузилась
        self.voice_mode = False                                   # голосовой режим: чат свёрнут, под Mico — кнопки
        self._voice_rest = None                                   # где Mico стоял до голосового режима (вернётся туда)
        self._mico_hidden = False                                 # «переключись на текст»: Mico скрыт, остаётся только чат
        self.voice_dock = VoiceDock(cfg)
        self.voice_dock.color_pick.connect(self.blob.pick_color)
        self.voice_dock.mute_clicked.connect(self._voice_mute_toggle)
        self.voice_dock.exit_clicked.connect(self.exit_voice_mode)
        self.voice_dock.voice_pick.connect(self._voice_pick)          # голос — тот же выбор, что в чате
        self.voice_dock.speed_pick.connect(self._voice_speed_pick)
        self.voice_dock.subs_toggled.connect(self._voice_subs_toggle)
        self.voice.sentence.connect(self.voice_dock.show_mico)      # субтитры: фраза, которую Mico сейчас говорит
        self.voice.mic_level.connect(self.voice_dock.set_user_level)  # волны: громкость пользователя
        self.voice.level.connect(self.voice_dock.set_mico_level)      # волны: громкость голоса Mico
        self.voice.said.connect(self.voice_dock.show_user)          # субтитры: вопрос пользователя
        self.voice.partial.connect(self._voice_partial)             # слова появляются, пока человек говорит
        self.blob.tapped.connect(self._blob_tapped)                 # нажатия по Mico в голосовом режиме
        self.blob.slept.connect(self._voice_slept)                  # сон в голосовом режиме: полоска сужается до обводки
        self.blob.woke.connect(self._voice_woke)                    # проснулся от нажатия — полоска разворачивается
        self._taps = []                                             # времена последних нажатий
        self._tap_warn_at = 0.0                                     # когда последний раз просили не нажимать так часто
        if self.voice.enabled() or self.voice.wake_on():
            self.voice.ensure_ready()                             # модели грузим заранее, в фоне
        self.load_bar = LoadBar(cfg)
        self.dnd_until = 0                      # «не беспокоить» до этого времени (0 — не включено)
        self._last_answer = None                # последний ответ — для «короче/подробнее»
        self._bridge = _Bridge()
        self._bridge.done.connect(self._quick_done)
        self._last_clip = None                  # последний текст из буфера (его уже смотрели)
        self._clip_offered = None               # когда последний раз предлагали объяснить текст из буфера
        self._hang = errwatch.HangTracker()     # сколько проверок подряд окно молчит
        self._dialog_alert = {}                 # когда последний раз говорили про окно с ошибкой
        # пока Mico AI включён: следим за полноэкранным режимом и проверяем систему раз в 10 минут
        self.guard = QTimer()                 # без родителя: Intel — не QObject, сохранён в self
        self.guard.setInterval(2000)
        self.guard.timeout.connect(self._guard)
        self.checks = QTimer()
        self.checks.setInterval(10 * 60 * 1000)
        self.checks.timeout.connect(self.check_system)
        if self.on():
            self._start()
            QTimer.singleShot(1500, self._text_default)          # в режиме Mico AI по умолчанию открывается текстовый чат

    def on(self):
        return intel.style_of(self.cfg.get("assist_style")) == intel.INTELLIGENCE

    def restyle(self):
        """Сменили цвет Mico AI или тему: строка и чат Mico AI перекрашиваются сразу, без перезапуска."""
        self.aichat._apply_style()
        if getattr(self, "voice_dock", None) is not None:
            self.voice_dock.refresh(self.voice.muted())

    def quiet(self):
        """В полноэкранном режиме (игра, видео, презентация) Mico AI не появляется."""
        return self.on() and fullscreen_now()

    def hushed(self):
        """Mico AI не начинает разговор сам: полноэкранный режим, «не беспокоить» или тихий час.
        Ответы на вопросы пользователя это не блокирует."""
        if self.quiet():
            return True
        now = time.time()
        return now < self.dnd_until or intel.in_quiet_hours(now, self.cfg.get("wi_quiet_from"),
                                                            self.cfg.get("wi_quiet_to"),
                                                            bool(self.cfg.get("wi_quiet_on")))

    def _start(self):
        self._session(True)
        self.glow.set_idle(True)                                # волны внизу видны, пока режим Mico AI включён
        self.guard.start()
        QTimer.singleShot(3 * 60 * 1000, self.check_system)     # первая проверка — через три минуты после включения
        self.checks.start()

    def _stop(self):
        self.guard.stop()
        self.glow.set_idle(False)
        self.checks.stop()
        self._session(False)

    def _session(self, wi):
        """Mico AI помнит разговор дольше (30 минут), обычный Mico AI — как и раньше, из настроек."""
        brain = getattr(self.panel, "brain", None)
        dlg = getattr(brain, "dialog", None)
        if dlg is None:
            return
        normal = int(self.cfg.get("dialog_memory_min", 15)) * 60
        dlg.window = max(normal, intel.SESSION_SEC) if wi else normal

    def _guard(self):
        """Полноэкранный режим начался — гасим полоску и строку, не дожидаясь нового ответа.
        Когда полноэкранный режим кончился, волны возвращаются."""
        if self.quiet():
            self.glow.keep = False
            self.glow.idle = False
            self.glow.set_on(False)
        elif self.on() and not self.glow.idle:
            self.glow.set_idle(True)

    # ----- переход в Mico AI и обратно (после «Сохранить») -----
    def switch(self, on, tip_lines=()):
        """Режим сохранили и он сменился. Mico AI: Mico AI выезжает из угла вниз по центру, полоска расходится от низа
        к верху и встречается сверху; потом Mico AI рассказывает о Mico AI в чате. Выключили: всё возвращается в угол."""
        if on:
            self._start()
            self._arrive(tip_lines)
        else:
            self._stop()
            self._leave()

    def _spot(self):
        x, y = sleepmode.corner_spot(self.blob._screen_avail(), self.blob.width(), sleepmode.SPOT)
        return QPoint(x, y)

    def _base_opacity(self):
        return 1.0                                  # прозрачности нет: Mico всегда непрозрачный

    def _run(self, obj, prop, start, end, ms, curve=None, after=None):
        """Одна плавная анимация. Ссылку храним в _live, пока она идёт. curve — None: плавно туда и обратно."""
        anim = QPropertyAnimation(obj, prop, obj)
        anim.setDuration(int(ms))
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(curve if curve is not None else QEasingCurve.Type.InOutCubic)
        self._live.append(anim)

        def done():
            if anim in self._live:
                self._live.remove(anim)
            if after is not None:
                after()
        anim.finished.connect(done)
        anim.start()
        return anim

    def _glide_blob(self, target, ms, after=None):
        """Mico AI едет в точку target плавно. На это время движением управляем здесь, а не _glide."""
        if self._move is not None:
            self._move.stop()
        self.blob.locked = True

        def arrived():
            self.blob.locked = False
            if after is not None:
                after()
        self._move = self._run(self.blob, b"pos", QPoint(self.blob.pos()), target, ms,
                               QEasingCurve.Type.OutCubic, after=arrived)

    def _arrive(self, tip_lines):
        if self.blob.asleep:
            self.blob.wake(silent=True)
        self._show_blob()
        ms = int(intel.ARRIVE_SEC * 1000)
        self._glide_blob(self._spot(), ms)
        self.glow.sweep(intel.EDGE_SWEEP_SEC, "listen", goal=1.0)     # полоска расходится от низа к верху
        self.blob.jump(160)
        QTimer.singleShot(ms + 120, lambda: self._tour(intel.tour_lines(tip_lines), 0))

    def _leave(self):
        self.aichat.dismiss()
        self.load_bar.hide_bar()
        self.glow.keep = False
        ms = int(intel.LEAVE_SEC * 1000)
        self.glow.sweep(intel.LEAVE_SEC, "listen", goal=0.0)           # полоска стягивается обратно
        QTimer.singleShot(ms + 60, lambda: self.glow.set_on(False))
        self.blob.locked = False                                       # Mico AI поедет в свой угол сам (_glide)
        self._mico_hidden = False
        self._show_blob()

    def _tour(self, lines, i):
        """Mico AI по порядку рассказывает о Mico AI в своём чате. Закрыли чат — тур прекращается."""
        if not self.on() or (i and not self.aichat.isVisible()):
            return
        if i >= len(lines):
            self.glow.set_on(True, "listen")              # тур кончился, чат открыт — полоса горит дальше
            return
        self.show_aichat(activate=False)
        self.aichat.set_busy(True)
        QTimer.singleShot(400 if i == 0 else intel.TOUR_GAP_MS, lambda: self._tour_say(lines, i))

    def _tour_say(self, lines, i):
        if not self.on():
            return
        self.aichat.set_busy(False)
        self.aichat.add_mico(lines[i])
        secs = intel.speak_seconds(lines[i])
        self.glow.set_on(True, "tip")
        self.glow.wave_for(secs)
        self.blob.set_mood("happy", 3)
        QTimer.singleShot(int(secs * 1000) + 200, lambda: self._tour(lines, i + 1))

    def preview(self):
        """Настройку меняют (толщина, волны, цвет): показываем полосу и волны, чтобы увидеть результат."""
        if self.on() and not self.quiet():
            self.glow.pulse(1.6, "listen")
            self.glow.wave_for(1.6)

    # ----- показ и гашение -----
    def _show_blob(self):
        """Mico AI виден. Если он был спрятан во сне в Mico AI — поднимается снизу и проявляется."""
        if self._mico_hidden:                       # текстовый режим: Mico не показываем
            return
        for anim in (self._move, self._fade_out, self._drop):
            if anim is not None:
                anim.stop()
        self._live = [a for a in self._live if a.state() != QAbstractAnimation.State.Stopped]
        self.blob.locked = False
        base = self._base_opacity()
        if self.blob.isVisible():
            self.blob.setWindowOpacity(base)
            return
        if self.on():
            spot = self._spot()
            self.blob.move(spot + QPoint(0, 40))
            self.blob.setWindowOpacity(0.0)
            self.blob.show()
            self.blob.locked = True
            self._glide_blob(spot, 420, after=None)
            self._run(self.blob, b"windowOpacity", 0.0, base, 420, QEasingCurve.Type.OutCubic)
        else:
            self.blob.setWindowOpacity(base)
            self.blob.show()

    def on_sleep(self):
        """Mico AI уснул: его чат уходит вместе с ним. Сам Mico растворяется на месте (см. Blob.vanish)."""
        if not self.on():
            return
        self.aichat.dismiss()

    # ----- свой чат Mico AI -----
    def show_aichat(self, activate=True):
        if self.voice_mode:                        # голосовой режим: чат свёрнут, Mico говорит вслух
            return
        """Открывает чат Mico AI над Mico. Mico AI при этом ждёт: полоса горит."""
        self.blob.touch()
        if not self.voice_mode:
            self.blob.keep_awake = True                # чат открыт — Mico не засыпает под чтение ответа
        if self.blob.asleep and not self._mico_hidden:
            self.blob.wake(silent=True)
        self._show_blob()
        if not self.aichat.isVisible():
            self.glow.set_on(True, "listen")
        self.aichat.show_near(self.blob, activate)

    def toggle_aichat(self):
        if self.aichat.isVisible():
            self.aichat.dismiss()
        else:
            self.show_aichat()

    def _aichat_closed(self):
        if self.voice_mode and getattr(self, "_voice_inline", False):
            self.exit_voice_mode()                         # чат закрыли — голосовой режим внутри него тоже заканчивается
        if not self.voice_mode:
            self.blob.keep_awake = False               # чат закрыт — Mico снова может уснуть по настройке
        if self.on():
            if self.panel.busy:
                self.glow.set_on(True, "think")
            else:
                self.glow.set_on(False)

    def wi_user(self, q):
        """Вопрос пользователя (из чата или горячей клавиши) — в чат Mico AI короткой подписью."""
        self.aichat.add_user(self._labels.pop(q, q))

    def wi_mico(self, text):
        """Текст Mico AI (ответ, напоминание, приветствие) — в чат Mico AI."""
        self.blob.touch()
        self.aichat.add_mico(text)

    def wi_fx(self, spec):
        """Карточка-анимация переключателя — в чат Mico AI."""
        try:
            self.aichat.add_fx(spec)
        except Exception:
            pass

    def wi_stream(self, text):
        """Живой ответ по кускам — в чат Mico AI сразу, как в панели."""
        self.blob.touch()
        self.aichat.stream_delta(text)

    def busy(self, on):
        """Mico AI думает: полоса горит цветом «думает». Чат Mico AI показывает, что Mico AI печатает."""
        if on and self.voice_mode:
            self.voice.stop_listening()                       # Mico думает — не слушаем
        elif not on and self.voice_mode:
            QTimer.singleShot(500, self._voice_rearm)         # ответа может не быть — тогда снова слушаем
        if not self.on():
            return
        self.aichat.set_busy(on)
        self.glow.keep = bool(on) and not self.quiet()           # думает — полоска горит до ответа
        if on and not self.blob.asleep:
            self.blob.set_mood("thinking")                       # Mico AI показывает своё «думаю», а не точки в чате
        elif not on and self.blob.mood == "thinking":
            self.blob.set_mood("idle")
        if self.quiet():
            return
        if on:
            self.glow.set_on(True, "think")
        elif self.aichat.isVisible():
            self.glow.set_on(True, "listen")
        else:
            self.glow.pulse(1.0, "think")

    def answer(self, text):
        """Ответ пришёл: Mico AI говорит — полоса волнуется. Короткий — строкой над Mico AI, длинный — открываем чат.
        В полноэкранном режиме тихо: ответ останется в чате."""
        if not self.on() or not text or self.quiet():
            return
        if self.voice.enabled() or self.voice_mode:
            tag_mood, _ = emotions.split_mood(text)
            mood = tag_mood or emotions.detect_emotion(text) or "idle"   # настроение ответа — и в голосе, и в мимике
            if mood != "idle":
                self.blob.set_mood(mood, 4)
            if self.voice_mode:
                self.voice_dock.show_mico(emotions.split_mood(text)[1])   # субтитры: ответ целиком, дальше фразы по ходу речи
            if not self.voice.speak_feed_end(text, mood):   # живая озвучка уже говорила фразы — доигрываем хвост
                self.voice.speak(text, mood)                          # ответ говорим вслух, рот двигается в такт
        self._last_answer = text
        self.aichat.add_mico(text)                       # ответ — сразу, а кнопки — под ним (раньше кнопки
        self.aichat._expect_dup = text                   # появлялись первыми, а текст — секунд через 10)
        self.aichat.show_rewrite_row()
        secs = intel.speak_seconds(text)
        self.glow.wave_for(secs)
        if self.voice_mode:
            return                                  # голосовой режим: чат свёрнут, ответ уже говорим — чат не открываем
        if self.aichat.isVisible():                      # чат открыт: полоса горит, пока он открыт
            self.glow.set_on(True, "listen")
            return
        self.glow.pulse(secs + 0.5, "think", label="отвечаю…")
        if intel.opens_chat(text):
            self.show_aichat(activate=False)
            return
        self.show_aichat(activate=False)

    def _wi_open_conv(self, cid, rid=None):
        """Открыть прежний разговор в чате Mico AI: открываем его в обычном чате и показываем его реплики."""
        if self.panel.busy or self.panel._store is None:
            return
        self.panel.open_chat(cid, focus_rid=rid)
        if self.panel.conv_id == cid:
            self.aichat.show_history(self.panel._store.conv_messages(cid, limit=200), focus_rid=rid)

    def _wi_new_conv(self):
        """Новый чат из бокового меню: пустая лента и новый разговор (память начнётся с первого вопроса)."""
        if self.panel.busy:
            return
        self.panel.new_chat()
        self.aichat.clear_messages()

    def notify(self, text, state="tip"):
        """Mico AI сам что-то сообщает: перерыв, наблюдение, проблема, приветствие. Цвет полоски — по причине.
        Текст всегда попадает в чат Mico AI; строкой над Mico AI показываем, если чат закрыт."""
        if not self.on() or not text:
            return
        self.aichat.add_mico(text)
        if self.hushed():
            return
        if self.aichat.isVisible():
            self.glow.set_on(True, state)                 # чат открыт: полоска держит цвет причины до следующего события
            return
        self.glow.pulse(4.0, state)

    def greet(self, hello_text, summary_text):
        """Приветствие в Mico AI — строка с итогом дня, без открытия чата."""
        self.notify(intel.greeting_line(hello_text, summary_text), "tip")

    # ----- функции только для Mico AI -----
    def gate(self):
        """Вне Mico AI функции не работают: честно говорим, как включить."""
        if self.on():
            return True
        self.panel.explain(intel.GATE_TEXT)
        return False

    def ask(self, question, label=None):
        """Отправляет вопрос как обычный запрос: ответ придёт строкой над Mico AI или откроет чат."""
        if self.panel.busy:
            return
        if label:
            self._labels[question] = label
        self.panel.submit(question)

    def window_hotkey(self, title):
        """Горячая клавиша «Помочь с окном»: подсказка по программе, которой пользуешься сейчас."""
        if self.gate():
            self.ask(intel.window_question(title), "Помочь с окном")

    def screen_hotkey(self):
        """Горячая клавиша «Что на экране?»: снимок экрана и ответ модели с картинкой."""
        if self.gate():
            self.ask(intel.SCREEN_QUESTION, "Что на экране?")

    def retry(self):
        last = getattr(self.panel, "last_pair", None)
        if last and last.get("q"):
            self.ask(last["q"], "Повторить")

    def check_system(self):
        """Мешает ли что-то работе: мало места, память, батарея. Напоминаем не чаще раза в два часа."""
        if not self.on() or self.hushed():
            return
        disk, mem, batt, plugged = system_readings()
        now = time.time()
        for key, text in intel.problems(disk, mem, batt, plugged):
            if intel.warn_due(key, now, self._warned):
                self._warned[key] = now
                self.notify(text, "warn")

    # ----- помощник по буферу, реакция на ошибки, файлы (только Mico AI) -----
    def quick(self, label, prompt, image=None):
        """Короткий вопрос в фоне: файл, буфер, ошибка. Ответ — в чат Mico AI; в память разговора не пишется."""
        self.aichat.add_user(label)
        self.aichat.set_busy(True)
        self.glow.keep = True
        self.glow.set_on(True, "think")
        if self.blob.isVisible():
            self.blob.set_mood("thinking")          # тело Mico думает: над головой мигают три точки

        def work():
            try:
                text = self.panel.brain.quick_answer(prompt)     # картинки в быстрых вопросах не передаём: brain.quick_answer берёт только текст
            except Exception as e:
                text = f"Не получилось ответить: {e}"
            self._bridge.done.emit(text or "Ответа нет.")
        threading.Thread(target=work, daemon=True).start()

    def _quick_done(self, text):
        self.glow.keep = False
        self.aichat.set_busy(False)
        if self.blob.isVisible() and self.blob.mood == "thinking":
            self.blob.set_mood("idle")              # ответ готов — точки уходят
        self.aichat.add_mico(text)
        self.answer(text)

    def _error_options(self, title, text):
        """Варианты под предложением о любой ошибке: объяснить или найти решение."""
        return [("Объяснить", lambda: self.quick(f"Объяснить ошибку: {title}", intel.explain_prompt(text))),
                ("Найти решение", lambda: self.quick(f"Найти решение: {title}", errhelp.solution_prompt(title, text)))]

    def _offer(self, text, options, state="warn"):
        """Mico AI сам предлагает помощь: текст в чат и кнопки с вариантами под ним. «Не сейчас» — убрать кнопки."""
        self.aichat.add_mico(text)
        self.aichat.show_offer_row(list(options) + [("Не сейчас", None)])
        self.glow.pulse(4.0, state)
        if not self.aichat.isVisible():
            self.show_aichat(activate=False)

    def clip_seen(self, text, now):
        """Буфер обмена: если там текст ошибки — предложить объяснить. Один и тот же текст — один раз."""
        if not self.on() or self.hushed() or not self.cfg.get("wi_clip_help", True):
            return
        if text == self._last_clip:
            return
        self._last_clip = text
        if not clipbuf.looks_like_error(text) or not errwatch.due(self._clip_offered, now, intel.CLIP_OFFER_GAP_SEC):
            return
        self._clip_offered = now
        errhelp.remember("текст из буфера обмена", text)
        self._offer("Похоже, в буфере обмена текст ошибки. Что сделать?", self._error_options("из буфера", text),
                    state="tip")

    def watch_errors(self, info, now):
        """Окно на переднем плане: программа молчит или открыто окно с ошибкой. info — errwatch.probe()."""
        if not self.on() or self.hushed() or not self.cfg.get("wi_error_help", True) or info is None:
            return
        hwnd, proc, _cls, title, hung, text = info
        if self._hang.observe(hwnd, hung, now):
            name = proc or "программа"
            errhelp.remember(f"«{name}» не отвечает", "программа не отвечает уже несколько секунд")
            self._offer(f"«{name}» не отвечает уже несколько секунд. Обычно помогает минута ожидания. Что сделать?",
                        [("Что делать?", lambda: self.quick(f"Что делать: «{name}» не отвечает",
                                                          intel.hung_prompt(proc)))])
        elif text and errwatch.due(self._dialog_alert.get(hwnd), now):
            self._dialog_alert[hwnd] = now
            errhelp.remember(title, text)
            self._offer(f"На экране окно с ошибкой «{title}». Что сделать?", self._error_options(title, text))

    def _on_send(self, text):
        """Сообщение из чата Mico AI всегда является обычным текстовым вопросом."""
        self.panel.submit(text)

    def _save(self):
        try:
            self.panel.brain.save_cfg()
        except Exception:
            pass

    # ----- голосовой режим: отдельное окно с Mico, внизу быстрая панель -----
    def _enter_voice_inline(self):
        """Голосовой режим при открытой боковой панели: чат остаётся на месте, пропадают кнопки действий и выбор
        стиля, а Mico плавно переезжает в центр чата. Нижняя полоска с кнопками не нужна — микрофон в чате закончит режим."""
        self._voice_inline = True
        self.blob.keep_awake = True                           # чат открыт: Mico не засыпает, пока идёт разговор
        self.voice_dock.chat_open = True                      # субтитры идут перепиской в чате
        self.voice.set_session(True)
        self.voice.set_muted(False)
        if not self.voice.is_ready():
            self.voice.ensure_ready()
        self.voice_dock.clear_subs()
        self.voice_dock.refresh(self.voice.muted())
        self.aichat.set_voice_muted(False)
        self.aichat.set_voice_view(True)
        self._voice_rearm()

    def enter_voice_mode(self):
        """Микрофон в чате нажат: чат сворачивается, открывается окно с Mico и панелью, Mico слушает вопрос."""
        if getattr(self, "update_locked", False):                 # нужно обновление: вместо голоса — просьба обновить
            self.show_aichat()
            return
        if self.voice_mode:
            if getattr(self, "_voice_inline", False):
                self.exit_voice_mode()                        # микрофон в чате нажат ещё раз — голосовой режим заканчивается
            return
        self.voice_mode = True
        self._mico_hidden = False                             # голосовой режим: Mico снова на виду
        self.blob.keep_awake = False                          # голосовой режим: Mico может уснуть (в обводке)
        self.blob.touch()
        if self.blob.asleep:
            self.blob.wake(silent=True)
        self._show_blob()
        self._voice_rest = QPoint(self.blob.pos())            # где Mico стоял — туда вернётся после режима
        if self.aichat.isVisible() and self.aichat.side_panel():
            self._enter_voice_inline()                        # чат не трогаем: всё происходит внутри него
            return
        if self.aichat.isVisible():                           # чат не закрывается насовсем: он переедет над Mico в центре
            self.aichat._undock_blob()
            self.aichat.hide()
        self.voice_dock.chat_open = True                      # чат открыт над Mico: субтитры — перепиской в чате
        self.voice.set_session(True)                          # ответы говорим вслух, даже если озвучка выключена
        self.voice.set_muted(False)
        if not self.voice.is_ready():
            self.voice.ensure_ready()                         # голос и распознавание грузятся в фоне
        self.voice_dock.clear_subs()
        self.voice_dock.refresh(self.voice.muted())
        self.blob.voice_taps = True
        self.voice_dock.show_stage(self.blob)
        QTimer.singleShot(760, self._voice_chat_open)          # Mico доехал в центр — над ним открывается чат
        self._voice_rearm()

    def _voice_chat_open(self):
        """Голосовой режим: Mico в центре, над ним открыт чат, внизу — кнопки голосового режима.
        С субтитрами разговор выглядит как чат: слова человека появляются прямо пока он говорит."""
        if not self.voice_mode or self.voice_dock.in_pill():
            return
        self.aichat.voice_float = True                         # окно над Mico, а не боковая панель (она забрала бы Mico в шапку)
        self.voice_dock.chat_open = True
        self.voice_dock.clear_subs()
        self.aichat.show_near(self.blob, False)

    def _voice_chat_close(self):
        """Выход из голосового режима: чат над Mico убирается сразу, потом открывается обычный (или не открывается во сне)."""
        self.voice_dock.chat_open = False
        self.aichat.end_live_user()
        if self.aichat.isVisible():
            self.aichat.hide()
            self.aichat.setWindowOpacity(intel.chat_opacity(self.cfg))
        self.aichat.voice_float = False

    def _voice_partial(self, text):
        """Слова на ходу: с субтитрами они сразу видны — в чате (если он открыт) или в плашке над полоской."""
        inline = getattr(self, "_voice_inline", False)
        if not self.voice_mode or not (self.cfg.get("voice_chat_subs", True) if inline else self.cfg.get("voice_subs", False)):
            return
        if self.aichat.isVisible():
            self.aichat.live_user(text)
        self.voice_dock.show_user(text)

    def _text_default(self):
        """При запуске Mico AI открывается обычный текстовый чат, голос включается только по запросу."""
        if not self.cfg.get("tour_done") and not self.cfg.get("quiet_mode"):
            return
        if self.on() and not self.voice_mode and not self.quiet():
            self.show_aichat(activate=False)

    def exit_voice_mode(self, to_text=False):
        """Крестик: микрофон закрыт, Mico замолкает, окно гаснет, Mico возвращается на место, затем открывается чат.
        to_text — «хватит» или «переключись на текст»: Mico пропадает совсем, остаётся обычный чат."""
        if not self.voice_mode:
            return
        self.blob.touch()                                     # отсчёт до сна начинается заново, и до возврата Mico он не заснёт
        self.voice_mode = False
        if self.blob.asleep:
            self.blob.wake(silent=True)                       # Mico должен быть на виду, когда голосовой режим закрыт
        self.voice.stop_speaking()
        self.voice.stop_listening()
        self.voice.set_session(False)
        self.voice.set_muted(False)                           # микрофон как был: «мико», если он включён
        if getattr(self, "_voice_inline", False):             # режим шёл внутри чата: чат остаётся, Mico возвращается в шапку
            self._voice_inline = False
            self._voice_rest = None
            self.voice_dock.chat_open = False
            self.aichat.set_voice_view(False)
            self.blob.keep_awake = self.aichat.isVisible()
            return
        rest, self._voice_rest = self._voice_rest, None
        self.blob.keep_awake = False
        self.blob.voice_taps = False
        self._voice_chat_close()
        if to_text:
            self.voice_dock.dismiss(return_to=None, after=self._text_gone)
        else:
            self.voice_dock.dismiss(return_to=rest, after=self._voice_gone)

    def _text_gone(self):
        """Текстовый режим: голос выключен, открывается обычный чат. Mico остаётся на виду (раньше он пропадал совсем)."""
        self._mico_hidden = False
        self._show_blob()
        self.show_aichat()

    def _blob_tapped(self):
        """Нажали на Mico в голосовом режиме: чат не открываем. Mico радуется, а если нажимают часто — просит не спешить."""
        if not self.voice_mode or self.voice_dock.in_pill():
            return
        now = time.time()
        self._taps = [t for t in self._taps if now - t < intel.TAP_WINDOW_SEC] + [now]
        self.blob.touch()
        if len(self._taps) >= intel.TAP_LIMIT and now - self._tap_warn_at > intel.TAP_WARN_GAP_SEC:
            self._tap_warn_at = now
            self._taps = []
            self.blob.set_mood("shy", 4)
            self.blob.jump(120)
            self.voice_dock.show_mico(intel.TAP_WARNING)            # чат свёрнут — просьба идёт в субтитры и голосом
            self.voice.speak(intel.TAP_WARNING, "shy")
            return
        self.blob.set_mood("excited", 2.5)                          # веселая реакция на нажатие
        self.voice_dock.toggle_detach()                             # без прыжка: Mico аккуратно выезжает сам                             # один клик: Mico выпрыгивает из полоски или возвращается

    def _voice_slept(self):
        """Mico уснул в голосовом режиме: голосовой режим закрывается, Mico уходит в обычный сон на рабочем столе."""
        if not self.voice_mode:
            return
        rest, self._voice_rest = self._voice_rest, None
        self.voice_mode = False                                # без пробуждения и без открытия чата: это обычный сон
        self.voice.stop_speaking()
        self.voice.stop_listening()
        self.voice.set_session(False)
        self.voice.set_muted(False)
        self.blob.keep_awake = False
        self.blob.voice_taps = False
        self._voice_chat_close()
        self.voice_dock.dismiss(return_to=rest, after=None)   # полоска гаснет, Mico едет на свой угол сна

    def _voice_woke(self):
        """Mico проснулся (нажали на него): полоска возвращается."""
        if self.voice_mode:
            self.voice_dock.expand_pill()

    def _voice_gone(self):
        """Mico уже на месте — открываем чат Mico AI."""
        self.blob.touch()
        self.show_aichat()

    def _voice_chat_subs_toggle(self, on):
        """Субтитры в чате: слова человека появляются пузырём в ленте, пока он говорит."""
        self.cfg["voice_chat_subs"] = bool(on)
        self._save()

    def _voice_subs_toggle(self, on):
        """Кнопка субтитров: запоминаем выбор, чтобы при следующем голосовом режиме субтитры были включены."""
        self.cfg["voice_subs"] = bool(on)
        self._save()

    def _voice_rearm(self):
        """Снова слушаем, когда Mico ответил и замолчал. Пока он думает или говорит — не слушаем."""
        if not self.voice_mode or self.panel.busy or self.voice.is_speaking():
            return
        self.voice.begin_listening()

    def _on_voice_speaking(self, on):
        if not on and self.voice_mode:
            QTimer.singleShot(350, self._voice_rearm)

    def _voice_mute_toggle(self):
        """Кнопка микрофона: выключить или снова включить. Включили — сразу слушаем."""
        on = not self.voice.muted()
        self.voice.set_muted(on)
        self.blob.keep_awake = on                           # микрофон выключен — Mico не засыпает и остаётся на виду
        self.voice_dock.refresh(on)
        self.aichat.set_voice_muted(on)                     # значок микрофона в чате
        if not on:
            self._voice_rearm()

    def _voice_toggle(self, on):
        if on:
            self.notify("Озвучиваю ответы. Голос скачается один раз, около 60 МБ.", "tip")
        self.voice.set_enabled(on)
        self._save()

    def _voice_pick(self, name):
        self.voice.set_voice(name)
        self._save()

    def _voice_speed_pick(self, speed):
        """Скорость речи из кнопки настроек: следующая фраза уже идёт с новой скоростью."""
        self.cfg["voice_speed"] = float(speed)
        self._save()

    def _voice_heard(self, text):
        """В режиме «мико» показываем, что распознано: так видно, слышит ли Mico вообще и как записалось слово."""
        self.aichat.inp.setPlaceholderText(f"Слышу: «{text[:60]}»" if text else "Слышу тишину…")

    def _voice_status(self, text):
        """Статус голоса: в строке ввода, а в голосовом режиме — под Mico. Ошибки — в чате."""
        self.aichat.inp.setPlaceholderText(text or "Напиши Mico AI…")
        self.aichat.set_voice_status(text)                       # в голосовом чате: процент и полоска над кнопками
        if self.voice_mode:
            self.voice_dock.set_status(text)
        if text.startswith("Голос не") or text.startswith("Микрофон не"):
            self.notify(text, "worried")
        if self.voice_mode and text.startswith(("Не расслышал", "Не разобрал", "Голос не распознал")):
            self.aichat.end_live_user()
            QTimer.singleShot(400, self._voice_rearm)         # вопрос не разобрали — снова слушаем

    def _on_wake(self, rest):
        """Услышали «мико!»: сразу открываем голосовой чат. Если вопрос сказан в той же фразе — он уходит ответом."""
        if self.voice_mode:
            if self.voice_dock.in_pill():                      # спал в обводке — будим и разворачиваем полоску
                self.blob.wake(silent=True)
                self.voice_dock.expand_pill()
            return
        self.enter_voice_mode()
        if rest:
            QTimer.singleShot(700, lambda: self._on_send(rest))      # сначала режим откроется, потом вопрос

    def _on_voice_said(self, text):
        """Фраза из микрофона. «Хватит» в голосовом режиме — завершаем его, всё остальное — вопрос."""
        self.blob.touch()                                       # говорят — Mico не засыпает
        self.aichat.end_live_user()                             # живой пузырь сменяется итоговой фразой
        from voice.text import is_stop_phrase
        if self.voice_mode and is_stop_phrase(text):
            self.voice_dock.show_mico("Хорошо, переключаюсь на текст 👋")
            self.exit_voice_mode(to_text=True)
            return
        if self.voice_mode and self.voice_dock.in_pill():      # вопрос во сне — будим Mico и отвечаем
            self.blob.wake(silent=True)
            self.voice_dock.expand_pill()
        self._on_send(text)

    def _voice_listening(self, on):
        self.blob.set_listening(on)                             # мимика: внимательно слушает
        if on and not self.blob.asleep:                         # во сне настроение не меняем: Mico спит
            self.blob.set_mood("curious", 3)           # слушает — смотрит на строку ввода

    def _chat_activity(self):
        """Человек пишет или нажимает в чате: Mico AI рядом и не засыпает."""
        self.blob.touch()
        if self.blob.asleep and not self._mico_hidden:
            self.blob.wake(silent=True)

    def rewrite(self, mode):
        """«Короче» или «Подробнее» для последнего ответа. Не пишется в память разговора."""
        try:
            if not self._last_answer:
                self.aichat.add_mico("Нечего переписать: сначала задай вопрос.")
                return
            if mode not in intel.REWRITE_PROMPTS:
                return
            self.quick(intel.REWRITE_LABELS[mode], intel.REWRITE_PROMPTS[mode] + self._last_answer[:3000])
        except Exception as e:
            self.aichat.add_mico(f"Не получилось переписать ответ: {e}")

    def set_dnd(self, minutes):
        """«Не беспокоить» на N минут: Mico AI молчит сам. 0 — снова можно."""
        if minutes <= 0:
            self.dnd_until = 0
            self.aichat.add_mico("Снова могу подсказывать сам.")
            return
        self.dnd_until = time.time() + minutes * 60
        until = time.strftime("%H:%M", time.localtime(self.dnd_until))
        self.aichat.add_mico(f"Не буду беспокоить до {until}. Если спросишь сам — отвечу.")

    def set_load(self, percent):
        """Загрузка процессора: тонкая линия внизу, если это включено и Mico AI не молчит по расписанию."""
        want = self.on() and self.cfg.get("wi_load_bar") and not self.hushed() and not self.quiet()
        if not want:
            if self.load_bar.isVisible():
                self.load_bar.hide_bar()
            return
        self.load_bar.set_target(percent)

    def break_note(self, text):
        """Напоминание о перерыве. Сводку за час не добавляем."""
        self.notify(text, "break")

