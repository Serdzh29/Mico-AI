"""Напоминание о перерыве: если человек работает без перерыва дольше заданного времени, Mico AI советует отдохнуть.
Перерыв — это простой дольше IDLE_RESET: мышь и клавиатура не трогались. Напоминание идёт и когда Mico AI спит.
Чистая логика без Qt — проверяется в tests/test_breaks.py."""
import time

IDLE_RESET = 5 * 60            # простой дольше этого — перерыв засчитан, отсчёт начинается заново, сек
COOLDOWN = 15 * 60             # минимум между двумя напоминаниями о перерыве, сек
BREAK_TEXT = ("Ты работаешь без перерыва уже {minutes} мин. Может, встанешь и разомнёшься? "
              "Могу напомнить через 10 минут: «напомни через 10 минут отдохнуть».")


class BreakWatch:
    def __init__(self, break_minutes=60, start=None):
        self.break_seconds = max(5, int(break_minutes)) * 60
        self.session_start = start if start is not None else time.time()
        self.notified = False                  # уже напомнили в этой сессии
        self.last_message = None

    def set_minutes(self, minutes):
        self.break_seconds = max(5, int(minutes)) * 60

    def tick(self, now, idle, allowed=True):
        """Вызывать раз в 30 секунд. idle — секунды без ввода. allowed=False — напоминать не надо
        (режим тишины или отключено), но отсчёт перерыва всё равно ведём."""
        if idle > IDLE_RESET:                  # был перерыв: сессия начинается заново
            self.session_start = now
            self.notified = False
        if not allowed or self.notified:
            return None
        if self.last_message is not None and now - self.last_message < COOLDOWN:
            return None
        if now - self.session_start >= self.break_seconds:
            self.notified = True
            self.last_message = now
            return BREAK_TEXT.format(minutes=int((now - self.session_start) // 60))
        return None
