"""Пункты контекстного меню Mico (правый щелчок по шару). Пользователь выбирает, какие показывать и сколько.
«Выход» показывается всегда — иначе программу нельзя будет закрыть из меню."""

# (id, подпись по умолчанию, группа)
ITEMS = [
    ("chat", "💬 Чат", "main"),
    ("settings", "⚙️ Настройки…", "main"),
    ("capabilities", "✨ Что ты умеешь?", "main"),
    ("pause", "⏸ Не следить за активностью", "main"),
    ("forget_hour", "🧹 Забыть последний час", "history"),
    ("wipe", "🗑 Удалить всю историю", "history"),
    ("quiet", "🔕 Режим тишины", "mode"),
    ("report", "🐞 Сохранить отчёт об ошибке", "help"),
    ("idea", "💡 Предложить идею", "help"),
    ("tour", "👋 Знакомство", "help"),
    ("whatsnew", "📜 Что нового", "help"),
    ("env", "🩺 Проверить окружение", "help"),
    ("about", "ℹ О Mico", "about"),
    ("uninstall", "🗑 Удалить Mico…", "about"),
    ("exit", "Выход", "about"),
]
LABELS = {i: l for i, l, _ in ITEMS}
GROUP = {i: g for i, _, g in ITEMS}
DEFAULT_ON = ["chat", "settings", "capabilities", "quiet", "report", "exit"]
MIN_MAX, MAX_MAX, DEFAULT_MAX = 3, len(ITEMS), 8


def visible(cfg):
    """Какие пункты показывать и в каком порядке: только выбранные, не больше menu_max, «Выход» всегда."""
    chosen = set(cfg.get("menu_items", DEFAULT_ON)) & set(LABELS)
    limit = max(MIN_MAX, min(MAX_MAX, int(cfg.get("menu_max", DEFAULT_MAX))))
    order = [i for i, _, _ in ITEMS if i in chosen and i != "exit"]
    order = order[: max(0, limit - 1)]          # место под «Выход» остаётся
    return order + ["exit"]
