"""Проверки модели и локального движка Mico AI."""
import os

from llm import engine as local_llm
from llm import store as model_store


def explain_model_error(exc, model):
    """Возвращает понятную причину ошибки локальной модели и совет."""
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    if "connection" in name or "connect" in text:
        return (f"Не получилось подключиться к модели «{model}»: движок не запущен или пропало соединение. "
                "Нажми «Повторить». Если ошибка повторяется — перезапусти Mico AI и проверь интернет.")
    if "timeout" in name or "timed out" in text:
        return (f"Модель «{model}» думает слишком долго. Закрой тяжёлые программы и нажми «Повторить».")
    if "memory" in text or "alloc" in text:
        return (f"Не хватило памяти для модели «{model}». Закрой тяжёлые программы и перезапусти Mico AI.")
    if "model" in text and ("not found" in text or "no such file" in text):
        return (f"Модель «{model}» не найдена на компьютере. Переустанови Mico AI, чтобы скачать её и нажми «Повторить».")
    return (f"Не получилось получить ответ от локальной модели «{model}». Нажми «Повторить». Если ошибка повторится — "
            "меню Mico AI → «Проверить окружение» покажет состояние движка и модели.")


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


def local_model_probe(model_id):
    """Проверяет локальный llama.cpp и наличие GGUF-файла."""
    if not local_llm.available():
        return False, "движок llama-cpp-python не установлен. Переустанови Mico AI."
    path = model_store.path_for(model_id or "")
    if not path or not os.path.isfile(path):
        return False, f"Модель «{model_id}» не скачана. Переустанови Mico AI, чтобы подготовить её."
    return True, ""
