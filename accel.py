"""Где считать ответы встроенной модели: на видеокарте NVIDIA, если она есть, иначе на процессоре.
Видеокарта используется для всех запросов: текста, команд и экрана. Скорость не сравниваем: если модель
на видеокарте запустилась, работаем на ней. Процессор — только когда видеокарты нет, сборка её не умеет
или модель на ней не запустилась совсем.
Чистая логика: проверка запуска передаётся извне, поэтому тестируется без Qt и без видеокарты."""
import json
import os
import subprocess

RESERVE_MB = 900                    # запас видеопамяти под контекст и служебные данные CUDA
PARTIAL_LAYERS = (24, 12)           # если модель целиком не влезает: часть слоёв на видеокарте
FULL_GPU = -1                       # все слои на видеокарте
CPU = 0                             # ни одного слоя на видеокарте

_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def gpu_info(run=subprocess.run):
    """Видеокарта NVIDIA: имя и свободная память, МБ. None — её нет или драйвер не отвечает."""
    try:
        r = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, creationflags=_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not (r.stdout or "").strip():
        return None
    parts = [p.strip() for p in r.stdout.strip().splitlines()[0].split(",")]
    if len(parts) < 3:
        return None
    try:
        return {"name": ",".join(parts[:-2]), "total_mb": float(parts[-2]), "free_mb": float(parts[-1])}
    except ValueError:
        return None


def choose(model_mb, info, supported, try_load, cache, key):
    """Возвращает (слои на видеокарте, отчёт для пользователя).
    try_load(слои) → True, если модель загрузилась на этих слоях и ответила.
    cache — словарь уже сделанных проверок; key — ключ «модель + видеокарта + версия проверки»."""
    if info is None:
        return CPU, "видеокарта NVIDIA не найдена, отвечаю на процессоре"
    if not supported:
        return CPU, "эта сборка движка не умеет работать с видеокартой, отвечаю на процессоре"
    if key in cache:
        return cache[key]["layers"], cache[key]["report"]
    fits = info["free_mb"] >= model_mb + RESERVE_MB
    candidates = ([FULL_GPU] if fits else []) + list(PARTIAL_LAYERS)
    for layers in candidates:
        if try_load(layers):
            if layers == FULL_GPU:
                report = f"все ответы считаются на видеокарте {info['name']}"
            else:
                report = f"ответы считаются на видеокарте {info['name']}, часть слоёв модели — на процессоре"
            result = (layers, report)
            break
    else:
        result = (CPU, f"видеокарта {info['name']} не запустила модель, отвечаю на процессоре")
    cache[key] = {"layers": result[0], "report": result[1]}
    return result


def load_cache(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(path, cache):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except OSError:
        pass                                   # не записали — в следующий раз проверим заново
