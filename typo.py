"""Понимание опечаток и обучение на ошибках пользователя.
Источники знаний — только то, что пользователь пишет Mico сам (его чат):
  1) словарь команд и названий переключателей;
  2) слова из фраз, которые Mico успешно выполнил (так словарь растёт под пользователя);
  3) исправления: если фраза не сработала, а следующая, похожая на неё, сработала — запоминаем замену.
Ничего из других программ (браузер, мессенджеры) не читается."""
import difflib, re

TOKEN = re.compile(r"[а-яёa-z][а-яёa-z-]*", re.IGNORECASE)

BASE_VOCAB = set("""
открой открыть закрой закрыть запусти запустить включи включить выключи выключить отключи отключить
поставь установи сделай переключи переключить найди найти загугли напомни громче тише громкость яркость
ярче темнее дальше назад пауза заблокируй сверни разверни покажи проверь таймер будильник скриншот
настройки переведи буфер экран трек следующий предыдущий музыку звук блютуз вайфай интернет тему
светлую темную режим полёта проводник обновления обновлений перезагрузи перезагрузка выключить пк
спящий громче ещё еще мико
""".split())


def _norm(w):
    return w.lower().replace("ё", "е")


class Corrector:
    def __init__(self, store=None, extra=()):
        self.store = store
        self.vocab = {_norm(w) for w in BASE_VOCAB | set(extra)}
        self.fixes = {}
        self.last_failed = None
        if store is not None:
            self.fixes = {_norm(k): _norm(v) for k, v in store.load_fixes().items()}
            self.vocab |= {_norm(w) for w in store.load_words()}

    # ---------- исправление ----------
    def _closest(self, w):
        c = difflib.get_close_matches(w, self.vocab, n=1, cutoff=0.8)
        return c[0] if c and abs(len(c[0]) - len(w)) <= 2 else None

    def correct(self, text):
        """Возвращает (исправленный текст, [(было, стало)])."""
        changes = []

        def repl(m):
            w = m.group(0)
            lw = _norm(w)
            if len(lw) < 4 or lw in self.vocab:
                return w
            fix = self.fixes.get(lw) or self._closest(lw)
            if fix and fix != lw:
                if w[0].isupper():
                    fix = fix[0].upper() + fix[1:]
                changes.append((w, fix))
                return fix
            return w
        return TOKEN.sub(repl, text), changes

    # ---------- обучение ----------
    def observe(self, original, used, handled, changes=()):
        """original — что написал пользователь, used — что реально выполнили, handled — сработала ли команда."""
        toks_used = [_norm(t) for t in TOKEN.findall(used)]
        if not handled:
            self.last_failed = [_norm(t) for t in TOKEN.findall(original)]
            return
        if self.last_failed and len(self.last_failed) == len(toks_used):
            for a, b in zip(self.last_failed, toks_used):
                if a != b and difflib.SequenceMatcher(None, a, b).ratio() >= 0.6 and len(a) >= 3:
                    self.fixes[a] = b                       # «открй» → «открой» запомнено
                    if self.store is not None:
                        self.store.save_fix(a, b)
        self.last_failed = None
        new = [t for t in toks_used if len(t) >= 4 and t not in self.vocab]
        for t in new[:5]:
            self.vocab.add(t)                               # слово, которое пользователь написал правильно
            if self.store is not None:
                self.store.save_word(t)

    def forget(self):
        self.fixes.clear()
        self.last_failed = None
        self.vocab = {_norm(w) for w in BASE_VOCAB}


def note(changes):
    """Короткая пометка, что Mico понял фразу иначе: «(понял как «открой»)»."""
    if not changes:
        return ""
    fixed = ", ".join(f"«{b}»" for _, b in changes[:3])
    return f"(понял как {fixed}) "
