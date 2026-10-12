"""Каждый пример из «Что ты умеешь» должен куда-то попадать: команды Windows либо один из модулей Mico.
Фразы, которые обрабатывает Brain (память, индекс, справка, планировщик), в список для commands не входят."""
import os as _os, sys as _sys, types
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "win32gui", "win32process", "win32con", "requests",
          "cryptography", "cryptography.fernet"]:
    _sys.modules.setdefault(m, types.ModuleType(m))
_sys.modules["mss"].mss = object
_sys.modules["PIL"].Image = types.SimpleNamespace()
_sys.modules["cryptography.fernet"].Fernet = object
_sys.modules["requests"].RequestException = Exception

import capabilities as C
import winctl as W
from actions import Reply

# Фразы, которые обрабатывает не commands, а Brain (память, индекс, справка, знания, планировщик, экран)
BRAIN_ONLY = {"помодоро", "напомни каждый понедельник в 9:00 проверить отчёт", "сравни 24h2 и 25h2", "что я делал час назад?", "что я делал вчера", "проиндексируй компьютер", "найди договор",
              "что у меня на экране?", "какая у меня версия Windows", "где найти настройку Bluetooth",
              "как изменить тему", "что такое гибернация", "как перезапустить проводник", "сделай скриншот",
              "подготовь рабочее место", "переведи буфер обмена"}


def _stub_windows():
    for name in ["press", "get_volume", "set_volume", "change_volume", "set_mute", "get_brightness",
                 "set_brightness", "radio", "reg_set", "broadcast_setting", "shell_refresh", "run_elevated",
                 "set_service", "set_feature", "set_defender_realtime", "set_firewall", "run_quiet",
                 "open_path", "check_updates", "swap_mouse_buttons", "airplane", "hotspot", "set_theme"]:
        setattr(W, name, lambda *a, **k: (True, "") if name in ("run_elevated", "set_service", "set_feature",
                                                               "set_defender_realtime", "set_firewall",
                                                               "check_updates", "airplane", "hotspot") else True)


def test_examples_reach_a_handler():
    import commands
    _stub_windows()
    commands.os.startfile = lambda *a, **k: None
    commands.subprocess.Popen = lambda *a, **k: None
    commands.subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr="")
    unhandled = []
    for _, items in C.CATEGORIES:
        for phrase, _ in items:
            if phrase in BRAIN_ONLY:
                continue
            try:
                r = commands.handle(phrase, lambda t: None, lambda: None)
            except Exception as e:
                r = Reply(f"ошибка: {e}")
            if r is None:
                unhandled.append(phrase)
    assert not unhandled, unhandled


def test_html_links_round_trip():
    import re, urllib.parse
    beta = {"update_channel": "beta"}
    links = re.findall(r'href="mico-do:([^"]+)"', C.html_capabilities(beta))
    phrases = [p for _, items in C.CATEGORIES for p, _ in items]
    assert [urllib.parse.unquote(x) for x in links] == phrases


def test_stable_channel_hides_beta_functions():
    stable = {"update_channel": "stable"}
    text = C.plain_capabilities(stable) + C.html_capabilities(stable)
    for phrase in C.BETA_PHRASES:
        assert phrase not in text, phrase
    assert "BETA" not in C.html_capabilities(stable)
    assert "открой блокнот" in C.html_capabilities(stable)
    assert "подготовь рабочее место" in C.html_capabilities(dict(stable, update_channel="beta"))


def test_tour_has_six_steps_with_phrases():
    assert len(C.TOUR) == 6
    assert all(title and text and phrase for title, text, phrase in C.TOUR)


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
