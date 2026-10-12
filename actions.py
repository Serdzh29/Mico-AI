"""Действия Mico: скриншоты, поиск файлов, напоминания, состояние ПК. Команды Windows — в commands.py."""
import datetime, html, os, re, subprocess, time
from dataclasses import dataclass
from urllib.parse import quote
import mss, psutil
from PIL import Image

NOWIN = 0x08000000  # CREATE_NO_WINDOW
HOME = os.path.expanduser("~")

CAPS = ("Вот что я умею (напиши команду в чат):\n"
        "📸 Скриншот — «сделай скриншот»\n"
        "👀 Смотреть на экран — «что у меня на экране?», «помоги ответить другу»\n"
        "🕐 Помнить, что ты делал — «что я делал час назад?»\n"
        "📁 Искать файлы — «найди файл договор pdf»\n"
        "🚀 Программы и сайты — «открой блокнот, калькулятор и хром», «открой сайт apple.com», «закрой хром»\n"
        "🔎 Поиск в интернете — «загугли рецепт борща»\n"
        "📡 Связь — «включи/выключи wi-fi», «блютуз», «режим полёта», «точка доступа»\n"
        "🔕 Режимы — «не беспокоить», «тёмная тема», «экономия заряда», «игровой режим», «скрытые файлы»\n"
        "🔊 Звук и экран — «громкость 30», «громче», «без звука», «яркость 50», «ярче», «следующий трек»\n"
        "🪟 Окна — «переключи задачу», «сверни все», «новый рабочий стол», «переключись на телеграм»\n"
        "⏰ Время — «таймер на 10 минут», «будильник на 7:30», «напомни через час позвонить»\n"
        "⚙️ Настройки — «открой настройки Bluetooth» (любой раздел Windows)\n"
        "⚡ Питание — «заблокируй пк», «сон», «выключи/перезагрузи пк» (спрошу подтверждение)\n"
        "📋 Буфер обмена — «переведи то, что в буфере»\n"
        "💻 Состояние ПК — «заряд батареи», «что грузит процессор», «сколько места на диске»\n"
        "💬 И просто болтать!")


@dataclass
class Reply:
    text: str = ""
    mood: str = "idle"
    html: str = ""
    image: str = ""


# ---------- скриншот ----------
def screenshot():
    folder = os.path.join(HOME, "Pictures", "Mico")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, time.strftime("screenshot_%Y%m%d_%H%M%S.png"))
    with mss.mss() as s:
        shot = s.grab(s.monitors[0])
    Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX").save(path)
    return Reply(f"Готово! Скриншот сохранён ({path}) и скопирован в буфер обмена 📸", "surprised", image=path)


# ---------- поиск файлов ----------
STOP = set("найди найти поищи поиск искать ищи файл файлы файла документ документы мне пожалуйста на компьютере "
           "пк по в с про где лежит называется название именем папку папка диске скачанный скачанные".split())
EXT = {"pdf": (".pdf",), "word": (".docx", ".doc"), "ворд": (".docx", ".doc"), "docx": (".docx",),
       "excel": (".xlsx", ".xls"), "эксель": (".xlsx", ".xls"), "таблиц": (".xlsx", ".xls", ".csv"),
       "презентац": (".pptx", ".ppt"), "картинк": (".png", ".jpg", ".jpeg", ".gif", ".webp"),
       "фото": (".png", ".jpg", ".jpeg", ".heic"), "изображен": (".png", ".jpg", ".jpeg", ".gif", ".webp"),
       "видео": (".mp4", ".mkv", ".avi", ".mov"), "музык": (".mp3", ".wav", ".flac"), "текстов": (".txt", ".md")}
SKIP_DIRS = {"node_modules", "appdata", "$recycle.bin", "__pycache__", "site-packages"}


def _user_dirs():
    out = []
    for n in ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music"):
        for base in (HOME, os.path.join(HOME, "OneDrive")):
            p = os.path.join(base, n)
            if os.path.isdir(p) and p not in out:
                out.append(p)
    return out


def find_files(ql, limit=10, seconds=8):
    exts, stems = [], []
    for w in re.findall(r"[\w.\-]+", ql):
        if w in STOP:
            continue
        hit = next((v for k, v in EXT.items() if w.startswith(k)), None)
        if hit:
            exts += hit
        else:
            stems.append(w[:-2] if len(w) > 5 else w)
    if not exts and not stems:
        return Reply("Что искать? Например: «найди файл договор pdf» 📁", "curious")
    found, deadline = [], time.time() + seconds
    for root in _user_dirs():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if not d.startswith(".") and d.lower() not in SKIP_DIRS]
            for f in fn:
                low = f.lower()
                if exts and not low.endswith(tuple(exts)):
                    continue
                if all(s in low for s in stems):
                    p = os.path.join(dp, f)
                    try:
                        found.append((os.path.getmtime(p), p))
                    except OSError:
                        pass
            if time.time() > deadline:
                break
    if not found:
        return Reply("Ничего не нашёл 😔 Попробуй другое слово.", "sad")
    found.sort(reverse=True)
    rows = "".join(
        f'<a href="mico-open:{quote(p)}">{html.escape(os.path.basename(p))}</a> '
        f'<a href="mico-dir:{quote(p)}">📂</a><br><small style="color:#888">{html.escape(os.path.dirname(p))}</small><br>'
        for _, p in found[:limit])
    return Reply(f"Нашёл {len(found)}", "happy",
                 html=f"Нашёл {len(found)} (показываю {min(limit, len(found))} новейших). Нажми на имя, чтобы открыть, "
                      f"или на 📂, чтобы показать в папке:<br>{rows}")


# ---------- напоминания ----------
def reminder(ql, notify):
    if not re.search(r"\bнапомни", ql):
        return None
    m = re.search(r"напомни(?:\s+мне)?\s+через\s+(\d+)\s*(сек|мин|час|ч)\w*\s*(.*)", ql)
    if not m:
        return Reply("Скажи так: «напомни через 10 минут выпить воды» ⏰", "curious")
    n, unit, text = int(m.group(1)), m.group(2), m.group(3).strip() or "время вышло!"
    secs = n * (1 if unit.startswith("сек") else 60 if unit.startswith("мин") else 3600)
    import reminders
    reminders.add(text, time.time() + secs, notify)          # сохраняется и переживёт перезапуск
    return Reply(f"Хорошо, напомню через {n} {unit}. ⏰", "happy")


# ---------- состояние ПК ----------
def sysinfo(ql):
    if re.search(r"который час|сколько времени|какое (сегодня )?число|какой (сегодня )?день", ql):
        now = datetime.datetime.now()
        return Reply(f"Сейчас {now:%H:%M}, {now:%d.%m.%Y} 🕒", "happy")
    if re.search(r"заряд|батаре", ql):
        b = psutil.sensors_battery()
        if not b:
            return Reply("Не вижу батарею — наверное, это настольный ПК 🔌", "curious")
        return Reply(f"Заряд {b.percent:.0f}% {'(заряжается ⚡)' if b.power_plugged else '(от батареи 🔋)'}", "happy")
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
