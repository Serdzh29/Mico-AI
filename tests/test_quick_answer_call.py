"""«Короче» и «Подробнее» падали: intel_ui передавал в Brain.quick_answer лишний аргумент.
Проверяем по исходникам, что все вызовы quick_answer совпадают с его сигнатурой."""
import ast, glob, os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _arity_of_def():
    tree = ast.parse(open(_os.path.join(ROOT, "core/brain.py"), encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "quick_answer":
            args = node.args
            return len(args.args) - 1, len(args.args) - 1 - len(args.defaults)   # без self: всего и обязательных
    raise AssertionError("brain.quick_answer не найден")


def test_quick_answer_calls_match_signature():
    total, required = _arity_of_def()
    for path in glob.glob(_os.path.join(ROOT, "*.py")):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "quick_answer":
                n = len(node.args) + len(node.keywords)
                assert required <= n <= total, f"{_os.path.basename(path)}:{node.lineno} передано {n}, нужно {required}–{total}"


if __name__ == "__main__":
    test_quick_answer_calls_match_signature()
    print("OK quick_answer call")
