"""Mico AI: мягкий blob с эмоциями, анимациями ожидания (моргает, крутится, становится сердечком),
анимацией «думает» и взглядом вниз, пока пользователь печатает."""
from energy import FRAME_MS
import math, random, time
import intel
import sleepmode
import theme                        # шрифты Mico AI: Segoe UI Variable и Nunito Bold для значков
from voice_text import mouth_for_level            # рот по громкости настоящей речи
from PyQt6.QtCore import Qt, QTimer, QPointF, QPoint, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPainterPath, QPen, QCursor, QGuiApplication, QFont
from PyQt6.QtWidgets import QWidget


from emotions import VALID as MOODS                # одна правда: все эмоции, которые можно выбрать
from shapes import HEART as HEART_PTS             # сглаженное сердце (см. shapes.py)
HEAD_TILT_MAX = 7.0                    # больше этого угла голова не наклоняется (градусы): иначе выглядит неестественно
TILT = {"curious": 7, "sad": -4, "worried": -3, "thinking": 4, "proud": -6, "playful": 5, "confused": 6}
N = 96


def pebble(a, wob, t, morph=1.0):
    """Асимметричная форма-«камушек» как на референсе. Гармоники медленно «плывут» (morph),
    поэтому силуэт всё время перетекает: то яйцо, то округлый треугольник — как в видео."""
    k = morph
    r = (1.0 + (0.085 + 0.025 * k * math.sin(t * 0.35)) * math.sin(2 * a + 0.9 + 0.55 * k * math.sin(t * 0.23))
         + (0.055 + 0.02 * k * math.sin(t * 0.41 + 1.0)) * math.sin(3 * a + 2.1 + 0.6 * k * math.sin(t * 0.31 + 2.0))
         + 0.025 * math.sin(5 * a + 0.3 * k * math.sin(t * 0.5)))
    return r + wob * (0.012 * math.sin(3 * a + t * 2) + 0.01 * math.sin(4 * a - t * 1.6))


# положения рта при речи: (полуширина, высота) в долях R. Закрытых больше: между слогами рот смыкается
VISEMES = [(0.12, 0.0), (0.12, 0.0), (0.08, 0.075), (0.12, 0.115), (0.17, 0.07), (0.07, 0.045),
           (0.15, 0.135), (0.11, 0.03), (0.19, 0.10), (0.09, 0.09)]


def ease_out_back(x):
    """Плавный «выскок» с лёгким перелётом — так Mico появляется."""
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def smooth(x):
    """Плавный переход 0→1 без рывков на краях (для переливания цвета)."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def mix(c1, c2, k):
    return QColor(int(c1.red() * (1 - k) + c2.red() * k), int(c1.green() * (1 - k) + c2.green() * k),
                  int(c1.blue() * (1 - k) + c2.blue() * k))


BASE_PX = 300                        # базовый размер Mico AI в пикселях при масштабе 100%; чат — 360×430


class Blob(QWidget):
    clicked = pyqtSignal()
    settings_requested = pyqtSignal()        # двойной щелчок левой кнопкой — настройки
    menu_requested = pyqtSignal(QPoint)
    moved = pyqtSignal()
    slept = pyqtSignal()                  # Mico AI заснул: чат нужно спрятать
    woke = pyqtSignal()                   # Mico AI проснулся от клика: чат нужно вернуть
    awake = pyqtSignal()                  # Mico AI проснулся по любой причине (клик, чат, Mico AI): островок сна убирается
    dropped = pyqtSignal(list)            # на Mico AI перетащили файлы (пути) — Mico AI читает их
    tapped = pyqtSignal()                 # каждое нажатие левой кнопкой (в т.ч. быстрые, двойным щелчком) — для голосового режима
    color_set = pyqtSignal(str)           # цвет из палитры уже применён (посреди поворота): main сохраняет и перекрашивает чат
    # состояние «живой» анимации: значения по умолчанию, чтобы всё работало и без полной инициализации
    mw, mh, mtilt = 0.10, 0.0, 0.0                    # рот: полуширина, высота, наклон
    viseme, viseme_until, next_talk_anim = (0.10, 0.0), 0.0, 0.0
    brow_l = brow_r = brow_tl = brow_tr = 0.0         # брови: подъём и наклон (в долях R)
    brow_gl = brow_gr = brow_gtl = brow_gtr = 0.0
    brow_until = 0.0
    face_dx = face_dy = face_gx = face_gy = 0.0       # лицо «ездит» по телу
    face_until = 0.0
    emph = emph_goal = emph_until = 0.0               # акценты речи: брови вверх, глаза крупнее
    next_emph = 0.0
    talk_amt = 0.0                                    # 0..1: насколько Mico сейчас разговорчив
    eye_k = 1.0
    _tilt_dir = 1
    voice_level = None                    # громкость настоящей речи 0..1; None — голоса нет, рот «по-старому»
    voice_active = False                  # Mico сейчас говорит голосом (чат не должен гасить рот по таймеру)
    listen_voice = False                  # Mico внимательно слушает пользователя: голова набок, глаза чуть больше, брови вверх
    _pending_color = None                 # цвет из палитры, который Mico примерит на середине поворота
    _col_from = None                      # цвет, с которого плавно переливаемся во второй половине поворота
    WAKE_SETTLE_MS = 650                  # после пробуждения прыжок длится около полсекунды: чат открываем после него

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.t0 = time.time()
        self._fonts = {}                                   # шрифты кешируем, а не создаём каждый кадр
        self.mood, self.mood_until = "idle", 0
        self.anim = None                      # (имя, старт, длительность)
        self.next_idle = time.time() + 6
        self.typing_until, self.talking = 0, False
        self.vx = self.vy = self.dvx = self.dvy = 0.0
        self.drag, self.moved_px, self.last_move = None, 0, (None, 0)
        self.squash = self.squash_v = 0.0
        self.jh = self.jv = 0.0               # прыжок
        self.heart = self.tilt = 0.0
        self.lean = 0.0                       # наклон при движении к углу
        self.look_at = None                   # глобальная точка, на которую смотрит Mico AI (строка ввода)
        self._fx, self._fy, self._last_glide = 0.0, 0.0, time.time()   # плавные (дробные) координаты
        self.blink_at, self.blink_until, self.blink_start = time.time() + 3, 0, 0
        self.lid = 1.0                        # открытость глаз: 1 — открыты, меньше — прикрыты (плавно, без рывков)
        self.locked = False                   # на время перехода Mico AI движением управляет Intel, а не _glide
        self.last_cursor, self.last_input = QCursor.pos(), time.time()
        self.asleep = False                   # спит ли Mico AI
        self.size_k = 1.0                     # доля размера: 1 — обычный, sleepmode.SLEEP_SCALE — во сне
        self.morphing = False                 # переезд в голосовую полоску: размер меняется вокруг центра
        self.voice_k = None                   # голосовой режим: доля размера, которую держим (None — обычный размер)
        self.rest_pos = None                  # где Mico AI стоял до сна — туда вернётся
        self.last_attention = time.time()     # когда к нему обращались в последний раз
        self.can_sleep = lambda: True         # main подставит: нет ли открытого разговора
        self.keep_awake = False               # голосовой режим: Mico не засыпает и не выглядит сонным
        self.voice_taps = False               # голосовой режим: двойной щелчок не открывает настройки, а считается нажатием
        self._fade = None                     # текущее проявление/растворение
        self.apply_config()
        self.start_anim("appear")             # при запуске Mico «выскакивает» из ничего
        self.timer = QTimer(self)
        # точный таймер: на Windows обычный даёт кадры неровно (рывки), точный — ровный ритм анимации
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.setInterval(FRAME_MS)      # ~120 кадров в секунду: как и раньше, плавно
        self.timer.start()
        self._click_timer = QTimer(self)      # одинарный щелчок ждёт паузы: вдруг это двойной
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self.clicked.emit)

    # ---------- API ----------
    def apply_config(self):
        s = self._size_px()
        self.setFixedSize(s, s)
        self._apply_opacity()
        self.update()

    def _apply_opacity(self):
        """Прозрачность из настроек — на рабочем столе. В голосовом режиме Mico в полоске всегда яркий:
        иначе при движении ползунков в настройках он сереет."""
        self.setWindowOpacity(1.0)                # прозрачности нет

    def _size_px(self):
        return max(1, int(BASE_PX * self.cfg["scale"] * self.size_k))

    def touch(self):
        """К Mico AI обратились: отсчёт до сна начинается заново."""
        self.last_attention = time.time()

    def _sleep_limit(self):
        return sleepmode.limit_seconds(self.cfg.get("sleep_after_min", sleepmode.DEFAULT_MINUTES))

    def sleep_now(self):
        """Засыпает: запоминает место, мрачнеет лицом, сообщает чату, что пора спрятаться."""
        if self.asleep or self.keep_awake:
            return
        self.rest_pos = QPoint(self.pos())
        self.asleep = True
        self.timer.setInterval(self._sleep_interval())   # во сне — частота из настроек
        self.mood, self.mood_until = "sleepy", 0
        self.slept.emit()

    def placement(self):
        """Где Mico AI стоит по настройкам: в режиме Windows Intelligence — внизу по центру."""
        return intel.placement_for(self.cfg.get("assist_style"), self.cfg.get("placement"))

    def _sleep_interval(self):
        """Миллисекунды между кадрами во сне: из настройки «Частота анимации во сне»."""
        fps = max(1, int(self.cfg.get("anim_sleep_fps", 20)))
        return max(8, round(1000 / fps))

    def wake(self, silent=False, moved=False):
        """Просыпается: возвращается на прежнее место (если его не перетащили), радуется и открывает чат."""
        if not self.asleep:
            return
        self.asleep = False
        self.locked = False
        self.timer.setInterval(FRAME_MS)
        self.touch()
        if not moved and self.rest_pos is not None and sleepmode.home_corner(False, self.placement(), None) is None:
            self.move(self.rest_pos)            # на прежнее место; если выбран угол — плавно доведёт до него _glide
        self.rest_pos = None
        self.set_mood("happy", 5)
        self.jump(260)
        self.squash_v += 0.8
        self.awake.emit()
        if not silent:
            self.woke.emit()

    def set_mood(self, mood, secs=None):
        self.mood = mood if mood in MOODS else "idle"
        if self.mood == "proud":                           # гордится: чуть выпрямляется и подпрыгивает
            self.jump(140)
        self.mood_until = time.time() + secs if secs else 0
        self.last_input = time.time()

    def jump(self, power=280):
        self.jv = power

    def set_speaking(self, on):
        """Голос начал или закончил говорить: рот двигается в такт звуку, пока идёт речь."""
        self.voice_active = bool(on)
        self.talking = bool(on)
        if not on:
            self.voice_level = None

    def set_listening(self, on):
        """Слушает голос: как на видео — голова чуть набок, глаза крупнее, брови приподняты."""
        self.listen_voice = bool(on)

    def set_voice_level(self, level):
        """Громкость звука в этот момент — по ней открывается рот."""
        self.voice_level = float(level)

    def pick_color(self, hex_color):
        """Цвет из палитры в чате: Mico крутится, на середине поворота меняет цвет,
        а вторая половина поворота плавно переливает его, как в видео. Тот же цвет — ничего не делает."""
        if not hex_color or hex_color.upper() == str(self.cfg.get("color", "")).upper():
            return
        if self.asleep:
            self.wake(silent=True)
        self._pending_color = hex_color.upper()
        self.start_anim("spin")

    def _commit_color(self):
        """Применяет цвет из палитры: запоминает старый для переливания и сообщает main, что цвет сменился."""
        self._col_from = QColor(self.cfg["color"])
        self.cfg["color"] = self._pending_color
        self._pending_color = None
        self.color_set.emit(self.cfg["color"])

    def set_look(self, global_point):
        """Куда смотреть (глобальные координаты), например на строку ввода."""
        self.look_at = global_point

    def _glide(self, now):
        """Плавно едет в свой угол (во сне — угол для сна, иначе — выбранное положение). Возвращает наклон (lean)."""
        dt = min(0.05, max(0.001, now - self._last_glide))
        self._last_glide = now
        if self.drag is not None or self.locked or abs(self.x() - self._fx) > 3 or abs(self.y() - self._fy) > 3:
            self._fx, self._fy = float(self.x()), float(self.y())      # перетащили или сдвинули сами
        if self.locked:                                  # переход Mico AI ведёт Intel: здесь не двигаем
            return 0.0
        corner = sleepmode.home_corner(self.asleep, self.placement(), self.cfg.get("sleep_corner"))
        if corner is None or self.drag is not None:      # стоит, где поставил, или его сейчас тащат
            return 0.0
        target = QPoint(*sleepmode.corner_spot(self._screen_avail(), self.width(), corner))
        dx, dy = target.x() - self._fx, target.y() - self._fy
        if abs(dx) < 0.5 and abs(dy) < 0.5:
            return 0.0
        k = 1 - math.exp(-dt * 6.0)                 # одинаково плавно на любом FPS
        self._fx += dx * k
        self._fy += dy * k
        nx, ny = round(self._fx), round(self._fy)
        lean = max(-6.0, min(6.0, dx * k * 0.6))
        if (nx, ny) != (self.x(), self.y()):
            self.move(nx, ny)
            self.last_input = now
        return lean

    def notify_typing(self):
        self.typing_until = time.time() + 1.5
        self.last_input = time.time()
        self.touch()

    def start_anim(self, name):
        dur = {"lookaround": 2.6, "blink2": 0.6, "wink": 0.9, "spin": 1.2,
               "appear": 0.9, "cheer": 0.9, "headtilt": 1.8}[name]   # все имена — из этой таблицы
        if name == "headtilt":
            self._tilt_dir = random.choice((-1, 1))          # в какую сторону склонить голову
        self.anim = (name, time.time(), dur)

    def anim_u(self):
        if not self.anim:
            return None
        return min(1.0, (time.time() - self.anim[1]) / self.anim[2])

    def _screen_avail(self):
        scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        return (g.left(), g.top(), g.right() + 1, g.bottom() + 1)

    def effective_mood(self):
        if self.mood == "idle" and not self.keep_awake and time.time() - self.last_input > 120:
            return "sleepy"
        return self.mood

    # ---------- физика и таймеры ----------
    def tick(self):
        now = time.time()
        dt = min(0.05, max(0.001, now - getattr(self, "_last_tick", now - 0.016)))   # реальное время кадра
        self._last_tick = now
        if self.mood_until and now > self.mood_until:
            self.mood, self.mood_until = "idle", 0
        target_k = self.voice_k if self.voice_k is not None else (sleepmode.SLEEP_SCALE if self.asleep else 1.0)
        self.size_k = sleepmode.ease(self.size_k, target_k, dt)
        if self._size_px() != self.width():
            px = self._size_px()
            if self.morphing:                                  # переезд: держим центр, Mico не уезжает
                cx, cy = self.x() + self.width() // 2, self.y() + self.height() // 2
                self.setFixedSize(px, px)
                self.move(cx - px // 2, cy - px // 2)
            else:
                self.setFixedSize(px, px)
        if (not self.asleep and self.drag is None and self._sleep_limit()
                and sleepmode.should_sleep(now, self.last_attention, self._sleep_limit(), not self.can_sleep())):
            self.sleep_now()
        cur = QCursor.pos()
        if cur != self.last_cursor:
            self.last_cursor = cur
            if not self.asleep:                             # спящего движение мыши не трогает: будит только нажатие
                self.last_input = now
        if now > self.blink_at:
            self.blink_start, self.blink_until = now, now + intel.BLINK_SEC
            self.blink_at = now + random.uniform(3, 6)
        close = intel.blink_close((now - self.blink_start) / intel.BLINK_SEC) if now < self.blink_until else 0.0
        if self.anim and self.anim[0] == "blink2":            # двойное моргание — тоже плавно
            close = max(close, intel.double_blink_close(min(1.0, (now - self.anim[1]) / self.anim[2])))
        self.lid = 1.0 - 0.92 * close                          # 0.08 — почти закрыт, не полностью
        if self.anim and now > self.anim[1] + self.anim[2]:
            self.anim = None
        if (not self.anim and self.effective_mood() == "idle" and now > self.next_idle and not self.talking
                and self.drag is None and now > self.typing_until):
            self.start_anim(random.choice(["lookaround", "blink2", "wink", "headtilt"]))   # простой: без прыжков и без сердечка — они только в ответ на события
            self.next_idle = now + random.uniform(8, 16)
        if self.jh > 0 or self.jv != 0:
            self.jv -= 900 * dt
            self.jh += self.jv * dt
            if self.jh <= 0 and self.jv < 0:
                if self.jv < -120:
                    self.squash_v += 0.6
                self.jh = self.jv = 0.0
        want_heart = self.mood == "love"          # сердечко — только при настроении «love»
        self.heart += ((1.0 if want_heart else 0.0) - self.heart) * 0.15
        lean_goal = self._glide(now)
        self.lean += (lean_goal - self.lean) * (1 - math.exp(-dt * 9))
        tilt_goal = TILT.get(self.effective_mood(), 0) + self.lean + (4 if self.listen_voice else 0)
        self.tilt += (max(-HEAD_TILT_MAX, min(HEAD_TILT_MAX, tilt_goal)) - self.tilt) * (1 - math.exp(-dt * 7))
        if self.drag is None and (abs(self.vx) > 0.3 or abs(self.vy) > 0.3):
            scr = QGuiApplication.screenAt(self.geometry().center()) or QGuiApplication.primaryScreen()
            g, m = scr.availableGeometry(), int(self.width() * 0.15)
            nx, ny = self.x() + self.vx, self.y() + self.vy
            if nx < g.left() - m or nx > g.right() - self.width() + m:
                self.vx, self.squash_v = -self.vx * 0.6, self.squash_v + 0.6
                nx = max(g.left() - m, min(nx, g.right() - self.width() + m))
            if ny < g.top() - m or ny > g.bottom() - self.height() + m:
                self.vy, self.squash_v = -self.vy * 0.6, self.squash_v + 0.6
                ny = max(g.top() - m, min(ny, g.bottom() - self.height() + m))
            self.move(int(nx), int(ny))
            self.vx *= 0.9 ** (dt / 0.033)
            self.vy *= 0.9 ** (dt / 0.033)
        self._life(now, dt)
        self.squash_v += (-60 * self.squash - 8 * self.squash_v) * dt
        self.squash += self.squash_v * dt
        self.update()

    def _life(self, now, dt):
        """Мелкая «жизнь» лица: рот попадает в слоги, брови ходят по отдельности, лицо дрейфует по телу,
        на акцентах речи глаза крупнее, а брови взлетают. Всё сглаживается и не зависит от FPS."""
        talking = bool(self.talking) and not self.asleep
        listening = now < self.typing_until or self.listen_voice
        ex = lambda rate: 1 - math.exp(-dt * rate)
        self.talk_amt += ((1.0 if talking else 0.0) - self.talk_amt) * ex(6)
        # --- палитра: на середине поворота применяем выбранный цвет
        if self._pending_color and self.anim and self.anim[0] == "spin" and now - self.anim[1] >= self.anim[2] * 0.5:
            self._commit_color()
        if self._col_from is not None and not (self.anim and self.anim[0] == "spin"):
            self._col_from = None
        # --- рот: каждые 60–170 мс новая форма, плавно перетекает в неё
        if talking and self.voice_level is not None:          # речь голосом: рот повторяет громкость звука
            self.viseme = mouth_for_level(self.voice_level)
            self.mtilt_goal = 5.0 * math.sin(now * 2.0)
        elif talking:
            if now >= self.viseme_until:
                self.viseme = random.choice(VISEMES)
                self.viseme_until = now + random.uniform(0.09, 0.2)
                self.mtilt_goal = random.uniform(-6, 6)
        else:
            self.viseme = (0.12, 0.0)
            self.mtilt_goal = 0.0
        k = ex(24 if talking else 10)
        self.mw += (self.viseme[0] - self.mw) * k
        self.mh += (self.viseme[1] - self.mh) * k
        self.mtilt += (getattr(self, "mtilt_goal", 0.0) - self.mtilt) * ex(14)
        # --- акценты речи
        if talking and now >= self.next_emph:
            self.emph_goal, self.emph_until = 1.0, now + random.uniform(0.35, 0.8)
            self.next_emph = now + random.uniform(0.9, 2.2)
            self.squash_v += 0.12
        if self.emph_goal and now >= self.emph_until:
            self.emph_goal = 0.0
        if not talking:
            self.emph_goal = 0.0
            self.next_emph = max(self.next_emph, now + 0.5)
        self.emph += (self.emph_goal - self.emph) * ex(10)
        self.eye_k = 1.0 + 0.14 * self.emph + (0.08 if self.listen_voice else 0.0)
        # --- брови: левая и правая живут независимо
        if now >= self.brow_until:
            amp = 1.0 if (talking or listening) else 0.35
            self.brow_gl = random.uniform(-0.03, 0.055) * amp
            self.brow_gr = random.uniform(-0.03, 0.055) * amp
            self.brow_gtl = random.uniform(-0.03, 0.03) * amp
            self.brow_gtr = random.uniform(-0.03, 0.03) * amp
            self.brow_until = now + (random.uniform(0.5, 1.5) if talking else random.uniform(2.0, 5.0))
        kb = ex(9)
        up = 0.045 * self.emph + (0.02 if listening else 0.0)
        self.brow_l += (self.brow_gl + up - self.brow_l) * kb
        self.brow_r += (self.brow_gr + up - self.brow_r) * kb
        self.brow_tl += (self.brow_gtl - self.brow_tl) * kb
        self.brow_tr += (self.brow_gtr - self.brow_tr) * kb
        # --- лицо дрейфует по телу (в видео оно уезжает то вверх, то в сторону)
        if now >= self.face_until:
            rng = 0.09 if (talking or listening) else 0.05
            self.face_gx = random.uniform(-rng, rng)
            self.face_gy = random.uniform(-rng * 0.8, rng * 0.6)
            self.face_until = now + random.uniform(1.2, 3.0)
        kf = ex(2.2)
        self.face_dx += (self.face_gx - self.face_dx) * kf
        self.face_dy += (self.face_gy - self.face_dy) * kf
        # --- во время разговора иногда радуется, склоняет голову или моргает дважды
        if not talking:
            self.next_talk_anim = max(self.next_talk_anim, now + 1.2)
        elif not self.anim and now >= self.next_talk_anim:
            if random.random() < 0.7:
                self.start_anim(random.choice(["headtilt", "blink2"]))
            self.next_talk_anim = now + random.uniform(2.5, 5.0)

    def dragEnterEvent(self, e):
        """Файл перетащили на Mico AI: принимаем, если это файлы с диска."""
        if any(u.isLocalFile() for u in e.mimeData().urls()):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            e.acceptProposedAction()
            self.dropped.emit(paths)

    def moveEvent(self, e):
        self.moved.emit()
        super().moveEvent(e)

    # ---------- мышь ----------
    def mousePressEvent(self, e):
        self.touch()
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag, self.moved_px, self.vx, self.vy = True, 0, 0, 0
            self.last_move, self.dvx, self.dvy = (e.globalPosition(), time.time()), 0, 0
        elif e.button() == Qt.MouseButton.RightButton:
            self.menu_requested.emit(e.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, e):
        """Двойной щелчок левой кнопкой — открывает настройки. В голосовом режиме это просто ещё одно нажатие."""
        if e.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.drag = None
            self.tapped.emit()
            if not self.voice_taps:
                self.settings_requested.emit()

    def mouseMoveEvent(self, e):
        if self.drag is None:
            return
        g, now = e.globalPosition(), time.time()
        d, dt = g - self.last_move[0], max(now - self.last_move[1], 1e-3)
        self.move(self.pos() + QPoint(int(d.x()), int(d.y())))
        self.moved_px += abs(d.x()) + abs(d.y())
        self.dvx, self.dvy = d.x() / dt / 30, d.y() / dt / 30
        self.last_move = (g, now)
        self.last_input = now

    def mouseReleaseEvent(self, e):
        if self.drag is None:
            return
        self.drag = None
        if self.asleep:                           # спящего тронули: просыпается, без лишнего клика
            self.wake(moved=self.moved_px >= 5)
            return
        if self.moved_px < 5:
            self.tapped.emit()
            self.set_mood("happy", 1.5)
            self.squash_v += 1.0
            self._click_timer.start(QGuiApplication.styleHints().mouseDoubleClickInterval())
        if self.moved_px >= 5 and time.time() - self.last_move[1] < 0.1:
            self.vx, self.vy = max(-40, min(40, self.dvx)), max(-40, min(40, self.dvy))

    # ---------- рисование ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        t = time.time() - self.t0
        cx, R = w / 2, w * 0.28
        cy0 = h * 0.54
        cy = cy0 - self.jh
        mood, u = self.effective_mood(), self.anim_u()
        anim = self.anim[0] if self.anim else None
        if anim == "wink":
            mood = "curious"
        speed = 0.6 if mood == "sleepy" else 1.0
        breath = 1 + 0.03 * math.sin(t * 1.6 * speed)
        sx, sy = breath * (1 + self.squash), breath * (1 - self.squash)
        ta = self.talk_amt
        sy *= 1 + 0.25 * self.mh * ta                       # на открытом слоге тело чуть вытягивается
        cy -= R * 0.025 * math.sin(t * 1.9) * (1 + ta)      # лёгкое покачивание вверх-вниз
        if self.asleep:                                     # во сне дыхание медленное и глубокое
            cy += R * 0.05 * math.sin(t * 0.8)
        base_op = 1.0
        if anim == "appear" and u is not None:              # появление: выскакивает с перелётом и проявляется
            pop = max(0.05, ease_out_back(min(1.0, u / 0.8)))
            sx, sy = sx * pop, sy * pop
            base_op = min(1.0, u * 2.4)
            p.setOpacity(base_op)
        if mood == "proud":                                # грудь колесом: чуть выше и уже
            sx, sy = sx * 0.97, sy * 1.05
        wob = 2.5 if mood == "thinking" else 1.0 + 1.2 * ta
        spin_c, spin_s, spin_turn, side = 1.0, 0.0, 0.0, 0.0     # без вращения, кроме анимации «spin»
        if anim == "spin" and u is not None:
            yaw = 2 * math.pi * (u * u * (3 - 2 * u))           # настоящий оборот вокруг вертикальной оси: медленно-быстро-медленно
            spin_c, spin_s = math.cos(yaw), math.sin(yaw)       # лицо уезжает вбок, сужается и прячется за спину
            side = abs(spin_s)
            sx *= 1 - 0.10 * side                               # корпус при повороте уже
            spin_turn = 7 * spin_s                              # и чуть качается
        shake = math.sin(t * 28) * 3 if mood == "laugh" else math.sin(t * 40) * 1.2 if mood == "scared" else 0
        sway = math.sin(t * 0.7) * 1.8 + ta * (math.sin(t * 2.3) * 3.0 + math.sin(t * 3.7 + 1.0) * 1.5)   # голова покачивается, при речи сильнее
        if anim == "headtilt" and u is not None:
            sway += self._tilt_dir * 6 * math.sin(math.pi * u)  # склоняет голову набок и возвращает (мягко, в пределах лимита)
            mood = "curious"                                    # один глаз прищурен, бровь вверх
        elif anim == "cheer" and u is not None:
            sy *= 1 + 0.04 * math.sin(math.pi * u)
            mood = "laugh"                                      # только если анимацию запустили явно (не случайно)
        col = QColor(self.cfg["color"])
        if self._col_from is not None and anim == "spin" and u is not None and u >= 0.5:
            col = mix(self._col_from, col, smooth((u - 0.5) * 2))     # вторая половина поворота: цвет переливается
        body_col = mix(col, QColor(255, 170, 195), 0.45 * side) if side > 0.001 else col   # при повороте тело розовеет

        p.setPen(Qt.PenStyle.NoPen)                              # мягкая тень
        p.setBrush(QColor(120, 70, 40, max(8, int(34 - self.jh * 0.4))))
        p.drawEllipse(QPointF(cx, cy0 + R * 1.18), R * 0.85 * sx * (1 - self.jh / 300), R * 0.13)

        p.save()
        p.translate(cx, cy)
        head = max(-HEAD_TILT_MAX, min(HEAD_TILT_MAX, self.tilt + sway))   # голова не наклоняется дальше лимита
        p.rotate(head + shake + spin_turn)
        p.translate(-cx, -cy)
        path = QPainterPath()
        for i in range(N):
            a = 2 * math.pi * i / N
            r = pebble(a, wob, t, 0.5 + 0.5 * ta)
            bx, by = math.cos(a) * r * 1.05, math.sin(a) * r * 0.98
            if self.heart > 0.001:
                hx, hy = HEART_PTS[i]
                bx += (hx * 1.42 - bx) * self.heart        # сердце крупнее и шире: как на референсе
                by += (hy * 1.30 - by) * self.heart
            x, y = cx + bx * R * sx, cy + by * R * sy
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        path.closeSubpath()
        # мягкое внешнее свечение (как ореол вокруг Mico в видео)
        glow = mix(body_col, QColor(255, 255, 255), 0.55)
        p.setBrush(Qt.BrushStyle.NoBrush)
        for gw, ga in ((0.34, 12), (0.20, 20), (0.10, 28)):
            gc = QColor(glow)
            gc.setAlpha(ga)
            p.setPen(QPen(gc, R * gw))
            p.drawPath(path)
        # тело: кремово-персиковый градиент с розовым свечением по краю
        pink = QColor(255, 160, 150)
        g = QRadialGradient(QPointF(cx - R * 0.15, cy - R * 0.2), R * 1.3)
        g.setColorAt(0, mix(body_col, QColor(255, 250, 240), 0.35))
        g.setColorAt(0.55, body_col)
        g.setColorAt(0.85, mix(body_col, pink, 0.35))
        g.setColorAt(1, mix(body_col, pink, 0.6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawPath(path)
        p.save()
        p.setClipPath(path)
        sheen = QRadialGradient(QPointF(cx - R * 0.45, cy - R * 0.6), R * 0.6)   # блик
        sheen.setColorAt(0, QColor(255, 255, 255, 130))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(sheen)
        p.drawRect(self.rect())
        irid = QRadialGradient(QPointF(cx + R * 0.85, cy + R * 0.6), R * 0.65)    # перламутр
        irid.setColorAt(0, QColor(170, 240, 220, 80))
        irid.setColorAt(1, QColor(170, 240, 220, 0))
        p.setBrush(irid)
        p.drawRect(self.rect())
        if side > 0.02:                                                            # поворот: перламутровая «спинка»
            pa = min(1.0, side * 1.3)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 248, 250, int(120 * pa)))
            p.drawRect(self.rect())
            shift = spin_c * R * 0.45                                              # цветные полосы едут вместе с вращением
            for (dx, dy, rad, c) in ((-0.5, -0.1, 1.05, (255, 165, 200)), (0.6, 0.15, 0.95, (150, 200, 255)),
                                     (0.0, 0.55, 0.8, (255, 215, 170))):
                gr = QRadialGradient(QPointF(cx + dx * R + shift, cy + dy * R), R * rad)
                gr.setColorAt(0, QColor(c[0], c[1], c[2], int(170 * pa)))
                gr.setColorAt(1, QColor(c[0], c[1], c[2], 0))
                p.setBrush(gr)
                p.drawRect(self.rect())
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 95), R * 0.08))                       # светящийся край
        p.drawPath(path)
        p.restore()
        # лицо: маленькое, смещено вверх-влево (при вращении — «боком»)
        fx = cx - R * 0.12 * (1 - self.heart) + R * self.face_dx * (1 - self.heart)
        fy = cy - R * 0.16 * (1 - self.heart) - R * 0.04 * self.heart + R * self.face_dy * (1 - self.heart)
        if spin_c > 0.04:                                    # за спиной лица нет
            p.save()
            p.setOpacity(base_op * min(1.0, (spin_c - 0.04) / 0.45))
            p.translate(fx + spin_s * R * 0.75, fy)
            p.scale(spin_c, 1)
            p.translate(-fx, -fy)
            self._face(p, fx, fy, R, col, mood, t, u, anim)
            p.restore()
        p.restore()
        self._overlays(p, cx, cy, R, mood, t)
        if base_op < 1.0:
            p.setOpacity(1.0)

    def _look(self, fx, fy, R, mood, u, anim):
        """Взгляд + едва заметные быстрые подёргивания зрачков (микросаккады), чтобы глаза были живыми."""
        v = self._look0(fx, fy, R, mood, u, anim)
        t = time.time()
        jx = (math.sin(t * 1.3) + 0.5 * math.sin(t * 3.1 + 1.0)) * R * 0.006
        jy = (math.cos(t * 1.7) + 0.5 * math.sin(t * 2.7)) * R * 0.005
        return QPointF(v.x() + jx, v.y() + jy)

    def _look0(self, fx, fy, R, mood, u, anim):
        if time.time() < self.typing_until:
            if self.look_at is not None:                      # смотрит на строку ввода, что там пишут
                v = QPointF(self.mapFromGlobal(self.look_at)) - QPointF(fx, fy)
                d = math.hypot(v.x(), v.y()) or 1
                k = min(d / 200, 1) * R * 0.06 / d
                return QPointF(v.x() * k, v.y() * k)
            return QPointF(0, R * 0.07)
        if anim == "headtilt" and u is not None:                # смотрит в ту сторону, куда склонил голову
            return QPointF(-self._tilt_dir * R * 0.05 * math.sin(math.pi * u), -R * 0.01)
        if mood == "thinking":
            return QPointF(R * 0.04 * math.sin(time.time() * 2), -R * 0.05)
        if anim == "lookaround":
            return QPointF(math.sin(u * 2 * math.pi * 1.5) * R * 0.05, 0)
        if mood == "curious":
            return QPointF(R * 0.03, -R * 0.01)
        v = QPointF(self.mapFromGlobal(QCursor.pos())) - QPointF(fx, fy)
        d = math.hypot(v.x(), v.y()) or 1
        k = min(d / 200, 1) * R * 0.045 / d
        return QPointF(v.x() * k, v.y() * k)

    def _face(self, p, fx, fy, R, col, mood, t, u, anim):
        dark = col.lightness() > 110
        ink = QColor("#2a1d1d") if dark else QColor("#ffffff")
        pupil = ink
        shine = QColor(255, 255, 255) if dark else QColor(40, 30, 20)
        nopen = Qt.PenStyle.NoPen
        pen = QPen(ink, max(1.6, R * 0.03))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        typing = time.time() < self.typing_until
        look = self._look(fx, fy, R, mood, u, anim)

        p.setPen(nopen)                                       # румянец
        p.setBrush(QColor(255, 120, 120, 160 if mood in ("shy", "proud") else 105 if mood in ("happy", "love", "laugh", "excited") else 55))
        for s in (-1, 1):
            p.drawEllipse(QPointF(fx + s * R * 0.52, fy + R * 0.22), R * 0.12, R * 0.075)

        for s in (-1, 1):
            ex, ey = fx + s * R * 0.38 + look.x(), fy + look.y() + (R * 0.05 if mood == "shy" else 0) \
                - (R * 0.02 if mood == "confused" and s == 1 else 0)
            ew, eh = R * 0.075, R * 0.105
            squint = mood == "curious" and s == -1
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            if mood == "sleepy" or (mood == "playful" and s == 1):      # подмигивание — правый глаз
                p.drawLine(QPointF(ex - ew, ey), QPointF(ex + ew, ey))
            elif mood in ("happy", "laugh", "love", "proud", "playful"):
                p.drawArc(QRectF(ex - ew * 1.15, ey - eh * 0.5, ew * 2.3, eh * 1.5), 0, 180 * 16)
            elif squint:                                      # прищуренный глаз
                p.setBrush(pupil)
                p.setPen(nopen)
                p.drawEllipse(QPointF(ex, ey + eh * 0.2), ew * 1.05, eh * 0.4)
            else:
                big = (1.35 if mood == "surprised" else 1.3 if mood == "scared" else 1.15 if mood == "excited" else 1.0) * self.eye_k
                sq = 0.75 if (typing or mood == "angry") else 1.0
                p.setBrush(pupil)
                p.setPen(nopen)
                p.drawEllipse(QPointF(ex, ey), ew * big, eh * big * sq * self.lid)
                p.setBrush(shine)
                p.drawEllipse(QPointF(ex + ew * 0.3, ey - eh * 0.3 * sq * self.lid), ew * 0.32 * big, ew * 0.32 * big * self.lid)
                if mood == "sad" and s == 1:                  # слезинка
                    f = (t * 0.8) % 1
                    p.setBrush(QColor(120, 180, 255, int(170 * (1 - f) + 60)))     # слезинка видна почти всё время
                    p.drawEllipse(QPointF(ex + ew * 0.4, ey + eh * 1.3 + f * R * 0.3), ew * 0.4, ew * 0.55)
            # бровки — маленькие дужки
            by = ey - R * 0.2 - look.y() * 0.5
            so, si, curve = R * 0.01, -R * 0.005, R * 0.045
            if mood == "sad":
                so, si, curve = R * 0.03, -R * 0.05, R * 0.012
            elif mood == "worried":
                so, si, curve = R * 0.04, -R * 0.07, R * 0.01
            elif mood == "surprised":
                by -= R * 0.05
                curve = R * 0.06
            elif mood == "scared":
                by -= R * 0.07
                curve = R * 0.06
            elif mood == "excited":
                by -= R * 0.05
                curve = R * 0.06
            elif mood == "angry":
                so, si, curve = -R * 0.02, R * 0.05, R * 0.01
            elif mood == "shy":
                by += R * 0.02
                curve = R * 0.02
            elif mood == "confused" and s == 1:
                by -= R * 0.07
            elif mood in ("thinking", "curious"):
                if s == 1:
                    by -= R * 0.06
                elif squint:
                    by += R * 0.03
                    curve = R * 0.01
            by -= R * (self.brow_l if s == -1 else self.brow_r)                   # живые брови: каждая сама по себе
            bt = self.brow_tl if s == -1 else self.brow_tr
            so, si = so + R * bt, si - R * bt
            bl = R * 0.09
            br = QPainterPath()
            br.moveTo(ex + s * bl, by + so)
            br.quadTo(ex, by - curve, ex - s * bl, by + si)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, max(1.4, R * 0.024), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(br)

        # крошечный рот
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        my = fy + R * 0.22
        if self.heart < 0.5 and mood not in ("laugh", "scared", "sleepy") and self.mh > 0.012:   # речь: рот попадает в слоги (у сердца всегда улыбка)
            hw, hh = R * self.mw, R * self.mh
            if mood in ("happy", "love", "proud", "playful", "excited"):
                hw *= 1.12                                       # когда рад — рот шире
            p.save()
            p.translate(fx, my + R * 0.05)
            p.rotate(self.mtilt * self.talk_amt)
            mp = QPainterPath()                                  # плоский верх и круглое дно, как в видео
            mp.moveTo(-hw, -hh * 0.12)
            mp.quadTo(0, -hh * 0.38, hw, -hh * 0.12)
            mp.cubicTo(hw * 0.95, hh * 1.0, -hw * 0.95, hh * 1.0, -hw, -hh * 0.12)
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawPath(mp)
            p.restore()
        elif mood in ("happy", "love", "proud", "playful"):
            p.drawArc(QRectF(fx - R * 0.17, my - R * 0.07, R * 0.34, R * 0.20), 200 * 16, 140 * 16)
        elif mood == "laugh":
            big = 1.0 + 0.2 * math.sin(t * 18)
            p.setPen(nopen)
            p.setBrush(ink)
            p.drawChord(QRectF(fx - R * 0.13 * big, my - R * 0.03, R * 0.26 * big, R * 0.2 * big), 180 * 16, 180 * 16)
        elif mood == "sad":                                     # грусть: рот домиком, уголки вниз
            frown = QPainterPath()
            frown.moveTo(fx - R * 0.14, my + R * 0.1)
            frown.quadTo(fx, my - R * 0.06, fx + R * 0.14, my + R * 0.1)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(ink, max(1.2, R * 0.03), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(frown)
            p.setPen(nopen)
        elif mood == "worried":
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawEllipse(QPointF(fx, my + R * 0.05), R * 0.03, R * 0.04)
        elif mood == "scared":                                  # испуг: дрожащая линия
            zz = QPainterPath()
            for i in range(6):
                zx = fx - R * 0.1 + i * R * 0.04
                zy = my + R * 0.05 + (R * 0.018 if i % 2 else -R * 0.018)
                zz.moveTo(zx, zy) if i == 0 else zz.lineTo(zx, zy)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(zz)
        elif mood == "angry":                                   # злость: сжатый рот, уголки вниз
            fr = QPainterPath()
            fr.moveTo(fx - R * 0.1, my + R * 0.02)
            fr.quadTo(fx, my + R * 0.1, fx + R * 0.1, my + R * 0.02)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(fr)
        elif mood == "shy":                                     # смущение: маленькая улыбка
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(fx - R * 0.06, my - R * 0.02, R * 0.12, R * 0.08), 200 * 16, 140 * 16)
        elif mood == "confused":                                # растерянность: волнистая линия
            cf = QPainterPath()
            for i in range(9):
                cx2 = fx - R * 0.1 + i * R * 0.025
                cy2 = my + R * 0.04 + math.sin(i * 1.4) * R * 0.012
                cf.moveTo(cx2, cy2) if i == 0 else cf.lineTo(cx2, cy2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(pen)
            p.drawPath(cf)
        elif mood == "excited":                                 # восторг: широкая улыбка
            p.setPen(nopen)
            p.setBrush(ink)
            p.drawChord(QRectF(fx - R * 0.14, my - R * 0.03, R * 0.28, R * 0.2), 180 * 16, 180 * 16)
        elif mood == "surprised":
            p.setBrush(ink)
            p.setPen(nopen)
            p.drawEllipse(QPointF(fx, my + R * 0.05), R * 0.04, R * 0.058)
        elif mood in ("curious", "thinking"):
            p.drawLine(QPointF(fx - R * 0.05, my + R * 0.05), QPointF(fx + R * 0.09, my + R * 0.03))
        elif mood == "sleepy":
            r = R * (0.03 + 0.012 * math.sin(t * 1.2))
            p.drawEllipse(QPointF(fx, my + R * 0.05), r, r * 1.2)
        else:
            p.drawArc(QRectF(fx - R * 0.1, my - R * 0.04, R * 0.2, R * 0.12), 210 * 16, 120 * 16)

    def _font(self, family, size, bold=False):
        key = (family, size, bold)
        font = self._fonts.get(key)
        if font is None:
            font = QFont(family, size, QFont.Weight.Bold if family == theme.FONT_DISPLAY else QFont.Weight.Normal)
            self._fonts[key] = font
        return font

    def _overlays(self, p, cx, cy, R, mood, t):
        p.setPen(Qt.PenStyle.NoPen)
        if mood == "thinking":                                 # три прыгающие точки «думаю…» над головой, чуть ниже прежнего
            for i in range(3):
                bounce = max(0, math.sin(t * 6 - i * 0.9)) * R * 0.12
                p.setBrush(QColor(90, 90, 90, 210))
                p.drawEllipse(QPointF(cx + R * 0.45 + i * R * 0.22, cy - R * 0.98 - bounce), R * 0.07, R * 0.07)
        elif mood == "sleepy":                              # сон: буквы z над головой плывут вверх и гаснут
            for k in range(3):
                ph = ((t * 0.3) + k / 3) % 1
                alpha = int(235 * math.sin(math.pi * ph) ** 1.4)
                if alpha <= 6:
                    continue
                p.setPen(QColor(130, 130, 175, alpha))
                p.setFont(QFont(theme.FONT_DISPLAY, max(8, int(R * (0.2 + 0.12 * k))), QFont.Weight.Bold))
                p.drawText(QPointF(cx + R * (0.3 + 0.35 * ph), cy - R * (1.0 + 0.9 * ph) - k * R * 0.05), "z")
        elif mood == "surprised":
            p.setPen(QColor(230, 90, 60))
            p.setFont(QFont(theme.FONT_DISPLAY, max(8, int(R * 0.45)), QFont.Weight.Bold))
            p.drawText(QPointF(cx - R * 0.12, cy - R * 1.0), "!")
        if mood == "proud":                                 # гордость: искорки вокруг головы
            p.setFont(self._font("Segoe UI Symbol", max(8, int(R * 0.22))))
            for k in range(3):
                ph = (t * 0.7 + k / 3) % 1
                ang = -math.pi * 0.15 - k * 0.55
                rad = R * (1.05 + 0.15 * ph)
                p.setPen(QColor(255, 205, 90, int(255 * math.sin(ph * math.pi))))
                p.drawText(QPointF(cx + math.cos(ang) * rad, cy - R * 0.2 + math.sin(ang) * rad), "✦")
