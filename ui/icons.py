"""Иконки интерфейса Mico AI: стрелка отправки и значки настроек. Рисуются штрихами, поэтому ровные в любом масштабе
и подходят к цвету темы. Эмодзи не используем: на разных системах они выглядят по-разному."""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _pen(color, width):
    pen = QPen(QColor(color), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _canvas(size):
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    return pix, p


def send_icon(color, size=18):
    """Аккуратный бумажный самолётик, смотрит вправо. Круг под ним рисует сама кнопка."""
    pix, p = _canvas(size)
    s = size / 18.0
    p.scale(s, s)
    pen = _pen(color, 1.7)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(2.8, 3.4)
    path.lineTo(15.4, 9.0)
    path.lineTo(2.8, 14.6)
    path.lineTo(5.6, 9.0)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(5.6, 9.0), QPointF(10.4, 9.0))
    p.end()
    return QIcon(pix)


def mix(hex_color, other, amount):
    """Смешивает два цвета: amount 0 — первый, 1 — второй. Для лёгкой подсветки при наведении."""
    a = QColor(hex_color)
    b = QColor(other)
    t = max(0.0, min(1.0, float(amount)))
    r = round(a.red() + (b.red() - a.red()) * t)
    g = round(a.green() + (b.green() - a.green()) * t)
    bl = round(a.blue() + (b.blue() - a.blue()) * t)
    return "#%02X%02X%02X" % (r, g, bl)


# ---------- минималистичные иконки-штрихи: без цвета и эмодзи, цвет задаёт тема ----------
def _stroke_icon(draw, color, size, width=1.6):
    pix, p = _canvas(size)
    s = size / 18.0
    p.scale(s, s)
    p.setPen(_pen(color, width))
    p.setBrush(Qt.BrushStyle.NoBrush)
    draw(p)
    p.end()
    return QIcon(pix)


def _look(p):                                         # глаз: вид
    path = QPainterPath()
    path.moveTo(2.0, 9.0)
    path.quadTo(9.0, 2.6, 16.0, 9.0)
    path.quadTo(9.0, 15.4, 2.0, 9.0)
    p.drawPath(path)
    p.drawEllipse(QPointF(9.0, 9.0), 2.2, 2.2)


def _general(p):                                      # ползунки: основное
    for y, x in ((4.5, 6.0), (9.0, 12.0), (13.5, 7.5)):
        p.drawLine(QPointF(2.5, y), QPointF(15.5, y))
        p.drawEllipse(QPointF(x, y), 1.6, 1.6)


def _profile(p):                                      # силуэт пользователя: профиль
    p.drawEllipse(QPointF(9.0, 5.7), 3.0, 3.0)
    p.drawArc(QRectF(3.3, 9.0, 11.4, 7.2), 202 * 16, 136 * 16)


def _functions(p):                                    # облачко диалога с тремя точками
    p.drawRoundedRect(QRectF(2.5, 3.0, 13.0, 10.5), 4.0, 4.0)
    tail = QPainterPath()
    tail.moveTo(6.0, 13.0)
    tail.lineTo(5.0, 16.0)
    tail.lineTo(9.0, 13.0)
    p.drawPath(tail)
    for x in (6.0, 9.0, 12.0):
        p.drawEllipse(QPointF(x, 8.2), 0.65, 0.65)


def _models(p):                                       # куб: модели
    pts = [QPointF(9.0, 2.5), QPointF(15.0, 5.7), QPointF(15.0, 12.3),
           QPointF(9.0, 15.5), QPointF(3.0, 12.3), QPointF(3.0, 5.7)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        p.drawLine(a, b)
    p.drawLine(QPointF(3.0, 5.7), QPointF(9.0, 9.0))
    p.drawLine(QPointF(15.0, 5.7), QPointF(9.0, 9.0))
    p.drawLine(QPointF(9.0, 9.0), QPointF(9.0, 15.5))


def _privacy(p):                                      # замок: приватность
    p.drawRoundedRect(QRectF(4.0, 8.0, 10.0, 7.5), 2.0, 2.0)
    p.drawArc(QRectF(6.0, 3.5, 6.0, 8.0), 0, 180 * 16)


def _close(p):                                        # крестик
    p.drawLine(QPointF(4.5, 4.5), QPointF(13.5, 13.5))
    p.drawLine(QPointF(13.5, 4.5), QPointF(4.5, 13.5))


def _moon(p):                                         # луна: тишина
    path = QPainterPath()
    path.moveTo(12.5, 3.0)
    path.arcTo(QRectF(3.0, 3.0, 12.0, 12.0), 60, 240)
    path.arcTo(QRectF(7.0, 2.2, 9.0, 9.6), 205, -150)
    p.drawPath(path)


def _bolt_path():
    path = QPainterPath()
    path.moveTo(10.5, 2.5)
    path.lineTo(4.5, 10.0)
    path.lineTo(9.0, 10.0)
    path.lineTo(7.5, 15.5)
    path.lineTo(13.5, 8.0)
    path.lineTo(9.0, 8.0)
    path.closeSubpath()
    return path


def _bolt(p):                                         # молния: быстрые действия
    p.drawPath(_bolt_path())


def _search(p):                                       # лупа: поиск
    p.drawEllipse(QPointF(7.8, 7.8), 4.8, 4.8)
    p.drawLine(QPointF(11.4, 11.4), QPointF(15.5, 15.5))


def _chev_down(p):                                    # стрелка вниз: раскрыть
    p.drawLine(QPointF(4.5, 7.0), QPointF(9.0, 11.5))
    p.drawLine(QPointF(9.0, 11.5), QPointF(13.5, 7.0))


def _chev_up(p):                                      # стрелка вверх: свернуть
    p.drawLine(QPointF(4.5, 11.0), QPointF(9.0, 6.5))
    p.drawLine(QPointF(9.0, 6.5), QPointF(13.5, 11.0))


def _chev_right(p):                                   # стрелка вправо: открыть подраздел
    p.drawLine(QPointF(7.0, 4.5), QPointF(11.5, 9.0))
    p.drawLine(QPointF(11.5, 9.0), QPointF(7.0, 13.5))


def _drop(p):                                         # капля: цвет и тема
    path = QPainterPath()
    path.moveTo(9.0, 2.5)
    path.cubicTo(13.5, 8.0, 15.0, 10.0, 15.0, 11.5)
    path.cubicTo(15.0, 14.3, 12.3, 16.0, 9.0, 16.0)
    path.cubicTo(5.7, 16.0, 3.0, 14.3, 3.0, 11.5)
    path.cubicTo(3.0, 10.0, 4.5, 8.0, 9.0, 2.5)
    p.drawPath(path)


def _palette(p):                                      # палитра художника: выбор цвета Mico AI
    path = QPainterPath()
    path.moveTo(9.0, 2.4)
    path.cubicTo(4.4, 2.4, 2.4, 5.6, 2.4, 8.8)
    path.cubicTo(2.4, 12.0, 5.0, 13.6, 7.0, 13.2)
    path.cubicTo(8.4, 12.9, 8.2, 15.6, 10.6, 15.6)
    path.cubicTo(13.9, 15.6, 15.6, 13.2, 15.6, 9.6)
    path.cubicTo(15.6, 5.0, 12.8, 2.4, 9.0, 2.4)
    p.drawPath(path)
    for x, y in ((5.4, 7.2), (8.2, 4.8), (12.0, 5.4)):   # три краски
        p.drawPoint(QPointF(x, y))


def _speaker(p):                                      # динамик: озвучка ответов
    p.drawPolyline([QPointF(3.0, 7.0), QPointF(6.0, 7.0), QPointF(10.0, 3.5), QPointF(10.0, 14.5),
                    QPointF(6.0, 11.0), QPointF(3.0, 11.0)])
    p.drawArc(QRectF(10.5, 5.5, 4.5, 7.0), -60 * 16, 120 * 16)


def _mic(p):                                          # микрофон: голосовой ввод
    p.drawRoundedRect(QRectF(6.5, 2.5, 5.0, 8.5), 2.5, 2.5)
    p.drawArc(QRectF(4.0, 6.5, 10.0, 8.0), 180 * 16, 180 * 16)
    p.drawLine(QPointF(9.0, 14.5), QPointF(9.0, 16.0))


def _resize(p):                                       # уголки: размер и прозрачность
    for pts in (((2.5, 6.5), (2.5, 2.5), (6.5, 2.5)), ((11.5, 2.5), (15.5, 2.5), (15.5, 6.5)),
                ((15.5, 11.5), (15.5, 15.5), (11.5, 15.5)), ((6.5, 15.5), (2.5, 15.5), (2.5, 11.5))):
        p.drawPolyline([QPointF(x, y) for x, y in pts])


def _frame(p):                                        # рамка с подсветкой: обводки
    p.drawRoundedRect(QRectF(2.0, 3.0, 14.0, 12.0), 3.0, 3.0)
    p.drawRoundedRect(QRectF(5.5, 6.5, 7.0, 5.0), 1.5, 1.5)


def _bar(p):                                          # экран с полоской сверху: полоска Mico AI
    p.drawRoundedRect(QRectF(2.5, 3.0, 13.0, 11.0), 2.0, 2.0)
    p.drawLine(QPointF(6.0, 6.0), QPointF(12.0, 6.0))


def _power(p):                                        # кнопка питания: запуск
    p.drawArc(QRectF(3.8, 3.8, 10.4, 10.4), 130 * 16, 280 * 16)
    p.drawLine(QPointF(9.0, 2.5), QPointF(9.0, 8.5))


def _history(p):                                      # часы: история
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    p.drawPolyline([QPointF(9.0, 5.5), QPointF(9.0, 9.0), QPointF(11.5, 10.5)])


def _menu(p):                                         # три строки: меню
    for y in (5.0, 9.0, 13.0):
        p.drawLine(QPointF(3.0, y), QPointF(15.0, y))


def _pulse(p):                                        # линия нагрузки: тишина и загрузка
    p.drawPolyline([QPointF(2.0, 9.0), QPointF(5.0, 9.0), QPointF(7.0, 4.0), QPointF(10.0, 14.0),
                    QPointF(12.0, 9.0), QPointF(16.0, 9.0)])


def _chat(p):                                         # облачко: свои фразы
    p.drawRoundedRect(QRectF(2.5, 3.0, 13.0, 9.5), 3.0, 3.0)
    p.drawPolyline([QPointF(6.0, 12.5), QPointF(5.0, 15.5), QPointF(9.5, 12.5)])


def _buttons(p):                                      # три кнопки: кнопки под чатом
    p.drawRoundedRect(QRectF(2.5, 3.5, 6.0, 4.0), 2.0, 2.0)
    p.drawRoundedRect(QRectF(10.0, 3.5, 5.5, 4.0), 2.0, 2.0)
    p.drawRoundedRect(QRectF(2.5, 10.5, 13.0, 4.0), 2.0, 2.0)


def _sun(p):                                          # солнце: погода и приветствие
    import math
    p.drawEllipse(QPointF(9.0, 9.0), 2.8, 2.8)
    for k in range(8):
        a = k * math.pi / 4
        p.drawLine(QPointF(9.0 + 5.3 * math.cos(a), 9.0 + 5.3 * math.sin(a)),
                   QPointF(9.0 + 6.8 * math.cos(a), 9.0 + 6.8 * math.sin(a)))


def _layers(p):                                       # слои: память и перерывы
    p.drawPolyline([QPointF(9.0, 3.0), QPointF(15.0, 6.0), QPointF(9.0, 9.0), QPointF(3.0, 6.0), QPointF(9.0, 3.0)])
    p.drawPolyline([QPointF(3.0, 9.0), QPointF(9.0, 12.0), QPointF(15.0, 9.0)])
    p.drawPolyline([QPointF(3.0, 12.0), QPointF(9.0, 15.0), QPointF(15.0, 12.0)])


def _download(p):                                     # стрелка в лоток: скачивание и удаление
    p.drawLine(QPointF(9.0, 3.0), QPointF(9.0, 11.5))
    p.drawPolyline([QPointF(5.5, 8.0), QPointF(9.0, 11.5), QPointF(12.5, 8.0)])
    p.drawPolyline([QPointF(3.0, 12.5), QPointF(3.0, 15.0), QPointF(15.0, 15.0), QPointF(15.0, 12.5)])


def _screen(p):                                       # экран с подставкой: Mico смотрит на экран
    p.drawRoundedRect(QRectF(2.5, 3.0, 13.0, 9.5), 2.0, 2.0)
    p.drawLine(QPointF(9.0, 12.5), QPointF(9.0, 15.0))
    p.drawLine(QPointF(6.0, 15.0), QPointF(12.0, 15.0))


def _tune(p):                                         # ползунки: быстрые настройки голоса
    for y, x in ((5.0, 6.5), (9.0, 11.5), (13.0, 7.5)):
        p.drawLine(QPointF(3.0, y), QPointF(15.0, y))
        p.drawEllipse(QPointF(x, y), 1.6, 1.6)


def _subs(p):                                         # субтитры: рамка с двумя строками текста
    p.drawRoundedRect(QRectF(2.5, 4.0, 13.0, 10.0), 2.5, 2.5)
    p.drawLine(QPointF(5.0, 8.0), QPointF(13.0, 8.0))
    p.drawLine(QPointF(5.0, 11.0), QPointF(10.5, 11.0))


def _mic_off(p):                                      # микрофон перечёркнут: микрофон выключен
    _mic(p)
    p.drawLine(QPointF(3.0, 3.0), QPointF(15.0, 15.0))


def _timer(p):                                        # секундомер: таймер
    p.drawEllipse(QPointF(9.0, 10.0), 6.0, 6.0)
    p.drawLine(QPointF(9.0, 10.0), QPointF(9.0, 6.8))
    p.drawLine(QPointF(7.4, 2.4), QPointF(10.6, 2.4))


def _bell(p):                                         # колокольчик: напоминание и будильник
    path = QPainterPath()
    path.moveTo(4.0, 13.0)
    path.lineTo(14.0, 13.0)
    path.quadTo(12.6, 11.6, 12.6, 9.0)
    path.quadTo(12.6, 4.2, 9.0, 4.2)
    path.quadTo(5.4, 4.2, 5.4, 9.0)
    path.quadTo(5.4, 11.6, 4.0, 13.0)
    p.drawPath(path)
    p.drawLine(QPointF(7.8, 15.2), QPointF(10.2, 15.2))


def _lock(p):                                         # замок: заблокировать
    p.drawRoundedRect(QRectF(4.0, 8.0, 10.0, 7.5), 1.8, 1.8)
    p.drawArc(QRectF(6.0, 3.0, 6.0, 9.0), 0, 180 * 16)


def _play(p):                                         # треугольник: музыка и пауза
    path = QPainterPath()
    path.moveTo(6.0, 4.0)
    path.lineTo(14.0, 9.0)
    path.lineTo(6.0, 14.0)
    path.closeSubpath()
    p.drawPath(path)


def _globe(p):                                        # глобус: сайт
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    p.drawEllipse(QPointF(9.0, 9.0), 2.8, 6.5)
    p.drawLine(QPointF(2.5, 9.0), QPointF(15.5, 9.0))


def _app(p):                                          # окно программы: открыть приложение
    p.drawRoundedRect(QRectF(2.5, 3.5, 13.0, 11.0), 2.2, 2.2)
    p.drawLine(QPointF(2.5, 6.8), QPointF(15.5, 6.8))


def _battery(p):                                      # батарея: заряд
    p.drawRoundedRect(QRectF(2.5, 5.5, 11.5, 7.0), 1.6, 1.6)
    p.drawLine(QPointF(15.5, 7.8), QPointF(15.5, 10.2))
    p.drawLine(QPointF(5.0, 9.0), QPointF(9.0, 9.0))


def _chip(p):                                         # процессор: что грузит ПК
    p.drawRoundedRect(QRectF(5.0, 5.0, 8.0, 8.0), 1.4, 1.4)
    for k in (7.0, 11.0):
        p.drawLine(QPointF(k, 2.5), QPointF(k, 5.0))
        p.drawLine(QPointF(k, 13.0), QPointF(k, 15.5))
        p.drawLine(QPointF(2.5, k), QPointF(5.0, k))
        p.drawLine(QPointF(13.0, k), QPointF(15.5, k))


def _disk(p):                                         # диск: место на диске
    p.drawRoundedRect(QRectF(2.5, 5.0, 13.0, 8.0), 2.0, 2.0)
    p.drawEllipse(QPointF(12.5, 9.0), 0.8, 0.8)


def _gear(p):                                         # шестерёнка: настройки
    p.drawEllipse(QPointF(9.0, 9.0), 2.3, 2.3)
    path = QPainterPath()
    for i in range(16):                               # 8 зубцов: внешний и внутренний радиус по очереди
        a = math.pi * 2 * i / 16 - math.pi / 16
        rad = 6.6 if i % 2 == 0 else 5.0
        pt = QPointF(9.0 + rad * math.cos(a), 9.0 + rad * math.sin(a))
        b = math.pi * 2 * (i + 1) / 16 - math.pi / 16
        pt2 = QPointF(9.0 + rad * math.cos(b), 9.0 + rad * math.sin(b))
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
        path.lineTo(pt2)
    path.closeSubpath()
    p.drawPath(path)


_DRAW = {"chev_right": _chev_right, "chev_down": _chev_down, "chev_up": _chev_up, "look": _look, "general": _general, "profile": _profile, "functions": _functions, "models": _models,
         "privacy": _privacy, "close": _close, "moon": _moon, "bolt": _bolt, "api_bolt": _bolt, "search": _search,
         "drop": _drop, "resize": _resize, "frame": _frame, "bar": _bar, "power": _power, "history": _history,
         "menu": _menu, "pulse": _pulse, "chat": _chat, "buttons": _buttons, "sun": _sun,
         "layers": _layers, "download": _download, "palette": _palette, "speaker": _speaker, "mic": _mic, "mic_off": _mic_off, "screen": _screen, "tune": _tune, "subs": _subs,
         "timer": _timer, "bell": _bell, "lock": _lock, "play": _play, "globe": _globe, "app": _app,
         "battery": _battery, "chip": _chip, "disk": _disk, "gear": _gear}


def icon(name, color, size=18, width=1.6):
    """Монохромная иконка по имени. Неизвестное имя — молния, а не ошибка."""
    return _stroke_icon(_DRAW.get(name, _bolt), color, size, width)


def icon_frame(name, color, u, size=18):
    """Кадр анимированной иконки в момент u (0…1). Это обычная иконка того же размера, что и неанимированная."""
    return _stroke_icon(lambda p: paint_animated(name, p, u), color, size)


# ---------- анимация иконок разделов настроек: u от 0 до 1, за один проход ----------
def _anim_look(p, u):                                 # глаз моргает: веки опускаются и поднимаются
    k = 1.0 - 0.92 * math.sin(math.pi * u)
    p.save()
    p.translate(9.0, 9.0)
    p.scale(1.0, max(0.06, k))
    p.translate(-9.0, -9.0)
    _look(p)
    p.restore()


def _anim_profile(p, u):                              # профиль: искра появляется у имени и раскрывается мягким сиянием
    ease = math.sin(math.pi * u)
    _profile(p)
    p.save()
    p.setOpacity(0.9 * ease)
    ink = p.pen().color()
    p.setPen(_pen(ink, 1.25))
    cx, cy = 12.8, 4.0
    reach = 1.6 + 2.4 * ease
    for angle in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
        dx, dy = math.cos(angle) * reach, math.sin(angle) * reach
        p.drawLine(QPointF(cx + dx * 0.42, cy + dy * 0.42), QPointF(cx + dx, cy + dy))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    p.drawEllipse(QPointF(cx, cy), 0.9 + 0.45 * ease, 0.9 + 0.45 * ease)
    p.restore()


def _anim_general(p, u):                              # ползунки ездят туда-сюда, у каждого свой ритм
    for i, (y, x) in enumerate(((4.5, 6.0), (9.0, 12.0), (13.5, 7.5))):
        dx = 2.8 * math.sin(2 * math.pi * u + i * 1.9)
        p.drawLine(QPointF(2.5, y), QPointF(15.5, y))
        p.drawEllipse(QPointF(x + dx, y), 1.6, 1.6)


def _anim_functions(p, u):                            # три точки по очереди подпрыгивают в облачке чата
    p.drawRoundedRect(QRectF(2.5, 3.0, 13.0, 10.5), 4.0, 4.0)
    tail = QPainterPath()
    tail.moveTo(6.0, 13.0)
    tail.lineTo(5.0, 16.0)
    tail.lineTo(9.0, 13.0)
    p.drawPath(tail)
    for i, x in enumerate((6.0, 9.0, 12.0)):
        phase = max(0.0, min(1.0, (u - i * 0.16) / 0.48))
        lift = math.sin(math.pi * phase) if phase > 0.0 else 0.0
        p.save()
        p.setOpacity(0.58 + 0.42 * lift)
        p.setBrush(p.pen().color())
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x, 8.2 - 1.35 * lift), 0.72 + 0.18 * lift, 0.72 + 0.18 * lift)
        p.restore()


def _anim_speaker(p, u):                              # динамик «говорит»: звуковые волны по очереди
    _speaker(p)
    for i, (rect, start) in enumerate(((QRectF(12.2, 3.6, 3.6, 10.8), 0.15),      # волны внутри 18×18, не обрезаются
                                        (QRectF(13.6, 1.9, 3.6, 14.2), 0.40))):
        local = (u - start) / 0.45
        if 0.0 <= local <= 1.0:
            p.save()
            p.setOpacity(math.sin(math.pi * local))
            p.drawArc(rect, -60 * 16, 120 * 16)
            p.restore()


def _anim_models(p, u):                              # кубик подпрыгивает и поворачивается на 90°, мягко приземляясь
    ease = u * u * (3.0 - 2.0 * u)
    lift = -3.0 * math.sin(math.pi * u)
    squash = 1.0 + 0.10 * math.sin(math.pi * u)
    p.save()
    p.translate(0.0, lift)
    p.translate(9.0, 9.0)
    p.rotate(120.0 * ease)                            # поворот на 120°: куб совпадает сам с собой, без скачка в конце
    p.scale(squash, 2.0 - squash)
    p.translate(-9.0, -9.0)
    _models(p)
    p.restore()


def _anim_history(p, u):                              # часы: минутная стрелка делает один полный круг
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    p.drawLine(QPointF(9.0, 9.0), QPointF(11.2, 7.8))  # часовая стрелка стоит
    p.save()
    p.translate(9.0, 9.0)
    p.rotate(360.0 * u)
    p.drawLine(QPointF(0.0, 0.0), QPointF(0.0, -4.6))  # минутная стрелка
    p.restore()


def _anim_bolt(p, u):                                 # молния «бьёт»: вспышка заливает контур, по бокам проскакивают искры
    flash = math.sin(math.pi * min(1.0, u / 0.75)) if u < 0.75 else 0.0
    shake = 0.45 * math.sin(4.0 * math.pi * u) * (1.0 - u)     # короткое дрожание после удара
    p.save()
    p.translate(shake, 0.0)
    p.save()
    p.setOpacity(0.25 + 0.75 * flash)
    p.setBrush(p.pen().color())
    p.drawPath(_bolt_path())
    p.restore()
    p.drawPath(_bolt_path())                          # контур всегда на месте
    p.restore()
    for (x1, y1, x2, y2), start in (((2.0, 5.0, 3.2, 4.2), 0.30), ((16.0, 6.0, 14.8, 4.6), 0.45),
                                    ((15.5, 13.0, 17.0, 13.6), 0.55)):
        local = (u - start) / 0.30
        if 0.0 <= local <= 1.0:
            p.save()
            p.setOpacity(math.sin(math.pi * local))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            p.restore()


ANIMATED = {"look": _anim_look, "general": _anim_general, "profile": _anim_profile, "functions": _anim_functions,
            "speaker": _anim_speaker, "models": _anim_models, "history": _anim_history, "api_bolt": _anim_bolt}



# ---------- набор иконок настроек (s_*): сетка 18×18, одна толщина линии, скруглённые углы ----------
def _fill(p):
    p.setBrush(p.pen().color())


def _s_chat(p):
    path = QPainterPath()
    path.addRoundedRect(QRectF(2.5, 3.0, 13.0, 10.0), 3.6, 3.6)
    p.drawPath(path)
    p.drawLine(QPointF(5.4, 13.0), QPointF(4.6, 15.6))
    p.drawLine(QPointF(4.6, 15.6), QPointF(8.2, 13.0))
    p.drawLine(QPointF(5.8, 6.9), QPointF(12.2, 6.9))
    p.drawLine(QPointF(5.8, 9.6), QPointF(10.0, 9.6))


def _s_look(p):
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    half = QPainterPath()
    half.moveTo(9.0, 2.5)
    half.arcTo(QRectF(2.5, 2.5, 13.0, 13.0), 90, 180)
    half.closeSubpath()
    p.save()
    _fill(p)
    p.drawPath(half)
    p.restore()


def _s_screen(p):
    p.drawRoundedRect(QRectF(2.0, 3.0, 14.0, 9.5), 2.2, 2.2)
    p.drawLine(QPointF(9.0, 12.5), QPointF(9.0, 15.0))
    p.drawLine(QPointF(6.2, 15.2), QPointF(11.8, 15.2))
    p.save()
    _fill(p)
    p.drawEllipse(QPointF(12.2, 9.2), 1.6, 1.4)
    p.restore()


def _s_voice(p):
    p.drawRoundedRect(QRectF(6.5, 2.2, 5.0, 8.6), 2.5, 2.5)
    p.drawArc(QRectF(3.8, 5.2, 10.4, 8.6), 200 * 16, 140 * 16)
    p.drawLine(QPointF(9.0, 13.8), QPointF(9.0, 15.8))


def _s_action(p):
    path = QPainterPath()
    path.moveTo(4.0, 3.5)
    path.lineTo(12.0, 9.2)
    path.lineTo(8.6, 10.0)
    path.lineTo(10.4, 13.9)
    path.lineTo(8.9, 14.6)
    path.lineTo(7.1, 10.7)
    path.lineTo(4.6, 12.9)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(14.2, 3.0), QPointF(14.2, 5.6))
    p.drawLine(QPointF(12.9, 4.3), QPointF(15.5, 4.3))


def _sparkle(p, cx, cy, r):
    s = QPainterPath()
    s.moveTo(cx, cy - r)
    s.quadTo(cx, cy, cx + r, cy)
    s.quadTo(cx, cy, cx, cy + r)
    s.quadTo(cx, cy, cx - r, cy)
    s.quadTo(cx, cy, cx, cy - r)
    p.drawPath(s)


def _s_ai(p):
    _sparkle(p, 7.8, 9.6, 5.6)
    _sparkle(p, 13.6, 4.4, 2.4)


def _s_data(p):
    p.drawEllipse(QPointF(9.0, 4.6), 5.6, 2.1)
    p.drawLine(QPointF(3.4, 4.6), QPointF(3.4, 13.4))
    p.drawLine(QPointF(14.6, 4.6), QPointF(14.6, 13.4))
    p.drawArc(QRectF(3.4, 6.9, 11.2, 4.2), 180 * 16, 180 * 16)
    p.drawArc(QRectF(3.4, 11.3, 11.2, 4.2), 180 * 16, 180 * 16)


def _s_profile(p):
    p.drawEllipse(QPointF(9.0, 6.0), 3.0, 3.0)
    p.drawArc(QRectF(3.4, 10.4, 11.2, 8.6), 0, 180 * 16)


def _s_quick(p):
    for x, y in ((2.8, 2.8), (2.8, 10.0), (10.0, 10.0)):
        p.drawRoundedRect(QRectF(x, y, 5.2, 5.2), 1.6, 1.6)
    _sparkle(p, 12.6, 5.4, 2.8)


def _s_sun(p):
    p.drawEllipse(QPointF(9.0, 9.0), 3.0, 3.0)
    for i in range(8):
        a = math.pi * i / 4
        p.drawLine(QPointF(9 + 5.0 * math.cos(a), 9 + 5.0 * math.sin(a)), QPointF(9 + 6.6 * math.cos(a), 9 + 6.6 * math.sin(a)))


def _s_snow(p):                                      # снежинка: шесть лучей с веточками
    for i in range(6):
        a = math.pi * i / 3
        ca, sa = math.cos(a), math.sin(a)
        p.drawLine(QPointF(9, 9), QPointF(9 + 7.0 * ca, 9 + 7.0 * sa))
        bx, by = 9 + 4.4 * ca, 9 + 4.4 * sa
        for s_ in (-1, 1):
            b = a + s_ * math.pi / 4
            p.drawLine(QPointF(bx, by), QPointF(bx + 2.0 * math.cos(b), by + 2.0 * math.sin(b)))


def _s_help(p):
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    p.drawEllipse(QPointF(9.0, 9.0), 2.8, 2.8)
    for a in (45, 135, 225, 315):
        r = math.radians(a)
        p.drawLine(QPointF(9 + 2.8 * math.cos(r), 9 + 2.8 * math.sin(r)), QPointF(9 + 6.5 * math.cos(r), 9 + 6.5 * math.sin(r)))


def _s_palette(p):
    path = QPainterPath()
    path.moveTo(9.0, 2.5)
    path.cubicTo(13.4, 2.5, 15.8, 5.6, 15.5, 8.8)
    path.cubicTo(15.3, 11.0, 12.6, 10.6, 11.6, 11.6)
    path.cubicTo(10.6, 12.6, 12.6, 15.5, 9.0, 15.5)
    path.cubicTo(5.2, 15.5, 2.5, 12.6, 2.5, 9.0)
    path.cubicTo(2.5, 5.4, 5.2, 2.5, 9.0, 2.5)
    p.drawPath(path)
    p.save()
    _fill(p)
    for x, y in ((6.0, 7.0), (9.2, 5.4), (12.0, 7.2), (5.8, 10.6)):
        p.drawEllipse(QPointF(x, y), 0.85, 0.85)
    p.restore()


def _s_size(p):
    for (x1, y1, x2, y2, hx, hy) in ((10.5, 7.5, 15.0, 3.0, -1, 1), (7.5, 10.5, 3.0, 15.0, 1, -1)):
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        p.drawLine(QPointF(x2, y2), QPointF(x2 + hx * 3.6, y2))
        p.drawLine(QPointF(x2, y2), QPointF(x2, y2 + hy * 3.6))


def _s_outline(p):
    p.drawRoundedRect(QRectF(2.5, 2.5, 13.0, 13.0), 3.6, 3.6)
    p.drawRoundedRect(QRectF(5.6, 5.6, 6.8, 6.8), 1.8, 1.8)


def _s_bar(p):
    p.drawRoundedRect(QRectF(2.0, 3.0, 14.0, 11.0), 2.4, 2.4)
    pen = p.pen()
    wide = QPen(pen)
    wide.setWidthF(pen.widthF() * 1.8)
    p.setPen(wide)
    p.drawLine(QPointF(5.0, 11.2), QPointF(13.0, 11.2))
    p.setPen(pen)


def _s_sleep(p):
    path = QPainterPath()
    path.moveTo(11.0, 3.0)
    path.cubicTo(6.2, 3.4, 3.6, 8.6, 6.2, 12.6)
    path.cubicTo(8.6, 16.0, 13.6, 15.6, 15.4, 12.0)
    path.cubicTo(11.4, 12.6, 8.6, 7.6, 11.0, 3.0)
    p.drawPath(path)


def _s_power(p):
    p.drawArc(QRectF(3.0, 3.6, 12.0, 12.0), 120 * 16, 300 * 16)
    p.drawLine(QPointF(9.0, 2.2), QPointF(9.0, 8.6))


def _s_quiet(p):
    _bell(p)
    p.drawLine(QPointF(3.0, 3.0), QPointF(15.0, 15.0))


def _s_menu(p):
    for y in (5.0, 9.0, 13.0):
        p.save()
        _fill(p)
        p.drawEllipse(QPointF(4.0, y), 0.9, 0.9)
        p.restore()
        p.drawLine(QPointF(7.0, y), QPointF(15.0, y))


def _s_dance(p):
    p.drawLine(QPointF(7.0, 13.0), QPointF(7.0, 3.6))
    p.drawLine(QPointF(7.0, 3.6), QPointF(14.0, 2.6))
    p.drawLine(QPointF(14.0, 2.6), QPointF(14.0, 11.6))
    p.drawEllipse(QPointF(5.2, 13.4), 2.0, 1.6)
    p.drawEllipse(QPointF(12.2, 12.0), 2.0, 1.6)


def _s_phrase(p):
    p.drawRoundedRect(QRectF(2.5, 2.5, 5.0, 5.0), 1.6, 1.6)
    p.drawRoundedRect(QRectF(10.5, 10.5, 5.0, 5.0), 1.6, 1.6)
    path = QPainterPath()
    path.moveTo(7.5, 5.0)
    path.cubicTo(12.6, 5.0, 13.0, 6.2, 13.0, 10.5)
    p.drawPath(path)


def _s_agent(p):
    p.drawRoundedRect(QRectF(3.0, 5.6, 12.0, 9.4), 3.0, 3.0)
    p.drawLine(QPointF(9.0, 5.6), QPointF(9.0, 3.0))
    p.save()
    _fill(p)
    p.drawEllipse(QPointF(9.0, 2.6), 0.9, 0.9)
    p.drawEllipse(QPointF(6.8, 10.2), 1.0, 1.2)
    p.drawEllipse(QPointF(11.2, 10.2), 1.0, 1.2)
    p.restore()


def _s_model(p):
    top = QPainterPath()
    top.moveTo(9.0, 2.4)
    top.lineTo(15.4, 5.2)
    top.lineTo(9.0, 8.0)
    top.lineTo(2.6, 5.2)
    top.closeSubpath()
    p.drawPath(top)
    for dy in (3.6, 7.2):
        layer = QPainterPath()
        layer.moveTo(2.6, 5.2 + dy)
        layer.lineTo(9.0, 8.0 + dy)
        layer.lineTo(15.4, 5.2 + dy)
        p.drawPath(layer)


def _s_memory(p):
    path = QPainterPath()
    path.moveTo(4.0, 2.5)
    path.lineTo(11.0, 2.5)
    path.lineTo(14.5, 6.0)
    path.lineTo(14.5, 15.5)
    path.lineTo(4.0, 15.5)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(11.0, 2.5), QPointF(11.0, 6.0))
    p.drawLine(QPointF(11.0, 6.0), QPointF(14.5, 6.0))
    p.drawLine(QPointF(6.6, 9.4), QPointF(11.8, 9.4))
    p.drawLine(QPointF(6.6, 12.4), QPointF(10.2, 12.4))


def _s_bulb(p):
    path = QPainterPath()
    path.moveTo(6.6, 12.2)
    path.cubicTo(6.4, 10.6, 3.8, 9.4, 3.8, 7.0)
    path.cubicTo(3.8, 4.2, 6.2, 2.2, 9.0, 2.2)
    path.cubicTo(11.8, 2.2, 14.2, 4.2, 14.2, 7.0)
    path.cubicTo(14.2, 9.4, 11.6, 10.6, 11.4, 12.2)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(6.8, 14.4), QPointF(11.2, 14.4))
    p.drawLine(QPointF(7.8, 16.2), QPointF(10.2, 16.2))


def _s_history(p):
    p.drawArc(QRectF(2.5, 2.5, 13.0, 13.0), 200 * 16, -320 * 16)
    p.drawLine(QPointF(2.6, 6.2), QPointF(2.9, 8.9))
    p.drawLine(QPointF(2.9, 8.9), QPointF(5.4, 8.0))
    p.drawLine(QPointF(9.0, 5.6), QPointF(9.0, 9.0))
    p.drawLine(QPointF(9.0, 9.0), QPointF(11.4, 10.6))


def _s_test(p):
    p.drawEllipse(QPointF(9.0, 9.0), 6.5, 6.5)
    path = QPainterPath()
    path.moveTo(5.8, 9.2)
    path.lineTo(8.0, 11.4)
    path.lineTo(12.4, 6.8)
    p.drawPath(path)


def _s_speaker(p):
    path = QPainterPath()
    path.moveTo(2.8, 7.0)
    path.lineTo(5.4, 7.0)
    path.lineTo(9.0, 4.0)
    path.lineTo(9.0, 14.0)
    path.lineTo(5.4, 11.0)
    path.lineTo(2.8, 11.0)
    path.closeSubpath()
    p.drawPath(path)
    p.drawArc(QRectF(8.6, 6.2, 4.6, 5.6), -60 * 16, 120 * 16)
    p.drawArc(QRectF(8.6, 3.8, 7.6, 10.4), -60 * 16, 120 * 16)


S_ICONS = {"s_chat": _s_chat, "s_look": _s_look, "s_screen": _s_screen, "s_voice": _s_voice, "s_action": _s_action,
           "s_ai": _s_ai, "s_data": _s_data, "s_profile": _s_profile, "s_quick": _s_quick, "s_sun": _s_sun,
           "s_help": _s_help, "s_palette": _s_palette, "s_size": _s_size, "s_outline": _s_outline, "s_bar": _s_bar,
           "s_sleep": _s_sleep, "s_power": _s_power, "s_quiet": _s_quiet, "s_menu": _s_menu, "s_dance": _s_dance,
           "s_phrase": _s_phrase, "s_agent": _s_agent, "s_model": _s_model, "s_memory": _s_memory, "s_bulb": _s_bulb,
           "s_history": _s_history, "s_mic": _s_voice, "s_test": _s_test, "s_speaker": _s_speaker, "s_snow": _s_snow}
_DRAW.update(S_ICONS)


# ---------- у каждого раздела настроек своя анимация иконки: движение самой иконки + «эффект» вокруг неё ----------
ANIM_ACCENT = "#FFCFA3"                               # цвет эффектов (искры, волны); SideTabs ставит цвет Mico


def set_anim_accent(color):
    global ANIM_ACCENT
    ANIM_ACCENT = str(color or ANIM_ACCENT)


def _c01(x):
    return max(0.0, min(1.0, x))


def _env(u):                                          # 0 → 1 → 0: плавный подъём и спад за один проход
    return math.sin(math.pi * _c01(u))


def _ease(u):
    u = _c01(u)
    return u * u * (3 - 2 * u)


def _back(u):                                         # «пружинка»: проскакивает и возвращается
    u = _c01(u)
    c = 1.70158
    return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2


def _acc(alpha=1.0):
    c = QColor(ANIM_ACCENT)
    c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


# движения самой иконки: u → (сдвиг x, сдвиг y, поворот°, растяжение x, растяжение y)
def _t_bounce(u):
    return 0, -2.2 * abs(math.sin(math.pi * 3 * u)) * (1 - u), 0, 1, 1


def _t_wiggle(u):
    return 0, 0, 16 * math.sin(math.pi * 5 * u) * (1 - u), 1, 1


def _t_rock(u):
    return 0, 0, 13 * math.sin(math.pi * 2 * u) * (1 - 0.3 * u), 1, 1


def _t_pulse(u):                                      # два удара, как сердце
    e = max(0.0, math.sin(math.pi * 4 * u)) * (1 - u * 0.5)
    return 0, 0, 0, 1 + 0.2 * e, 1 + 0.2 * e


def _t_spin(u):
    return 0, 0, 360 * _ease(u), 1, 1


def _t_spin_back(u):
    return 0, 0, -360 * _ease(u), 1, 1


def _t_squash(u):
    e = math.sin(math.pi * 4 * u) * _env(u)
    return 0, 0, 0, 1 + 0.16 * e, 1 - 0.16 * e


def _t_tap(u):
    return 0.8 * _env(u * 2 if u < .5 else 0), 1.8 * _env(u * 2 if u < .5 else 0), 0, 1, 1


def _t_shake(u):
    return 1.6 * math.sin(math.pi * 8 * u) * (1 - u), 0, 0, 1, 1


def _t_grow(u):
    e = 0.2 * _env(u)
    return 0, 0, 0, 1 + e, 1 + e


def _t_blink(u):
    k = max(0.0, math.sin(math.pi * 4 * u)) ** 2
    return 0, 0, 0, 1, 1 - 0.85 * k


def _t_slide(u):
    return 2.0 * math.sin(math.pi * 3 * u) * (1 - u), 0, 0, 1, 1


# эффекты вокруг иконки: рисуют в сетке 18×18
def _star(p, cx, cy, r, alpha):
    path = QPainterPath()
    for i in range(8):
        a = math.pi / 4 * i
        rr = r if i % 2 == 0 else r * 0.38
        pt = QPointF(cx + math.cos(a) * rr, cy + math.sin(a) * rr)
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_acc(alpha))
    p.drawPath(path)


def _o_sparkles(spots=((14.6, 3.4), (3.2, 4.6), (14.2, 14.6))):
    def run(p, u):
        for i, (x, y) in enumerate(spots):
            k = _c01((u - i * 0.2) / 0.5)
            e = math.sin(math.pi * k) if 0 < k < 1 else 0.0
            if e > 0.02:
                _star(p, x, y, 0.8 + 2.0 * e, e)
    return run


def _o_waves(side=1, x0=11.0):
    def run(p, u):
        for j in range(2):
            k = (u * 1.6 - j * 0.35)
            if not 0 < k < 1:
                continue
            r = 2.0 + 5.5 * k
            pen = QPen(_acc(math.sin(math.pi * k) * 0.95), 1.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            cx = x0 if side > 0 else 18 - x0
            p.drawArc(QRectF(cx - r, 9 - r, 2 * r, 2 * r), int((-38 if side > 0 else 142) * 16), 76 * 16)
    return run


def _o_ring(cx=9.0, cy=9.0, rmax=8.0):
    def run(p, u):
        k = _c01(u * 1.15)
        if 0 < k < 1:
            p.setPen(QPen(_acc((1 - k) * 0.9), 1.4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            r = 2 + (rmax - 2) * _ease(k)
            p.drawEllipse(QPointF(cx, cy), r, r)
    return run


def _o_zzz(p, u):
    for i in range(3):
        k = _c01((u - i * 0.22) / 0.55)
        if not 0 < k < 1:
            continue
        s = 1.2 + 0.9 * i
        x, y = 11.5 + i * 1.7, 6.5 - 5.0 * k - i * 0.4
        pen = QPen(_acc(math.sin(math.pi * k)), 1.3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        z = QPainterPath()
        z.moveTo(x - s, y - s)
        z.lineTo(x + s, y - s)
        z.lineTo(x - s, y + s)
        z.lineTo(x + s, y + s)
        p.drawPath(z)


def _o_dots(p, u):                                    # три точки набора текста
    for i in range(3):
        k = _c01((u - 0.1 - i * 0.14) / 0.45)
        e = math.sin(math.pi * k) if 0 < k < 1 else 0.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_acc(0.35 + 0.65 * e))
        p.drawEllipse(QPointF(5.2 + i * 3.8, 8.6 - 2.4 * e), 1.1 + 0.4 * e, 1.1 + 0.4 * e)


def _o_orbit(p, u):
    k = _env(u)
    if k > 0.02:
        a = -math.pi / 2 + 2 * math.pi * _ease(u)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_acc(k))
        p.drawEllipse(QPointF(9 + math.cos(a) * 8.0, 9 + math.sin(a) * 8.0), 1.5, 1.5)


def _o_rays(p, u):
    e = _env(u)
    if e < 0.02:
        return
    pen = QPen(_acc(e), 1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for i in range(8):
        a = math.pi / 4 * i + math.pi * u
        r0, r1 = 7.2, 7.2 + 1.8 * e
        p.drawLine(QPointF(9 + math.cos(a) * r0, 9 + math.sin(a) * r0), QPointF(9 + math.cos(a) * r1, 9 + math.sin(a) * r1))


def _o_drops(p, u):                                   # цветные капли выпрыгивают из палитры
    cols = (0.0, 0.35, 0.7)
    for i, (x, y) in enumerate(((14.8, 3.2), (16.2, 7.0), (3.0, 3.4))):
        k = _c01((u - i * 0.18) / 0.5)
        e = _back(k) if k < 1 else 1.0
        fade = 1 - _c01((u - 0.78) / 0.22)
        if k > 0:
            c = _acc(fade)
            c = QColor(c.red() + int((255 - c.red()) * cols[i]), c.green() + int((255 - c.green()) * cols[i] * 0.6),
                       c.blue(), int(255 * fade))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y), 1.8 * e, 1.8 * e)


def _o_scan(p, u):                                    # линия-сканер проходит сверху вниз
    e = _env(u)
    if e < 0.03:
        return
    y = 2.5 + 13.0 * _ease(u)
    pen = QPen(_acc(e), 1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(2.0, y), QPointF(16.0, y))


def _o_bars(p, u):                                    # столбики эквалайзера поднимаются
    for i in range(3):
        h = 2.0 + 5.0 * abs(math.sin(math.pi * (u * 2.2 + i * 0.33))) * _env(u)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_acc(_env(u)))
        p.drawRoundedRect(QRectF(11.2 + i * 2.1, 16.4 - h, 1.4, h), 0.7, 0.7)


def _o_corners(p, u):                                 # уголки рамки разъезжаются и сходятся
    e = _env(u)
    if e < 0.02:
        return
    d = 1.4 * e
    pen = QPen(_acc(e), 1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        cx, cy = 9 + sx * (7.6 + d), 9 + sy * (7.6 + d)
        p.drawLine(QPointF(cx, cy), QPointF(cx - sx * 2.2, cy))
        p.drawLine(QPointF(cx, cy), QPointF(cx, cy - sy * 2.2))


def _o_dashring(p, u):
    e = _env(u)
    if e < 0.02:
        return
    pen = QPen(_acc(e), 1.3)
    pen.setStyle(Qt.PenStyle.CustomDashLine)
    pen.setDashPattern([1.2, 1.6])
    pen.setDashOffset(-u * 12)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(9, 9), 8.0, 8.0)


def _o_zap(p, u):
    for i, (x, y, dx, dy) in enumerate(((15.0, 3.0, 1.6, -1.6), (3.0, 14.8, -1.6, 1.6), (15.4, 14.0, 1.6, 1.6))):
        k = _c01((u * 3 - i * 0.5) % 1.0) if u < 0.95 else 0.0
        e = math.sin(math.pi * k)
        if e > 0.2:
            pen = QPen(_acc(e), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(QPointF(x, y), QPointF(x + dx * e, y + dy * e))
            p.drawLine(QPointF(x + dx * e * 0.4, y), QPointF(x + dx * e * 1.4, y + dy * e * 0.3))


def _o_notes(p, u):                                   # ноты поднимаются и тают
    for i in range(3):
        k = _c01((u - i * 0.2) / 0.6)
        if not 0 < k < 1:
            continue
        x, y = 12.5 + i * 1.8, 12.5 - 9.5 * k
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_acc(math.sin(math.pi * k)))
        p.drawEllipse(QPointF(x, y), 1.3, 1.0)
        p.setPen(QPen(_acc(math.sin(math.pi * k)), 1.0))
        p.drawLine(QPointF(x + 1.2, y), QPointF(x + 1.2, y - 3.0))


def _o_check(p, u):
    k = _c01((u - 0.25) / 0.45)
    if k <= 0:
        return
    fade = 1 - _c01((u - 0.85) / 0.15)
    pts = [QPointF(11.4, 4.2), QPointF(13.2, 6.0), QPointF(16.4, 2.4)]
    pen = QPen(_acc(fade), 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    seg = k * 2
    path = QPainterPath(pts[0])
    if seg <= 1:
        path.lineTo(pts[0] + (pts[1] - pts[0]) * seg)
    else:
        path.lineTo(pts[1])
        path.lineTo(pts[1] + (pts[2] - pts[1]) * (seg - 1))
    p.drawPath(path)


def _o_sweep(p, u):                                   # полоска блика проезжает наискосок
    e = _env(u)
    if e < 0.03:
        return
    x = -2 + 22 * _ease(u)
    pen = QPen(_acc(0.8 * e), 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(x, 16), QPointF(x + 4, 2))


# для каждого раздела — своя пара «движение + эффект»; пары не повторяются
_NAV_ANIM = {
    "s_chat": (_t_bounce, _o_dots), "s_look": (_t_blink, _o_sparkles()), "s_screen": (_t_grow, _o_scan),
    "s_voice": (_t_pulse, _o_waves(1)), "s_mic": (_t_squash, _o_waves(-1, 7.0)), "s_action": (_t_tap, _o_ring(14.0, 14.0, 5.5)),
    "s_ai": (_t_wiggle, _o_sparkles(((14.8, 3.0), (3.0, 3.2), (9.0, 16.4), (16.0, 10.6)))), "s_data": (_t_squash, _o_bars),
    "s_profile": (_t_rock, _o_sparkles(((15.0, 3.0), (3.0, 12.8)))), "s_quick": (_t_shake, _o_zap), "s_sun": (_t_spin, _o_rays),
    "s_help": (_t_wiggle, _o_ring(9.0, 9.0, 8.4)), "s_palette": (_t_rock, _o_drops), "s_size": (_t_grow, _o_corners),
    "s_outline": (_t_spin_back, _o_dashring), "s_bar": (_t_slide, _o_bars), "s_sleep": (_t_rock, _o_zzz),
    "s_power": (_t_pulse, _o_ring(9.0, 9.0, 8.0)), "s_quiet": (_t_wiggle, _o_zzz), "s_menu": (_t_slide, _o_sweep),
    "s_dance": (_t_wiggle, _o_notes), "s_phrase": (_t_squash, _o_dots), "s_agent": (_t_wiggle, _o_orbit),
    "s_model": (_t_bounce, _o_orbit), "s_memory": (_t_pulse, _o_ring(9.0, 9.0, 8.4)), "s_bulb": (_t_pulse, _o_rays),
    "s_history": (_t_spin_back, _o_ring(9.0, 9.0, 8.0)), "s_test": (_t_tap, _o_check), "s_speaker": (_t_pulse, _o_waves(1, 12.0)),
    "s_data2": (_t_slide, _o_sweep), "s_snow": (_t_spin, _o_sparkles(((14.6, 3.2), (3.0, 4.2), (14.8, 14.8)))),
}


def _nav_anim(name):
    move, effect = _NAV_ANIM.get(name, (_t_spin, _o_sparkles()))
    base = S_ICONS[name]

    def run(p, u):
        tx, ty, rot, sx, sy = move(u)
        s0 = 1.0 - 0.12 * _env(u)                          # иконка чуть уменьшается, чтобы эффектам хватало места
        p.save()
        p.translate(9.0 + tx, 9.0 + ty)
        p.rotate(rot)
        p.scale(s0 * sx, s0 * sy)
        p.translate(-9.0, -9.0)
        base(p)
        p.restore()
        p.save()
        effect(p, u)
        p.restore()
    return run


for _n in S_ICONS:
    ANIMATED[_n] = _nav_anim(_n)


def paint_animated(name, p, u):
    """Рисует иконку раздела в момент u анимации (0…1). Неанимированные иконки рисуются обычно."""
    fn = ANIMATED.get(name)
    if fn is None:
        _DRAW[name](p)
    else:
        fn(p, max(0.0, min(1.0, float(u))))
