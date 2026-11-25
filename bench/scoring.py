"""Оценка ответов моделей на фиксированном наборе запросов (prompts_ru.json).
Чистая логика: без сети, без Ollama и без Windows. Проверяется в tests/test_bench.py.

Автоматические проверки ловят грубые ошибки: пустой ответ, рассуждения по-английски, «утекшие»
метки <think>, неверный JSON у команд, нет нужного слова. Тонкость ответа (уместность, грамотность)
оценивается вручную: колонка manual в results.csv (0 — плохо, 1 — приемлемо, 2 — хорошо)."""
import json, os, re, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROMPTS_FILE = os.path.join(HERE, "prompts_ru.json")
CATEGORIES = ("chat", "system", "windows", "action")
MIN_CYRILLIC = 0.7                       # доля русских букв среди всех букв в ответе
LEAK = re.compile(r"<think>|</think>|\b(the user|let me think|i need to|okay, the|first, i)\b", re.IGNORECASE)


def load_prompts(path=PROMPTS_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["prompts"]


def cyrillic_ratio(text):
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text or "")
    if not letters:
        return 0.0
    cyr = sum(1 for ch in letters if "\u0400" <= ch <= "\u04ff" or ch in "Ёё")
    return cyr / len(letters)


def parse_action(text):
    """Вызов действия из ответа — той же функцией, что и в программе (osagent.parse). None — не вызов."""
    import sys
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from win import osagent
    try:
        return osagent.parse(text)
    except ValueError:
        return None


def check_reply(prompt, reply):
    """Список причин провала. Пустой список — ответ прошёл автоматические проверки."""
    reasons = []
    text = (reply or "").strip()
    if not text:
        return ["пустой ответ"]
    if LEAK.search(text):
        reasons.append("рассуждения или английский внутри ответа")
    if prompt["category"] == "action":
        call = parse_action(text)
        if call is None:
            reasons.append("нет корректного JSON-вызова действия")
        elif call[0] != prompt.get("expect"):
            reasons.append(f"выбрано «{call[0]}», ожидали «{prompt.get('expect')}»")
        return reasons
    if cyrillic_ratio(text) < MIN_CYRILLIC:
        reasons.append("ответ не по-русски")
    for pattern in prompt.get("must", []):
        flags = 0
        if pattern.startswith("(?i)"):
            flags, pattern = re.IGNORECASE, pattern[4:]
        if not re.search(pattern, text, flags):
            reasons.append(f"нет ожидаемого: {pattern}")
    return reasons


def median_or_none(values):
    vals = [v for v in values if v is not None]
    return round(statistics.median(vals), 2) if vals else None


def summarize(rows):
    """rows — словари с полями category, auto_ok, ttft_ms, tok_s, total_s.
    Возвращает сводку: медианы скорости и доля прошедших проверку по категориям."""
    summary = {
        "n": len(rows),
        "auto_pass_pct": round(100 * sum(1 for r in rows if r["auto_ok"]) / len(rows), 1) if rows else None,
        "ttft_ms_median": median_or_none([r.get("ttft_ms") for r in rows]),
        "tok_s_median": median_or_none([r.get("tok_s") for r in rows]),
        "total_s_median": median_or_none([r.get("total_s") for r in rows]),
        "by_category": {},
    }
    for cat in CATEGORIES:
        part = [r for r in rows if r["category"] == cat]
        if part:
            summary["by_category"][cat] = round(100 * sum(1 for r in part if r["auto_ok"]) / len(part), 1)
    return summary
