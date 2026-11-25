"""Значок Mico берётся прямо у живого Mico приложения: его же тело, лицо и цвет. Раньше везде лежала старая картинка
assets/mico.png, поэтому значок в настройках и окнах отличался от настоящего Mico."""
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QIcon, QPixmap

COLOR = "#FFCFA3"                 # цвет Mico из настроек (main обновляет его при запуске и при смене цвета)
_CACHE = {}


def _render(color):
    from ui.blob import Blob, BASE_PX
    big = 180                                               # рисуем крупно, потом уменьшаем: края получаются гладкими
    b = Blob({"color": color, "scale": big / BASE_PX, "opacity": 1.0, "sleep_after_min": 0, "assist_style": "classic",
              "placement": "manual", "sleep_corner": "br", "anim_sleep_fps": 20})
    b.can_sleep = lambda: False
    b.timer.stop()
    b.anim = None                                           # без «выскакивания» при запуске: иначе Mico в кадре ещё не вырос и значок пустой
    b._fade = None
    b.asleep, b.size_k = False, 1.0
    b.set_mood("happy", 999)
    for _ in range(14):                                     # несколько кадров: лицо и тело встают в обычный вид
        b.tick()
    pix = QPixmap(b.width(), b.height())
    pix.fill(Qt.GlobalColor.transparent)
    b.render(pix)
    b.timer.stop()
    b.deleteLater()
    img = pix.toImage()
    x0, y0, x1, y1 = img.width(), img.height(), -1, -1
    for y in range(0, img.height(), 2):                     # рамка по видимому телу: поля вокруг Mico обрезаем
        for x in range(0, img.width(), 2):
            if img.pixelColor(x, y).alpha() > 24:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    if x1 < 0:
        return pix
    side = max(x1 - x0, y1 - y0) + 8
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    return pix.copy(QRect(cx - side // 2, cy - side // 2, side, side))


def blob_pixmap(size, color=None):
    """Значок Mico нужного размера в его настоящем виде. Результат кешируется по цвету."""
    color = str(color or COLOR)
    key = color.lower()
    if key not in _CACHE:
        try:
            _CACHE[key] = _render(color)
        except Exception:
            _CACHE[key] = None
    big = _CACHE[key]
    if big is None or big.isNull():
        return None
    return big.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def blob_icon(color=None, sizes=(16, 24, 32, 48, 64, 128)):
    icon = QIcon()
    for s in sizes:
        pm = blob_pixmap(s, color)
        if pm is not None:
            icon.addPixmap(pm)
    return icon


def set_color(color):
    global COLOR
    COLOR = str(color or COLOR)
