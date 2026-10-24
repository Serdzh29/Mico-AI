"""Окно настроек: каждый обработчик и каждый виджет, на который ссылаются, должны существовать.
Иначе окно падает при открытии (так и случилось, когда при удалении строк зацепили чужой обработчик)."""
import ast, os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _dialog():
    tree = ast.parse(open(_os.path.join(ROOT, "main.py"), encoding="utf-8").read())
    return next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "SettingsDialog")


def test_every_connected_handler_exists():
    cls = _dialog()
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    class_names = {t.id for n in cls.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    assigned = {n.attr for n in ast.walk(cls) if isinstance(n, ast.Attribute)
                and isinstance(n.value, ast.Name) and n.value.id == "self" and isinstance(n.ctx, ast.Store)}
    bad = set()
    for node in ast.walk(cls):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self" \
                and isinstance(node.ctx, ast.Load) and node.attr.startswith(("_", "wi_")):
            if node.attr not in methods and node.attr not in assigned and node.attr not in class_names:
                bad.add((node.attr, node.lineno))
    assert not bad, sorted(bad)


def test_edge_handler_present():
    names = {n.name for n in _dialog().body if isinstance(n, ast.FunctionDef)}
    assert "_wi_edge_changed" in names


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
