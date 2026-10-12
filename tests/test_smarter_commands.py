import os as _os, sys as _sys, types
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
for m in ["mss", "psutil", "PIL", "PIL.Image", "requests", "cryptography", "cryptography.fernet"]:
    _sys.modules.setdefault(m, types.ModuleType(m))
_sys.modules["mss"].mss = object
_sys.modules["PIL"].Image = types.SimpleNamespace()
_sys.modules["cryptography.fernet"].Fernet = object
_sys.modules["requests"].RequestException = Exception
import components as C
import commands as K


def test_hibernation_with_typo_is_found_on_and_off():
    assert C.find_toggle("отключи гибергацию").name == "Режим гибернации"
    assert C.find_toggle("включи гибернацию").name == "Режим гибернации"
    assert C.find_toggle("выключи гибернацию").name == "Режим гибернации"


def test_exact_names_still_win():
    assert C.find_toggle("выключи wi-fi").name == "Wi-Fi"
    assert C.find_toggle("включи блютуз").name == "Bluetooth"


def test_unknown_component_gets_suggestions():
    assert "Режим гибернации" in C.suggest("включи гибернацю")


def test_new_system_components_exist_and_have_notes_where_risky():
    names = {t.name: t for t in C.TOGGLES}
    for n in ["Фоновые приложения", "Удалённый помощник", "Отчёты об ошибках Windows",
              "Сжатие памяти", "Аппаратное планирование GPU", "Служба обновлений Windows"]:
        assert n in names, n
    assert names["Служба обновлений Windows"].note
    assert names["Аппаратное планирование GPU"].note


def _swapped(pairs, fn):
    """Подменяем функции на время проверки и возвращаем всё на место (работает без pytest)."""
    missing = object()
    saved = [(obj, name, getattr(obj, name, missing)) for obj, name, _ in pairs]
    try:
        for obj, name, value in pairs:
            setattr(obj, name, value)
        return fn()
    finally:
        for obj, name, old in saved:
            if old is missing:
                delattr(obj, name)
            else:
                setattr(obj, name, old)


def test_music_without_installed_app_opens_web():
    opened = []
    def run():
        return K._music("включи музыку", None)
    r = _swapped([(K.webbrowser, "open", lambda url, *a, **k: opened.append(url)),
                  (K, "_find_start_app", lambda name: None)], run)
    assert r and opened and "music.yandex.ru" in opened[-1]


def test_music_named_service_with_typo():
    opened = []
    r = _swapped([(K.webbrowser, "open", lambda url, *a, **k: opened.append(url)),
                  (K, "_find_start_app", lambda name: None)],
                 lambda: K._music("включи музыку в саунд кладу", None))
    assert r and any("soundcloud.com" in u for u in opened)


def test_music_prefers_installed_app():
    started = []
    find = lambda name: ("Spotify", "Spotify.App!App") if name == "Spotify" else None
    r = _swapped([(K, "_find_start_app", find), (K.os, "startfile", lambda p: started.append(p))],
                 lambda: K._music("включи музыку", None))
    assert "Spotify" in r.text and started and "Spotify.App" in started[-1]


def test_non_music_phrase_is_not_taken_by_music_handler():
    assert K._music("открой блокнот", None) is None


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
