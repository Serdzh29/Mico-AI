"""Срочные исправления: версии вида 2026.10.1305(a), (b)… — порядок, запись, проверка обновлений."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import version as V
import updatecheck as U

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# порядок: основной выпуск < (a) < (b) < следующий выпуск
order = ["2026.10.1304", "2026.10.1305", "2026.10.1305(a)", "2026.10.1305(b)", "2026.10.1306"]
keys = [V._vt(x) for x in order]
check(keys == sorted(keys), keys)
check(len(set(keys)) == len(keys), "все номера различаются")

# одна запись для разных вариантов ввода
for raw in ["2026.10.1305a", "2026.10.1305 (a)", "v2026.10.1305(a)", "2026.10.1305(A)".lower()]:
    check(V.normalize(raw) == "2026.10.1305(a)", (raw, V.normalize(raw)))
check(V.normalize("2026.10.1305") == "2026.10.1305", "без буквы не меняем")
check(V.normalize("3.29") == "3.29", "старые номера не трогаем")

# проверка обновлений: тег с буквой принимается и сравнивается правильно
check(U.version_of("v2026.10.1305a") == "2026.10.1305(a)")
check(U.version_of("v2026.10.1305") == "2026.10.1305")
check(U.version_of("v2026.10.1305ab") is None, "две буквы — не номер")
check(U.is_newer("2026.10.1305(a)", "2026.10.1305"), "(a) предлагаем тем, у кого 1305")
check(not U.is_newer("2026.10.1305", "2026.10.1305(a)"), "основной выпуск не предлагаем тем, у кого уже (a)")
check(U.is_newer("2026.10.1305(b)", "2026.10.1305(a)"), "(b) новее (a)")
check(U.is_newer("2026.10.1306", "2026.10.1305(b)"), "следующий выпуск новее всех исправлений")

print("ALL OK")
