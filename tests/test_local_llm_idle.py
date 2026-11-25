"""Встроенная модель уходит из памяти после простоя. Раньше unload_if_idle() никто не вызывал."""
import os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from llm import engine as L


def test_idle_model_is_unloaded_and_busy_one_is_kept():
    e = L._Engine()
    e._llm, e._path, e._layers = object(), "model.gguf", 0
    e._last = time.time()
    e.unload_if_idle()
    assert e._llm is not None, "модель, которой только что ответили, остаётся"
    e._last = time.time() - L.KEEP_SEC - 1
    e.unload_if_idle()
    assert e._llm is None and e._path is None, "после простоя модель выгружается"


def test_watchdog_is_wired_to_load_and_idle_check():
    src = open(os.path.join(ROOT, "llm/engine.py"), encoding="utf-8").read()
    assert "def _start_watch" in src and "self._start_watch()" in src, "фоновая проверка запускается при загрузке"
    assert "time.sleep(WATCH_SEC)" in src and "self.unload_if_idle()" in src, "фоновая проверка вызывает выгрузку"
    assert L.WATCH_SEC <= 60, "проверка должна идти чаще, чем раз в минуту"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK local_llm idle unload")
