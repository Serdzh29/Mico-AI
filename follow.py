"""Наблюдатель за окнами: помнит последнее окно, с которым работает пользователь (для ответов и погоды).
Mico AI по окнам не ходит: его положение задаёт настройка «Положение»."""
import os

import win32gui, win32process
from PyQt6.QtCore import QObject, QTimer

IGNORE_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "NotifyIconOverflowWindow",
                  "XamlExplorerHostIslandWindow", "TopLevelWindowForOverflowXamlIsland"}


class WindowWatcher(QObject):
    def __init__(self):
        super().__init__()
        self.last_hwnd = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(400)

    def tick(self):
        try:
            fg = win32gui.GetForegroundWindow()
            if fg and win32process.GetWindowThreadProcessId(fg)[1] != os.getpid() \
                    and win32gui.GetClassName(fg) not in IGNORE_CLASSES and win32gui.IsWindowVisible(fg):
                self.last_hwnd = fg
        except Exception:
            return
