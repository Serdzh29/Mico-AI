"""«Mico AI думает»: при вопросе из кнопок (объяснить, найти решение, короче, подробнее) в ленте есть строка с точками."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def test_busy_shows_animated_line_and_hides_when_done():
    w = read("aichat.py")
    body = w[w.index("    def set_busy(self, on):"):w.index("    def _restore_draft")]
    assert "chat_look.TypingRow(" in body and "self._add(self._thinking)" in body, "пузырь с точками появляется"
    assert "show_typing(True)" in body, "точки волной поднимаются, пока думает"
    assert "self._stop_thinking()" in body, "строка убирается по окончании"


def test_quick_questions_use_the_indicator():
    ui = read("intel_ui.py")
    q = ui[ui.index("    def quick(self, label, prompt, image=None):"):ui.index("    def _quick_done")]
    assert "self.aichat.set_busy(True)" in q
    done = ui[ui.index("    def _quick_done"):ui.index("    def _error_options")]
    assert "self.aichat.set_busy(False)" in done, "после ответа строка исчезает"


def test_rewrite_buttons_go_through_quick():
    ui = read("intel_ui.py")
    rw = ui[ui.index("    def rewrite(self, mode):"):ui.index("    def set_dnd")]
    assert "self.quick(" in rw, "«Короче» и «Подробнее» показывают тот же индикатор"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)


def test_body_shows_thinking_dots_during_quick_questions():
    ui = read("intel_ui.py")
    q = ui[ui.index("    def quick(self, label, prompt, image=None):"):ui.index("    def _quick_done")]
    assert 'self.blob.set_mood("thinking")' in q, "тело Mico думает"
    done = ui[ui.index("    def _quick_done"):ui.index("    def _error_options")]
    assert 'self.blob.set_mood("idle")' in done, "после ответа точки уходят"
    blob = read("blob.py")
    assert 'mood == "thinking"' in blob and "math.sin(t * 6" in blob, "три точки уже рисуются в blob.py"
