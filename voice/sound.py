"""Звук и корзина для Mico AI (только Windows):
- Mico танцует, когда играет музыка или видео из программы со звуком (сеансы звука Windows, pycaw);
- Mico «ест» файлы, когда корзину очистили (SHQueryRecycleBin: число элементов упало до нуля).
Логика переходов (Hysteresis, bin_emptied) — без Windows и Qt, проверяется в tests/test_soundwatch.py.
Опрос идёт в фоновом потоке; сигналы в окно Mico передаёт main.py через Bus (потокобезопасно).

Ограничение: восстановление последнего файла из корзины выглядит так же, как очистка, и тоже даст анимацию."""
import ctypes, os, threading, time

START_PEAK = 0.02       # громкость, с которой считаем, что звук играет
STOP_PEAK = 0.008       # ниже этого — тишина
START_SEC = 1.2         # звук должен играть без перерыва столько, чтобы это не было щелчком
STOP_SEC = 3.0          # тишина дольше этого — танец заканчивается
POLL_SEC = 0.4


class Hysteresis:
    """Танец: включается, когда звук играет START_SEC подряд; выключается, когда тихо STOP_SEC подряд."""

    def __init__(self):
        self.on = False
        self._loud_since = None
        self._quiet_since = None

    def feed(self, peak, now):
        """peak — громкость 0..1 (максимум по программам). True — состояние только что сменилось."""
        if not self.on:
            if peak >= START_PEAK:
                if self._loud_since is None:
                    self._loud_since = now
                if now - self._loud_since >= START_SEC:
                    self.on, self._quiet_since = True, None
                    return True
            else:
                self._loud_since = None
            return False
        if peak < STOP_PEAK:
            if self._quiet_since is None:
                self._quiet_since = now
            if now - self._quiet_since >= STOP_SEC:
                self.on, self._loud_since = False, None
                return True
        else:
            self._quiet_since = None
        return False


def bin_emptied(prev, now_count):
    """Корзину очистили: в прошлый раз в ней что-то было (prev > 0), сейчас пусто. None — ещё не смотрели."""
    return prev is not None and prev > 0 and now_count == 0


def peak_level():
    """Громкость самой громкой программы, которая сейчас играет звук (0..1). None — не удалось узнать.
    Системные звуки и сам Mico (его голос) не считаем."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        best, me = 0.0, os.getpid()
        for s in AudioUtilities.GetAllSessions():
            try:                                              # один сеанс с ошибкой не должен прятать остальные
                if s.Process is None or s.Process.pid == me or s.State != 1:    # 1 — сеанс звука активен
                    continue
                meter = s._ctl.QueryInterface(IAudioMeterInformation)
                best = max(best, float(meter.GetPeakValue()))
            except Exception:
                continue
        return best
    except Exception:
        return None


class _SHQUERYRBINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]


def recycle_count():
    """Сколько элементов в корзине всех дисков. None — не удалось узнать."""
    try:
        info = _SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) != 0:   # 0 — S_OK
            return None
        return int(info.i64NumItems)
    except Exception:
        return None


class Watcher:
    """Опрос раз в POLL_SEC в фоновом потоке.
    flags() -> (танцевать, есть файлы из корзины) — читает настройки на каждом круге, поэтому меняются сразу.
    on_playing(bool) — танец включился или выключился. on_emptied() — корзину очистили."""

    def __init__(self, flags, on_playing, on_emptied):
        self.flags, self.on_playing, self.on_emptied = flags, on_playing, on_emptied
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="mico-sound").start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        try:
            import comtypes
            comtypes.CoInitialize()                           # pycaw работает с COM — в каждом потоке свой
        except Exception:
            pass
        hys, prev_count = Hysteresis(), None
        while not self._stop.is_set():
            now = time.time()
            try:
                dance, eat = self.flags()
                if dance:
                    peak = peak_level()
                    if peak is not None and hys.feed(peak, now):
                        self.on_playing(hys.on)
                elif hys.on:                                  # танец выключили в настройках
                    hys = Hysteresis()
                    self.on_playing(False)
                if eat:
                    count = recycle_count()
                    if count is not None:
                        if bin_emptied(prev_count, count):
                            self.on_emptied()
                        prev_count = count
                else:
                    prev_count = None
            except Exception:
                pass                                          # наблюдение — украшение, не должно ломать Mico
            self._stop.wait(POLL_SEC)
