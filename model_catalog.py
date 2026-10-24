"""Каталог моделей для встроенного режима Mico AI (без Ollama): модели в формате GGUF с Hugging Face.
Для каждой модели указано, сколько оперативной памяти нужно, чтобы она работала не на пределе.
Ступени по памяти: 4–16 ГБ — Qwen2.5 3B (чем больше памяти, тем точнее квантование), 24 ГБ — 7B, 32 ГБ — 14B, 64 ГБ и больше — 32B.
Модель для экрана (kind = vision) не участвует в выборе текстовой модели; у неё есть файл-проектор картинки.
Список — данные, а не код: добавить модель можно здесь, остальной код менять не нужно.
Чистая логика, без Qt и без сети — проверяется в tests/test_model_catalog.py."""

HF = "https://huggingface.co"

# Windows показывает память чуть меньше номинальной (8 ГБ → около 7,8 ГБ), поэтому сравниваем с запасом.
MEMORY_SLACK_GB = 0.5

CATALOG = [
    {"id": "qwen2.5-3b", "title": "Qwen2.5 3B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen2.5-3B-Instruct-GGUF", "file": "Qwen2.5-3B-Instruct-Q4_K_M.gguf",
     "size_gb": 1.9, "min_ram_gb": 4, "verified": False,
     "note": "самая лёгкая, для компьютеров с 4–6 ГБ памяти"},
    {"id": "qwen2.5-3b-q5", "title": "Qwen2.5 3B", "quant": "Q5_K_M",
     "repo": "bartowski/Qwen2.5-3B-Instruct-GGUF", "file": "Qwen2.5-3B-Instruct-Q5_K_M.gguf",
     "size_gb": 2.2, "min_ram_gb": 8, "verified": False,
     "note": "точнее версии Q4 почти при том же размере, для компьютеров с 8 ГБ памяти", "hint": "точнее Q4, для компьютеров с 8 ГБ памяти"},
    {"id": "qwen2.5-3b-q6", "title": "Qwen2.5 3B", "quant": "Q6_K",
     "repo": "bartowski/Qwen2.5-3B-Instruct-GGUF", "file": "Qwen2.5-3B-Instruct-Q6_K.gguf",
     "size_gb": 2.5, "min_ram_gb": 16, "verified": False, "legacy": True,
     "note": "не рекомендуется: для 16 ГБ теперь Qwen3.5 4B"},
    {"id": "qwen2.5-7b", "title": "Qwen2.5 7B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen2.5-7B-Instruct-GGUF", "file": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
     "size_gb": 4.7, "min_ram_gb": 24, "verified": False, "legacy": True,
     "note": "больше не рекомендуется: тяжёлая для ПК, отвечает медленно", "hint": "умнее, для 24 ГБ памяти и больше"},
    {"id": "qwen2.5-14b", "title": "Qwen2.5 14B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen2.5-14B-Instruct-GGUF", "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
     "size_gb": 9.0, "min_ram_gb": 32, "verified": False, "legacy": True,
     "note": "не рекомендуется: для 32 ГБ теперь Gemma 4 26B"},
    {"id": "qwen2.5-32b", "title": "Qwen2.5 32B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen2.5-32B-Instruct-GGUF", "file": "Qwen2.5-32B-Instruct-Q4_K_M.gguf",
     "size_gb": 19.9, "min_ram_gb": 64, "verified": False, "legacy": True,
     "note": "не рекомендуется: для 64 ГБ теперь Qwen3.6 35B"},
    {"id": "gemma-4-26b-a4b", "title": "Gemma 4 26B-A4B", "quant": "UD-Q4_K_M",
     "repo": "unsloth/gemma-4-26B-A4B-it-GGUF", "file": "gemma-4-26B-A4B-it-UD-Q4_K_M.gguf",
     "size_gb": 16.9, "min_ram_gb": 32, "verified": False, "legacy": True,
     "note": "больше не рекомендуется: слишком тяжёлая для ПК", "hint": "быстрая и сильная, для 32 ГБ памяти"},
    {"id": "qwen3.6-35b-a3b", "title": "Qwen3.6 35B-A3B", "quant": "UD-Q4_K_M",
     "repo": "unsloth/Qwen3.6-35B-A3B-GGUF", "file": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
     "size_gb": 22.1, "min_ram_gb": 64, "verified": False, "legacy": True,
     "note": "больше не рекомендуется: слишком тяжёлая для ПК", "hint": "самая умная, быстрая, для 64 ГБ памяти"},
    # Gemma 3 4B (QAT, Q4_0): многоязычная, без рассуждений. Файл 3,16 ГБ — полностью в видеопамяти
    # только на картах с запасом больше 4 ГБ, поэтому не подбирается автоматически, выбирается вручную в настройках.
    {"id": "gemma-3-4b-q4", "title": "Gemma 3 4B", "quant": "Q4_0",
     "repo": "vinimuchulski/gemma-3-4b-it-qat-q4_0-gguf", "file": "gemma-3-4b-it-q4_0.gguf",
     "size_gb": 3.2, "min_ram_gb": 8, "verified": False, "auto": False,
     "note": "многоязычная, без рассуждений; на видеокарте 4 ГБ часть работает на процессоре"},
    # Модель для экрана: понимает картинку. Нужны и сама модель, и файл-проектор картинки (mmproj).
    {"id": "qwen2.5-vl-3b", "title": "Qwen2.5-VL 3B", "quant": "Q4_K_M", "kind": "vision",
     "repo": "ggml-org/Qwen2.5-VL-3B-Instruct-GGUF", "file": "Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
     "mmproj_file": "mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf", "mmproj_size_gb": 0.85,
     "size_gb": 1.9, "min_ram_gb": 8, "verified": False,
     "note": "смотрит на экран, для любого компьютера с 8 ГБ памяти и больше"},
    # Старые модели Qwen3.5: больше не предлагаются, но уже скачанные работают.
    {"id": "qwen3.5-4b", "title": "Qwen3.5 4B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen_Qwen3.5-4B-GGUF", "file": "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
     "size_gb": 3.0, "min_ram_gb": 6, "verified": False, "legacy": True,
     "note": "старая модель, больше не рекомендуется"},
    {"id": "qwen3.5-4b-q5", "title": "Qwen3.5 4B", "quant": "Q5_K_M",
     "repo": "bartowski/Qwen_Qwen3.5-4B-GGUF", "file": "Qwen_Qwen3.5-4B-Q5_K_M.gguf",
     "size_gb": 3.4, "min_ram_gb": 8, "verified": False, "legacy": True,
     "note": "старая модель, больше не рекомендуется"},
    {"id": "qwen3.5-4b-q6", "title": "Qwen3.5 4B", "quant": "Q6_K",
     "repo": "bartowski/Qwen_Qwen3.5-4B-GGUF", "file": "Qwen_Qwen3.5-4B-Q6_K.gguf",
     "size_gb": 3.8, "min_ram_gb": 16, "verified": False, "legacy": True,
     "note": "больше не рекомендуется: думает долго и тяжёлая для ПК", "hint": "умнее, отвечает быстро, для 16 ГБ памяти"},
    {"id": "qwen3.5-9b-q5", "title": "Qwen3.5 9B", "quant": "Q5_K_M",
     "repo": "bartowski/Qwen_Qwen3.5-9B-GGUF", "file": "Qwen_Qwen3.5-9B-Q5_K_M.gguf",
     "size_gb": 7.1, "min_ram_gb": 32, "verified": False, "legacy": True,
     "note": "старая модель, больше не рекомендуется"},
    {"id": "qwen3.5-9b", "title": "Qwen3.5 9B", "quant": "Q4_K_M",
     "repo": "bartowski/Qwen_Qwen3.5-9B-GGUF", "file": "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
     "size_gb": 6.2, "min_ram_gb": 16, "verified": True, "legacy": True,
     "note": "старая модель, больше не рекомендуется"},
]

VISION_ID = "qwen2.5-vl-3b"


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


def _text_models():
    return [m for m in CATALOG if not m.get("legacy") and m.get("kind") != "vision"]


def _auto_models():
    """Модели, которые Mico подбирает сам по памяти. Остальные доступны только вручную в настройках."""
    return [m for m in _text_models() if m.get("auto", True)]


def recommend(ram_gb):
    """Самая крупная рекомендуемая текстовая модель, которая подходит по памяти. Если память меньше всех — самая лёгкая."""
    current = _auto_models()
    fitting = [m for m in current if fits(m, ram_gb)]
    if not fitting:
        return min(current, key=lambda m: m["min_ram_gb"])
    return max(fitting, key=lambda m: m["min_ram_gb"])


# Режим Ollama: два уровня — лёгкий (qwen2.5, быстро и хорошо по-русски) и мощный (qwen3.5, умнее).
OLLAMA_TIERS = [
    {"id": "qwen2.5:3b", "title": "Qwen2.5 3B", "quant": "Ollama", "min_ram_gb": 8, "size_gb": 2.0,
     "note": "лёгкая: быстро отвечает и хорошо понимает русский"},
    {"id": "qwen3.5:9b", "title": "Qwen3.5 9B", "quant": "Ollama", "min_ram_gb": 14, "size_gb": 6.6,
     "note": "мощная: умнее, для 16 ГБ памяти и больше"},
]


def pair_for(ram_gb, tiers=None):
    """(лёгкая, мощная) для этой памяти. Мощная — самая крупная подходящая модель (или самая лёгкая, если
    памяти мало). Лёгкая — ступенью ниже. Если ниже нет — обе совпадают."""
    current = sorted(tiers if tiers is not None else _auto_models(), key=lambda m: m["min_ram_gb"])
    fitting = [m for m in current if ram_gb + MEMORY_SLACK_GB >= m["min_ram_gb"]]
    heavy = fitting[-1] if fitting else current[0]
    i = current.index(heavy)
    light = current[i - 1] if i > 0 else heavy
    return light, heavy


def recommend_vision(ram_gb):
    """Модель для экрана: одна на все компьютеры, но только если памяти хватает."""
    entry = by_id(VISION_ID)
    return entry if entry and fits(entry, ram_gb) else None


def label(entry, ram_gb):
    """Подпись для списка в настройках: что это, сколько места и подходит ли для этой памяти."""
    if fits(entry, ram_gb):
        verdict = "подходит для этого компьютера"
    else:
        verdict = f"нужно не меньше {entry['min_ram_gb']} ГБ памяти"
    return f"{entry['title']} ({entry['quant']}, около {entry['size_gb']} ГБ) — {verdict}. {entry['note']}"
