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


def test_radio_label_is_short_and_hint_wraps_under_it():
    ins = read("installer.py")
    check("rb = QRadioButton(f\"{kind}: {entry['title']} ({entry['quant']}, около {entry['size_gb']} ГБ)\")" in ins,
          "название варианта короткое: QRadioButton не переносит текст и обрезал его")
    check("hint.setWordWrap(True)" in ins and "entry.get(\"hint\") or entry[\"note\"]" in ins,
          "пояснение переносится под вариантом")


def test_download_status_does_not_repeat_megabytes():
    ins = read("installer.py")
    check("скачиваю {title}\").format(title=entry[\"title\"])" in ins,
          "строка статуса без мегабайт")
    check("Готовлю ответы Mico AI — скачиваю {title}: {done}" not in ins,
          "мегабайты в статусе больше не дублируются")


def test_download_progress_does_not_override_mood():
    ins = read("installer.py")
    check("worker.progress.emit(min(pct, 99), text, \"\")" in ins, "скачивание не меняет лицо")
    check("if mood:                                         # пустое настроение" in ins,
          "полоска не перебивает настроение, пустое значение пропускается")
    check("\"thinking\")" not in ins.split("def show(done, total)")[1].split("got = _download_model")[0],
          "во время скачивания нет принудительного «думает»")


def test_gemma_is_third_option_and_window_fits_it():
    ins = read("installer.py")
    check('alt = model_catalog.by_id("gemma-3-4b-q4") if builtin else None' in ins,
          "Gemma предлагается третьим вариантом только при встроенном движке")
    check('options.append((alt, None))' in ins and 'kind = i18n.t("Альтернатива")' in ins,
          "вариант подписан как альтернатива")
    check("self.setFixedSize(700, 480)" in ins, "окно выше, чтобы третий вариант не обрезался")


def test_new_visible_strings_are_translated():
    import i18n_installer_en as en
    ins = read("installer.py")
    for key in ["Какую модель использовать для ответов?", "Мощная", "Лёгкая", "Альтернатива",
                "Скачать выбранную модель для ответов сейчас",
                "Готовлю ответы Mico AI — скачиваю {title}"]:
        check(key in ins and key in en.INSTALLER_EN, f"нет перевода: {key}")
    import model_catalog as mc
    for e in mc.CATALOG:
        if e.get("hint") and not e.get("legacy"):
            check(e["hint"] in en.INSTALLER_EN, f"нет перевода подсказки: {e['hint']}")


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
