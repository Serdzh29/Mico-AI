"""Окна Mico AI (Windows Intelligence): полоса по краю экрана, волны при ответе, строка ответа над Mico AI,
кнопки под ней и переходы Mico. Все окна не забирают фокус (кроме собственного чата Mico AI). Полоса пропускает клики.
Расчёты — в intel.py; здесь рисование, анимации и связь с чатом. В полноэкранном режиме Mico AI молчит."""
from energy import GLOW_MS, LOAD_MS
import base64
import math
import os
import threading
import time

from PyQt6.QtCore import (QAbstractAnimation, QObject, Qt, QTimer, QRectF, QPoint, QPointF, QPropertyAnimation,
                          QEasingCurve, pyqtSignal)
from PyQt6.QtGui import (QAction, QBrush, QColor, QGuiApplication, QLinearGradient, QPainter, QPainterPath)
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QToolButton,
                             QVBoxLayout, QWidget)

import clipbuf
import errhelp
import errwatch
import filereader
import intel
import sleepmode
import theme
from wichat import WiChat


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
        bh = intel.glow_height(self.cfg)                          # высота свечения внизу, px
        breathe = 0.85 + 0.15 * math.sin(self.phase)              # дыхание: едва заметно
        strength = (0.22 + 0.10 * self.wave) * breathe            # во время ответа — ярче
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

    def _draw_waves(self, p, w, h, bh, rgb):
        """Две волны: передняя плотнее и ближе к краю, задняя светлее и выше. Кривые плавные (квадратичные
        дуги между серединами отрезков), без углов. В покое — пульсация, при ответе — подъёмы в нескольких местах.
        Цвет — из настроек волн (rgb), а не от состояния: готовый набор не откатывается через секунду."""
        n = max(40, int(w / 9))
        r, g, b = rgb

        scale = intel.wave_height(self.cfg) / 100.0                       # толщина волн из настроек
        max_px = h * 0.33                                                 # волна не выше трети экрана

        def layer(offset, amp, a_top, a_bot):
            heights = intel.wave_profile(n, self.phase + offset, answer=self.wave)
            top_px = min(bh * amp * scale, max_px)
            pts = [(w * i / (n - 1), h - hv * top_px) for i, hv in enumerate(heights)]
            path = QPainterPath()
            path.moveTo(0, h)
            path.lineTo(pts[0][0], pts[0][1])
            for i in range(1, len(pts)):
                x0, y0 = pts[i - 1]
                x1, y1 = pts[i]
                path.quadTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2)
            path.lineTo(pts[-1][0], pts[-1][1])
            path.lineTo(w, h)
            path.closeSubpath()
            grad = QLinearGradient(QPointF(0, h), QPointF(0, h - top_px))
            grad.setColorAt(0.0, QColor(r, g, b, a_bot))
            grad.setColorAt(1.0, QColor(r, g, b, a_top))
            p.fillPath(path, QBrush(grad))

        k = max(0.0, min(1.0, float(self.cfg.get("wave_opacity", 85)) / 100.0))   # 0 — невидимы, 100 — непрозрачны
        layer(1.7, 0.6, round(90 * k), round(255 * k))     # задняя: светлее и выше
        layer(0.0, 0.85, round(150 * k), round(255 * k))   # передняя: плотнее, ближе к краю


class Island(QWidget):
    """Капсула рядом с Mico AI (слева): цветная точка и короткая строка о том, что он делает.
    Выезжает из Mico AI, когда он ждёт, думает или отвечает; цвет — цвет действия из настроек."""
    W, H = 260, 34

    def __init__(self, cfg, blob):
        super().__init__(None, _window_flags() | Qt.WindowType.WindowTransparentForInput)
        self.cfg = cfg
        self.blob = blob
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.resize(self.W, self.H)
        self.text, self.rgb = "", intel.hex_rgb(intel.state_color(cfg, "listen"))
        self.level, self.target = 0.0, 0.0                                  # видна ли капсула
        self.wk, self.target_w = 0.0, 0.0                                   # насколько раскрыта строка
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(GLOW_MS)
        self.timer.timeout.connect(self._tick)

    def show_state(self, state, label=None):
        self.rgb = intel.hex_rgb(intel.state_color(self.cfg, state))
        self.text = label or intel.STATE_TEXT.get(state, "")
        self.target, self.target_w = 1.0, (1.0 if self.text else 0.0)
        if not self.isVisible():
            self.show()
        if not self.timer.isActive():
            self.timer.start()
        self._place()

    def hide_state(self):
        self.target, self.target_w = 0.0, 0.0

    def _place(self):
        """Слева от Mico AI, по его середине. Чат Mico AI открывается над Mico AI — капсула ему не мешает."""
        if not self.blob.isVisible():
            return
        x = self.blob.x() - self.W + 8
        y = self.blob.y() + self.blob.height() // 2 - self.H // 2
        self.move(x, y)

    def _tick(self):
        self.phase += 0.08
        self.level = intel.approach(self.level, self.target, 0.18)
        self.wk = intel.approach(self.wk, self.target_w, 0.18)
        self._place()
        if self.level <= 0.0 and self.target <= 0.0:
            self.timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, e):
        if self.level <= 0.0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.level)
        font = self.font()
        font.setPixelSize(13)
        p.setFont(font)
        tw = p.fontMetrics().horizontalAdvance(self.text) if self.text else 0
        dot, pad, gap = 8, 14, 7
        width = pad * 2 + dot + (gap + tw) * self.wk
        x0 = self.W - 4 - width                                          # капсула прижата к Mico AI
        rect = QRectF(x0, 3, width, self.H - 6)
        dark = theme.is_dark(self.cfg)
        bg = QColor(24, 22, 28, 226) if dark else QColor(255, 252, 245, 236)
        fg = QColor(239, 233, 223) if dark else QColor(43, 33, 24)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        r, g, b = self.rgb
        pulse = 4 + 0.6 * math.sin(self.phase)
        p.setBrush(QColor(r, g, b, 235))
        p.drawEllipse(QPointF(x0 + pad + dot / 2, self.H / 2), pulse, pulse)
        if self.wk > 0.01 and self.text:
            fg.setAlphaF(min(1.0, self.wk))
            p.setPen(fg)
            p.drawText(QRectF(x0 + pad + dot + gap, 0, tw + 4, self.H),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text)
        p.end()


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
        self.wichat = WiChat(cfg)
        import brain as _brain                     # модели Ollama: список и память
        self.wichat.models_provider = _brain.list_models
        self.wichat.model_pick.connect(self._pick_model)
        self.wichat.send.connect(self._on_send)
        self.wichat.closed.connect(self._wichat_closed)
        self.wichat.dnd.connect(self.set_dnd)
        self.wichat.rewrite.connect(self.rewrite)
        self.wichat.file_cleared.connect(self._clear_file)
        self.load_bar = LoadBar(cfg)
        self.dnd_until = 0                      # «не беспокоить» до этого времени (0 — не включено)
        self._file = None                       # файл, о котором спрашивают в чате Mico AI (только в памяти)
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

    def on(self):
        return intel.style_of(self.cfg.get("assist_style")) == intel.INTELLIGENCE

    def restyle(self):
        """Сменили цвет Mico AI или тему: строка и чат Mico AI перекрашиваются сразу, без перезапуска."""
        self.wichat._apply_style()

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
        try:
            return float(self.cfg.get("opacity", 1.0))
        except (TypeError, ValueError):
            return 1.0

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
        self.wichat.dismiss()
        self.load_bar.hide_bar()
        self.glow.keep = False
        ms = int(intel.LEAVE_SEC * 1000)
        self.glow.sweep(intel.LEAVE_SEC, "listen", goal=0.0)           # полоска стягивается обратно
        QTimer.singleShot(ms + 60, lambda: self.glow.set_on(False))
        self.blob.locked = False                                       # Mico AI поедет в свой угол сам (_glide)
        self._show_blob()

    def _tour(self, lines, i):
        """Mico AI по порядку рассказывает о Mico AI в своём чате. Закрыли чат — тур прекращается."""
        if not self.on() or (i and not self.wichat.isVisible()):
            return
        if i >= len(lines):
            self.glow.set_on(True, "listen")              # тур кончился, чат открыт — полоса горит дальше
            return
        self.show_wichat(activate=False)
        self.wichat.set_busy(True)
        QTimer.singleShot(400 if i == 0 else intel.TOUR_GAP_MS, lambda: self._tour_say(lines, i))

    def _tour_say(self, lines, i):
        if not self.on():
            return
        self.wichat.set_busy(False)
        self.wichat.add_mico(lines[i])
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
        """Mico AI уснул: в Mico AI он плавно уходит вниз и растворяется, а не прячется в угол."""
        if not self.on():
            return
        self.wichat.dismiss()                                    # Mico AI уходит — и его чат уходит вместе с ним
        start = QPoint(self.blob.pos())
        self.blob.locked = True
        self._drop = self._run(self.blob, b"pos", start, start + QPoint(0, intel.SLEEP_DROP_PX), 900)
        self._fade_out = self._run(self.blob, b"windowOpacity", self.blob.windowOpacity(), 0.0, 900,
                                   after=self._gone)

    def _gone(self):
        self.blob.locked = False
        if self.blob.windowOpacity() <= 0.01:
            self.blob.hide()
            self.blob.setWindowOpacity(self._base_opacity())
            self.blob.move(self._spot())                    # на месте: при возвращении поднимется снизу

    # ----- свой чат Mico AI -----
    def show_wichat(self, activate=True):
        self.wichat.refresh_model_info()           # кнопка модели показывает точное имя модели
        """Открывает чат Mico AI над Mico. Mico AI при этом ждёт: полоса горит."""
        self.blob.touch()
        if self.blob.asleep:
            self.blob.wake(silent=True)
        self._show_blob()
        if not self.wichat.isVisible():
            self.glow.set_on(True, "listen")
        self.wichat.show_near(self.blob, activate)

    def toggle_wichat(self):
        if self.wichat.isVisible():
            self.wichat.dismiss()
        else:
            self.show_wichat()

    def _wichat_closed(self):
        if self.on():
            if self.panel.busy:
                self.glow.set_on(True, "think")
            else:
                self.glow.set_on(False)

    def wi_user(self, q):
        """Вопрос пользователя (из чата или горячей клавиши) — в чат Mico AI короткой подписью."""
        self.wichat.add_user(self._labels.pop(q, q))

    def wi_mico(self, text):
        """Текст Mico AI (ответ, напоминание, приветствие) — в чат Mico AI."""
        self.wichat.add_mico(text)

    def busy(self, on):
        """Mico AI думает: полоса горит цветом «думает». Чат Mico AI показывает, что Mico AI печатает."""
        if not self.on():
            return
        self.wichat.set_busy(on)
        self.glow.keep = bool(on) and not self.quiet()           # думает — полоска горит до ответа
        if on and not self.blob.asleep:
            self.blob.set_mood("thinking")                       # Mico AI показывает своё «думаю», а не точки в чате
        elif not on and self.blob.mood == "thinking":
            self.blob.set_mood("idle")
        if self.quiet():
            return
        if on:
            self.glow.set_on(True, "think")
        elif self.wichat.isVisible():
            self.glow.set_on(True, "listen")
        else:
            self.glow.pulse(1.0, "think")

    def answer(self, text):
        """Ответ пришёл: Mico AI говорит — полоса волнуется. Короткий — строкой над Mico AI, длинный — открываем чат.
        В полноэкранном режиме тихо: ответ останется в чате."""
        if not self.on() or not text or self.quiet():
            return
        self._last_answer = text
        self.wichat.show_rewrite_row()
        secs = intel.speak_seconds(text)
        self.glow.wave_for(secs)
        if self.wichat.isVisible():                      # чат открыт: полоса горит, пока он открыт
            self.glow.set_on(True, "listen")
            return
        self.glow.pulse(secs + 0.5, "think", label="отвечаю…")
        if intel.opens_chat(text):
            self.show_wichat(activate=False)
            return
        self.show_wichat(activate=False)

    def _pick_model(self, name):
        """Смена модели прямо в чате: следующий ответ пойдёт ею. Выбор сохраняем в настройках."""
        self.cfg["text_model"] = name
        try:
            self.panel.brain.save_cfg()
        except Exception:
            pass
        self.wichat.refresh_model_info()
        self.notify(f"Теперь отвечаю моделью {name}. Первый ответ может занять время: модель загружается в память.", "tip")

    def notify(self, text, state="tip"):
        """Mico AI сам что-то сообщает: перерыв, наблюдение, проблема, приветствие. Цвет полоски — по причине.
        Текст всегда попадает в чат Mico AI; строкой над Mico AI показываем, если чат закрыт."""
        if not self.on() or not text:
            return
        self.wichat.add_mico(text)
        if self.hushed():
            return
        if self.wichat.isVisible():
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

    def screen_hotkey(self):
        """Горячая клавиша «Что на экране?»: скриншот и ответ моделью для экрана."""
        if self.gate():
            self.ask(intel.SCREEN_QUESTION, "Что на экране?")

    def window_hotkey(self, title):
        """Горячая клавиша «Помочь с окном»: подсказка по программе, которой пользуешься сейчас."""
        if self.gate():
            self.ask(intel.window_question(title), "Помочь с окном")

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
        self.wichat.add_user(label)
        self.wichat.set_busy(True)
        self.glow.keep = True
        self.glow.set_on(True, "think")
        if self.blob.isVisible():
            self.blob.set_mood("thinking")          # тело Mico думает: над головой мигают три точки

        def work():
            try:
                text = self.panel.brain.quick_answer(prompt, image)
            except Exception as e:
                text = f"Не получилось ответить: {e}"
            self._bridge.done.emit(text or "Ответа нет.")
        threading.Thread(target=work, daemon=True).start()

    def _quick_done(self, text):
        self.glow.keep = False
        self.wichat.set_busy(False)
        if self.blob.isVisible() and self.blob.mood == "thinking":
            self.blob.set_mood("idle")              # ответ готов — точки уходят
        self.wichat.add_mico(text)
        self.answer(text)

    def _error_options(self, title, text):
        """Варианты под предложением о любой ошибке: объяснить или найти решение."""
        return [("Объяснить", lambda: self.quick(f"Объяснить ошибку: {title}", intel.explain_prompt(text))),
                ("Найти решение", lambda: self.quick(f"Найти решение: {title}", errhelp.solution_prompt(title, text)))]

    def _offer(self, text, options, state="warn"):
        """Mico AI сам предлагает помощь: текст в чат и кнопки с вариантами под ним. «Не сейчас» — убрать кнопки."""
        self.wichat.add_mico(text)
        self.wichat.show_offer_row(list(options) + [("Не сейчас", None)])
        self.glow.pulse(4.0, state)
        if not self.wichat.isVisible():
            self.show_wichat(activate=False)

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

    def file_dropped(self, paths):
        """Файл перетащили на Mico AI: Mico AI перескажет текст или опишет картинку и запомнит файл —
        дальше в чате Mico AI можно задавать вопросы по нему. Только Mico AI."""
        if not paths or not self.gate():
            return
        path = paths[0]
        name = os.path.basename(path)
        kind = filereader.kind(path)
        if kind == "image":
            try:
                with open(path, "rb") as f:
                    img = base64.b64encode(f.read()).decode()
            except OSError:
                self.notify("Не получилось открыть картинку.", "tip")
            else:
                self._file = {"name": name, "text": "", "image": img, "ts": time.time()}
                self.wichat.set_file(name)
                self.quick(f"Картинка: {name}", intel.IMAGE_PROMPT, image=img)
        elif kind == "text":
            text = filereader.read_text(path)
            if text:
                self._file = {"name": name, "text": text, "image": None, "ts": time.time()}
                self.wichat.set_file(name)
                self.quick(f"Файл: {name}", intel.file_prompt(name, text))
            else:
                self.notify("Не получилось прочитать этот файл: он пустой или не текстовый.", "tip")
        else:
            self.notify(intel.FILE_UNSUPPORTED, "tip")
        if len(paths) > 1:
            self.notify("Пока разбираю только первый файл.", "tip")

    def _on_send(self, text):
        """Сообщение из чата Mico AI: если открыт файл — вопрос по нему, иначе обычный разговор."""
        if self._file is not None and self.on():
            self._file["ts"] = time.time()
            f = self._file
            if f["image"]:
                self.quick(text, intel.IMAGE_CHAT_PROMPT.format(question=text), image=f["image"])
            else:
                self.quick(text, intel.FILE_CHAT_PROMPT.format(name=f["name"], text=filereader.excerpt(f["text"], text, 6000), question=text))
            return
        self.panel.submit(text)

    def _clear_file(self):
        self._file = None
        self.wichat.set_file(None)

    def expire_file(self, now):
        """Файл забываем, если о нём долго не спрашивали."""
        if self._file is not None and now - self._file["ts"] > intel.FILE_TTL_SEC:
            self._clear_file()

    def rewrite(self, mode):
        """«Короче» или «Подробнее» для последнего ответа. Не пишется в память разговора."""
        if not self._last_answer or mode not in intel.REWRITE_PROMPTS:
            return
        self.quick(intel.REWRITE_LABELS[mode], intel.REWRITE_PROMPTS[mode] + self._last_answer[:3000])

    def set_dnd(self, minutes):
        """«Не беспокоить» на N минут: Mico AI молчит сам. 0 — снова можно."""
        if minutes <= 0:
            self.dnd_until = 0
            self.wichat.add_mico("Снова могу подсказывать сам.")
            return
        self.dnd_until = time.time() + minutes * 60
        until = time.strftime("%H:%M", time.localtime(self.dnd_until))
        self.wichat.add_mico(f"Не буду беспокоить до {until}. Если спросишь сам — отвечу.")

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

