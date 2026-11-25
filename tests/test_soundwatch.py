"""Звук и корзина (soundwatch.py): когда Mico начинает и перестаёт танцевать, когда корзину «съели».
Без Windows: громкость и корзина подаются вручную. Запуск: python tests/test_soundwatch.py"""
import ast, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from voice import sound as S


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def run(h, steps):
    """steps: [(громкость, секунды)] — кадры каждые 0.4 с. Возвращает, что вернул feed на каждом кадре."""
    t, out = 0.0, []
    for peak, secs in steps:
        for _ in range(int(secs / 0.4)):
            out.append(h.feed(peak, t))
            t += 0.4
    return out


def test_short_sound_does_not_start_dancing():
    h = S.Hysteresis()
    changes = run(h, [(0.5, 0.8), (0.0, 1.0)])
    check(not any(changes) and not h.on, "щелчок звука — не танец")


def test_music_starts_dancing_after_start_sec():
    h = S.Hysteresis()
    changes = run(h, [(0.2, 2.0)])
    check(h.on and changes.count(True) == 1, "музыка идёт — танцуем один раз")


def test_brief_pause_in_music_keeps_dancing():
    h = S.Hysteresis()
    run(h, [(0.2, 2.0)])
    changes = run(h, [(0.0, 1.5), (0.2, 2.0)])          # пауза короче STOP_SEC
    check(h.on and not any(changes), "короткая пауза — танец продолжается")


def test_silence_stops_dancing_after_stop_sec():
    h = S.Hysteresis()
    run(h, [(0.2, 2.0)])
    changes = run(h, [(0.0, 4.0)])
    check(not h.on and changes.count(True) == 1, "тишина — танец кончился один раз")


def test_quiet_level_between_thresholds_is_not_silence():
    h = S.Hysteresis()
    run(h, [(0.2, 2.0)])
    run(h, [(0.012, 6.0)])                              # тихо, но не тишина
    check(h.on, "слабый звук не выключает танец")


def test_bin_emptied_only_when_it_had_items():
    check(S.bin_emptied(5, 0) is True, "было 5, стало 0 — очистили")
    check(S.bin_emptied(0, 0) is False, "и было пусто, и сейчас пусто — ничего не съели")
    check(S.bin_emptied(None, 0) is False, "первый замер — не событие")
    check(S.bin_emptied(3, 2) is False, "часть удалили — не очистка")


def test_soundwatch_has_no_qt_import():
    tree = ast.parse(open(os.path.join(ROOT, "voice/sound.py"), encoding="utf-8").read())
    names = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
    names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
    check(not any("PyQt" in n for n in names), "модуль не тянет Qt — его можно проверять без окна")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK soundwatch")
