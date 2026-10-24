"""Палитра в чате: Mico крутится (как в видео, ~1,2 с), на середине поворота меняет цвет и плавно его переливает.
Qt не нужен: проверяется логика состояния на подменённом времени и подключение сигналов по исходникам."""
import os as _os, sys, re, time
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
exec(open(_os.path.join(ROOT, "tests", "test_animations.py"), encoding="utf-8").read().split("import blob as Bl")[0])
import blob as Bl

clock = [1000.0]
time.time = lambda: clock[0]          # start_anim и anim_u берут время отсюда


class Rec:
    def __init__(self):
        self.got = []

    def emit(self, value):
        self.got.append(value)


def make(color="#FFCFA3"):
    b = Bl.Blob.__new__(Bl.Blob)
    b.anim, b.talking, b.asleep, b.typing_until = None, False, False, 0
    b.squash = b.squash_v = 0.0
    b.cfg = {"color": color}
    b.color_set = Rec()
    return b


def run(b, seconds):
    steps = int(round(seconds * 60))
    for _ in range(steps):
        clock[0] += 1 / 60
        Bl.Blob._life(b, clock[0], 1 / 60)


# 1. поворот короткий, как в видео (~1,2 с), и он в таблице анимаций
src = open(_os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
assert re.search(r'"spin":\s*1\.2\b', src), "длительность поворота должна быть 1.2 с"

# 2. выбор цвета запускает поворот, но сам цвет ещё не меняется
b = make()
b.pick_color("#b8c0ff")
assert b.anim and b.anim[0] == "spin" and b.anim[2] == 1.2, b.anim
assert b.cfg["color"] == "#FFCFA3" and b.color_set.got == [], "цвет поменялся до поворота"

# 3. до середины поворота цвет не меняется
run(b, 0.5)
assert b.cfg["color"] == "#FFCFA3" and b.color_set.got == [], "цвет поменялся слишком рано"

# 4. на середине поворота цвет применяется и сообщается наверх (main сохранит его)
run(b, 0.2)
assert b.cfg["color"] == "#B8C0FF", b.cfg
assert b.color_set.got == ["#B8C0FF"], b.color_set.got
assert b._pending_color is None and b._col_from is not None, "нет переливания от старого цвета"

# 5. после поворота переливание выключается, цвет остаётся новым
b.anim = None
run(b, 0.1)
assert b._col_from is None and b.cfg["color"] == "#B8C0FF"

# 6. тот же цвет ничего не делает: без поворота и без сигнала
c = make("#9FD3FF")
c.pick_color("#9fd3ff")
assert c.anim is None and c.color_set.got == [], "повтор того же цвета не должен крутить Mico"

# 7. два выбора подряд: последний побеждает и тоже проходит через поворот
d = make()
d.pick_color("#A8E6CF")
run(d, 0.3)
d.pick_color("#F6D365")
run(d, 1.5)
assert d.cfg["color"] == "#F6D365", d.cfg
assert d.color_set.got[-1] == "#F6D365"

# 8. сплошная проверка: во время поворота не падает отрисовка логики (smooth в пределах 0..1)
for x in (-1, 0, 0.25, 0.5, 0.75, 1, 2):
    k = Bl.smooth(x)
    assert 0.0 <= k <= 1.0, (x, k)
assert Bl.smooth(0.5) == 0.5 and Bl.smooth(0) == 0 and Bl.smooth(1) == 1

# 9. палитра в чате использует те же цвета, что при первом запуске
ob = open(_os.path.join(ROOT, "onboarding.py"), encoding="utf-8").read()
onb = re.findall(r'\("(#[0-9A-Fa-f]{6})", "[^"]+"\)', ob)
assert len(onb) == 6, onb
wc = open(_os.path.join(ROOT, "aichat.py"), encoding="utf-8").read()
assert "from onboarding import COLORS as PALETTE" in wc, "палитра должна браться из onboarding"
assert 'Цвет Mico AI…' in wc, "пункт цвета остаётся в коде меню"
assert "self.side.settings.connect" not in wc, "кнопки «Настройки Mico AI» в боковом меню больше нет"
assert "color_pick = pyqtSignal(str)" in wc and "self.color_pick.emit(hex_c)" in wc   # полоска цветов внутри чата

# 10. связка: чат → Mico (intel_ui) и Mico → сохранение и перекраска (main)
iu = open(_os.path.join(ROOT, "intel_ui.py"), encoding="utf-8").read()
assert "self.aichat.color_pick.connect(self.blob.pick_color)" in iu
mn = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
assert "blob.color_set.connect(" in mn and "save_cfg(cfg)" in mn.split("blob.color_set.connect(")[1][:120]

print("ALL OK palette spin")
