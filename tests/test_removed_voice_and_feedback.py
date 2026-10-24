"""Отзывы («отчёт об ошибке», «предложить идею») убраны полностью: модулей нет, в коде и документах нет упоминаний.
Голос возвращён (Piper + Whisper, см. voice_*.py), но системные голоса Windows запрещены: проверяем это ниже.
Также: прогресс скачивания модели не больше её размера, строки Ollama внизу не показываем,
«что ты умеешь» без устаревших пунктов. Без Qt, микрофона и Ollama."""
import ast, json, os, re, sys, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import capabilities as C
import menu_items

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def _read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

# ---------- модули удалены ----------
def test_voice_and_feedback_modules_are_gone():
    for name in ["report.py", "feedback.py"]:
        check(not os.path.exists(os.path.join(ROOT, name)), f"{name} должен быть удалён")
    for name in ["test_feedback.py"]:
        check(not os.path.exists(os.path.join(ROOT, "tests", name)), f"{name} должен быть удалён")

# ---------- нет системных голосов Windows ----------
# Голос Mico — только свои модели (Piper, faster-whisper). Встроенные средства Windows и онлайн-сервисы запрещены.
WINDOWS_VOICE = re.compile(r"SAPI|pyttsx3|SpeechSynthesizer|Windows\.Media\.SpeechRecognition|"
                           r"speech_recognition|SpeechRecognizer|win32com\.client\.Dispatch\(['\"]SAPI|"
                           r"recognize_google|recognize_bing|OneCore")
FEEDBACK_WORDS = re.compile(r"отчёт об ошибке|отчет об ошибке|Предложить идею|предложить идею|Ящик идей|"
                            r"ящик идей|Что-то не так|report\.build_report|feedback\.")

def _project_files():
    skip_dirs = {"__pycache__", ".git", ".github", "tests"}
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if name.endswith((".py", ".md", ".txt", ".bat", ".cmd", ".yml", ".json")):
                yield name, os.path.join(root, name)

def test_no_windows_voices_in_project():
    found = []
    for name, path in _project_files():
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in WINDOWS_VOICE.finditer(text):
            found.append((name, m.group(0)))
    check(not found, found)

def test_no_feedback_or_report_mentions_in_project():
    found = []
    for name, path in _project_files():
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in FEEDBACK_WORDS.finditer(text):
            found.append((name, m.group(0)))
    check(not found, found)

def test_requirements_and_build_do_not_need_voice_packages():
    req = _read("requirements.txt")
    # старое распознавание Vosk убрано; пакет vosk-tts (синтез речи, Apache 2.0) — отдельный движок голоса
    check(not re.search(r"^vosk(\s|[<>=]|$)", req, re.M) and "pyttsx3" not in req and "speech_recognition" not in req, req)
    for f in ("build_exe.bat", ".github/workflows/release.yml"):
        check(not re.search(r"collect-all vosk(?!_tts)", _read(f)), f"старый Vosk-распознаватель не собирается: {f}")

# ---------- меню и хранилище ----------
def test_menu_has_no_report_or_idea():
    ids = [i for i, _, _ in menu_items.ITEMS]
    check("report" not in ids and "idea" not in ids, ids)
    check("report" not in menu_items.DEFAULT_ON, menu_items.DEFAULT_ON)
    check(menu_items.visible({"menu_items": ["report", "idea", "settings"]}) == ["settings", "exit"],
          "старые настройки меню с этими пунктами не ломают показ")

def test_storage_drops_old_feedback_table():
    src = _read("storage.py")
    check("DROP TABLE IF EXISTS feedback" in src, "старая таблица отзывов удаляется")
    check("def add_feedback" not in src and "def list_feedback" not in src, "методов отзывов нет")

# ---------- «что ты умеешь» ----------
def test_capabilities_have_no_outdated_items():
    phrases = [p for _, items in C.CATEGORIES for p, _ in items]
    for stale in ["итог дня", "список дел", "Ctrl+Alt+M"]:
        check(not any(stale in p for p in phrases), (stale, phrases))
    check("Ctrl+Alt+M" not in C.html_capabilities({}), "подвал: чат — F8, а не Ctrl+Alt+M")
    check("F8" in C.html_capabilities({}), "подвал называет F8")

def test_capabilities_show_current_features():
    phrases = " | ".join(p for _, items in C.CATEGORIES for p, _ in items)
    for must in ["помодоро", "запомни рабочее место", "как дела у ПК?", "что занимает место",
                 "наведи порядок в загрузках", "запиши: купить молоко"]:
        check(must in phrases, must)

# ---------- скачивание модели ----------
def _brain_pull(lines, manifest=None):
    """Достаём REGISTRY, model_layer_sizes и pull_model из brain.py (без mss и win32gui).
    manifest — ответ реестра; None — реестр недоступен (get падает)."""
    src = _read("brain.py")
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("model_layer_sizes", "pull_model"))
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "REGISTRY" for t in n.targets))]
    class _Resp:
        def __init__(self, data=None):
            self.data = data
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def raise_for_status(self):
            pass
        def json(self):
            return self.data
        def iter_lines(self):
            return iter([json.dumps(x).encode() for x in lines])
    def get(url, **k):
        if manifest is None:
            raise ConnectionError("нет сети")
        return _Resp(manifest)
    fake = types.SimpleNamespace(post=lambda *a, **k: _Resp(), get=get, ConnectionError=ConnectionError)
    ns = {"requests": fake, "json": json, "BASE": "http://x",
          "time": types.SimpleNamespace(sleep=lambda s: None)}   # пауза между повторами не нужна в тесте
    exec(compile(ast.Module(body=keep, type_ignores=[]), "brain_pull", "exec"), ns)
    return ns["pull_model"]

def test_progress_never_exceeds_model_size():
    """Раньше скачано оказывалось больше размера модели (777 из 626 МБ) и полоска шла дальше 100%."""
    lines = [{"status": "pulling manifest"},
             {"status": "pulling a", "digest": "a", "total": 600, "completed": 600},
             {"status": "pulling a", "digest": "a", "total": 600, "completed": 700},   # переписанная строка слоя
             {"status": "pulling a", "digest": "a", "total": 600, "completed": 650},   # и откат назад
             {"status": "pulling b", "digest": "b", "total": 100, "completed": 100},
             {"status": "verifying sha256 digest"}, {"status": "success"}]
    bars = []
    ok = _brain_pull(lines)("m", lambda s: None, lambda d, t: bars.append((d, t)))
    check(ok is True)
    check(bars, "прогресс передаётся")
    for done, total in bars:
        check(0 <= done <= total, (done, total))
    check(bars[-1] == (700, 700), bars[-1])

def test_manifest_gives_total_before_download_starts():
    """Итог берём из манифеста реестра: полоска сразу знает, сколько всего, и не растёт рывками."""
    manifest = {"layers": [{"digest": "a", "size": 600}, {"digest": "b", "size": 100}],
                "config": {"digest": "c", "size": 10}}
    lines = [{"status": "pulling a", "digest": "a", "total": 600, "completed": 300},
             {"status": "pulling b", "digest": "b", "total": 100, "completed": 100},
             {"status": "pulling c", "digest": "c", "total": 10, "completed": 10},
             {"status": "success"}]
    bars = []
    _brain_pull(lines, manifest)("llama3.1:8b", lambda s: None, lambda d, t: bars.append((d, t)))
    check(bars[0] == (0, 710), f"сразу итог из манифеста: {bars[0]}")
    check(all(t == 710 for _d, t in bars), bars)
    check(bars[-1] == (710, 710), bars[-1])

def test_negative_or_broken_numbers_never_show_negative_progress():
    """Раньше на экране было «-1606 из 626 МБ · -257%»."""
    lines = [{"status": "pulling a", "digest": "a", "total": 600, "completed": -1606000000},
             {"status": "pulling a", "digest": "a", "total": 600, "completed": "bad"},
             {"status": "pulling a", "digest": "a", "total": 600, "completed": 100}]
    bars = []
    _brain_pull(lines)("m", lambda s: None, lambda d, t: bars.append((d, t)))
    for done, total in bars:
        check(0 <= done <= total, (done, total))

def test_pull_status_lines_are_not_reported():
    lines = [{"status": "pulling 5ee4f07cdb9b", "digest": "d", "total": 10, "completed": 5},
             {"status": "pulling 5ee4f07cdb9b", "digest": "d", "total": 10, "completed": 10}]
    shown = []
    _brain_pull(lines)("m", shown.append, None)
    check(not any("pulling" in s for s in shown), shown)

def test_pull_errors_are_still_reported():
    shown = []
    ok = _brain_pull([{"error": "model not found"}])("nope", shown.append, None)
    check(ok is False and shown and "model not found" in shown[-1], shown)

def test_pull_bar_is_clamped_and_says_checking_at_100():
    src = _read("main.py")
    check("max(0, min(done, total))" in src, "полоска не показывает больше размера модели и не отрицательной")
    check("проверяю…" in _read("brain.py"), "когда Ollama проверяет файлы, пишем об этом")

# ---------- строка модели в чате ----------
def test_aichat_model_label_has_no_not_in_memory_text():
    src = _read("aichat.py")
    check("не в памяти" not in src, "«не в памяти» убрано")

if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok  ", name)
            except Exception as e:
                fails += 1
                print("FAIL", name, "-", e)
    sys.exit(1 if fails else 0)
