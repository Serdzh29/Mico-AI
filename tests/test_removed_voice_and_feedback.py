"""Отзывы («отчёт об ошибке», «предложить идею») убраны полностью: модулей нет, в коде и документах нет упоминаний.
Голос возвращён (Piper + Whisper, см. voice_*.py), но системные голоса Windows запрещены: проверяем это ниже.
Также: прогресс скачивания модели не больше её размера, строки Ollama внизу не показываем,
«что ты умеешь» без устаревших пунктов. Без Qt, микрофона и Ollama."""
import ast, json, os, re, sys, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import capabilities as C
from ui import menu as menu_items

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
    skip_dirs = {"__pycache__", ".git", ".github", "tests", "node_modules", "build", "dist", "mico-ad"}
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
    src = _read("data/storage.py")
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

# ---------- скачивание модели (теперь model_store: один GGUF, без Ollama) ----------
def test_old_registry_pull_is_gone():
    brain = _read("core/brain.py")
    check("pull_model" not in brain and "REGISTRY" not in brain and "model_layer_sizes" not in brain,
          "выкачка через реестр Ollama удалена")
    check("pulling" not in _read("llm/store.py") and "pulling" not in _read("setup/installer.py"),
          "строки статуса Ollama («pulling …») не показываем")


class _Resp:
    def __init__(self, body, total=None):
        self.status_code = 200
        self._body = body
        self.headers = {"Content-Length": str(len(body) if total is None else total)}

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_progress_never_exceeds_model_size():
    """Раньше скачано оказывалось больше размера модели (777 из 626 МБ) и полоска шла дальше 100%."""
    import tempfile
    from unittest import mock
    from llm import store as S
    bars = []
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(S.requests, "get", return_value=_Resp(b"x" * 5000)):
            ok = S.download("qwen3.5-4b", progress=lambda d, t: bars.append((d, t)), root=tmp)
    check(ok is True and bars, "прогресс передаётся")
    for done, total in bars:
        check(0 <= done <= total, (done, total))
    dones = [d for d, _ in bars]
    check(dones == sorted(dones), "полоска не откатывается назад")
    check(bars[-1] == (5000, 5000), bars[-1])


def test_manifest_gives_total_before_download_starts():
    """Итог известен сразу: полоска не растёт рывками и не пересчитывается по ходу."""
    import tempfile
    from unittest import mock
    from llm import store as S
    bars = []
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(S.requests, "get", return_value=_Resp(b"x" * 5000)):
            S.download("qwen3.5-4b", progress=lambda d, t: bars.append((d, t)), root=tmp)
    check(bars[0] == (0, 5000), f"сразу итог: {bars[0]}")
    check(all(t == 5000 for _d, t in bars), bars)


def test_negative_or_broken_numbers_never_show_negative_progress():
    """Раньше на экране было «-1606 из 626 МБ · -257%». Мусор в Content-Length не роняет загрузку."""
    import tempfile
    from unittest import mock
    from llm import store as S
    bars = []
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(S.requests, "get", return_value=_Resp(b"x" * 300, "мусор")):
            S.download("qwen3.5-4b", progress=lambda d, t: bars.append((d, t)), root=tmp)
    for done, total in bars:
        check(0 <= done and total > 0 and done <= total, (done, total))


def test_pull_errors_are_still_reported():
    import tempfile
    from unittest import mock
    from llm import store as S
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.object(S.requests, "get", side_effect=S.requests.ConnectionError("нет сети")):
            check(S.download("qwen3.5-4b", root=tmp, retries=2) is False, "обрыв связи — честный False")
        check(not os.path.exists(S.path_for("qwen3.5-4b", tmp)), "недокачанная модель не выдаётся за готовую")


def test_pull_bar_is_clamped_and_says_nothing_about_verifying():
    check("min(done, total)" in _read("setup/installer.py"), "полоска не показывает больше размера модели и не отрицательной")
    check("проверяю…" not in _read("core/brain.py"), "строк Ollama внизу нет")

# ---------- строка модели в чате ----------
def test_aichat_model_label_has_no_not_in_memory_text():
    src = _read("assist/chat.py")
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
