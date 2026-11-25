"""Действия Mico AI: скриншоты, напоминания, состояние ПК. Команды Windows — в commands.py."""
import datetime, html, os, re, subprocess, time
from dataclasses import dataclass
import mss, psutil
from PIL import Image

NOWIN = 0x08000000  # CREATE_NO_WINDOW
HOME = os.path.expanduser("~")

@dataclass
class Reply:
    text: str = ""
    mood: str = None          # None — эмоция по смыслу текста (emotions.for_reply)
    html: str = ""
    image: str = ""
    copy_image: bool = False  # в буфер обмена — только для скриншота, картинки из поиска буфер не трогают
    fx: dict = None           # описание карточки-анимации для чата (ui/switchfx.py): переключатель, шкала, таймер

    def __post_init__(self):
        if self.mood is None:
            from core import emotions
            self.mood = emotions.for_reply(self.text)


# ---------- скриншот ----------
def screenshot():
    folder = os.path.join(HOME, "Pictures", "Mico")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, time.strftime("screenshot_%Y%m%d_%H%M%S.png"))
    with mss.mss() as s:
        shot = s.grab(s.monitors[0])
    Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX").save(path)
    return Reply(f"Готово! Скриншот сохранён ({path}) и скопирован в буфер обмена 📸", "surprised", image=path,
                 copy_image=True)


# ---------- напоминания ----------
def reminder(ql, notify):
    if not re.search(r"\bнапомни", ql):
        return None
    m = re.search(r"напомни(?:\s+мне)?\s+через\s+(\d+)\s*(сек|мин|час|ч)\w*\s*(.*)", ql)
    if not m:
        return Reply("Скажи так: «напомни через 10 минут выпить воды» ⏰", "curious")
    n, unit, text = int(m.group(1)), m.group(2), m.group(3).strip() or "время вышло!"
    secs = n * (1 if unit.startswith("сек") else 60 if unit.startswith("мин") else 3600)
    from data import reminders
    reminders.add(text, time.time() + secs, notify)          # сохраняется и переживёт перезапуск
    return Reply(f"Хорошо, напомню через {n} {unit}. ⏰", None)


# ---------- состояние ПК ----------
def sysinfo(ql):
    if re.search(r"который час|сколько времени|какое (сегодня )?число|какой (сегодня )?день", ql):
        now = datetime.datetime.now()
        return Reply(f"Сейчас {now:%H:%M}, {now:%d.%m.%Y} 🕒", None)
    if re.search(r"заряд|батаре", ql):
        b = psutil.sensors_battery()
        if not b:
            return Reply("Не вижу батарею — наверное, это настольный ПК 🔌", "curious")
        return Reply(f"Заряд {b.percent:.0f}% {'(заряжается ⚡)' if b.power_plugged else '(от батареи 🔋)'}", None)
    if re.search(r"процессор|\bcpu\b|что грузит|нагрузк", ql):
        procs = list(psutil.process_iter(["name"]))
        for p in procs:
            try:
                p.cpu_percent(None)
            except psutil.Error:
                pass
        time.sleep(0.6)
        top = []
        for p in procs:
            try:
                top.append((p.cpu_percent(None), p.info["name"]))
            except psutil.Error:
                pass
        top = sorted(top, reverse=True)[:3]
        return Reply(f"Процессор загружен на {psutil.cpu_percent():.0f}%. Больше всего: " +
                     ", ".join(f"{n} ({c:.0f}%)" for c, n in top) + " 💻", "curious")
    if re.search(r"оперативн|\bозу\b|сколько памяти|\bram\b", ql):
        v = psutil.virtual_memory()
        return Reply(f"Память: занято {v.used / 2**30:.1f} из {v.total / 2**30:.1f} ГБ ({v.percent:.0f}%) 🧠", "curious")
    if re.search(r"место на диск|свободно на диск|сколько места", ql):
        d = psutil.disk_usage(os.path.splitdrive(HOME)[0] + "\\")
        return Reply(f"Диск: свободно {d.free / 2**30:.0f} из {d.total / 2**30:.0f} ГБ 💾", "curious")
    return None


def get_clipboard():
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                       capture_output=True, text=True, encoding="utf-8", creationflags=NOWIN, timeout=10)
    return r.stdout
