import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import sleepmode as SM


def test_limit_minutes_to_seconds():
    assert SM.limit_seconds(3) == 180
    assert SM.limit_seconds("2.5") == 150
    assert SM.limit_seconds(0) == 0                    # 0 — не засыпать
    assert SM.limit_seconds(None) == 180               # испорченная настройка — значение по умолчанию


def test_sleeps_only_after_limit_without_attention():
    assert not SM.should_sleep(now=179, last_attention=0, limit_sec=180, busy=False)
    assert SM.should_sleep(now=180, last_attention=0, limit_sec=180, busy=False)


def test_busy_or_disabled_never_sleeps():
    assert not SM.should_sleep(now=1000, last_attention=0, limit_sec=180, busy=True)   # идёт разговор
    assert not SM.should_sleep(now=1000, last_attention=0, limit_sec=0, busy=False)    # выключено


def test_attention_resets_countdown():
    # обращение в 100-й секунде: до 280-й ещё не спит, с 280-й — спит
    assert not SM.should_sleep(now=279, last_attention=100, limit_sec=180, busy=False)
    assert SM.should_sleep(now=280, last_attention=100, limit_sec=180, busy=False)


def test_corner_spot_is_bottom_right_with_margin():
    # рабочая область 0..1920 x 0..1040 (правая и нижняя границы не входят)
    x, y = SM.corner_spot((0, 0, 1920, 1040), 100, margin=6)
    assert (x, y) == (1920 - 100 - 6, 1040 - 100 - 6)


def test_corner_spot_all_four_corners():
    avail = (0, 0, 1920, 1040)
    assert SM.corner_spot(avail, 100, "br", margin=6) == (1814, 934)
    assert SM.corner_spot(avail, 100, "bl", margin=6) == (6, 934)
    assert SM.corner_spot(avail, 100, "tr", margin=6) == (1814, 6)
    assert SM.corner_spot(avail, 100, "tl", margin=6) == (6, 6)


def test_corner_spot_respects_taskbar_offset():
    # панель задач сверху 40 px: верхние углы начинаются ниже неё
    assert SM.corner_spot((0, 40, 1920, 1040), 100, "tl", margin=6) == (6, 46)


def test_unknown_corner_falls_back_to_bottom_right():
    assert SM.corner_spot((0, 0, 1920, 1040), 100, "zz", margin=6) == (1814, 934)


def test_home_corner_awake_is_placement_or_free():
    assert SM.home_corner(False, "manual", "br") is None        # стоит, где поставил
    assert SM.home_corner(False, "tl", "br") == "tl"            # выбран угол — держится в нём
    assert SM.home_corner(False, None, "br") is None            # старый конфиг без поля — свободно
    assert SM.home_corner(False, "bogus", "br") is None


def test_home_corner_asleep_is_bottom_center():
    assert SM.home_corner(True, "tr", "bl") == SM.SPOT           # во сне — внизу по центру, как и просили
    assert SM.home_corner(True, "manual", "tr") == SM.SPOT
    assert SM.home_corner(True, "tr", "bogus") == SM.SPOT
    assert 0.5 <= SM.SLEEP_SCALE <= 0.7                          # уменьшается, но не слишком сильно


def test_ease_converges_and_snaps():
    v, dt = 1.0, 0.016
    for _ in range(400):
        v = SM.ease(v, SM.SLEEP_SCALE, dt)
    assert v == SM.SLEEP_SCALE
    assert SM.ease(0.5, 0.5, dt) == 0.5                # уже на месте — не двигается


def test_ease_moves_toward_target_monotonically():
    a = SM.ease(1.0, 0.42, 0.016)
    assert 0.42 < a < 1.0


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
