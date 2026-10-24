import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)
import typo as T

class FakeStore:
    def __init__(self):
        self.fx, self.wd = {}, set()
    def load_fixes(self): return dict(self.fx)
    def load_words(self): return list(self.wd)
    def save_fix(self, a, b): self.fx[a] = b
    def save_word(self, w): self.wd.add(w)

st = FakeStore()
c = T.Corrector(st, extra={"блютуз", "вайфай"})
for src, want in [("открй ютуб", "открой ютуб"), ("переключи трек", "переключи трек"),
                  ("выключи вайфай", "выключи вайфай"), ("громчее", "громче"),
                  ("дальшее", "дальше"), ("Открй Блокнот", "Открой Блокнот")]:
    out, ch = c.correct(src)
    print(f"{src!r:22} -> {out!r:22} {'OK' if out == want else 'FAIL want '+want} {ch}")
    assert out == want, (src, out)
print("note:", repr(T.note([("открй", "открой")])))

# обучение: фраза не сработала, похожая сработала -> запоминаем замену
c.observe("блютс вкл", "блютс вкл", handled=False)
c.observe("блютс вкл", "блютуз вкл", handled=True)
out, ch = c.correct("блютс вкл")
print("learned:", out, ch); assert "блютуз" in out
assert st.fx.get("блютс") == "блютуз"
# слова из успешных фраз попадают в словарь и в хранилище
c.observe("включи ньютонию", "включи ньютонию", handled=True)
assert "ньютонию" in st.wd
# новый экземпляр — всё подтянулось из хранилища
c2 = T.Corrector(st)
assert c2.correct("блютс")[0] == "блютуз"
# забыть
c2.forget(); assert c2.correct("блютс")[0] == "блютс" or c2.fixes == {}
print("ALL OK")
