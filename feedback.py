"""Обратная связь от бета-тестеров: 👍 / 👎 под ответом, «Что-то не так», ящик идей, опрос через неделю.
Всё хранится локально в зашифрованном хранилище. Ничего не отправляется само: отзыв уходит разработчику,
только когда человек сам передаёт zip-отчёт."""
import json, time

SURVEY_DAYS = 7
SURVEY_QUESTIONS = ("Что понравилось?", "Что раздражает?", "Чего не хватает?")
KINDS = {"up", "down", "problem", "idea", "survey"}
MAX_TEXT = 1000
MAX_CONTEXT = 300


def make_entry(kind, text="", question="", answer=""):
    if kind not in KINDS:
        raise ValueError(f"неизвестный вид отзыва: {kind}")
    return {"kind": kind, "text": (text or "").strip()[:MAX_TEXT],
            "question": (question or "").strip()[:MAX_CONTEXT], "answer": (answer or "").strip()[:MAX_CONTEXT],
            "time": int(time.time())}


def should_show_survey(cfg, now=None):
    """Опрос один раз, через SURVEY_DAYS дней после первого запуска."""
    now = now or time.time()
    first = cfg.get("first_run")
    if not first or cfg.get("survey_done"):
        return False
    return now - float(first) >= SURVEY_DAYS * 86400


def survey_prompt():
    return "\n".join(f"{i + 1}. {q}" for i, q in enumerate(SURVEY_QUESTIONS))


def export_json(entries):
    """Отзывы для приложения к отчёту: без времени и без служебных полей."""
    return json.dumps([{k: e[k] for k in ("kind", "text", "question", "answer")} for e in entries],
                      ensure_ascii=False, indent=2)


def summary(entries):
    counts = {k: 0 for k in KINDS}
    for e in entries:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    return counts
