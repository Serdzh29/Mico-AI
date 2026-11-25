"""Фоновый учёт активности: какое окно/процесс было активно и сколько времени."""
import ctypes, os, threading, time
import psutil, win32gui, win32process


class _LII(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float:
    lii = _LII(ctypes.sizeof(_LII), 0)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    return (ctypes.windll.kernel32.GetTickCount() - lii.dwTime) / 1000.0


class Tracker(threading.Thread):
    def __init__(self, store, cfg):
        super().__init__(daemon=True)
        self.store, self.cfg = store, cfg
        self.paused = False
        self.last_hwnd = None      # последнее НЕ-Mico окно
        self.last_blocked = False
        self._cur = None           # (key, start, process, title)

    def is_blocked(self, process, title):
        p, t = process.lower(), title.lower()
        return (any(x in p for x in self.cfg["block_processes"]) or
                any(x in t for x in self.cfg["block_titles"]))

    def _flush(self):
        if self._cur:
            _, start, proc, title = self._cur
            if time.time() - start >= 3:
                self.store.add(start, time.time(), proc, title)
        self._cur = None

    def run(self):
        while True:
            time.sleep(2)
            try:
                if self.paused or idle_seconds() > 300:
                    self._flush()
                    continue
                hwnd = win32gui.GetForegroundWindow()
                pid = win32process.GetWindowThreadProcessId(hwnd)[1]
                if not hwnd or pid == os.getpid():
                    continue
                proc = psutil.Process(pid).name()
                title = win32gui.GetWindowText(hwnd)
                blocked = self.is_blocked(proc, title)
                self.last_hwnd, self.last_blocked = hwnd, blocked
                if blocked:
                    title = "[скрыто]"
                key = (proc, title)
                if not self._cur or self._cur[0] != key:
                    self._flush()
                    self._cur = (key, time.time(), proc, title)
            except Exception:
                pass
