import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, os, time
sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "requests", "cryptography", "cryptography.fernet"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
sys.modules["cryptography.fernet"].Fernet = object
sys.modules["requests"].RequestException = Exception
import winctl as W
calls = []
def rec(name, ret=None):
    def f(*a, **k):
        calls.append((name, a)); return ret
    return f
W.press = rec("press")
W.get_volume = rec("get_volume", 40)
W.set_volume = rec("set_volume", 50)
W.change_volume = rec("change_volume", 55)
W.set_mute = rec("mute")
W.get_brightness = rec("get_brightness", 50)
W.set_brightness = rec("set_brightness", 60)
W.radio = rec("radio", (True, ""))
W.reg_set = rec("reg_set"); W.broadcast_setting = rec("bcast"); W.shell_refresh = rec("refresh")
W.run_elevated = rec("run_elevated", (False, "нужны права администратора"))
W.set_service = rec("set_service", (True, ""))
W.set_feature = rec("set_feature", (True, ""))
W.set_defender_realtime = rec("defender", (True, ""))
W.set_firewall = rec("firewall", (True, ""))
W.run_quiet = rec("run_quiet", True)
W.open_path = rec("open_path")
W.check_updates = lambda: (calls.append(("check_updates", ())), (True, ""))[1]
W.swap_mouse_buttons = rec("swap")
W.airplane = rec("airplane", (True, ""))
W.hotspot = rec("hotspot", (True, ""))
W.set_theme = rec("theme")
W.abort_shutdown = rec("abort")

import commands as C
C.os.startfile = rec("startfile")   # на Linux нет os.startfile
def say(q):
    calls.clear()
    r = C.handle(q)
    print(f"{q!r:28} -> {(r.text if r else None)!r:70.70} | {[c[0] for c in calls]}")
    return r

say("переключи трек")
say("дальше")
say("назад")
say("громче")
say("ещё")
say("назад")
say("выключи вайфай")
say("а блютуз?")
say("проверь обновления")
say("выключи защитник")
say("включи hyper-v")
say("выключи службу поиска Windows")
say("сбрось сеть")
say("да")
say("включи секунды в часах")
say("дальше")
say("яркость 30")
say("назад")
say("выключи звук")
say("ещё")
say("выключи службу поиска Windows")
say("выключи телеметрию")
say("включи wsl")
say("проверь целостность системы")
