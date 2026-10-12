"""Углы экрана и сон Mico: куда он встаёт (в выбранный угол или остаётся там, где его поставили),
где спит и когда засыпает. Чистая логика без Qt — проверяется в tests/test_sleep.py."""
import math

SLEEP_SCALE = 0.42         # во сне Mico становится меньше в этом отношении
CORNER_MARGIN = 6          # отступ от края экрана в углу, px
DEFAULT_MINUTES = 3
DEFAULT_CORNER = "br"
# код угла: первая буква — t (верх) / b (низ), вторая — l (лево) / r (право)
CORNERS = {"tl": "Левый верхний", "tr": "Правый верхний", "bl": "Левый нижний", "br": "Правый нижний"}


def limit_seconds(minutes):
    """Минуты из настроек -> секунды. 0 или пусто — не засыпать (вернём 0)."""
    try:
        m = float(minutes)
    except (TypeError, ValueError):
        m = DEFAULT_MINUTES
    return max(0, int(m * 60))


def should_sleep(now, last_attention, limit_sec, busy):
    """Пора ли спать: прошло больше limit_sec без внимания и никто не занят разговором."""
    if limit_sec <= 0 or busy:
        return False
    return now - last_attention >= limit_sec


def corner_spot(avail, size, corner=DEFAULT_CORNER, margin=CORNER_MARGIN):
    """Левый верхний угол квадрата size в выбранном углу рабочей области.
    avail — (left, top, right, bottom) с правой и нижней границами, не входящими в область (как в Qt +1).
    Неизвестный угол — правый нижний."""
    if corner not in CORNERS:
        corner = DEFAULT_CORNER
    left, top, right, bottom = avail
    x = left + margin if corner[1] == "l" else right - size - margin
    y = top + margin if corner[0] == "t" else bottom - size - margin
    return int(x), int(y)


def home_corner(asleep, placement, sleep_corner):
    """Угол, где Mico стоит сейчас: во сне — выбранный для сна, иначе — выбранное положение.
    None — Mico стоит там, где его поставил пользователь (мышкой)."""
    if asleep:
        return sleep_corner if sleep_corner in CORNERS else DEFAULT_CORNER
    return placement if placement in CORNERS else None


def ease(current, target, dt, rate=2.5):
    """Плавно подтягивает current к target; в конце «защёлкивает», чтобы не дрожать."""
    k = 1 - math.exp(-dt * rate)
    nxt = current + (target - current) * k
    return target if abs(target - nxt) < 0.002 else nxt
