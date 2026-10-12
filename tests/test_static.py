"""Статическая проверка Qt-вызовов: ловит ошибки вида «у QCheckBox нет setWordWrap», которые проявляются
только при открытии окна. Работает без PyQt6."""
import glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Методы, которых нет у галочек и кнопок (есть у текстовых меток)
LABEL_ONLY = {"setWordWrap", "setTextFormat", "setOpenExternalLinks"}


def test_checkbox_has_no_label_only_methods():
    problems = []
    for path in glob.glob(os.path.join(ROOT, "*.py")):
        src = open(path, encoding="utf-8").read()
        boxes = set(re.findall(r"self\.(\w+)\s*=\s*QCheckBox\(", src))
        boxes |= set(re.findall(r"^\s*(\w+)\s*=\s*QCheckBox\(", src, re.M))
        for name in boxes:
            for meth in LABEL_ONLY:
                if re.search(rf"\b{name}\.{meth}\(", src):
                    problems.append((os.path.basename(path), name, meth))
    assert not problems, problems


if __name__ == "__main__":
    test_checkbox_has_no_label_only_methods()
    print("OK test_checkbox_has_no_label_only_methods")


def test_main_uses_names_only_after_assignment():
    """В main() переменная не должна использоваться раньше, чем её присвоили (UnboundLocalError при запуске)."""
    import ast
    tree = ast.parse(open(os.path.join(ROOT, "main.py"), encoding="utf-8").read())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    # пропускаем вложенные функции и лямбды: их параметры и локальные имена — не переменные main()
    skip = set()
    for n in ast.walk(main):
        if isinstance(n, (ast.FunctionDef, ast.Lambda)) and n is not main:
            skip.update(id(x) for x in ast.walk(n))
    first_store, first_load = {}, {}
    for n in ast.walk(main):
        if isinstance(n, ast.Name) and id(n) not in skip:
            if isinstance(n.ctx, ast.Store):
                first_store[n.id] = min(first_store.get(n.id, 10 ** 9), n.lineno)
            elif isinstance(n.ctx, ast.Load):
                first_load[n.id] = min(first_load.get(n.id, 10 ** 9), n.lineno)
    defs = {n.name for n in ast.walk(main) if isinstance(n, ast.FunctionDef)}
    bad = [(k, first_load[k], first_store[k]) for k in first_load
           if k in first_store and k not in defs and first_load[k] < first_store[k]]
    assert not bad, bad


if __name__ == "__main__" and "test_main_uses_names_only_after_assignment" not in globals().get("_done", ()):
    test_main_uses_names_only_after_assignment()
    print("OK test_main_uses_names_only_after_assignment")
