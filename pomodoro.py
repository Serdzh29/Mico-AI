"""Помодоро: 25 минут работы, 5 минут перерыва. Считает завершённые циклы за день."""
import threading, time

WORK, REST = 25 * 60, 5 * 60


class Pomodoro:
    def __init__(self, notify, on_cycle_done, work=WORK, rest=REST):
        self.notify, self.on_cycle_done = notify, on_cycle_done
        self.work, self.rest = work, rest
        self.phase, self.timer, self.started = None, None, 0.0

    def running(self):
        return self.phase is not None

    def start(self):
        if self.running():
            return False
        self._phase("work")
        return True

    def stop(self):
        if self.timer:
            self.timer.cancel()
        was = self.running()
        self.phase, self.timer = None, None
        return was

    def _phase(self, name):
        self.phase = name
        self.started = time.time()
        length = self.work if name == "work" else self.rest
        self.timer = threading.Timer(length, self._finish, args=(name,))
        self.timer.daemon = True
        self.timer.start()
        if name == "work":
            self.notify("🍅 Помодоро: 25 минут работы. Я напомню про перерыв.")
        else:
            self.notify("☕ Перерыв 5 минут. Встань, разомнись.")

    def _finish(self, name):
        if name == "work":
            self.on_cycle_done()
            self._phase("rest")
        else:
            self.stop()
            self.notify("Перерыв закончился. Готов к следующему циклу? Скажи «помодоро».")

