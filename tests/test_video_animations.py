"""Анимации «как в видео»: рот попадает в слоги, брови живут по отдельности, поворот вокруг оси, появление.
Qt не нужен: проверяется логика состояния (_life) на подменённом времени."""
import os as _os, sys, types, math, random
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
exec(open(_os.path.join(ROOT, "tests", "test_animations.py"), encoding="utf-8").read().split("import blob as Bl")[0])
import blob as Bl

def make():
    b = Bl.Blob.__new__(Bl.Blob)
    b.anim, b.talking, b.asleep, b.typing_until = None, False, False, 0
    b.squash = b.squash_v = 0.0
    b.start_anim = lambda name: setattr(b, "anim", (name, 0, 1))
    return b

random.seed(1)
b = make()
# 1. при речи рот открывается и меняет форму; без речи закрывается
shapes, t = set(), 100.0
b.talking = True
for _ in range(600):
    t += 1 / 60
    Bl.Blob._life(b, t, 1 / 60)
    shapes.add((round(b.mw, 2), round(b.mh, 2)))
assert max(h for _, h in shapes) > 0.05 and len(shapes) > 40, "рот не двигается"
assert b.talk_amt > 0.9
b.talking = False
for _ in range(120):
    t += 1 / 60
    Bl.Blob._life(b, t, 1 / 60)
assert b.mh < 0.012 and b.talk_amt < 0.05, (b.mh, b.talk_amt)

# 2. брови: левая и правая движутся независимо, в разумных пределах
b = make(); b.talking = True; t = 200.0
seen = set()
for _ in range(900):
    t += 1 / 60
    Bl.Blob._life(b, t, 1 / 60)
    seen.add((round(b.brow_l, 2), round(b.brow_r, 2)))
    assert abs(b.brow_l) < 0.2 and abs(b.brow_r) < 0.2 and abs(b.face_dx) < 0.2 and abs(b.face_dy) < 0.2
assert any(l != r for l, r in seen), "брови ходят синхронно"

# 3. во время разговора запускаются радость / наклон головы / двойное моргание
b = make(); b.talking = True; t = 300.0; started = set()
for _ in range(60 * 40):
    t += 1 / 60
    Bl.Blob._life(b, t, 1 / 60)
    if b.anim:
        started.add(b.anim[0]); b.anim = None
assert started and started <= {"headtilt", "blink2"}, started      # смешка во время разговора нет

# 4. форма «плывёт» во времени и остаётся замкнутой и ограниченной
vals = [Bl.pebble(a / 10, 1.0, tt) for tt in (0, 7, 15, 31) for a in range(63)]
assert 0.7 < min(vals) and max(vals) < 1.3, (min(vals), max(vals))
assert Bl.pebble(1.0, 1.0, 0) != Bl.pebble(1.0, 1.0, 9), "форма не меняется"
assert abs(Bl.ease_out_back(0)) < 1e-9 and abs(Bl.ease_out_back(1) - 1) < 1e-9 and max(Bl.ease_out_back(x / 100) for x in range(101)) > 1.0
print("ALL OK video animations")
