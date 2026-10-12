"""Понятные ошибки и проверка окружения. Каждый сбой превращается в причину и совет, что делать."""
import requests


def explain_model_error(exc, model):
    """Текст для пользователя по ошибке обращения к Ollama."""
    if isinstance(exc, requests.exceptions.Timeout):
        return ("Модель отвечает слишком долго. Закрой тяжёлые программы или выбери модель поменьше "
                "(например, qwen2.5:3b) в ⚙ Настройки → Модели.")
    if isinstance(exc, requests.exceptions.ConnectionError):
        return ("Ollama не запущена. Запусти её (значок в трее или команда ollama serve) и повтори вопрос. "
                "Если Ollama не установлена — ссылка в инструкции.")
    if isinstance(exc, requests.HTTPError) and getattr(exc.response, "status_code", None) == 404:
        return f"Модель «{model}» ещё не скачана. Выполни в командной строке: ollama pull {model}"
    return "Не получилось получить ответ от модели. Открой меню Mico → «Проверить окружение» — там видно, что не так."


def environment_report(checks):
    """checks: список (название, функция() -> (ok: bool, совет: str)). Возвращает текст отчёта."""
    lines = ["Проверка окружения Mico:"]
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
            return False, "Ollama не отвечает. Запусти её."
        have = {m.get("name", "") for m in r.json().get("models", [])}
        missing = [m for m in models if m not in have]
        if missing:
            return False, "не скачана: " + ", ".join(missing) + ". Выполни ollama pull <имя>"
        return True, ""
    return probe
