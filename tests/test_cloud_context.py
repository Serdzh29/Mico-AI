"""Контекст диалога в облачном режиме: короткие вопросы не теряют предыдущие реплики. Без Windows и сети."""
import os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core import dialog   # noqa: E402


def test_short_question_is_not_seen_as_followup():
    """Так и было в жалобе: «что она делает» не считалось продолжением, и история в запрос не попадала."""
    d = dialog.Dialog()
    d.add("user", "расскажи про supersell")
    d.add("mico", "Supersell — финская компания.")
    assert not d.is_followup("что она делает")


def test_history_keeps_recent_turns_for_cloud():
    d = dialog.Dialog()
    d.add("user", "расскажи про supersell")
    d.add("mico", "Supersell — финская компания.")
    msgs = d.messages(limit=8)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert "supersell" in msgs[0]["content"]


def test_history_expires_after_window():
    d = dialog.Dialog(window=60)
    old = time.time() - 3600
    d.add("user", "старый вопрос", now=old)
    assert d.messages() == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
