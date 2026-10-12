import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import dialog as D


def test_remembers_within_window_and_forgets_after():
    d = D.Dialog(window=900)
    d.add("user", "громкость 30", now=1000)
    d.add("mico", "Громкость 30%", now=1001)
    assert len(d.recent(now=1500)) == 2                # через 8 минут помнит
    assert d.recent(now=1002 + 900) == []              # обе реплики старше окна — забывает


def test_keeps_only_last_turns():
    d = D.Dialog(max_turns=3)
    for i in range(5):
        d.add("user", f"реплика {i}", now=i)
    assert [t[2] for t in d.recent(now=5)] == ["реплика 2", "реплика 3", "реплика 4"]


def test_messages_map_roles_for_chat_model():
    d = D.Dialog()
    d.add("user", "привет", now=1)
    d.add("mico", "Привет!", now=2)
    assert d.messages(now=3) == [{"role": "user", "content": "привет"},
                                 {"role": "assistant", "content": "Привет!"}]


def test_long_text_is_cut():
    d = D.Dialog()
    d.add("mico", "я" * 1000, now=1)
    assert len(d.recent(now=2)[0][2]) == D.MAX_CHARS


def test_followup_needs_context_and_short_or_continuing_phrase():
    d = D.Dialog()
    assert not d.is_followup("а если больше")          # контекста нет
    d.add("user", "громкость 30", now=100)
    assert d.is_followup("а если больше", now=110)     # продолжающая фраза
    assert d.is_followup("сделай так же", now=110)
    assert d.is_followup("громкость 50", now=110)      # короткая
    assert not d.is_followup("расскажи подробно про историю Древнего Рима и его падение", now=110)
    assert not d.is_followup("расскажи про Марс", now=110)          # обычный короткий вопрос — не переписываем


def test_rewrite_prompt_contains_context_and_request():
    d = D.Dialog()
    d.add("user", "громкость 30", now=1)
    d.add("mico", "Громкость 30%", now=2)
    p = d.rewrite_prompt("а если больше", now=3)
    assert "громкость 30" in p and "а если больше" in p and "НЕТ" in p


def test_clean_rewrite_handles_model_answers():
    assert D.Dialog.clean_rewrite("громкость 40", "а если больше") == "громкость 40"
    assert D.Dialog.clean_rewrite("«Громкость 40».", "а если больше") == "Громкость 40"
    assert D.Dialog.clean_rewrite("НЕТ", "а если больше") is None
    assert D.Dialog.clean_rewrite("", "а если больше") is None
    assert D.Dialog.clean_rewrite("громкость 30", "громкость 30") is None      # то же самое
    assert D.Dialog.clean_rewrite("x" * 300, "а") is None                      # слишком длинно


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
