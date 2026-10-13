"""Отзыв бета-тестера через GitHub (бета): готовый текст открывается как новое обсуждение (issue) в браузере.
Mico ничего не отправляет сам: человек видит текст целиком, может его поправить и сам нажимает «Создать».
Токенов в программе нет. Issues публичны — это сказано в согласии на бету.
Чистая логика без Qt — проверяется в tests/test_ghreport.py."""
import re
from urllib.parse import quote

MAX_BODY = 3000          # длиннее не влезает в ссылку, которую понимает браузер
TEMPLATES = {"bug": ("beta_bug.md", "[БЕТА] Ошибка"),
             "usage": ("beta_usage.md", "[БЕТА] Как пользуюсь бетой")}
FEATURE_NAMES = {"workspace": "Рабочее место", "clipboard_search": "История копирования",
                 "day_summary": "Итог дня", "planner": "Многошаговые задачи",
                 "initiative": "Инициатива", "recurring": "Повторяющиеся напоминания"}
_ANY_PATH = re.compile(r"[A-Za-z]:\\[^\s\"']+")          # любой путь с буквой диска: C:\Users\..., D:\...


def mask_paths(text):
    """Прячем имя пользователя и пути к файлам: в журналах они есть, в публичном отчёте им не место."""
    return _ANY_PATH.sub("<путь>", text)


def build_body(kind, app_version, build_channel, windows_build, usage_counts, log_tail="", note=""):
    """Текст отчёта. В нём только версии, счётчики использования и (если выбрано) строки журнала без путей."""
    if kind == "usage":
        used = ", ".join(f"{FEATURE_NAMES.get(k, k)} — {v}" for k, v in usage_counts.items() if v) or "не пользовался"
        lines = ["## Как пользуюсь бетой", "",
                 "Версия Mico: " + app_version + f" ({build_channel})",
                 "Сборка Windows: " + (windows_build or "неизвестно"),
                 "Использование бета-функций: " + used, "",
                 "## Что понравилось", "", "## Что мешает", "", "## Чего не хватает"]
    else:
        lines = ["## Что случилось", "", note or "(опиши, что произошло)", "",
                 "## Как воспроизвести", "", "1. ", "",
                 "## Что ожидал", "", "",
                 "---",
                 f"Версия Mico: {app_version} ({build_channel})",
                 f"Сборка Windows: {windows_build or 'неизвестно'}",
                 f"Использование бета-функций: " + (", ".join(f"{FEATURE_NAMES.get(k, k)} — {v}"
                                                             for k, v in usage_counts.items() if v) or "нет")]
        if log_tail:
            lines += ["", "<details><summary>Журнал ошибок (пути скрыты)</summary>", "", "```",
                      mask_paths(log_tail)[-1200:], "```", "</details>"]
    return "\n".join(lines)


def issue_url(repo, kind, body):
    """Ссылка на новое обсуждение с шаблоном и заполненным текстом."""
    template, title = TEMPLATES[kind]
    clipped = body if len(body) <= MAX_BODY else body[:MAX_BODY] + "\n\n_(текст обрезан, добавь детали сам)_"
    return (f"https://github.com/{repo}/issues/new?template={quote(template)}"
            f"&title={quote(title)}&body={quote(clipped)}")


def is_too_long(body):
    return len(body) > MAX_BODY
