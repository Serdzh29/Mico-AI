"""Инициатива («Mico AI сам начинает разговор») убрана полностью, пункта «Чат» в меню нет,
модель в памяти Ollama держится 5 минут и не греется при запуске. Без Qt, Ollama и Windows."""
import ast, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from ui import menu as menu_items

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
    for name in ["mico.py", "core/brain.py", "ui/info.py", "core/features.py", "assist/ui.py", "assist/intel.py"]:
        found = pat.findall(_read(name))
        check(not found, (name, found))

def test_features_have_no_initiative():
    from core import features
    check("initiative" not in features.FEATURES and features.SETTING_FEATURE == {})

def test_chat_is_not_in_context_menu():
    check("chat" not in menu_items.LABELS and "chat" not in menu_items.DEFAULT_ON)
    check("chat" not in menu_items.visible({"menu_items": ["chat"]}))
    src = _read("mico.py")
    check('item == "chat"' not in src, "обработчика пункта «Чат» нет")

def test_model_warms_in_background_and_still_leaves_memory():
    llm = _read("llm/engine.py")
    m = re.search(r"KEEP_SEC\s*=\s*(\d+)", llm)
    check(m and int(m.group(1)) <= 300, "модель выгружается после простоя, а не живёт в памяти вечно")
    check("unload_if_idle" in llm, "выгрузка простоя работает")
    # прогрев при старте — требование живого отклика: первый вопрос не должен ждать загрузку модели
    check("def warmup(" in llm and "llm-warmup" in llm, "прогрев идёт в фоновом потоке")
    brain, main_src = _read("core/brain.py"), _read("mico.py")
    check("warmup" in brain and "brain.warmup()" in main_src, "прогрев запускается при старте и при открытии чата")

def test_brain_still_parses():
    ast.parse(_read("core/brain.py"))
    ast.parse(_read("mico.py"))

def test_no_loaded_memory_text_and_no_load_warning():
    for name in ["assist/chat.py", "assist/intel.py"]:
        src = _read(name)
        check("в памяти" not in src, (name, "«в памяти» убрано из надписей"))
        check("нагружает" not in src, (name, "предупреждение о нагрузке убрано"))
    check("loaded_models" not in _read("core/brain.py") and "memory_provider" not in _read("assist/chat.py"))

def test_chat_has_no_model_picker_anymore():
    src = _read("assist/chat.py")
    check("model_pick" not in src and "Модель:" not in src, "единственную модель нельзя переключать из чата")
    check("model_info_ready" not in src and "refresh_model_info" not in src,
          "интерфейс не показывает лишнюю кнопку выбора модели")

def test_claude_not_offered_and_vision_models_gone():
    brain = _read("core/brain.py")
    check('"claude"' not in brain, "claude убран из списка для скачивания")
    catalog = _read("llm/catalog.py")
    check(":cloud" not in catalog, "облачные модели не добавляем: Mico работает локально")
    check("VISION_MODELS" not in brain and "is_vision_model" not in brain, "vision-модели убраны: экран смотрит Groq")
    main = _read("mico.py")
    check("self.vm" not in main and 'cfg.pop("vision_model", None)' in main, "выбора модели для экрана в настройках нет")

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
