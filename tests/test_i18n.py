"""Язык интерфейса: русский по умолчанию, английский из настроек; переключатель есть в окне настроек."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import i18n


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def test_russian_is_default_and_unchanged():
    i18n.set_language("ru")
    assert i18n.t("Сохранить") == "Сохранить"
    assert i18n.t("Текст без перевода") == "Текст без перевода"


def test_english_translates_and_falls_back():
    i18n.set_language("en")
    try:
        assert i18n.t("Сохранить") == "Save"
        assert i18n.t("Вид") == "Look"
        assert i18n.t("Текст без перевода") == "Текст без перевода", "нет перевода — показываем русский"
    finally:
        i18n.set_language("ru")


def test_unknown_language_code_means_english():
    i18n.set_language("de")
    assert i18n.LANG == "en"
    i18n.set_language("ru")


def test_every_english_value_is_nonempty():
    assert all(v.strip() for v in i18n.EN.values())


def test_language_selector_in_settings_defaults_to_english():
    main = read("main.py")
    assert 'i18n.set_language(cfg.get("language", "en"))' in main, "язык берётся из настроек при запуске"
    assert 'for code, name in i18n.LANGUAGES' in main, "в настройках есть переключатель языка"
    assert "self.cfg.update(language=self.lang.currentData()" in main, "выбранный язык сохраняется"
    assert '"language": "en"' in main, "по умолчанию — английский"
    assert "EN = {" in read("i18n.py"), "английский перевод сохранён в файле"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
