"""Здоровье ПК (бета): только чтение. Ничего не меняет и не удаляет."""
import re, time

PHRASE = re.compile(r"^(?:как\s+дела\s+у\s+(?:пк|компьютера|ноутбука)|проверь\s+здоровье\s+(?:пк|компьютера|ноутбука)"
                    r"|состояние\s+(?:пк|компьютера|ноутбука))$")


def command(ql):
    return bool(PHRASE.match((ql or "").strip(" .!?")))


def _gb(n):
    return f"{n / 1024 ** 3:.1f} ГБ"


def report(disk_fn, boot_time, now, defender=None):
    """disk_fn(path) -> (total, used, free) в байтах. defender — True/False/None (не удалось узнать)."""
    lines = []
    total, _used, free = disk_fn("C:\\")
    pct = free * 100 // total if total else 0
    warn = " ⚠ места мало, стоит почистить временные файлы" if pct < 15 else ""
    lines.append(f"Диск C: свободно {_gb(free)} из {_gb(total)} ({pct}%).{warn}")
    hours = int((now - boot_time) // 3600)
    lines.append(f"Работает без перезагрузки: {hours} ч.")
    if defender is True:
        lines.append("Защита Windows включена.")
    elif defender is False:
        lines.append("⚠ Защита Windows выключена: проверь «Безопасность Windows».")
    lines.append("Обновления Windows проверь в «Параметры → Центр обновления» — отсюда Mico их не смотрит.")
    return "\n".join(lines)
