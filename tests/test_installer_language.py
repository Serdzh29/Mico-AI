"""Язык выбирается на этапе установки и удаления, и попадает в настройки программы. Без Qt."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_language_picked_before_install_and_uninstall():
    src = read("installer.py")
    assert "def pick_language(default):" in src, "есть окно выбора языка"
    run_part = src.split("def run():")[1].split("def ")[0]
    assert "pick_language(\"en\")" in run_part, "установка спрашивает язык первым шагом"
    unin = src.split("def uninstall(app):")[1].split("\ndef ")[0]
    assert "pick_language(previous)" in unin, "удаление спрашивает язык, по умолчанию — язык программы"


def test_install_language_saved_to_settings():
    src = read("installer.py")
    assert "language=i18n.LANG" in src, "выбранный язык сохраняется в настройки"


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
