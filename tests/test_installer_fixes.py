"""Мастер установки: текст не обрезается, мегабайты не повторяются, лицо Mico не перебивается скачиванием,
всё, что видит человек, переведено. Без Qt — по исходникам."""
import os as _os
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_installer_does_not_ask_which_model_to_use():
    ins = read("setup/installer.py")
    options = ins.split("def _page_options(self):", 1)[1].split("def _page_install(self):", 1)[0]
    check("_builtin_entry()" in options, "каталог сам задаёт единственную модель")
    check("_model_choice" not in ins and "Какую модель использовать для ответов?" not in ins,
          "установщик больше не показывает выбор модели")


def test_download_status_does_not_repeat_megabytes():
    ins = read("setup/installer.py")
    check("скачиваю {title}\").format(title=entry[\"title\"])" in ins,
          "строка статуса без мегабайт")
    check("Готовлю ответы Mico AI — скачиваю {title}: {done}" not in ins,
          "мегабайты в статусе больше не дублируются")


def test_download_progress_does_not_override_mood():
    ins = read("setup/installer.py")
    check("worker.progress.emit(min(pct, 99), text, \"\")" in ins, "скачивание не меняет лицо")
    check("if mood:                                         # пустое настроение" in ins,
          "полоска не перебивает настроение, пустое значение пропускается")
    check("\"thinking\")" not in ins.split("def show(done, total)")[1].split("got = _download_model")[0],
          "во время скачивания нет принудительного «думает»")


def test_gemma_is_not_an_installer_option_anymore():
    ins = read("setup/installer.py")
    check("def _model_choice" not in ins and "options.append((alt, None))" not in ins,
          "мастер не предлагает альтернативные модели")


def test_legacy_uninstall_command_opens_the_current_master():
    ins = read("setup/installer.py")
    check("def _write_legacy_remover():" in ins, "для старого UninstallString есть совместимый сценарий")
    check("f'start \"\" \"{INSTALL_EXE}\" --uninstall'" in ins,
          "старый remove_mico.cmd открывает актуальный мастер удаления")
    refresh = ins.split("def refresh_uninstall_entry():", 1)[1].split("def _unregister_uninstall():", 1)[0]
    check("_write_legacy_remover()" in refresh, "обновление не удаляет совместимый сценарий")


def test_install_clears_only_compatibility_elevation_flag():
    ins = read("setup/installer.py")
    check("COMPATIBILITY_KEY" in ins and "def _clear_compatibility_elevation():" in ins,
          "есть обработка флага совместимости Windows")
    check('part.upper() != "RUNASADMIN"' in ins,
          "убирается именно требование запуска от администратора")
    install = ins.split("def _install_steps", 1)[1].split("def _builtin_entry", 1)[0]
    check("_clear_compatibility_elevation()" in install,
          "установщик снимает флаг до регистрации автозапуска")
    refresh = ins.split("def refresh_uninstall_entry():", 1)[1].split("def _unregister_uninstall():", 1)[0]
    check("_clear_compatibility_elevation()" in refresh,
          "ручной запуск установленной копии также чинит следующий вход в Windows")


def test_new_visible_strings_are_translated():
    from i18n import setup_en as en
    ins = read("setup/installer.py")
    for key in ["Готовлю ответы Mico AI — скачиваю {title}"]:
        check(key in ins and key in en.INSTALLER_EN, f"нет перевода: {key}")
    from llm import catalog as mc
    for e in mc.CATALOG:
        if e.get("hint") and not e.get("legacy"):
            check(e["hint"] in en.INSTALLER_EN, f"нет перевода подсказки: {e['hint']}")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
