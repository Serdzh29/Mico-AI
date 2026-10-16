"""Проверки исправлений WI по отзыву: звук, две линии при появлении, скругление, думающий Mico, чат и сон."""
import os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()

import intel


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_thinner_default_strip():
    check(intel.THICK_DEFAULT == 4, "стандартная полоска тоньше")
    check(intel.thickness({}) == 4 and intel.THICK_MIN < intel.THICK_DEFAULT, "по умолчанию тонкая, минимум меньше")


def test_glow_and_side_capsule_replace_the_strip():
    ui = read("intel_ui.py")
    check("self.island = None" in ui and "Island(cfg, blob)" not in ui, "плашка «слушаю» убрана")
    check("def paintEvent" in ui and "QLinearGradient(QPointF(0, h), QPointF(0, h - bh))" in ui, "мягкое свечение снизу")
    check("class EdgeGlow" in ui and "addRoundedRect" not in ui and "_ring" not in ui, "полоска по краю убрана")
    check(intel.glow_height({"wi_thickness": 4}) == 88 and intel.STATE_TEXT["think"] == "думаю…", "высота и подписи")
    check(intel.glow_height({"wi_thickness": 99}) == 48 + intel.THICK_MAX * 10, "высота ограничена")


def test_thinking_is_mico_not_dots():
    ui = read("intel_ui.py")
    body = ui[ui.index("    def busy"):ui.index("\n    def ", ui.index("    def busy") + 5)]
    check('set_mood("thinking")' in body and 'set_mood("idle")' in body, "Mico сам думает, пока пишет ответ")
    chat = read("wichat.py")
    check("_dots" not in chat and "typing" not in chat, "точек в чате нет")


def test_chat_leaves_with_mico_and_blocks_sleep():
    ui = read("intel_ui.py")
    sleep = ui[ui.index("    def on_sleep"):ui.index("    def _gone")]
    check("self.wichat.dismiss()" in sleep, "Mico уходит — чат уходит с ним")
    main = read("main.py")
    check("intel_ctl.wichat.isVisible()" in main, "открытый чат не даёт Mico уснуть")


def test_chat_effect_is_removed_after_fade():
    chat = read("wichat.py")
    check("after=lambda: widget.setGraphicsEffect(None)" in chat, "после проявления эффект снимаем — текст не рвётся")


def test_html_answers_reach_wi_chat_as_text():
    txt = intel.plain_from_html("<div><b>Погода</b><br>Тепло, +12</div><p>Завтра дождь</p>")
    check("Погода" in txt and "Тепло, +12" in txt and "<" not in txt, "карточки становятся текстом")
    check(intel.plain_from_html("") != "", "пустой html — короткая подсказка, не пусто")
    main = read("main.py")
    check('self.queue.append(("wi", plain))' in main and 'elif kind == "wi":' in main, "html-ответ дублируется текстом для WI")
    check("if r is None:" in main and "Ответа нет. Попробуй сказать иначе." in main, "пустой ответ — не молчим")


def test_strip_is_kept_while_thinking():
    ui = read("intel_ui.py")
    glow = ui[ui.index("class EdgeGlow"):ui.index("    def pulse")]
    check("if not on and self.keep:" in glow, "полоска не гаснет, пока думает")
    busy = ui[ui.index("    def busy"):ui.index("\n    def ", ui.index("    def busy") + 5)]
    check("self.glow.keep = bool(on)" in busy, "busy держит полоску")
    check("self.glow.keep = True" in ui[ui.index("    def quick"):ui.index("    def _quick_done")], "вопрос из файла/буфера тоже держит")
    check("self.glow.keep = False" in ui[ui.index("    def _quick_done"):ui.index("    def _offer")], "после ответа — отпускаем")
    check("self.glow.keep = False" in ui[ui.index("    def _leave"):ui.index("    def _tour(")], "при выключении WI отпускаем")


def test_no_sound_left_in_wi():
    import glob
    for f in ("intel_ui.py", "main.py", "wichat.py", "intel.py", "version.py"):
        check("sounds" not in read(f) and "wi_sound" not in read(f), f"в {f} не осталось звуков")
    check(not os.path.exists(os.path.join(ROOT, "sounds.py")), "модуль звуков удалён")
    check(not os.path.exists(os.path.join(ROOT, "assets", "sounds")), "файлов звука нет")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
