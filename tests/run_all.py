"""Запуск всех проверок Mico: python tests/run_all.py (нужен только Python, без Windows и моделей)."""
import glob, os, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
failed = []
for path in sorted(glob.glob(os.path.join(here, "test_*.py"))):
    name = os.path.basename(path)
    r = subprocess.run([sys.executable, path], capture_output=True, cwd=os.path.dirname(here))
    status = "OK  " if r.returncode == 0 else "FAIL"
    print(f"{status} {name}")
    if r.returncode != 0:
        failed.append(name)
        print(r.stderr.decode("utf-8", "replace")[-800:])
print("все проверки прошли" if not failed else f"упали: {', '.join(failed)}")
sys.exit(1 if failed else 0)
