"""Запуск всех проверок Mico: python tests/run_all.py (нужен только Python, без Windows и моделей)."""
import glob, os, subprocess, sys

try:                                          # консоль Windows может быть cp1251: русский вывод не должен ронять раннер
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

here = os.path.dirname(os.path.abspath(__file__))
failed = []
for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
    name = os.path.basename(path)
    # PYTHONIOENCODING=utf-8: дочерние проверки печатают русский и значки (✓, ⌽), которых нет в cp1251
    r = subprocess.run([sys.executable, path], capture_output=True, cwd=os.path.dirname(here),
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    status = "OK  " if r.returncode == 0 else "FAIL"
    print(f"{status} {name}")
    if r.returncode != 0:
        failed.append(name)
        print(r.stderr.decode("utf-8", "replace")[-800:], file=sys.stderr)
print("все проверки прошли" if not failed else f"упали: {', '.join(failed)}")
sys.exit(1 if failed else 0)
