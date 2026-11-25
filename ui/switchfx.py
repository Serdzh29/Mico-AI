"""Анимации-карточки в чате: на каждый переключатель, ползунок и выбор Windows — своя живая картинка.

Как в знакомстве: карточка с названием, переключатель или шкала, а справа — маленькая сценка про этот
переключатель (Wi-Fi ловит сеть, колокольчик звенит, щит загорается и т.д.). Сценок около шестидесяти;
для каждого из 130+ переключателей выбирается подходящая, а ещё из названия берутся свой оттенок, свой
фоновый эффект и своя скорость — так что два переключателя с одной сценкой всё равно выглядят по-разному.
Всё рисуется кодом (только PyQt6), анимация идёт ~4 секунды и останавливается; по клику — повтор.
"""
import hashlib
import math
import time

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygonF
from PyQt6.QtWidgets import QSizePolicy, QWidget

DUR = 4.2          # сколько секунд длится показ
FLIP = (.45, 1.15)  # когда происходит само переключение (с, по)


# ---------- мелкие помощники ----------
def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back(x, c=1.70158):
    x = clamp(x)
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, k):
    return a + (b - a) * k


def mixc(a, b, k):
    a, b, k = QColor(a), QColor(b), clamp(k)
    return QColor(int(a.red() + (b.red() - a.red()) * k), int(a.green() + (b.green() - a.green()) * k),
                  int(a.blue() + (b.blue() - a.blue()) * k))


def alpha(col, a):
    c = QColor(col)
    c.setAlphaF(clamp(a))
    return c


def stroke(p, col, w=2.4):
    pen = QPen(QColor(col), w)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)


def fill(p, col):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(col))


def arc(p, r, a0, span, cx=0.0, cy=0.0):
    p.drawArc(QRectF(cx - r, cy - r, 2 * r, 2 * r), int(a0 * 16), int(span * 16))


def line(p, x0, y0, x1, y1):
    p.drawLine(QPointF(x0, y0), QPointF(x1, y1))


def dot(p, x, y, r):
    p.drawEllipse(QPointF(x, y), r, r)


def rr(p, x, y, w, h, r):
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def poly(p, pts):
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in pts]))


def pgon(p, pts):
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))


def txt(p, x, y, w, h, text, px, col, bold=False, align=None):
    f = QFont()
    f.setPixelSize(int(px))
    f.setBold(bool(bold))
    p.setFont(f)
    p.setPen(QColor(col))
    flags = int((align or Qt.AlignmentFlag.AlignHCenter).value) | int(Qt.AlignmentFlag.AlignVCenter.value)
    p.drawText(QRectF(x, y, w, h), flags, str(text))


def slash(p, c, k, size=26):
    """Зачёркивание «выключено»: линия прорисовывается по k от 0 до 1."""
    if k <= 0.01:
        return
    stroke(p, c.bad, 3.2)
    line(p, -size, -size, lerp(-size, size, k), lerp(-size, size, k))


class Ctx:
    """Что нужно рисунку: цвета, вариант, размер (R — «радиус» сценки, px)."""
    def __init__(self, acc, ink, mut, bad, v=0, R=32.0):
        self.acc, self.ink, self.mut, self.bad, self.v, self.R = acc, ink, mut, bad, v, R


def loop(t, period, shift=0.0):
    return ((t + shift) / period) % 1.0


# ---------- сценки (рисуются вокруг точки (0, 0), в единицах ~px; e: 0 — выключено, 1 — включено) ----------
def m_generic(p, t, e, c):
    for j in range(3):
        ph = loop(t, 1.6, j / 3)
        stroke(p, alpha(c.acc, (1 - ph) * .8 * e), 2)
        dot(p, 0, 0, 8 + ph * 26)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, 0, 11)
    stroke(p, QColor("#ffffff"), 2.8)
    poly(p, [(-5, 0), (-1.5, 4), (5.5, -4)])


def m_wifi(p, t, e, c):
    for i, r in enumerate((11, 21, 31)):
        a = .25 + .75 * e * (.55 + .45 * max(0.0, math.sin(t * 4 - i * 1.0)))
        stroke(p, alpha(mixc(c.mut, c.acc, e), a), 3.4)
        arc(p, r, 48, 84, 0, 16)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, 16, 3.8)
    slash(p, c, 1 - e)


def m_bluetooth(p, t, e, c):
    for j in range(2):
        ph = loop(t, 1.5, j * .5)
        stroke(p, alpha(c.acc, (1 - ph) * .7 * e), 2)
        dot(p, 0, 0, 14 + ph * 22)
    stroke(p, mixc(c.mut, c.acc, e), 3.2)
    poly(p, [(-11, -11), (11, 11), (0, 22), (0, -22), (11, -11), (-11, 11)])
    slash(p, c, 1 - e)


def m_plane(p, t, e, c):
    x = lerp(-34, 34, loop(t, 2.4)) if e > .5 else -10
    p.save()
    p.translate(x, -4 * math.sin(t * 3) * e)
    p.rotate(-12 if e > .5 else 0)
    fill(p, mixc(c.mut, c.acc, e))
    pgon(p, [(-14, 8), (16, 0), (-14, -8), (-8, 0)])
    stroke(p, alpha(c.ink, .5 * e), 2)
    line(p, -16, 0, -30, 0)
    p.restore()
    stroke(p, alpha(c.mut, .6), 2)
    line(p, -34, 22, 34, 22)


def m_hotspot(p, t, e, c):
    for j in range(4):
        ph = loop(t, 2.0, j / 4)
        stroke(p, alpha(c.acc, (1 - ph) * .85 * e), 2.4)
        arc(p, 6 + ph * 28, 30, 120, 0, 8)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, 8, 5)
    stroke(p, mixc(c.mut, c.acc, e), 3)
    line(p, 0, 8, 0, 24)
    slash(p, c, 1 - e)


def m_moon(p, t, e, c):
    path = QPainterPath()
    path.addEllipse(QPointF(0, 0), 17, 17)
    cut = QPainterPath()
    cut.addEllipse(QPointF(9 + 8 * (1 - e), -5), 14, 14)
    fill(p, mixc(c.mut, QColor("#ffe9a8"), e))
    p.drawPath(path.subtracted(cut))
    for k, (x, y) in enumerate(((20, -16), (24, 4), (14, 20))):
        tw = .4 + .6 * abs(math.sin(t * 2.2 + k * 1.7))
        fill(p, alpha(QColor("#ffffff"), tw * e))
        dot(p, x * .9, y * .9, 2.2 * tw)


def m_bell(p, t, e, c):
    swing = math.sin(t * 14) * math.exp(-max(0.0, t - FLIP[0]) * 1.1) * 16 * e if t > FLIP[0] else 0.0
    p.save()
    p.translate(0, -18)
    p.rotate(swing)
    p.translate(0, 18)
    path = QPainterPath()
    path.moveTo(-15, 10)
    path.cubicTo(-15, -6, -10, -18, 0, -18)
    path.cubicTo(10, -18, 15, -6, 15, 10)
    path.closeSubpath()
    fill(p, mixc(c.mut, c.acc, e))
    p.drawPath(path)
    stroke(p, mixc(c.mut, c.acc, e), 3)
    line(p, -19, 10, 19, 10)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, 17, 3.6)
    p.restore()
    if e > .5:
        ph = loop(t, 1.0)
        stroke(p, alpha(c.acc, (1 - ph) * .8), 2.4)
        arc(p, 25 + ph * 7, -25, 50, 0, -4)
        arc(p, 25 + ph * 7, 155, 50, 0, -4)
    slash(p, c, 1 - e)


def m_glass(p, t, e, c):
    fill(p, alpha(c.acc, .95))
    dot(p, -9, 0, 17)
    fill(p, alpha(mixc(c.ink, c.acc, .25), lerp(.95, .34, e)))
    dot(p, 9 + 3 * math.sin(t * 2), 0, 17)
    sweep = lerp(-34, 34, loop(t, 1.8))
    stroke(p, alpha(QColor("#ffffff"), .55 * e), 3)
    line(p, sweep - 8, 18, sweep + 8, -18)


def m_gamepad(p, t, e, c):
    col = mixc(c.mut, c.acc, e)
    fill(p, col)
    rr(p, -23, -11, 46, 25, 12)
    fill(p, alpha(QColor("#101010"), .8))
    rr(p, -15, -2, 12, 4, 2)
    rr(p, -11, -6, 4, 12, 2)
    k = int(t * 3) % 2
    for i, (x, y) in enumerate(((12, -4), (17, 2))):
        fill(p, QColor("#ffffff") if (i == k and e > .5) else alpha(QColor("#101010"), .8))
        dot(p, x, y, 3.2)


def m_record(p, t, e, c):
    stroke(p, alpha(c.ink, .8), 2.4)
    dot(p, 0, 0, 22)
    if e > .5:
        pulse = 1 + .16 * math.sin(t * 6)
        fill(p, QColor("#f0524f"))
        dot(p, 0, 0, 10 * pulse)
        fill(p, alpha(QColor("#f0524f"), .5 * (math.sin(t * 6) + 1) / 2))
        dot(p, 0, 0, 15 * pulse)
    else:
        fill(p, c.mut)
        rr(p, -9, -9, 18, 18, 3)


def m_clipboard(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .7), 2.6)
    rr(p, -15, -17, 30, 38, 5)
    fill(p, mixc(c.mut, c.acc, e))
    rr(p, -8, -22, 16, 9, 3)
    for i in range(3):
        k = clamp(e * 2.6 - i * .5 + (math.sin(t * 2 + i) * .08))
        stroke(p, alpha(c.acc, .9), 3)
        line(p, -9, -5 + i * 10, -9 + 18 * k, -5 + i * 10)


def m_eye(p, t, e, c):
    blink = 1.0 - max(0.0, 1 - abs((t % 2.6) - 1.3) * 7) * .9
    open_k = e * blink
    h = 15 * open_k
    path = QPainterPath()
    path.moveTo(-26, 0)
    path.quadTo(0, -h * 1.8, 26, 0)
    path.quadTo(0, h * 1.8, -26, 0)
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    p.drawPath(path)
    if open_k > .25:
        fill(p, c.acc)
        dot(p, 5 * math.sin(t * 1.6), 0, 8 * open_k)
        fill(p, QColor("#101010"))
        dot(p, 5 * math.sin(t * 1.6), 0, 3.6 * open_k)
    else:
        for x in (-14, 0, 14):
            line(p, x, 0, x * 1.05, 7)


def m_filetag(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 2.6)
    path = QPainterPath()
    path.moveTo(-14, -20)
    path.lineTo(6, -20)
    path.lineTo(16, -10)
    path.lineTo(16, 20)
    path.lineTo(-14, 20)
    path.closeSubpath()
    p.drawPath(path)
    line(p, 6, -20, 6, -10)
    line(p, 6, -10, 16, -10)
    txt(p, -14, -4, 30, 14, "file", 10, c.ink, True)
    x = lerp(-6, 0, out(e))
    fill(p, alpha(c.acc, e))
    rr(p, x - 16, 8, 38, 13, 6)
    txt(p, x - 16, 8, 38, 13, ".txt", 9, QColor("#101010"), True)


def m_sparkle(p, t, e, c):
    def star(x, y, r, col, rot=0.0):
        pts = []
        for k in range(8):
            ang = math.radians(k * 45 + rot)
            rad = r if k % 2 == 0 else r * .28
            pts.append((x + math.cos(ang) * rad, y + math.sin(ang) * rad))
        fill(p, col)
        pgon(p, pts)
    pulse = 1 + .18 * math.sin(t * 4)
    star(0, 0, 20 * pulse * (.5 + .5 * e), mixc(c.mut, c.acc, e), t * 20)
    star(-20, -14, 8 * (.6 + .4 * math.sin(t * 3 + 1)), alpha(c.acc, .9 * e))
    star(21, 15, 9 * (.6 + .4 * math.sin(t * 3.4)), alpha(c.ink, .8 * e))


def m_search(p, t, e, c):
    ox, oy = math.cos(t * 2.2) * 7 * e, math.sin(t * 2.2) * 5 * e
    p.save()
    p.translate(ox, oy)
    stroke(p, mixc(c.mut, c.acc, e), 3.6)
    dot(p, -4, -4, 13)
    line(p, 6, 6, 18, 18)
    stroke(p, alpha(c.ink, .55), 2.2)
    arc(p, 8, 110, 70, -4, -4)
    p.restore()


def m_widgets(p, t, e, c):
    for i, (x, y) in enumerate(((-17, -17), (3, -17), (-17, 3), (3, 3))):
        k = back((t - FLIP[0] - i * .12) / .4) if e > .5 else 1 - clamp((t - FLIP[0] - i * .1) / .3)
        k = clamp(k, 0, 1.15) if e > .5 else k
        col = c.acc if i != 3 else mixc(c.acc, c.ink, .5)
        fill(p, alpha(col, .25 + .75 * clamp(k)))
        s = 15 * (.5 + .5 * k)
        rr(p, x + 7.5 - s / 2, y + 7.5 - s / 2 + 2 * math.sin(t * 3 + i), s, s, 4)


def m_chat(p, t, e, c):
    path = QPainterPath()
    path.addRoundedRect(QRectF(-22, -17, 44, 28), 9, 9)
    tail = QPainterPath()
    tail.moveTo(-8, 10)
    tail.lineTo(-14, 21)
    tail.lineTo(2, 11)
    fill(p, mixc(c.mut, c.acc, e))
    p.drawPath(path.united(tail))
    for i in range(3):
        fill(p, QColor("#101010") if e > .2 else c.ink)
        dot(p, -10 + i * 10, -3 - (4 * max(0.0, math.sin(t * 7 - i * .9)) if e > .5 else 0), 3)


def m_taskview(p, t, e, c):
    sp = 11 * e
    for i in range(3):
        a = .35 + .3 * i
        fill(p, alpha(mixc(c.mut, c.acc, e), a))
        stroke(p, alpha(c.ink, .6), 2)
        p.setBrush(alpha(mixc(c.mut, c.acc, e), a))
        rr(p, -22 + (i - 1) * sp + 6, -14 + (i - 1) * sp * .5 + 3 * math.sin(t * 2 + i), 30, 24, 4)


def m_clock(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    dot(p, 0, 0, 22)
    for k in range(12):
        a = math.radians(k * 30)
        stroke(p, alpha(c.ink, .5), 1.6)
        line(p, math.sin(a) * 18, -math.cos(a) * 18, math.sin(a) * 20, -math.cos(a) * 20)
    a = math.radians(t * 20)
    stroke(p, c.ink, 3)
    line(p, 0, 0, math.sin(a) * 11, -math.cos(a) * 11)
    a2 = math.radians(t * 240)
    stroke(p, alpha(c.acc, .35 + .65 * e), 2)
    line(p, 0, 0, math.sin(a2) * 17, -math.cos(a2) * 17)
    fill(p, c.acc)
    dot(p, 0, 0, 2.6)


def m_centerdots(p, t, e, c):
    stroke(p, alpha(c.mut, .9), 2)
    p.setBrush(alpha(c.mut, .18))
    rr(p, -30, 6, 60, 15, 7)
    k = back((t - FLIP[0]) / .6) if e > .5 else 1 - clamp((t - FLIP[0]) / .6)
    for i in range(5):
        left = -26 + i * 11
        center = -22 + i * 11 + 3
        x = lerp(left, center, clamp(k, 0, 1.1)) if e > .5 else lerp(left, center, clamp(k))
        fill(p, c.acc if i != 2 else c.ink)
        rr(p, x, 9 - 2 * max(0.0, math.sin(t * 5 - i * .7)) * e, 8, 8, 3)
    fill(p, alpha(c.ink, .25))
    rr(p, -22, -18, 44, 20, 5)


def m_shield(p, t, e, c):
    path = QPainterPath()
    path.moveTo(0, -24)
    path.cubicTo(10, -18, 18, -17, 21, -16)
    path.cubicTo(21, 4, 14, 16, 0, 24)
    path.cubicTo(-14, 16, -21, 4, -21, -16)
    path.cubicTo(-18, -17, -10, -18, 0, -24)
    glow = .5 + .5 * math.sin(t * 3)
    if e > .5:
        fill(p, alpha(c.acc, .22 + .18 * glow))
        p.drawPath(path.translated(0, 0))
    stroke(p, mixc(c.mut, c.acc, e), 3.4)
    p.drawPath(path)
    k = clamp((t - FLIP[0]) / .5) if e > .5 else 0.0
    stroke(p, alpha(c.acc, 1), 4)
    if c.v == 1:                                       # брандмауэр: кирпичная стена
        for r_ in range(3):
            off = 8 if r_ % 2 else 0
            for b in range(3):
                x = -15 + b * 11 + off - (6 if r_ % 2 else 0)
                stroke(p, alpha(c.acc, .35 + .65 * e), 1.8)
                p.drawRect(QRectF(x, -8 + r_ * 9, 11, 9))
    elif k > 0:
        poly(p, [(-9, 0), (-2, 7), (10, -8)][:1 + int(k * 3 + .999)] if k < 1 else [(-9, 0), (-2, 7), (10, -8)])
    else:
        stroke(p, alpha(c.mut, .8), 3)
        line(p, -8, -6, 8, 8)
        line(p, 8, -6, -8, 8)


def m_bolt(p, t, e, c):
    fl = 1.0 if e < .5 else .75 + .25 * math.sin(t * 18)
    fill(p, mixc(c.mut, c.acc, e))
    pgon(p, [(4, -24), (-14, 3), (-2, 3), (-6, 24), (15, -6), (3, -6)])
    for k in range(4):
        ph = loop(t, .9, k / 4)
        stroke(p, alpha(c.acc, (1 - ph) * .9 * e), 2.2)
        a = math.radians(-30 + k * 90 + 20)
        line(p, math.cos(a) * (20 + ph * 12), math.sin(a) * (20 + ph * 12), math.cos(a) * (24 + ph * 14), math.sin(a) * (24 + ph * 14))


def m_sleep(p, t, e, c):
    path = QPainterPath()
    path.addEllipse(QPointF(-6, 4), 14, 14)
    cut = QPainterPath()
    cut.addEllipse(QPointF(0, -1), 12, 12)
    fill(p, mixc(c.mut, c.acc, e))
    p.drawPath(path.subtracted(cut))
    for i in range(3):
        ph = loop(t, 2.4, i / 3)
        txt(p, 4 + ph * 14, -8 - ph * 22, 16, 16, "z", 8 + i * 4 + ph * 4, alpha(c.ink, (1 - ph) * (.4 + .6 * e)), True)


def m_sun(p, t, e, c):
    warm = mixc(QColor("#9fd3ff"), QColor("#ffb04d"), e)
    for k in range(8):
        a = math.radians(k * 45 + t * 30)
        L = 4 + 4 * math.sin(t * 3 + k)
        stroke(p, alpha(warm, .9), 3)
        line(p, math.cos(a) * 17, math.sin(a) * 17, math.cos(a) * (21 + L), math.sin(a) * (21 + L))
    fill(p, warm)
    dot(p, 0, 0, 12)


def m_battery(p, t, e, c):
    stroke(p, c.ink, 3)
    rr(p, -24, -12, 44, 24, 5)
    fill(p, c.ink)
    rr(p, 21, -5, 4, 10, 2)
    lvl = lerp(.35, 1.0, e) if c.v == 0 else lerp(.9, .35, e)
    fill(p, mixc(QColor("#f0524f"), c.acc, clamp(lvl * 1.4 - .1)))
    rr(p, -21, -9, 38 * lvl * (.97 + .03 * math.sin(t * 5)), 18, 3)
    if e > .5:
        fill(p, QColor("#101010"))
        pgon(p, [(-1, -8), (-8, 2), (-2, 2), (-4, 9), (5, -2), (-1, -2)])


def m_mouse(p, t, e, c):
    stroke(p, c.ink, 2.8)
    rr(p, -13, -20, 26, 40, 13)
    line(p, 0, -20, 0, -4)
    line(p, -13, -4, 13, -4)
    k = int(t * 2) % 2
    left_on = (k == 0) != (e > .5)
    fill(p, alpha(c.acc, .95))
    path = QPainterPath()
    if left_on:
        path.addRoundedRect(QRectF(-13, -20, 13, 16), 6, 6)
    else:
        path.addRoundedRect(QRectF(0, -20, 13, 16), 6, 6)
    p.drawPath(path)
    stroke(p, alpha(c.acc, .9), 2.4)
    arc(p, 24, 40, 70, 0, 0)


def m_keyboard(p, t, e, c):
    n = int(t * 5) % 12
    for r_ in range(3):
        for k in range(5):
            idx = r_ * 4 + k
            on = (idx == n) and e > .3
            fill(p, c.acc if on else alpha(mixc(c.mut, c.ink, .4), .9))
            y = -14 + r_ * 11 + (1.5 if on else 0)
            rr(p, -26 + k * 11 - (3 if r_ == 1 else 0), y, 9, 8, 2)
    fill(p, alpha(mixc(c.mut, c.ink, .4), .9))
    rr(p, -14, 19, 28, 8, 2)


def m_colors(p, t, e, c):
    cols = [QColor("#ff5d5d"), QColor("#4cd964"), QColor("#4aa3ff")]
    for i, col in enumerate(cols):
        a = math.radians(t * 50 + i * 120)
        g = mixc(QColor("#8a8a8a"), col, e)
        fill(p, alpha(g, .72))
        dot(p, math.cos(a) * 9, math.sin(a) * 9, 15)


def m_contrast(p, t, e, c):
    p.save()
    p.rotate(t * 70 * e)
    stroke(p, c.ink, 3)
    dot(p, 0, 0, 21)
    path = QPainterPath()
    path.moveTo(0, -21)
    path.arcTo(QRectF(-21, -21, 42, 42), 90, 180)
    path.closeSubpath()
    fill(p, mixc(c.mut, c.ink, .5 + .5 * e))
    p.drawPath(path)
    p.restore()


def m_touchpad(p, t, e, c):
    stroke(p, c.ink, 2.8)
    rr(p, -24, -17, 48, 34, 6)
    line(p, -24, 9, 24, 9)
    for j in range(8):
        ph = loop(t, 1.8) - j * .03
        x, y = lerp(-14, 14, ph % 1), 0 + 6 * math.sin(ph * 6.28) * e
        fill(p, alpha(c.acc, (1 - j / 8) * (.4 + .6 * e)))
        dot(p, x, y - 2, 5 - j * .4)


def m_vpn(p, t, e, c):
    stroke(p, mixc(c.mut, c.acc, e), 3.2)
    lift = (1 - e) * 5
    p.drawArc(QRectF(-9, -24 - lift, 18, 24), 0, 180 * 16)
    fill(p, mixc(c.mut, c.acc, e))
    rr(p, -14, -4, 28, 22, 5)
    fill(p, QColor("#101010"))
    dot(p, 0, 6, 3)
    for j in range(6):
        a = math.radians(t * 90 + j * 60)
        fill(p, alpha(c.acc, .8 * e))
        dot(p, math.cos(a) * 28, math.sin(a) * 22, 1.8)


def m_pin(p, t, e, c):
    ph = (t - FLIP[0]) if t > FLIP[0] else 0.0
    bounce = abs(math.sin(ph * 6)) * math.exp(-ph * 1.3) * 12 * e
    stroke(p, alpha(c.acc, .5 * e), 2)
    p.drawEllipse(QPointF(0, 22), 12 + 3 * math.sin(t * 3), 3.5)
    p.save()
    p.translate(0, -bounce)
    path = QPainterPath()
    path.moveTo(0, 22)
    path.cubicTo(-18, 2, -14, -20, 0, -20)
    path.cubicTo(14, -20, 18, 2, 0, 22)
    fill(p, mixc(c.mut, c.acc, e))
    p.drawPath(path)
    fill(p, QColor("#101010"))
    dot(p, 0, -6, 5)
    p.restore()
    slash(p, c, 1 - e)


def m_camera(p, t, e, c):
    fill(p, mixc(c.mut, c.ink, .5))
    rr(p, -23, -12, 46, 30, 7)
    rr(p, -9, -17, 18, 8, 3)
    fill(p, QColor("#101010"))
    dot(p, 0, 3, 11)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, 3, 7 * (.3 + .7 * e))
    if e < .5:
        stroke(p, c.bad, 3)
        line(p, -22, 18, 22, -12)
    elif int(t * 2) % 4 == 0:
        fill(p, alpha(QColor("#ffffff"), .9))
        dot(p, 16, -6, 2.6)


def _gear(p, r_out, r_in, teeth, rot):
    pts = []
    n = teeth * 3
    for k in range(n):
        ang = math.radians(k * 360 / n + rot)
        r = r_out if (k % 3) < 2 else r_in
        pts.append((math.cos(ang) * r, math.sin(ang) * r))
    pgon(p, pts)


def m_gear(p, t, e, c):
    fill(p, mixc(c.mut, c.acc, e))
    _gear(p, 24, 18, 8, t * 40 * e)
    fill(p, QColor("#101010"))
    dot(p, 0, 0, 8)
    if c.v == 1:
        fill(p, alpha(c.ink, .8))
        p.save()
        p.translate(24, 14)
        _gear(p, 11, 8, 6, -t * 80 * e)
        p.restore()
    slash(p, c, 1 - e)


def m_printer(p, t, e, c):
    fill(p, mixc(c.mut, c.ink, .55))
    rr(p, -23, -4, 46, 20, 5)
    fill(p, QColor("#f4f4f4"))
    rr(p, -12, -20, 24, 16, 2)
    slide = (loop(t, 1.8) * 16) if e > .5 else 0
    p.save()
    p.setClipRect(QRectF(-30, 12, 60, 30))
    fill(p, QColor("#ffffff"))
    rr(p, -12, 12 - 14 + slide, 24, 22, 2)
    stroke(p, alpha(c.acc, .9), 2)
    for i in range(3):
        line(p, -8, 2 + slide + i * 5, 8, 2 + slide + i * 5)
    p.restore()
    fill(p, c.acc if e > .5 else c.mut)
    dot(p, 15, 3, 2)


def m_db(p, t, e, c):
    for i in range(3):
        y = -14 + i * 13
        fill(p, alpha(mixc(c.mut, c.acc, e), .55 + .15 * i))
        p.drawEllipse(QPointF(0, y), 20, 7)
        fill(p, alpha(mixc(c.mut, c.acc, e), .55 + .15 * i))
        p.drawRect(QRectF(-20, y, 40, 13))
        fill(p, alpha(c.ink, .85))
        p.drawEllipse(QPointF(0, y + 13), 20, 7)
        on = int(t * 3) % 3 == i and e > .4
        fill(p, c.acc if on else alpha(c.ink, .4))
        dot(p, 12, y + 7, 2)


def m_antenna(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .7), 3)
    line(p, 0, 22, -8, 2)
    line(p, 0, 22, 8, 2)
    line(p, -8, 2, 8, 2)
    fill(p, mixc(c.mut, c.acc, e))
    dot(p, 0, -6, 5)
    for j in range(3):
        ph = loop(t, 1.8, j / 3)
        stroke(p, alpha(c.acc, (1 - ph) * .9 * e), 2.4)
        arc(p, 9 + ph * 22, 30, 120, 0, -6)
    slash(p, c, 1 - e)


def m_remote(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    rr(p, -24, -18, 48, 31, 4)
    line(p, 0, 13, 0, 21)
    line(p, -9, 21, 9, 21)
    fill(p, alpha(c.acc, .25 + .3 * e))
    rr(p, -21, -15, 42, 25, 2)
    x, y = 12 * math.sin(t * 1.6) * e, 5 * math.cos(t * 2.2) * e
    fill(p, QColor("#ffffff") if e > .3 else c.mut)
    pgon(p, [(x - 2, y - 7), (x - 2, y + 5), (x + 1.5, y + 2), (x + 5, y + 7), (x + 7, y + 6), (x + 3.5, y + 1), (x + 8, y + 1)])


def m_cube(p, t, e, c):
    sway = math.sin(t * 1.4) * 4 * e
    top = [(0, -22), (20, -11), (0, 0), (-20, -11)]
    left = [(-20, -11), (0, 0), (0, 22), (-20, 11)]
    right = [(20, -11), (0, 0), (0, 22), (20, 11)]
    p.save()
    p.translate(sway, -2 * abs(math.sin(t * 2)) * e)
    base = mixc(c.mut, c.acc, e)
    fill(p, base.lighter(130))
    pgon(p, top)
    fill(p, base)
    pgon(p, left)
    fill(p, base.darker(125))
    pgon(p, right)
    p.restore()
    if c.v == 1:                                       # песочница / ВМ: внутри ещё один кубик
        fill(p, alpha(QColor("#ffffff"), .85 * e))
        dot(p, 0, 0, 3.4)


def m_terminal(p, t, e, c):
    fill(p, QColor("#161616"))
    rr(p, -26, -17, 52, 34, 5)
    fill(p, alpha(c.acc, .9))
    p.drawRoundedRect(QRectF(-26, -17, 52, 8), 5, 5)
    for i in range(3):
        fill(p, alpha(QColor("#ffffff"), .8))
        dot(p, -20 + i * 6, -13, 1.6)
    word = ("sudo" if c.v == 1 else "> _")
    shown = word[:max(0, int((t - .2) * 8))] if e > .5 else ""
    txt(p, -22, -6, 44, 14, ("$ " + shown) if c.v == 1 else shown, 11, c.acc, True, Qt.AlignmentFlag.AlignLeft)
    if int(t * 3) % 2 == 0:
        fill(p, c.acc)
        p.drawRect(QRectF(-21 + (len(shown) + (2 if c.v == 1 else 0)) * 6.4, 6, 7, 2.4))


def m_play(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    rr(p, -25, -17, 50, 34, 6)
    fill(p, mixc(c.mut, c.acc, e))
    s = 1 + .08 * math.sin(t * 5) * e
    pgon(p, [(-6 * s, -9 * s), (-6 * s, 9 * s), (10 * s, 0)])
    fill(p, alpha(c.ink, .3))
    rr(p, -19, 10, 38, 3, 1.5)
    fill(p, c.acc)
    rr(p, -19, 10, 38 * (loop(t, 3.0) if e > .5 else .15), 3, 1.5)


def m_layers(p, t, e, c):
    for i in range(3):
        y = 10 - i * 10 - 3 * math.sin(t * 2 + i) * e
        fill(p, alpha(mixc(c.mut, c.acc, e), .45 + .25 * i))
        pgon(p, [(0, y - 12), (24, y), (0, y + 12), (-24, y)])
    stroke(p, alpha(c.ink, .5), 1.6)
    pgon(p, [(0, -20 - 12), (24, -20), (0, -20 + 12), (-24, -20)])


def m_bulb(p, t, e, c):
    glow = .5 + .5 * math.sin(t * 4)
    if e > .5:
        for k in range(8):
            a = math.radians(k * 45 + 22)
            stroke(p, alpha(c.acc, .35 + .5 * glow), 2.6)
            line(p, math.cos(a) * 20, math.sin(a) * 20 - 4, math.cos(a) * 27, math.sin(a) * 27 - 4)
    fill(p, mixc(c.mut, QColor("#ffd45a"), e))
    dot(p, 0, -5, 13)
    fill(p, mixc(c.mut, c.ink, .7))
    rr(p, -6, 7, 12, 9, 2)
    rr(p, -4, 17, 8, 4, 2)


def m_sync(p, t, e, c):
    for s in (0, 180):
        a0 = t * 150 * e + s
        stroke(p, mixc(c.mut, c.acc, e), 3.6)
        arc(p, 17, a0 + 20, 120)
        ang = math.radians(a0 + 20 + 120)
        x, y = math.cos(ang) * 17, -math.sin(ang) * 17
        fill(p, mixc(c.mut, c.acc, e))
        pgon(p, [(x + 6, y - 2), (x - 5, y - 8), (x - 4, y + 7)])
    p.save()
    p.restore()


def m_finger(p, t, e, c):
    for i in range(4):
        stroke(p, alpha(mixc(c.mut, c.acc, e), .9), 2.6)
        arc(p, 6 + i * 5, 20, 140, 0, 6)
    sc = loop(t, 1.6)
    y = lerp(-20, 22, sc if sc < .5 else 1 - sc)
    stroke(p, alpha(c.acc, .95 * e), 3)
    line(p, -22, y, 22, y)
    fill(p, alpha(c.acc, .15 * e))
    p.drawRect(QRectF(-22, -22, 44, y + 22))


def m_chip(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 2.4)
    for k in range(4):
        x = -12 + k * 8
        line(p, x, -20, x, -14)
        line(p, x, 14, x, 20)
        line(p, -20, x, -14, x)
        line(p, 14, x, 20, x)
    fill(p, mixc(c.mut, c.acc, e))
    rr(p, -14, -14, 28, 28, 5)
    k = .5 + .5 * math.sin(t * 5)
    fill(p, alpha(QColor("#101010"), .5 + .4 * k * e))
    rr(p, -6, -6, 12, 12, 3)


def m_radar(p, t, e, c):
    stroke(p, alpha(c.ink, .5), 1.8)
    for r in (8, 16, 24):
        dot(p, 0, 0, r)
    a = t * 160 * e
    path = QPainterPath()
    path.moveTo(0, 0)
    path.arcTo(QRectF(-24, -24, 48, 48), -a, 40)
    path.closeSubpath()
    fill(p, alpha(c.acc, .55 * e))
    p.drawPath(path)
    for k, (x, y) in enumerate(((-10, -8), (12, 6), (6, -15))):
        fill(p, alpha(c.acc, .3 + .7 * abs(math.sin(t * 2 + k)) * e))
        dot(p, x, y, 2.8)


def m_path(p, t, e, c):
    pts = [(-26, 14), (-14, 14), (-14, 0), (2, 0), (2, -12), (18, -12), (18, 4), (26, 4)]
    n = len(pts) - 1
    k = clamp(e * 1.0) * n
    stroke(p, mixc(c.mut, c.acc, e), 3.2)
    for i in range(n):
        if k >= i + 1:
            line(p, *pts[i], *pts[i + 1])
        elif k > i:
            f = k - i
            line(p, pts[i][0], pts[i][1], lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
    fill(p, c.acc)
    idx = loop(t, 2.2) * n
    i = min(n - 1, int(idx))
    f = idx - i
    dot(p, lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f), 3.4 * e)


def m_closewin(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 2.8)
    rr(p, -24, -17, 48, 34, 5)
    line(p, -24, -8, 24, -8)
    k = back((t - FLIP[0]) / .35) if e > .5 else 0.0
    fill(p, alpha(c.acc, .9 * clamp(k)))
    dot(p, 14, -12.5, 4 * clamp(k, 0, 1.2))
    stroke(p, c.acc if e > .5 else c.mut, 3.4)
    s = 7 * clamp(k, 0, 1)
    line(p, -s, -s + 4, s, s + 4)
    line(p, s, -s + 4, -s, s + 4)


def m_snap(p, t, e, c):
    k = io((t - FLIP[0]) / .7) if e > .5 else 1 - io((t - FLIP[0]) / .7)
    fill(p, alpha(mixc(c.mut, c.acc, e), .9))
    rr(p, lerp(-30, -24, k), -16, lerp(26, 24, k), 32, 4)
    fill(p, alpha(c.ink, .75))
    rr(p, lerp(4, 0, k), -16, lerp(26, 24, k), 32, 4)
    stroke(p, alpha(c.acc, .8 * k), 2)
    line(p, 0, -20, 0, 20)


def m_shake(p, t, e, c):
    ph = t - FLIP[0]
    dx = math.sin(t * 40) * 5 * math.exp(-max(0.0, ph) * 1.2) * e if ph > 0 else 0.0
    p.save()
    p.translate(dx, 0)
    fill(p, alpha(mixc(c.mut, c.acc, e), .95))
    rr(p, -22, -15, 44, 7, 3)
    stroke(p, mixc(c.mut, c.ink, .8), 2.6)
    p.setBrush(alpha(c.ink, .12))
    rr(p, -22, -15, 44, 31, 4)
    p.restore()


def m_speaker(p, t, e, c):
    fill(p, mixc(c.mut, c.ink, .6 + .4 * e))
    pgon(p, [(-24, -6), (-14, -6), (-4, -16), (-4, 16), (-14, 6), (-24, 6)])
    n = 1 if c.v == 1 else 3
    for i in range(n):
        a = .3 + .7 * e * (.5 + .5 * math.sin(t * 5 - i * 1.0))
        stroke(p, alpha(c.acc, a), 3)
        arc(p, 9 + i * 8, -50, 100, 0, 0)
    slash(p, c, 1 - e)


def m_phone(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    rr(p, -12, -22, 24, 42, 6)
    line(p, -4, -17, 4, -17)
    fill(p, alpha(mixc(c.mut, c.acc, e), .5))
    rr(p, -9, -13, 18, 28, 2)
    pulse = 1 + .25 * math.sin(t * 6)
    fill(p, c.acc if e > .3 else c.mut)
    dot(p, 7, -13, 4 * pulse * (.4 + .6 * e))
    for j in range(2):
        ph = loop(t, 1.4, j * .5)
        stroke(p, alpha(c.acc, (1 - ph) * .8 * e), 2)
        arc(p, 18 + ph * 12, -30, 60, 0, 0)


def m_taskbar(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 2.6)
    rr(p, -26, -19, 52, 38, 5)
    shown = e if c.v == 0 else 1 - e
    y = lerp(24, 8, shown)
    p.save()
    p.setClipRect(QRectF(-26, -19, 52, 38))
    fill(p, alpha(c.acc, .9))
    rr(p, -26, y, 52, 11, 3)
    for i in range(4):
        fill(p, QColor("#ffffff"))
        rr(p, -16 + i * 9, y + 3, 5, 5, 1.5)
    p.restore()


def m_film(p, t, e, c):
    fill(p, mixc(c.mut, c.ink, .5))
    rr(p, -26, -17, 52, 34, 4)
    fill(p, QColor("#101010"))
    for k in range(5):
        rr(p, -23 + k * 10, -15, 6, 4, 1)
        rr(p, -23 + k * 10, 11, 6, 4, 1)
    fill(p, alpha(c.acc, .35 + .5 * e))
    rr(p, -22, -9, 44, 18, 2)
    sx = lerp(-26, 26, loop(t, 1.6))
    fill(p, alpha(QColor("#ffffff"), .55 * e))
    pgon(p, [(sx - 4, -9), (sx + 2, -9), (sx - 2, 9), (sx - 8, 9)])


def m_ethernet(p, t, e, c):
    stroke(p, mixc(c.mut, c.ink, .8), 3)
    rr(p, -20, -14, 40, 28, 4)
    for k in range(6):
        line(p, -12 + k * 5, -8, -12 + k * 5, 0)
    fill(p, mixc(c.mut, c.acc, e))
    rr(p, -6, 14, 12, 8, 2)
    for k in range(3):
        ph = loop(t, 1.2, k / 3)
        fill(p, alpha(c.acc, e * (1 - abs(ph - .5) * 1.6)))
        dot(p, lerp(-26, 26, ph), 24, 2.6)
    slash(p, c, 1 - e)


def m_dark(p, t, e, c):
    fill(p, mixc(QColor("#ffd45a"), QColor("#cfd8ff"), e))
    dot(p, 0, 0, 14)
    fill(p, alpha(mixc(QColor("#fff4cc"), QColor("#2b2f45"), e), e))
    dot(p, lerp(24, 7, e), -5, 12 * e)
    for k in range(8):
        a = math.radians(k * 45 + t * 25)
        stroke(p, alpha(QColor("#ffd45a"), 1 - e), 3)
        line(p, math.cos(a) * 19, math.sin(a) * 19, math.cos(a) * 25, math.sin(a) * 25)


def m_folder(p, t, e, c):                               # приложения, окна, прочее «открыть»
    fill(p, mixc(c.mut, c.acc, e))
    path = QPainterPath()
    path.moveTo(-24, -14)
    path.lineTo(-8, -14)
    path.lineTo(-2, -8)
    path.lineTo(24, -8)
    path.lineTo(24, 16)
    path.lineTo(-24, 16)
    path.closeSubpath()
    p.drawPath(path)
    fill(p, alpha(QColor("#ffffff"), .35))
    rr(p, -24, -4 + 3 * math.sin(t * 3), 48, 20, 3)


def m_microphone(p, t, e, c):
    fill(p, mixc(c.mut, c.acc, e))
    rr(p, -8, -22, 16, 28, 8)
    stroke(p, mixc(c.mut, c.acc, e), 3)
    arc(p, 15, 200, 140, 0, -2)
    line(p, 0, 13, 0, 22)
    line(p, -8, 22, 8, 22)


MOTIFS = {k[2:]: v for k, v in list(globals().items()) if k.startswith("m_") and callable(v)}


# ---------- какой переключатель — какая сценка ----------
# (часть названия в нижнем регистре, сценка, вариант). Первое совпадение побеждает, поэтому частное идёт раньше общего.
RULES = [
    ("wi-fi", "wifi", 0), ("wifi", "wifi", 0), ("bluetooth", "bluetooth", 0), ("полёта", "plane", 0),
    ("хот-спот", "hotspot", 0), ("не беспокоить", "moon", 0), ("фокусировка", "moon", 0),
    ("время", "clock", 0), ("часов", "clock", 0), ("секунды", "clock", 0),
    ("уведомлен", "bell", 0), ("прозрачност", "glass", 0),
    ("запись", "record", 0), ("геймпад", "gamepad", 0), ("игров", "gamepad", 0), ("кнопка «гид»", "gamepad", 0),
    ("xbox", "gamepad", 0), ("буфера", "clipboard", 0), ("скрытых", "eye", 0), ("скрыть имя", "eye", 0),
    ("расширен", "filetag", 0), ("анимации windows", "sparkle", 0), ("освещение", "sparkle", 0),
    ("лупа", "search", 0), ("поиск", "search", 0), ("виджет", "widgets", 0), ("мини-прилож", "widgets", 0),
    ("чат на панели", "chat", 0), ("субтитр", "chat", 0), ("текстовые предложения", "chat", 0),
    ("исправлять", "keyboard", 0), ("выделять слова", "keyboard", 0), ("клавиатур", "keyboard", 0),
    ("залипание", "keyboard", 0), ("представление задач", "taskview", 0), ("alt+tab", "taskview", 0),
    ("прикрепление окон", "snap", 0), ("встряхивание", "shake", 0), ("часовой пояс", "clock", 0),
    ("по центру", "centerdots", 0), ("значки приложений", "centerdots", 0), ("мигание", "centerdots", 0),
    ("значок", "centerdots", 0), ("защита защитника", "shield", 0), ("брандмауэр", "shield", 1),
    ("быстрый запуск", "bolt", 0), ("гибернац", "sleep", 0), ("спящ", "sleep", 0), ("отключение экрана", "sleep", 0),
    ("ночной свет", "sun", 0), ("автояркость", "sun", 0), ("экономия заряда", "battery", 0),
    ("обмен кнопок", "mouse", 0), ("указател", "mouse", 0), ("прокрутка неактивных", "mouse", 0),
    ("цветовые фильтры", "colors", 0), ("акцентный цвет", "colors", 0), ("высокий контраст", "contrast", 0),
    ("сенсорная", "touchpad", 0), ("vpn", "vpn", 0), ("прокси", "vpn", 0), ("геолокац", "pin", 0),
    ("камер", "camera", 0), ("принтер", "printer", 0), ("печат", "printer", 0), ("реестр", "db", 0),
    ("телеметр", "antenna", 0), ("отчёты об ошибках", "antenna", 0), ("удалённый рабочий", "remote", 0),
    ("удалённый помощ", "remote", 0), ("hyper-v", "cube", 0), ("виртуальных", "cube", 1), ("песочница", "cube", 1),
    (".net", "cube", 0), ("smb", "cube", 1), ("linux", "terminal", 0), ("telnet", "terminal", 0),
    ("sudo", "terminal", 1), ("терминал", "terminal", 0), ("выполнить", "terminal", 0), ("разработчик", "terminal", 0),
    ("media", "play", 0), ("видео", "film", 0), ("фоновые", "layers", 0), ("советы", "bulb", 0),
    ("предложения по использованию", "bulb", 0), ("синхрониз", "sync", 0), ("обновлен", "sync", 0),
    ("подключённые устройства", "sync", 0), ("биометр", "finger", 0), ("gpu", "chip", 0), ("памяти", "chip", 0),
    ("драйвер", "chip", 0), ("портал устройств", "radar", 0), ("обнаружение", "radar", 0),
    ("поблизости", "radar", 0), ("длинные пути", "path", 0), ("завершение задачи", "closewin", 0),
    ("монозвук", "speaker", 1), ("мобильн", "phone", 0), ("автоматически скрывать", "taskbar", 0),
    ("«пуск»", "taskbar", 1), ("в пуске", "taskbar", 1), ("начальном экране", "taskbar", 1), ("в меню «пуск»", "taskbar", 1),
    ("дальнем углу", "taskbar", 1), ("панели задач", "taskbar", 1), ("контекстное меню", "taskbar", 1),
    ("ethernet", "ethernet", 0), ("лимитн", "ethernet", 1), ("списках переходов", "taskbar", 1),
    ("факса", "gear", 1), ("служб", "gear", 0), ("windows управляет", "printer", 0), ("случайные", "wifi", 0),
    ("адаптер", "ethernet", 0), ("приложен", "folder", 0), ("устройств", "phone", 0), ("окон", "taskview", 0),
    ("звук", "speaker", 0), ("громк", "speaker", 0), ("яркост", "sun", 0), ("тёмн", "dark", 0), ("темн", "dark", 0),
    ("тем", "dark", 0), ("микрофон", "microphone", 0), ("мыш", "mouse", 0), ("экран", "sleep", 0),
    ("прокрутки", "mouse", 0), ("повтора", "keyboard", 0),
]


def pick_motif(name, explicit=None):
    """(сценка, вариант) для переключателя по названию. Своё слово не нашлось — общая сценка."""
    if explicit and explicit in MOTIFS:
        return explicit, 0
    n = str(name or "").lower()
    for key, motif, var in RULES:
        if key in n and motif in MOTIFS:
            return motif, var
    return "generic", 0


def _hash(name):
    return int(hashlib.md5(str(name or "").encode("utf-8")).hexdigest(), 16)


def look_for(name):
    """Свой «почерк» переключателя: фоновый эффект (0–4), сдвиг оттенка и скорость — берутся из названия."""
    h = _hash(name)
    return {"fx": h % 5, "hue": (h >> 8) % 61 - 30, "speed": .85 + ((h >> 16) % 31) / 100.0}


def backdrop(p, t, e, c, kind, R):
    """Фон сценки: волны, искры, блик, орбита или свечение — у каждого переключателя свой."""
    if kind == 0:                                    # расходящиеся круги
        for j in range(3):
            ph = loop(t, 2.4, j / 3)
            stroke(p, alpha(c.acc, (1 - ph) * .35 * (.4 + .6 * e)), 1.6)
            dot(p, 0, 0, R * (.7 + ph * .75))
    elif kind == 1:                                  # искры поднимаются вверх
        for j in range(9):
            ph = loop(t, 2.0 + (j % 3) * .4, j / 9)
            x = math.sin(j * 2.3) * R * .9
            fill(p, alpha(c.acc, (1 - ph) * .75 * e))
            dot(p, x, R * .8 - ph * R * 1.7, 1.2 + (j % 3) * .6)
    elif kind == 2:                                  # диагональный блик
        k = loop(t, 2.6)
        x = lerp(-R * 1.3, R * 1.3, k)
        fill(p, alpha(QColor("#ffffff"), .13 * (.3 + .7 * e)))
        pgon(p, [(x - 10, R), (x + 4, R), (x + 22, -R), (x + 8, -R)])
    elif kind == 3:                                  # точки по орбите
        for j in range(4):
            a = math.radians(t * 70 + j * 90)
            fill(p, alpha(c.acc, .55 * (.3 + .7 * e)))
            dot(p, math.cos(a) * R * 1.1, math.sin(a) * R * .9, 2.2)
    else:                                            # мягкое дыхание света
        g = .5 + .5 * math.sin(t * 2.2)
        fill(p, alpha(c.acc, (.06 + .09 * g) * (.4 + .6 * e)))
        dot(p, 0, 0, R * (1.0 + .12 * g))


# ---------- карточка ----------
def _fmt_time(sec):
    sec = max(0, int(math.ceil(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class SwitchCard(QWidget):
    """Карточка-анимация в ленте чата. spec: kind (toggle / slider / timer / choice / mute), name, on, value, prev,
    lo, hi, unit, label, secs, motif (по желанию)."""
    H = 158

    def __init__(self, spec, accent="#FFCFA3", dark=True, parent=None):
        super().__init__(parent)
        from ui import chatlook
        pal = chatlook.PALETTE[bool(dark)]
        self.spec = dict(spec or {})
        self.dark = bool(dark)
        self.name = str(self.spec.get("name") or "")
        self.kind = self.spec.get("kind") or "toggle"
        motif, var = pick_motif(self.name, self.spec.get("motif"))
        self.motif, self.var = motif, var
        self.look = look_for(self.name)
        self._pal = pal
        self._accent = QColor(accent or "#FFCFA3")
        h, s, l, a = self._accent.getHslF()
        if h >= 0:
            self._accent.setHslF((h + self.look["hue"] / 360.0) % 1.0, s, l, a)
        self.setFixedHeight(self.H)
        self.setMinimumWidth(270)
        self.setMaximumWidth(440)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Нажми, чтобы показать ещё раз")
        self._t0 = time.monotonic()
        self._born = self._t0                  # настоящий отсчёт таймера идёт от создания карточки и не сбрасывается при повторе анимации
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def replay(self):
        self._t0 = time.monotonic()
        if not self._timer.isActive():
            self._timer.start()

    def mousePressEvent(self, e):
        self.replay()
        super().mousePressEvent(e)

    def sizeHint(self):
        return QSize(380, self.H)

    def _left(self):
        """Сколько секунд осталось у настоящего таймера."""
        return max(0.0, float(self.spec.get("secs") or 0) - (time.monotonic() - self._born))

    def _tick(self):
        if time.monotonic() - self._t0 > DUR + .1:
            if self.kind == "timer" and self._left() > 0:
                self._timer.setInterval(250)           # таймер идёт в реальном времени: обновляем раз в четверть секунды
            else:
                self._timer.stop()
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        if time.monotonic() - self._t0 > DUR + .1 and not getattr(self, "_shown_once", False):
            self.replay()
        self._shown_once = True

    # --- рисование ---
    def _font(self, px, bold=False):
        f = QFont()
        try:
            from ui import theme
            f = QFont(theme.FONT_DISPLAY if bold else theme.FONT_FAMILY)
        except Exception:
            pass
        f.setPixelSize(int(px))
        if bold:
            f.setWeight(QFont.Weight.DemiBold)
        return f

    def _text(self, p, x, y, w, h, text, px, col, bold=False, align=None):
        p.setFont(self._font(px, bold))
        p.setPen(QColor(col))
        flags = int((align or Qt.AlignmentFlag.AlignLeft).value) | int(Qt.AlignmentFlag.AlignVCenter.value)
        p.drawText(QRectF(x, y, w, h), flags, str(text))

    def _state(self, t):
        k = io((t - FLIP[0]) / (FLIP[1] - FLIP[0]))
        if self.kind in ("toggle", "mute"):
            on = bool(self.spec.get("on"))
            return k if on else 1 - k, k
        return k, k

    def paintEvent(self, _):
        W, H = self.width(), self.H
        t = min(DUR, time.monotonic() - self._t0)
        tm = t * self.look["speed"]
        e, k = self._state(t)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        pal, acc = self._pal, self._accent
        ink, mut = QColor(pal["text"]), QColor(pal["muted"])
        card = QRectF(2, 2, W - 4, H - 14)
        # вход: карточка чуть въезжает и проявляется
        a_in = clamp(t / .35)
        p.setOpacity(a_in)
        p.translate(0, (1 - out(t / .45)) * 10)
        path = QPainterPath()
        path.addRoundedRect(card, 18, 18)
        p.fillPath(path.translated(0, 8), QColor(0, 0, 0, 95 if self.dark else 40))
        p.fillPath(path, QColor(pal["card"]))
        p.setPen(QPen(QColor(pal["stroke"]), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        title = self.spec.get("title") or self.name
        self._text(p, 20, 12, W - 150, 30, title, 15, ink, True)
        c = Ctx(acc, ink, mut, QColor("#ef5350"), self.var)
        cx, cy = W - 74, 70
        if self.kind == "timer":
            self._paint_timer(p, t, W, H, ink, mut, acc)
        else:
            p.save()
            p.translate(cx, cy)
            backdrop(p, tm, e, c, self.look["fx"], 36)
            p.setClipRect(QRectF(-46, -46, 92, 92))
            try:
                MOTIFS.get(self.motif, m_generic)(p, tm, e, c)
            except Exception:
                m_generic(p, tm, e, c)
            p.restore()
            if self.kind in ("slider",):
                self._paint_slider(p, t, k, W, H, ink, mut, acc)
            else:
                self._paint_toggle(p, t, e, k, W, H, ink, mut, acc)
        p.end()

    def _paint_toggle(self, p, t, e, k, W, H, ink, mut, acc):
        pal = self._pal
        stroke(p, alpha(ink, .55), 1.3)
        for j, wd in enumerate((.34, .26, .16)):                     # «строки» заглушки, как на карточке из знакомства
            rr(p, 20, 54 + j * 17, max(40, (W - 150) * wd * 2.2), 8, 4)
        by = H - 44
        if self.kind == "choice":
            label = self.spec.get("label") or ""
            self._text(p, 20, by - 17, W - 150, 34, label, 15, ink, True)
            return
        on = bool(self.spec.get("on")) if self.kind in ("toggle", "mute") else True
        word = ("Включено" if (e > .5) else "Выключено")
        self._text(p, 20, by - 17, W - 150, 34, word, 16, ink, True)
        tr = QRectF(W - 20 - 58, by - 15, 58, 30)
        fill(p, mixc(QColor("#6b6b6b") if self.dark else QColor("#c8c8c8"), acc, e))
        p.drawRoundedRect(tr, 15, 15)
        kx = tr.left() + 15 + 28 * clamp(e, 0, 1) + 3 * math.sin(clamp(k, 0, 1) * math.pi) * (1 if on else -1)
        fill(p, QColor(0, 0, 0, 50))
        dot(p, kx, tr.center().y() + 1.5, 11)
        fill(p, QColor("#ffffff"))
        dot(p, kx, tr.center().y(), 11)

    def _paint_slider(self, p, t, k, W, H, ink, mut, acc):
        lo, hi = float(self.spec.get("lo", 0)), float(self.spec.get("hi", 100))
        v1 = float(self.spec.get("value", hi))
        v0 = float(self.spec.get("prev", lo if v1 > (lo + hi) / 2 else hi))
        v = lerp(v0, v1, k)
        f = (v - lo) / (hi - lo) if hi > lo else 0
        unit = self.spec.get("unit", "%")
        lab = self.spec.get("label") or ""
        tr = QRectF(20, 66, W - 150, 8)
        fill(p, QColor(self._pal["stroke"]))
        p.drawRoundedRect(tr, 4, 4)
        fill(p, acc)
        p.drawRoundedRect(QRectF(tr.left(), tr.top(), tr.width() * f, 8), 4, 4)
        fill(p, QColor(0, 0, 0, 50))
        dot(p, tr.left() + tr.width() * f, tr.center().y() + 1.5, 11)
        fill(p, QColor("#ffffff"))
        dot(p, tr.left() + tr.width() * f, tr.center().y(), 11)
        shown = lab if (lab and k >= 1.0) else (f"{int(round(v))}{unit}" if unit != "" else f"{int(round(v))}")
        self._text(p, 20, H - 64, W - 150, 40, shown, 28, ink, True)

    def _paint_timer(self, p, t, W, H, ink, mut, acc):
        secs = max(1.0, float(self.spec.get("secs") or 5))
        left = self._left()                              # настоящий остаток: 10 минут — это 10 минут, а не 4 секунды анимации
        f = left / secs * out(t / .9)                    # кольцо в начале «заполняется», потом убывает по-настоящему
        cx, cy, R = W - 80, 72, 44
        base = QPen(QColor(self._pal["stroke"]), 9)
        base.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(base)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), R, R)
        pen = QPen(acc, 9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        if f > 0.004:
            p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R), 90 * 16, int(f * 360 * 16))
        num = str(int(math.ceil(left))) if secs <= 99 else (str(int(math.ceil(left / 60))) if secs <= 5999 else str(int(math.ceil(left / 3600))))
        self._text(p, cx - R, cy - R, 2 * R, 2 * R, num, 30 if len(num) < 3 else 22, ink, True, Qt.AlignmentFlag.AlignHCenter)
        self._text(p, 20, H - 86, W - 150, 40, _fmt_time(left), 30, ink, True)
        sub = (self.spec.get("label") or "идёт отсчёт…") if left > 0 else "время вышло!"
        self._text(p, 20, H - 50, W - 150, 24, sub, 13, mut)


def build_row(spec, accent, dark, parent=None):
    """Карточка в обёртке с отступом слева — под сообщение Mico в ленте."""
    from PyQt6.QtWidgets import QHBoxLayout
    wrap = QWidget(parent)
    lay = QHBoxLayout(wrap)
    lay.setContentsMargins(12, 4, 12, 6)
    card = SwitchCard(spec, accent, dark, wrap)
    lay.addStretch(1)                                    # карточка стоит по центру ленты, а не прижата вправо
    lay.addWidget(card, 100)
    lay.addStretch(1)
    wrap.card = card
    return wrap
