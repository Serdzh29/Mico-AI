"""Проверки связки brain.py и commands.py. brain и commands тянут Windows-модули, поэтому
регулярки вытаскиваем из исходника (ast), а остальное проверяем по тексту. Так не нужен Windows."""
import ast, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def _regex_from_class(name, attr):
    """Значение атрибута класса вида attr = re.compile(r\"...\") из исходника."""
    tree = ast.parse(_src(name))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == attr for t in node.targets):
            call = node.value
            parts = []
            for a in call.args:                          # несколько строк подряд склеиваются, как в Python
                parts.append(ast.literal_eval(a) if isinstance(a, ast.Constant) else "")
            return re.compile("".join(parts))
    raise AssertionError(f"{attr} не найден в {name}")


def test_deictic_question_triggers_active_window_note():
    rx = _regex_from_class("core/brain.py", "_DEICTIC")
    for q in ["что это?", "как тут сделать", "что это такое", "здесь что-то не так?"]:
        assert rx.search(q.lower()), q
    for q in ["открой блокнот", "какая погода в Москве", "как настроить wi-fi"]:
        assert not rx.search(q.lower()), q


def test_undo_phrase_is_exact():
    rx = _regex_from_class("core/brain.py", "_UNDO")
    for q in ["отмени", "отмени последнее действие", "отмени команду", "отмени последнее"]:
        assert rx.fullmatch(q), q
    for q in ["отмени сортировку", "отмени выключение", "отмени напоминание"]:
        assert not rx.fullmatch(q), q


def test_own_actions_question_matches_only_about_mico():
    rx = _regex_from_class("core/brain.py", "_OWN_ACTIONS")
    for q in ["что ты сам сделал?", "что ты делал на компьютере", "какие действия ты выполнил"]:
        assert rx.search(q), q
    assert not rx.search("что я делал вчера")
    assert not rx.search("что ты умеешь")


def test_changes_pc_pattern_covers_direct_commands_not_questions():
    rx = _regex_from_class("core/brain.py", "_CHANGES_PC")
    for q in ["громче", "открой блокнот", "включи тёмную тему", "яркость 50", "заблокируй пк"]:
        assert rx.match(q), q
    assert not rx.match("что на экране?")


def test_brain_integration_points_exist():
    src = _src("core/brain.py")
    must = [
        "user_profile.parse_command(q)", "self._profile_command(*pcmd)",
        "followup=followup", "context=self._active_app_note(q)", "self._profile_note(str(user))",
        "history = []\n        if use_history:", "self._extract_candidates(conv_id, rows)",
        "self.refresh_profile()", "on_no=lambda: self._count_reject(name)",
        "commands.preferred_browser_name = self._preferred_browser_name",
        "self._journal(what, text)", "self._undo_last()", "self._own_actions()",
    ]
    for frag in must:
        assert frag in src, frag


def test_brain_does_not_add_initiative():
    src = _src("core/brain.py")
    for bad in ("threading.Timer", "def _proactive", "auto_message", "suggest_now"):
        assert bad not in src, bad
    assert "ask_model_proactively" not in src


def test_commands_confirmation_has_refusal_hook_and_browser_routing():
    src = _src("win/commands.py")
    assert "def _ask(question, fn, on_no=None, ttl=30):" in src
    assert "_PENDING[\"no\"]()" in src, "отказ вызывает обработчик"
    assert "pref = preferred_browser_name()" in src and "_open_item(pref, strict=True)" in src
    assert "webbrowser.open(\"about:blank\")" in src, "если любимого браузера нет — прежнее поведение"


def test_os_action_prompt_does_not_conflict_with_mood_tag():
    src = _src("core/brain.py")
    assert "mood_tag and not tools" in src, "для JSON-действий метка настроения не должна загрязнять ответ"
    assert '"\\n" + osagent.prompt() if tools else ""' in src


def test_profile_regexes_in_brain_compile():
    for name in ("_DEICTIC", "_UNDO", "_OWN_ACTIONS", "_CHANGES_PC"):
        _regex_from_class("core/brain.py", name)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK brain wiring")
