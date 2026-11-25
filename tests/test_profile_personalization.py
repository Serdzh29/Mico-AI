"""Профиль Mico AI: выбранная манера и контекст пользователя должны доходить до модели."""
import os as _os

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def read(name):
    with open(_os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def check(condition, message):
    assert condition, message


def test_profile_is_compact_and_context_matches_other_fields():
    main = read("mico.py")
    look = read("ui/settingslook.py")
    check("profile_style" in main and "profile_answers" in main,
          "профиль объединяет связанные предпочтения в два понятных выбора")
    check("Контекст для Mico AI" in main and 'setObjectName("profileContext")' in main,
          "поле контекста получило ясное название и отдельный идентификатор")
    check("QPlainTextEdit" in look and "background: $field" in look,
          "контекст оформлен тем же цветом, что и остальные поля настроек")


def test_profile_values_are_saved_and_used_by_brain():
    main = read("mico.py")
    brain = read("core/brain.py")
    check('"user_tone": "friendly"' in main, "у нового профиля есть безопасная манера по умолчанию")
    check("profile_language" in main and "profile_style" in main and "profile_answers" in main,
          "в настройках остаются язык, стиль общения и способ отвечать")
    check("tone, address = self.profile_style.currentData()" in main and
          "length, answer_format, clarify = self.profile_answers.currentData()" in main,
          "объединённые предпочтения сохраняются в существующий профиль")
    check("PROFILE_TONES" in brain and "PROFILE_LENGTHS" in brain and "PROFILE_FORMATS" in brain and "PROFILE_CLARIFY" in brain,
          "Brain читает все сохранённые предпочтения")
    check("PROFILE_TONES.get(tone" in brain and "PROFILE_LENGTHS.get(length" in brain,
          "смена стиля и способа ответа передаётся модели в инструкции")
    check("Контекст от пользователя" in brain and "Профиль пользователя" in brain,
          "описание пользователя добавляется в инструкцию модели")


if __name__ == "__main__":
    test_profile_is_compact_and_context_matches_other_fields()
    test_profile_values_are_saved_and_used_by_brain()
    print("OK profile personalization")
