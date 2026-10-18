"""Иконки интерфейса Mico AI: стрелка отправки и значки настроек. Рисуются штрихами, поэтому ровные в любом масштабе
и подходят к цвету темы. Эмодзи не используем: на разных системах они выглядят по-разному."""
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


_DRAW = {"chev_right": _chev_right, "chev_down": _chev_down, "chev_up": _chev_up, "look": _look, "general": _general, "functions": _functions, "models": _models,
         "privacy": _privacy, "close": _close, "moon": _moon, "bolt": _bolt, "search": _search,
         "drop": _drop, "resize": _resize, "frame": _frame, "bar": _bar, "power": _power, "history": _history,
         "menu": _menu, "pulse": _pulse, "chat": _chat, "buttons": _buttons, "sun": _sun,
         "layers": _layers, "download": _download}


def icon(name, color, size=18):
    """Монохромная иконка по имени."""
    return _stroke_icon(_DRAW[name], color, size)
