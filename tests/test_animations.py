"""Проверка всех анимаций Mico: простои, реакции на события, вращение, подмигивание, моргание.
Qt подменён заглушкой, поэтому проверяется логика (старт, длительность, кадры, завершение), а не картинка."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, re, random
sys.path.insert(0, ROOT)

class _Any:
    """Любой вызов и атрибут возвращают заглушку: нужно, чтобы не тянуть настоящий Qt."""
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Any()
    def __getattr__(self, name): return _Any()
    def __iter__(self): return iter(())
    def __int__(self): return 0
    def __float__(self): return 0.0
    def __bool__(self): return False
    def __lt__(self, o): return False
    def __gt__(self, o): return False
    def __le__(self, o): return True
    def __ge__(self, o): return True
    def __eq__(self, o): return False
    def __hash__(self): return 0
    def __add__(self, o): return _Any()
    __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __truediv__ = __rtruediv__ = __add__
    def __neg__(self): return _Any()
    def __abs__(self): return _Any()

class _Signal:
    def __init__(self, *a): pass
    def __get__(self, obj, owner): return _Any()

class _QWidget(_Any):
    def __init__(self, *a, **k): pass

def _mod(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m

_Any_ = _Any
qt = _mod("PyQt6")
_mod("PyQt6.QtCore", Qt=_Any_(), QTimer=_Any_, QPointF=lambda *a: _Any_(), QPoint=lambda *a: _Any_(),
     QRectF=lambda *a: _Any_(), pyqtSignal=lambda *a: _Signal(), QObject=_QWidget)
_mod("PyQt6.QtGui", QPainter=_Any_(), QColor=lambda *a: _Any_(), QRadialGradient=_Any_(), QPainterPath=_Any_(),
     QPen=_Any_(), QCursor=_Any_(), QGuiApplication=_Any_(), QFont=_Any_())
_mod("PyQt6.QtWidgets", QWidget=_QWidget)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "requests", "cryptography",
          "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["cryptography.fernet"].Fernet = object

import blob as Bl

src = open(_os.path.join(ROOT, "blob.py"), encoding="utf-8").read()

# 1. все запускаемые анимации описаны в таблице длительностей
table = set(re.findall(r'"(\w+)":\s*[\d.]+', re.search(r"dur = \{(.*?)\}\[name\]", src, re.S).group(1)))
starts = set(re.findall(r'start_anim\(["\'](\w+)["\']\)', src)) | set(
    re.findall(r'start_anim\(random\.choice\(\[(.*?)\]\)', src, re.S) and
    re.findall(r'"(\w+)"', re.search(r'start_anim\(random\.choice\(\[(.*?)\]\)', src, re.S).group(1)))
assert starts <= table, f"анимации без длительности: {starts - table}"
used_elsewhere = set(re.findall(r'blob\.start_anim\("(\w+)"\)', open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()))
assert used_elsewhere <= table, used_elsewhere - table

# 2. простой не запускает прыжки и сердечко
idle_names = set(re.findall(r'"(\w+)"', re.search(r'start_anim\(random\.choice\(\[(.*?)\]\)', src, re.S).group(1)))
assert idle_names == {"lookaround", "blink2", "wink"}, idle_names
assert "hop" not in table and "heart" not in table, table

# 3. каждая анимация из таблицы стартует, идёт по кадрам 0..1 и завершается
class Clock:
    now = 1000.0
clock = Clock()
import time as _time
_time.time = lambda: clock.now

def make_blob():
    b = Bl.Blob.__new__(Bl.Blob)
    b.anim = None
    b.jv = 0.0
    b.jh = 0.0
    b.jump_calls = 0
    b.jump = lambda power=280: setattr(b, "jv", power) or setattr(b, "jump_calls", b.jump_calls + 1)
    return b

for name in sorted(table):
    b = make_blob()
    Bl.Blob.start_anim(b, name)
    assert b.anim and b.anim[0] == name, name
    u0 = Bl.Blob.anim_u(b)
    assert u0 == 0.0, (name, u0)
    dur = b.anim[2]
    clock.now += dur * 0.5
    mid = Bl.Blob.anim_u(b)
    assert 0.0 < mid < 1.0, (name, mid)
    clock.now += dur
    assert Bl.Blob.anim_u(b) == 1.0, name
    clock.now = 1000.0

# 4. старт анимации не вызывает прыжок (раньше «hop» прыгал сам)
b = make_blob()
for name in sorted(table):
    Bl.Blob.start_anim(b, name)
assert b.jump_calls == 0, b.jump_calls

# 5. реакции на события сохранены (прыжок — ответ на радость/удивление/пробуждение, а не случайный)
main_src = open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read()
assert main_src.count("self.blob.jump()") >= 2
print("ALL OK, анимаций:", len(table), sorted(table))

# 6. отрисовка кадра проходит для каждой анимации и каждого настроения, без исключений
class _Cfg(dict):
    pass
for name in sorted(table) + [None]:
    for mood in ("idle", "happy", "love", "playful", "sleepy"):
        b = make_blob()
        b.cfg = {"color": "#FFCFA3", "scale": 1.0, "opacity": 1.0}
        b.mood = mood
        b.mood_until = 0
        b.talking = False
        b.squash = 0.0
        b.heart = 1.0 if mood == "love" else 0.0
        b.tilt = 0.0
        b.blink_until = 0
        b.typing_until = 0
        b.t0 = 0
        b.anim = (name, 1000.0, 1.0) if name else None
        b.width = lambda: 240
        b.height = lambda: 240
        b.last_input = 1000.0
        b.blink_at = 9e9
        b.size_k = 1.0
        b.effective_mood = lambda m=mood: m
        b.anim_u = lambda: 0.5 if name else None
        b.paint_ok = True
        b.mapFromGlobal = lambda p: _Any()
        b.cfg["color"] = "#FFCFA3"
        try:
            Bl.Blob.paintEvent(b, None)
        except Exception as e:
            raise AssertionError(f"отрисовка упала: анимация={name}, настроение={mood}: {type(e).__name__}: {e}")
print("ALL OK paint")
