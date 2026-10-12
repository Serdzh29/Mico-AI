"""Отчёт разработчику по e-mail: готовое письмо открывается в почтовой программе, а zip человек прикрепляет сам.
Mico не отправляет письмо сам, не хранит пароли и не вставляет в письмо тексты отзывов — только счётчики.
Чистая логика без Qt — проверяется в tests/test_mailreport.py."""
from urllib.parse import quote

MAX_BODY = 1500          # длинные ссылки mailto почтовые программы обрезают


def build_body(app_version, windows_build, feedback_counts, note=""):
    counts = ", ".join(f"{k} — {v}" for k, v in feedback_counts.items() if v) or "нет"
    lines = ["Отчёт Mico из бета-канала.", "",
             f"Версия Mico: {app_version}",
             f"Сборка Windows: {windows_build or 'неизвестно'}",
             f"Отзывы на этом ПК: {counts}"]
    if note:
        lines += ["", note]
    lines += ["", "Zip-файл с отчётом прикреплю к этому письму."]
    return "\n".join(lines)[:MAX_BODY]


def mailto_link(to, subject, body):
    """Ссылка mailto: открывает письмо в почтовой программе. Нет адреса — None."""
    if not to or "@" not in to:
        return None
    return f"mailto:{to}?subject={quote(subject)}&body={quote(body[:MAX_BODY])}"
