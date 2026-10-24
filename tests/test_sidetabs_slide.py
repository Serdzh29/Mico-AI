"""Боковое меню настроек: полоска выбранного пункта плавно переезжает (как в видео), старая полоска в делегате убрана."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _src():
    return open(_os.path.join(ROOT, "sidetabs.py"), encoding="utf-8").read()


def test_bar_slides_between_items():
    s = _src()
    assert "QPropertyAnimation(self._bar, b\"geometry\"" in s, "полоска анимируется по геометрии"
    assert "setEasingCurve(QEasingCurve.Type.OutCubic)" in s, "плавный выход"
    assert "self._slide.start()" in s and "self._slide.setEndValue(target)" in s, "переезд к новому пункту"


def test_bar_follows_selected_item_and_layout():
    s = _src()
    assert "visualItemRect" in s, "полоска берёт место пункта из списка"
    assert "def resizeEvent" in s and "def showEvent" in s, "полоска встаёт на место при изменении окна"


def test_old_static_bar_removed():
    s = _src()
    assert "painter.drawRoundedRect" not in s, "старая полоска в делегате убрана, не будет двух полосок"
    assert "def paint(self, painter" not in s, "делегат ничего не рисует сам: иконки и пункты рисует стиль"


def test_animation_uses_regular_icons_only():
    """Анимация иконки — смена обычных иконок-кадров, а не рисование поверх пункта (оттуда был съезд)."""
    s = _src()
    assert "icon_frame(" in s, "кадры анимации — обычные иконки того же размера"
    assert "painter.translate" not in s and "option.icon" not in s, "рисования поверх пункта нет"


def test_selected_icon_not_shifted():
    """Иконка выбранного раздела стоит на одной линии с остальными: никакого съезда влево."""
    s = _src()
    for bad in ("SHIFT_PX", "sel_k", "sel_row", "_deco_dx", "_sel_anim", "_on_sel_anim"):
        assert bad not in s, f"съезд иконки убран: {bad}"


def test_api_unchanged_for_settings_dialog():
    s = _src()
    for name in ("def addTab", "def setCurrentIndex", "def setTabEnabled", "def set_accent", "def widget", "def count"):
        assert name in s, name


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
