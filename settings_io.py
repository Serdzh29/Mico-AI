"""Экспорт и импорт настроек. В файл не попадают секреты (ключи) и личные данные (согласия, счётчики, город)."""
import json

SECRET_KEYS = set()                 # ключей, которые нельзя выносить в файл, сейчас нет
PERSONAL_KEYS = {"last_version", "chip_usage", "loc_consent", "city"}
MARK = "mico-settings"


def export_settings(cfg, path, app_version):
    data = {k: v for k, v in cfg.items() if k not in SECRET_KEYS | PERSONAL_KEYS}
    data["_format"] = MARK
    data["_exported_from"] = str(app_version)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return sorted(k for k in data if not k.startswith("_"))


def _compatible(value, default):
    if default is None:
        return True
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, (int, float)):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))


def import_settings(path, cfg, defaults):
    """Применяет настройки из файла. Возвращает (применено, пропущено с причиной)."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict) or raw.get("_format") != MARK:
        raise ValueError("это не файл настроек Mico")
    applied, skipped = [], []
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if key in SECRET_KEYS | PERSONAL_KEYS:
            skipped.append((key, "личные данные не импортируются"))
        elif key not in defaults:
            skipped.append((key, "неизвестная настройка этой версии"))
        elif not _compatible(value, defaults[key]):
            skipped.append((key, "неверный тип значения"))
        else:
            cfg[key] = value
            applied.append(key)
    return applied, skipped
