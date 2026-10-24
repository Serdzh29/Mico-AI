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
    """Стрелка вверх без круга — круг рисует сама кнопка."""
    pix, p = _canvas(size)
    s = size / 18.0
    p.scale(s, s)
    p.setPen(_pen(color, 2.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(9.0, 14.5), QPointF(9.0, 4.2))
    path = QPainterPath()
    path.moveTo(4.6, 8.6)
    path.lineTo(9.0, 4.2)
    path.lineTo(13.4, 8.6)
    p.drawPath(path)
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


def _functions(p):                                    # звёздочка: функции
    p.drawLine(QPointF(9.0, 2.5), QPointF(9.0, 15.5))
    p.drawLine(QPointF(2.5, 9.0), QPointF(15.5, 9.0))
    p.drawLine(QPointF(4.6, 4.6), QPointF(13.4, 13.4))
    p.drawLine(QPointF(13.4, 4.6), QPointF(4.6, 13.4))


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


def _bolt(p):                                         # молния: быстрые действия
    path = QPainterPath()
    path.moveTo(10.5, 2.5)
    path.lineTo(4.5, 10.0)
    path.lineTo(9.0, 10.0)
    path.lineTo(7.5, 15.5)
    path.lineTo(13.5, 8.0)
    path.lineTo(9.0, 8.0)
    path.closeSubpath()
    p.drawPath(path)


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


_DRAW = {"chev_right": _chev_right, "chev_down": _chev_down, "chev_up": _chev_up, "look": _look, "general": _general, "functions": _functions, "models": _models,
         "privacy": _privacy, "close": _close, "moon": _moon, "bolt": _bolt, "search": _search,
         "drop": _drop, "resize": _resize, "frame": _frame, "bar": _bar, "power": _power, "history": _history,
         "menu": _menu, "pulse": _pulse, "chat": _chat, "buttons": _buttons, "sun": _sun,
         "layers": _layers, "download": _download, "palette": _palette, "speaker": _speaker, "mic": _mic, "mic_off": _mic_off, "screen": _screen, "tune": _tune, "subs": _subs}


def icon(name, color, size=18):
    """Монохромная иконка по имени."""
    return _stroke_icon(_DRAW[name], color, size)


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


def _anim_general(p, u):                              # ползунки ездят туда-сюда, у каждого свой ритм
    for i, (y, x) in enumerate(((4.5, 6.0), (9.0, 12.0), (13.5, 7.5))):
        dx = 2.8 * math.sin(2 * math.pi * u + i * 1.9)
        p.drawLine(QPointF(2.5, y), QPointF(15.5, y))
        p.drawEllipse(QPointF(x + dx, y), 1.6, 1.6)


def _anim_functions(p, u):                            # звёздочка искрит: поворачивается и пульсирует
    k = 1.0 + 0.22 * math.sin(math.pi * u)
    p.save()
    p.translate(9.0, 9.0)
    p.rotate(70 * math.sin(math.pi * u))
    p.scale(k, k)
    p.translate(-9.0, -9.0)
    _functions(p)
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


ANIMATED = {"look": _anim_look, "general": _anim_general, "functions": _anim_functions,
            "speaker": _anim_speaker, "models": _anim_models, "history": _anim_history}


def paint_animated(name, p, u):
    """Рисует иконку раздела в момент u анимации (0…1). Неанимированные иконки рисуются обычно."""
    fn = ANIMATED.get(name)
    if fn is None:
        _DRAW[name](p)
    else:
        fn(p, max(0.0, min(1.0, float(u))))
