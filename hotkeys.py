"""Глобальные горячие клавиши Windows (работают, даже когда окно Mico скрыто).
Отдельный поток с циклом сообщений: RegisterHotKey привязан к потоку."""
import ctypes
import re
import threading
from ctypes import wintypes

MODS = {"alt": 0x0001, "ctrl": 0x0002, "shift": 0x0004, "win": 0x0008}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312


def parse(combo):
    """'ctrl+alt+m' -> (модификаторы, код клавиши) или None, если не разобрать."""
    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    if not parts:
        return None
    key = parts[-1]
    mods = 0
    for p in parts[:-1]:
        if p not in MODS:
            return None
        mods |= MODS[p]
    if len(key) == 1 and (key.isalpha() or key.isdigit()):
        vk = ord(key.upper())
    elif re.fullmatch(r"f([1-9]|1[0-2])", key):
        vk = 0x70 + int(key[1:]) - 1
    else:
        return None
    if mods == 0:
        return None                      # без модификатора такие сочетания мешают обычной работе
    return mods, vk



class HotkeyThread(threading.Thread):
    def __init__(self, bindings, on_fire):
        """bindings: {id: 'ctrl+alt+m'}; on_fire(id) вызывается из фонового потока."""
        super().__init__(daemon=True)
        self.bindings, self.on_fire = bindings, on_fire
        self.failed = []                 # сочетания, которые Windows не дала занять
        self.ready = threading.Event()

    def run(self):
        u = ctypes.windll.user32
        registered = []
        for hid, combo in self.bindings.items():
            p = parse(combo)
            if p is None or not u.RegisterHotKey(None, hid, p[0] | MOD_NOREPEAT, p[1]):
                self.failed.append(combo)
            else:
                registered.append(hid)
        self.ready.set()
        msg = wintypes.MSG()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                self.on_fire(int(msg.wParam))
        for hid in registered:
            u.UnregisterHotKey(None, hid)
