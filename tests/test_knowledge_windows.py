import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import windows_info as W
import knowledge as K


def test_settings_catalog_is_complete_and_unique():
    uris = [s[3] for s in W.SETTINGS]
    assert len(uris) == len(set(uris)), "дубликаты адресов"
    assert len(uris) >= 150, len(uris)
    assert all(u.startswith("ms-settings:") for u in uris)


def test_settings_lookup_examples():
    cases = {"где найти настройку bluetooth": "Bluetooth", "как изменить тему": "Цвета",
             "где найти защитник": "Безопасность Windows",
             "где запись игр": "Запись игр", "как настроить распознавание лица": "Настройка распознавания лица (Hello)",
             "где включить субтитры": "Субтитры", "как приготовить борщ": None}
    for q, want in cases.items():
        r = W.find_setting(q)
        assert (r[0] if r else None) == want, (q, r)


def test_components_knowledge_answers():
    items = K.load()
    assert sum(1 for i in items if i["source"] == "components") >= 25
    for q, want in {"что такое hyper-v": "Hyper-V", "что такое телеметрия": "Телеметрия (DiagTrack)",
                    "зачем гибернация": "Режим гибернации"}.items():
        a = K.answer(q, items)
        assert a and a.splitlines()[0] == want, (q, a)
        assert "справка о компонентах" in a or "справка Windows" in a
