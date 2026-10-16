"""Реакция на ошибки (Mico WI): программа перестала отвечать или на экране окно с ошибкой.
Решения — здесь, без Qt. Вызовы Windows — в probe(), только чтение: ничего не закрываем и не нажимаем."""
import re

ERROR_TITLE = re.compile(r"ошиб|error|исключени|сбой|не отвечает|not responding|предупреждени|warning", re.I)
DIALOG_CLASS = "#32770"    # стандартное окно сообщения Windows
HUNG_CONFIRM = 3           # столько проверок подряд (по 2 с) программа молчит — только тогда говорим
COOLDOWN_SEC = 600         # про одно и то же окно не напоминаем чаще, чем раз в 10 минут
MAX_TEXT = 1500            # сколько текста окна отдаём модели


class HangTracker:
    """Считает, сколько проверок подряд окно молчит. Возвращает True один раз, когда молчание подтвердилось."""

    def __init__(self):
        self.count, self.alerted = {}, {}

    def observe(self, key, hung, now):
        if not hung:
            self.count.pop(key, None)
            return False
        n = self.count.get(key, 0) + 1
        self.count[key] = n
        if n < HUNG_CONFIRM or not due(self.alerted.get(key), now):
            return False
        self.alerted[key] = now
        return True


def due(last, now, gap=COOLDOWN_SEC):
    """Прошло ли достаточно времени с прошлого напоминания (last None — ещё не напоминали)."""
    return last is None or now - last >= gap


def is_error_dialog(cls, title):
    return cls == DIALOG_CLASS and bool(ERROR_TITLE.search(title or ""))


def joined_text(parts):
    """Тексты окна без повторов и пустых строк, не длиннее MAX_TEXT."""
    seen, out = set(), []
    for p in parts:
        s = " ".join(str(p or "").split())
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return "\n".join(out)[:MAX_TEXT]


def probe(own_pid, proc_of):
    """Окно на переднем плане: (hwnd, программа, класс, заголовок, молчит ли, текст окна ошибки или '').
    None — если окна нет, оно наше или его не удалось прочитать."""
    try:
        import ctypes
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or not win32gui.IsWindowVisible(hwnd):
            return None
        if win32process.GetWindowThreadProcessId(hwnd)[1] == own_pid:
            return None
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
        hung = bool(ctypes.windll.user32.IsHungAppWindow(hwnd))
        text = ""
        if is_error_dialog(cls, title):
            parts = []

            def take(child, _):
                try:
                    if win32gui.GetClassName(child) == "Static":
                        parts.append(win32gui.GetWindowText(child))
                except Exception:
                    pass
                return True
            win32gui.EnumChildWindows(hwnd, take, None)
            text = joined_text(parts)
        return hwnd, proc_of(hwnd) or "", cls, title, hung, text
    except Exception:
        return None
