"""Формы Mico AI без Qt: чистая математика, её можно проверять тестами и смотреть картинкой."""
import math


def _heart_raw(a):
    """Классическое сердце по углу a (радианы). Радиус около 1, острый кончик внизу."""
    t = a + math.pi / 2
    x = 16 * math.sin(t) ** 3
    y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
    return x / 17.0, -(y + 2.5) / 17.0


def heart_points(n=96, sigma=5.0):
    """Сердце из n точек по контуру, сглаженное по контуру: кончик внизу и вырез сверху становятся
    мягкими, как у референса. Сглаживание симметричное, поэтому сердце остаётся симметричным."""
    raw = [_heart_raw(2 * math.pi * i / n) for i in range(n)]
    reach = int(3 * sigma)
    offsets = list(range(-reach, reach + 1))
    weights = [math.exp(-(k * k) / (2 * sigma * sigma)) for k in offsets]
    out = []
    for i in range(n):
        sx = sy = ws = 0.0
        for k, w in zip(offsets, weights):
            x, y = raw[(i + k) % n]
            sx += x * w
            sy += y * w
            ws += w
        out.append((sx / ws, sy / ws))
    return out


HEART = heart_points()

# Один ритм ожидания во всём интерфейсе: точки над Mico и в чате всегда совпадают.
THINK_DOT_SPEED = 6.0
THINK_DOT_DELAY = 0.9


def thinking_dot_lift(t, index):
    """Фаза точки ожидания 0…1: мягкий подъём с общей временной шкалой."""
    return max(0.0, math.sin(float(t) * THINK_DOT_SPEED - int(index) * THINK_DOT_DELAY))
