"""Профиль и журнал действий в зашифрованной базе: в файле не должно быть открытого текста."""
import os, sys, tempfile, time, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()          # настоящий профиль пользователя не трогаем

from data import storage
from data import profile as U


def _store():
    return storage.Store()


def test_profile_round_trip_and_encrypted_on_disk():
    st = _store()
    p = U.merge(U.empty(), None, U.candidate_facts(["Работаю программистом на Python"]))
    st.save_profile(p)
    assert st.load_profile()["facts"][0]["text"] == "Работаю программистом на Python"
    raw = sqlite3.connect(os.path.join(storage.APPDIR, "timeline.db")).execute(
        "SELECT body FROM profile").fetchone()[0]
    assert b"programmist" not in raw and "программистом".encode() not in raw, "факты должны быть зашифрованы"


def test_empty_profile_when_nothing_saved():
    st = _store()
    st.db.execute("DELETE FROM profile")
    st.db.commit()
    assert st.load_profile() == {"facts": [], "forgotten": []}


def test_mico_action_journal_add_list_and_wipe():
    st = _store()
    st.wipe()
    now = time.time()
    st.add_mico_action(now - 60, "громкость 30% — Готово.")
    st.add_mico_action(now - 30, "открыть «блокнот» — Открыл.")
    rows = st.mico_actions_between(now - 3600, now + 1)
    assert [t for _, t in rows] == ["громкость 30% — Готово.", "открыть «блокнот» — Открыл."]
    st.wipe()
    assert st.mico_actions_between(now - 3600, now + 1) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok  ", name)
    print("OK profile store")
