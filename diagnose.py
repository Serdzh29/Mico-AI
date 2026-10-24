"""Понятные ошибки и проверка окружения. Каждый сбой превращается в причину и совет, что делать."""
import requests


def explain_model_error(exc, model):
    """Понятная причина, почему модель не ответила, и что сделать. В конце — подсказка нажать «Повторить»."""
    if isinstance(exc, requests.exceptions.Timeout):
        return (f"Модель «{model}» думает слишком долго. Закрой тяжёлые программы или выбери модель поменьше "
                "в ⚙ Настройки → Модели. Потом нажми «Повторить».")
    if isinstance(exc, requests.exceptions.ConnectionError):
        return ("Не получилось загрузить модель: движок не запущен. Перезапусти Mico AI "
                "и нажми «Повторить».")
    if isinstance(exc, requests.HTTPError) and getattr(exc.response, "status_code", None) == 404:
        return (f"Модели «{model}» нет на компьютере. Скачай её в ⚙ Настройки → Модели "
                "и нажми «Повторить».")
    return (f"Не получилось загрузить модель «{model}». Нажми «Повторить». Если снова не выйдет — "
            "меню Mico AI → «Проверить окружение» покажет, что не так.")


def environment_report(checks):
    """checks: список (название, функция() -> (ok: bool, совет: str)). Возвращает текст отчёта."""
    lines = ["Проверка окружения Mico AI:"]
    for name, probe in checks:
        try:
            ok, advice = probe()
        except Exception as e:
            ok, advice = False, f"не удалось проверить ({e.__class__.__name__})"
        lines.append(f"{'✓' if ok else '✗'} {name}" + ("" if ok else f" — {advice}"))
    return "\n".join(lines)


def ollama_probe(base, models):
    """Проверка Ollama и нужных моделей. models — список имён."""
    def probe():
        try:
            r = requests.get(base + "/api/tags", timeout=3)
            r.raise_for_status()
        except requests.RequestException:
            return False, "Движок моделей не отвечает. Перезапусти Mico AI."
        have = {m.get("name", "") for m in r.json().get("models", [])}
        missing = [m for m in models if m not in have]
        if missing:
            return False, "не скачана: " + ", ".join(missing) + ". Скачай её в ⚙ Настройки → Модели."
        return True, ""
    return probe
