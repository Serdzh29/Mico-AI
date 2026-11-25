"""Анимации Mico AI: танец под музыку и поедание файлов из корзины (blob.py, main.py, settings).
PyQt6 здесь не нужен: проверяем код разбором текста (ast) и формулу рта. Запуск: python tests/test_blob_animations.py"""
import ast, math, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def _src(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def _func(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"нет функции {name}")


def test_eat_open_stays_in_range_and_opens_and_closes():
    tree = ast.parse(_src("ui/blob.py"))
    code = ast.Module(body=[_func(tree, "eat_open")], type_ignores=[])
    env = {"math": math}
    exec(compile(code, "blob", "exec"), env)
    eat_open = env["eat_open"]
    values = [eat_open(i / 200) for i in range(201)]
    check(all(0.0 <= v <= 1.0 for v in values), "рот всегда между закрыт и открыт")
    check(eat_open(0.0) == 0.0 and eat_open(1.0) == 0.0, "в начале и в конце рот закрыт")
    check(max(values) > 0.8, "рот открывается широко")
    check(sum(1 for a, b in zip(values, values[1:]) if a < b) >= 4, "жуёт: несколько раз открывается")


def test_blob_has_dance_and_eat_api():
    tree = ast.parse(_src("ui/blob.py"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Blob")
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    for name in ("set_dancing", "eat_files", "_draw_eat", "_ellipse_path"):
        check(name in methods, f"в Blob нет {name}")
    src = _src("ui/blob.py")
    check(re.search(r'"eat": 2\.8', src), "длительность поедания задана в таблице анимаций")
    check('dk = self.dance_k' in src and 'dance_sway' in src, "танец влияет на тело и голову")


def test_main_wires_sound_signals_to_blob():
    src = _src("mico.py")
    check("playing = pyqtSignal(bool)" in src and "emptied = pyqtSignal()" in src, "сигналы в Bus")
    check("bus.playing.connect(blob.set_dancing)" in src, "музыка → танец")
    check("bus.emptied.connect(blob.eat_files)" in src, "корзина → поедание")
    check("soundwatch.Watcher(" in src and "sound.start()" in src, "наблюдатель запущен")


def test_defaults_and_hints_for_new_settings():
    src = _src("mico.py")
    check(re.search(r'"agent_mode": False', src), "режим агента выключен по умолчанию")
    check(re.search(r'"dance_music": True', src) and re.search(r'"eat_trash": True', src), "анимации включены")
    info = _src("ui/info.py")
    for key in ("agent_mode", "dance_music", "eat_trash"):
        check(f'"{key}": "' in info, f"нет подсказки для {key}")
    check('QLabel("BETA")' in src and '"Агент"' in src, "вкладка «Агент» помечена как BETA")


def test_agent_settings_are_saved_on_apply():
    src = _src("mico.py")
    check("agent_mode=self.agent_on.isChecked()" in src, "флажок агента сохраняется")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK blob_animations")
