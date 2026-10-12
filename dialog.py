"""Память диалога: что говорили недавно, чтобы понимать «а если больше?», «сделай так же», «он сломался».
Помнит реплики пользователя и ответы Mico, в том числе ответы команд, в пределах окна по времени.
Чистая логика без Qt и без модели — проверяется в tests/test_dialog.py."""
import re, time

WINDOW_SEC = 15 * 60          # через столько без общения контекст забывается
MAX_TURNS = 12                # сколько последних реплик помнить
MAX_CHARS = 400               # длина одной реплики в контексте (чтобы промпт не раздувался)
MAX_REWRITE = 200             # переписанная фраза длиннее этого — считаем, что модель запуталась

# начало фразы, которое обычно продолжает разговор
FOLLOWUP_RE = re.compile(
    r"^(а |и |ещё|еще|больше|меньше|ну |тоже|также|так же|то же|сделай|наоборот|давай|теперь|"
    r"вот (это|так)|а если|а вот|он |она |оно |его |её |ее |их |там |это )", re.IGNORECASE)


class Dialog:
    def __init__(self, window=WINDOW_SEC, max_turns=MAX_TURNS):
        self.window, self.max_turns = window, max_turns
        self.turns = []                                   # [(время, роль: 'user' | 'mico', текст)]

    def add(self, role, text, now=None):
        text = (text or "").strip()
        if not text:
            return
        self.turns.append((now or time.time(), role, text[:MAX_CHARS]))
        del self.turns[:-self.max_turns]

    def recent(self, now=None):
        """Реплики, которые ещё помнятся (не старше окна), от старых к новым."""
        now = now or time.time()
        self.turns = [t for t in self.turns if now - t[0] <= self.window]
        return self.turns[-self.max_turns:]

    def messages(self, now=None, limit=8):
        """Реплики в формате чат-модели (user / assistant)."""
        role = {"user": "user", "mico": "assistant"}
        return [{"role": role[r], "content": text} for _, r, text in self.recent(now)[-limit:]]

    def is_followup(self, q, now=None):
        """Похоже ли сообщение на продолжение разговора: есть недавний контекст и фраза из двух слов
        или начинается с продолжающего слова. Так не переписываем каждый короткий вопрос, экономим время."""
        if not self.recent(now):
            return False
        s = q.strip().lower()
        return len(s.split()) <= 2 or FOLLOWUP_RE.match(s) is not None

    def rewrite_prompt(self, q, now=None):
        """Просьба к модели: переписать продолжение разговора как самостоятельную фразу."""
        lines = []
        for _, r, text in self.recent(now):
            lines.append(("Пользователь: " if r == "user" else "Mico: ") + text)
        return ("Вот недавний разговор с Mico:\n" + "\n".join(lines) +
                f"\n\nНовая реплика пользователя: «{q.strip()}»\n"
                "Перепиши новую реплику одной самостоятельной фразой, которую можно понять без разговора "
                "(например, «а если больше» после «громкость 30» — это «громкость 40»). "
                "Ответь только этой фразой. Если понять нельзя — ответь ровно: НЕТ")

    @staticmethod
    def clean_rewrite(answer, original):
        """Чистит ответ модели. None — переписывать нечего: модель не поняла или ответила то же самое."""
        if not answer:
            return None
        s = answer.strip().splitlines()[0].strip().rstrip(".!").strip().strip("«»\"'`").strip()
        if not s or s.upper() == "НЕТ" or len(s) > MAX_REWRITE:
            return None
        if s.lower() == (original or "").strip().lower().rstrip(".!"):
            return None
        return s
