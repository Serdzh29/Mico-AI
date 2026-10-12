"""Инициатива: Mico сам заговаривает, если на экране появилось что-то, что стоит прокомментировать.
Правила: не чаще заданного интервала, только когда сменилось активное окно, не в приватных окнах,
не во время разговора или набора текста, и не повторяет уже сказанное. Чистая логика — tests/test_initiative.py."""
import re

WORD = re.compile(r"[а-яёa-z0-9]{4,}", re.IGNORECASE)
REPEAT_SHARE = 0.6            # если половина смысловых слов совпала с прошлой фразой — это повтор
KEEP = 5                      # сколько последних фраз помнить для проверки повторов


def _words(text):
    # основа слова (первые 5 букв): «погода» и «погоду» — одно и то же
    return {w.lower().replace("ё", "е")[:5] for w in WORD.findall(text or "")}


class Gate:
    def __init__(self, min_gap=15 * 60):
        self.min_gap = min_gap
        self.last_look = None          # когда в последний раз смотрели на экран
        self.last_window = None        # какое окно было на экране тогда
        self.recent = []               # последние сказанные фразы

    def should_look(self, now, window, busy, blocked, paused):
        """Можно ли сейчас посмотреть на экран и, возможно, заговорить.
        busy — идёт разговор или человек печатает; paused — режим тишины или Mico спит."""
        if paused or busy or blocked or window is None:
            return False
        if self.last_look is not None and now - self.last_look < self.min_gap:
            return False
        return window != self.last_window          # то же окно уже смотрели — не повторяемся

    def looked(self, now, window):
        self.last_look, self.last_window = now, window

    def is_repeat(self, text):
        mine = _words(text)
        if not mine:
            return True
        for old in self.recent:
            theirs = _words(old)
            if theirs and len(mine & theirs) >= REPEAT_SHARE * min(len(mine), len(theirs)):
                return True
        return False

    def remember(self, text):
        self.recent = (self.recent + [text])[-KEEP:]
