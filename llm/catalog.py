"""Каталог текстовой модели Mico AI в формате GGUF и выбор модели под вопрос (роутер fast/deep).
Чистая логика, без Qt и без сети — проверяется в tests/test_model_catalog.py."""

import re

HF = "https://huggingface.co"

# Windows показывает память чуть меньше номинальной (8 ГБ → около 7,8 ГБ), поэтому сравниваем с запасом.
MEMORY_SLACK_GB = 0.5

CATALOG = [
    {"id": "qwen3.5-4b", "title": "Qwen3.5 4B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen_Qwen3.5-4B-GGUF", "file": "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
     "size_gb": 3.01, "min_ram_gb": 8, "verified": True,
     "note": "универсальная текстовая модель для повседневных ответов"},
]



def by_id(model_id):
    for m in CATALOG:
        if m["id"] == model_id:
            return m
    return None


def url(entry):
    """Прямая ссылка на файл модели на Hugging Face."""
    return f"{HF}/{entry['repo']}/resolve/main/{entry['file']}"


def fits(entry, ram_gb):
    """Модель рекомендуется для такого объёма памяти (с учётом того, что Windows показывает память чуть меньше)."""
    return ram_gb + MEMORY_SLACK_GB >= entry["min_ram_gb"]


def recommend(ram_gb):
    """Единственная текстовая модель Mico."""
    return CATALOG[0]


def pair_for(ram_gb, tiers=None):
    """Совместимость со старым интерфейсом установщика: лёгкая и мощная — одна модель."""
    return CATALOG[0], CATALOG[0]


def label(entry, ram_gb):
    return f"{entry['title']} ({entry['quant']}, около {entry['size_gb']} ГБ) — {entry['note']}"


# Глубокие вопросы: объяснения, планы и код — умной модели; быстрые — лёгкой.
DEEP_ASK = re.compile(r"почему|объясни|подробно|как работает|напиши|сочини|сделай план|расскажи|сравни|проанализ",
                      re.I)


def route(q, installed, preferred=None):
    """Какой моделью отвечать: глубокие вопросы — умной, быстрые — лёгкой (роутер fast/deep).
    preferred — модель из настроек: на ней идут глубокие вопросы. Пока установлена одна модель —
    она и отвечает; роутер включится, когда появится вторая."""
    have = [i for i in dict.fromkeys(installed or []) if i]
    if len(have) <= 1:
        return preferred or (have[0] if have else None)
    deep = preferred if preferred in have else have[0]
    fast = next(i for i in have if i != deep)
    s = str(q or "")
    return deep if (len(s) > 80 or DEEP_ASK.search(s)) else fast
