"""Одноразовая миграция вида чата.

Старые config.json сохраняли «окно рядом с Mico AI» (panel_side = false). Новый дефолт —
панель сбоку, как Windows Copilot, — из-за этого до пользователя не доходил: load_cfg берёт
значения из файла поверх DEFAULTS. Миграция ставит панель один раз, по метке ui_layout.
После этого выбор в настройках («Как открывать чат») сохраняется и больше не перетирается."""

LAYOUT_VERSION = 2


def migrate(cfg):
    """Меняет cfg на месте. Возвращает True, если поменяли."""
    if cfg.get("ui_layout") == LAYOUT_VERSION:
        return False
    cfg["panel_side"] = True
    cfg["ui_layout"] = LAYOUT_VERSION
    return True
