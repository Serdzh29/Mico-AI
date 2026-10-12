"""Индекс компьютера: установленные программы, игры, папки, фото, документы, музыка, видео.
Индексируются только имена, пути, размеры и даты. Содержимое файлов не читается.
Индекс хранится зашифрованно в Store. Прогресс — в процентах через callback."""
import os, re, threading, time

from ru_text import translit

PHOTO = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".raw", ".cr2", ".nef"}
VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}
MUSIC = {".mp3", ".flac", ".wav", ".m4a", ".ogg"}
DOC = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".md", ".rtf", ".odt"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "site-packages", "appdata", "$recycle.bin",
             "system volume information", "windows", "temp", ".cache"}
MAX_DEPTH = 6
MAX_RECORDS = 200_000

STATE = {"running": False, "percent": 0, "count": 0, "updated": 0.0, "error": ""}
_lock = threading.Lock()


def kind_of(name):
    ext = os.path.splitext(name)[1].lower()
    if ext in PHOTO:
        return "photo"
    if ext in VIDEO:
        return "video"
    if ext in MUSIC:
        return "music"
    if ext in DOC:
        return "document"
    return None


def steam_libraries(steam_root=None):
    """Папки Steam с играми (из libraryfolders.vdf). Если Steam не найден — пустой список."""
    roots = []
    base = steam_root or os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Steam")
    vdf = os.path.join(base, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        try:
            text = open(vdf, encoding="utf-8", errors="replace").read()
            roots += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', text)]
        except OSError:
            pass
    if os.path.isdir(os.path.join(base, "steamapps")):
        roots.append(base)
    return [os.path.join(r, "steamapps", "common") for r in roots
            if os.path.isdir(os.path.join(r, "steamapps", "common"))]


def user_roots():
    home = os.path.expanduser("~")
    names = ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"]
    return [os.path.join(home, n) for n in names if os.path.isdir(os.path.join(home, n))]


def program_roots():
    out = []
    pd = os.environ.get("ProgramData", r"C:\ProgramData")
    out.append(os.path.join(pd, r"Microsoft\Windows\Start Menu\Programs"))
    out.append(os.path.join(os.path.expanduser("~"), r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs"))
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        p = os.environ.get(var)
        if p:
            out.append(p)
    return [o for o in out if os.path.isdir(o)]


def _skipped(name):
    return name.startswith(".") or name.lower() in SKIP_DIRS


def _walk(root, depth=0):
    """Обходит каталоги с ограничением глубины и пропуском служебных папок."""
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for e in entries:
        if _skipped(e.name):
            continue
        try:
            if e.is_dir(follow_symlinks=False):
                if depth < MAX_DEPTH:
                    yield from _walk(e.path, depth + 1)
            elif e.is_file(follow_symlinks=False):
                yield e
        except OSError:
            continue


def _record(kind, name, path, st=None):
    try:
        st = st or os.stat(path)
        mtime, size = int(st.st_mtime), int(st.st_size)
    except OSError:
        mtime, size = 0, 0
    return {"kind": kind, "name": name, "path": path, "mtime": mtime, "size": size}


def collect(progress=None, roots_user=None, roots_programs=None, roots_games=None):
    """Собирает записи индекса. progress(percent, text) вызывается по ходу."""
    def report(p, text):
        if progress:
            progress(max(0, min(100, int(p))), text)

    user = roots_user if roots_user is not None else user_roots()
    prog = roots_programs if roots_programs is not None else program_roots()
    games = roots_games if roots_games is not None else steam_libraries()
    plan = [("game", r) for r in games] + [("app", r) for r in prog] + [("user", r) for r in user]
    records, seen = [], set()
    total = max(1, len(plan))
    for i, (mode, root) in enumerate(plan):
        report(i / total * 100, f"Сканирую {os.path.basename(root) or root}")
        if mode == "game":
            try:
                for d in os.scandir(root):
                    if d.is_dir(follow_symlinks=False) and d.path not in seen:
                        seen.add(d.path)
                        records.append(_record("game", d.name, d.path))
            except OSError:
                pass
            continue
        if mode == "app":
            for e in _walk(root, depth=2):
                ext = os.path.splitext(e.name)[1].lower()
                if ext in (".lnk", ".exe") and e.path not in seen:
                    seen.add(e.path)
                    name = os.path.splitext(e.name)[0]
                    records.append(_record("app", name, e.path))
            continue
        for e in _walk(root):
            if len(records) >= MAX_RECORDS:
                break
            kind = kind_of(e.name)
            if kind and e.path not in seen:
                seen.add(e.path)
                records.append(_record(kind, e.name, e.path))
        if mode == "user":
            try:
                for d in os.scandir(root):
                    if d.is_dir(follow_symlinks=False) and d.path not in seen and not _skipped(d.name):
                        seen.add(d.path)
                        records.append(_record("folder", d.name, d.path))
            except OSError:
                pass
    report(100, f"Готово: {len(records)} элементов")
    return records


def run(store, progress=None, done=None):
    """Запускает индексацию в фоне и сохраняет результат. Повторный запуск во время работы игнорируется."""
    with _lock:
        if STATE["running"]:
            return False
        STATE.update(running=True, percent=0, error="")

    def work():
        def prog(p, text):
            STATE.update(percent=p, updated=time.time())
            if progress:
                progress(p, text)
        try:
            recs = collect(progress=prog)
            store.replace_index(recs)
            STATE.update(count=len(recs), percent=100, updated=time.time())
            if done:
                done(len(recs), "")
        except Exception as e:
            STATE["error"] = f"{e.__class__.__name__}: {e}"
            if done:
                done(0, STATE["error"])
        finally:
            STATE["running"] = False
    threading.Thread(target=work, daemon=True).start()
    return True


def status_text():
    if STATE["running"]:
        return f"Индексация идёт: {STATE['percent']}%"
    if STATE["error"]:
        return f"Индексация не получилась: {STATE['error']}"
    if STATE["count"]:
        return f"Индекс готов: {STATE['count']} элементов."
    return "Индекс ещё не создан. Скажи «проиндексируй компьютер»."


STOP = set("найди найти поищи покажи где мой моя мои мне файл файлы файла открой запусти мне пожалуйста "
           "на компьютере у меня есть было был".split())
KIND_WORDS = {"фото": "photo", "фотк": "photo", "картинк": "photo", "снимк": "photo",
              "видео": "video", "фильм": "video", "музык": "music", "песн": "music", "трек": "music",
              "документ": "document", "договор": "document", "таблиц": "document", "презентац": "document",
              "игр": "game", "приложен": "app", "программ": "app", "папк": "folder"}


def search(query, records, limit=8):
    """Поиск по индексу. Возвращает список записей, самые подходящие первыми."""
    q = query.lower().replace("ё", "е")
    words = [w for w in re.findall(r"[а-яa-z0-9]+", q) if w not in STOP]
    kinds = {v for k, v in KIND_WORDS.items() if any(k in w for w in words)}
    terms = [w for w in words if not any(k in w for k in KIND_WORDS)]
    # «телеграм» должен находить Telegram: ищем и по транслитерации
    variants = {t: {t, translit(t)} for t in terms}
    scored = []
    for r in records:
        name = r["name"].lower()
        score = 0
        for t, vs in variants.items():
            if any(v and v in name for v in vs):
                score += 3 if any(name.startswith(v) for v in vs if v) else 2
            elif any(v and v in r["path"].lower() for v in vs):
                score += 1
        if kinds and r["kind"] in kinds:
            score += 2
        elif kinds and not terms:
            continue
        if terms and score == 0:
            continue
        if not terms and not kinds:
            continue
        scored.append((score, r["mtime"], r))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [r for _, _, r in scored[:limit]]
