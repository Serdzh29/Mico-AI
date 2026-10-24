"""Mico AI виден в «Пуск → Все приложения» и удаляется оттуда через мастер. Проверки без Windows."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_start_menu_shortcut_created_and_removed():
    src = read("installer.py")
    check("'Programs'" in src and "_start_menu_shortcut(create=True)" in src, "ярлык в «Пуск» создаётся при установке")
    check("_start_menu_shortcut(create=False)" in src.split("def _unregister_uninstall")[1][:400], "ярлык убирается при удалении")
    check('"Start Menu", "Programs", "Mico.lnk"' in src, "проверка наличия ярлыка при запуске")


def test_uninstall_entry_opens_our_remover():
    src = read("installer.py")
    check('--uninstall" ' in src or "--uninstall\"" in src, "в «Приложениях» удаление через мастер")
    check('"UninstallString": uninstall_cmd' in src, "UninstallString — мастер Mico")
    check("is_uninstall_request" in read("main.py"), "мастер запускается по --uninstall")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
