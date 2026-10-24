"""Инициатива («Mico AI сам начинает разговор») убрана полностью, пункта «Чат» в меню нет,
модель в памяти Ollama держится 5 минут и не греется при запуске. Без Qt, Ollama и Windows."""
import ast, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import menu_items

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def _read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()

def test_initiative_module_and_tests_are_gone():
    check(not os.path.exists(os.path.join(ROOT, "initiative.py")))
    check(not os.path.exists(os.path.join(ROOT, "tests", "test_initiative.py")))

def test_no_initiative_or_glance_code_left():
    pat = re.compile(r"initiative_on|initiative_min|\bglance\b|GLANCE_PROMPT|wi_watch|"
                     r"import .*\binitiative\b|\bini_gate\b|\bini_t\b|Mico AI сам начинает разговор")
    for name in ["main.py", "brain.py", "settings_info.py", "features.py", "intel_ui.py", "intel.py"]:
        found = pat.findall(_read(name))
        check(not found, (name, found))

def test_features_have_no_initiative():
    import features
    check("initiative" not in features.FEATURES and features.SETTING_FEATURE == {})

def test_chat_is_not_in_context_menu():
    check("chat" not in menu_items.LABELS and "chat" not in menu_items.DEFAULT_ON)
    check("chat" not in menu_items.visible({"menu_items": ["chat"]}))
    src = _read("main.py")
    check('item == "chat"' not in src, "обработчика пункта «Чат» нет")

def test_model_leaves_memory_quickly_and_no_prewarm():
    brain = _read("brain.py")
    check('KEEP_ALIVE = "1m"' in brain, "модель выгружается через минуту")
    check('0 if image_b64 else KEEP_ALIVE' in brain, "после экрана модель выгружается сразу")
    check("def warm_up" not in brain and "warm_up" not in _read("main.py"), "прогрева при запуске нет")

def test_brain_still_parses():
    ast.parse(_read("brain.py"))
    ast.parse(_read("main.py"))

def test_no_loaded_memory_text_and_no_load_warning():
    for name in ["aichat.py", "intel.py"]:
        src = _read(name)
        check("в памяти" not in src, (name, "«в памяти» убрано из надписей"))
        check("нагружает" not in src, (name, "предупреждение о нагрузке убрано"))
    check("loaded_models" not in _read("brain.py") and "memory_provider" not in _read("aichat.py"))

def test_model_button_shows_exact_tag():
    src = _read("aichat.py")
    check('self.model_info_ready.emit(self.cfg.get("text_model")' in src, "кнопка показывает полное имя с тегом")
    check('split(":")[0]' not in src, "тег не отрезается")

def test_claude_not_offered_and_vision_models_selectable():
    brain = _read("brain.py")
    check('"claude"' not in brain, "claude убран из списка для скачивания")
    for tag in ("qwen3-coder", "gpt-oss:20b", "glm-4.7-flash"):
        check(f'"{tag}"' in brain, f"{tag} есть в списке для скачивания")
    check(":cloud" not in brain, "облачные модели не добавляем: Mico работает локально")
    check("VISION_MODELS = [" in brain and "SUGGEST_VISION = VISION_MODELS" in brain, "для экрана несколько моделей")
    main = _read("main.py")
    check("self.vm" in main, "выбор модели для экрана в настройках есть")
    check('cfg.get("vision_model") not in SUGGEST_VISION' in main, "выбранная модель для экрана сохраняется")

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
