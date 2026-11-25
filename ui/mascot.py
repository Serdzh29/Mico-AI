"""Живой Mico внутри окна (приветствие и другие диалоги): тот же блоб, что на рабочем столе —
дышит, моргает, меняет настроение. Кадры настоящего Blob рисуются в картинку, отдельного окна нет."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel


class LiveMico(QLabel):
    FRAME_MS = 33

    def __init__(self, size=150, color="#FFCFA3", mood="happy", parent=None):
        super().__init__(parent)
        from ui.blob import Blob, BASE_PX
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._blob = Blob({"color": color, "scale": size / BASE_PX, "opacity": 1.0, "sleep_after_min": 0,
                           "assist_style": "classic", "placement": "manual", "sleep_corner": "br",
                           "anim_sleep_fps": 20})
        self._blob.can_sleep = lambda: False                 # в окне Mico не засыпает
        self._blob.timer.stop()                              # кадры двигаем сами
        self._blob.set_mood(mood, 999)
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._frame)
        self._timer.start()
        self._frame()

    def set_color(self, hex_color):
        self._blob.cfg["color"] = hex_color
        try:
            self._blob.pick_color(hex_color)                 # та же смена цвета с поворотом, что на рабочем столе
        except Exception:
            pass
        self._blob.set_mood("happy", 3)
        self._blob.jump(200)

    def set_mood(self, mood, secs=4):
        self._blob.set_mood(mood, secs)

    def _frame(self):
        self._blob.tick()
        pix = QPixmap(self._blob.width(), self._blob.height())
        pix.fill(Qt.GlobalColor.transparent)
        self._blob.render(pix)
        self.setPixmap(pix)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def showEvent(self, e):
        self._timer.start()
        super().showEvent(e)
