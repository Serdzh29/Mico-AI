"""Шифрованное локальное хранилище таймлайна (SQLite + Fernet, ключ под защитой DPAPI)."""
import os, sqlite3, threading, time
from cryptography.fernet import Fernet

APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")
os.makedirs(APPDIR, exist_ok=True)

try:
    import win32crypt
except ImportError:  # запуск не на Windows (только для разработки)
    win32crypt = None


def _load_key() -> bytes:
    path = os.path.join(APPDIR, "key.bin")
    if os.path.exists(path):
        raw = open(path, "rb").read()
        return win32crypt.CryptUnprotectData(raw, None, None, None, 0)[1] if win32crypt else raw
    key = Fernet.generate_key()
    blob = win32crypt.CryptProtectData(key, "Mico", None, None, None, 0) if win32crypt else key
    with open(path, "wb") as f:
        f.write(blob)
    return key


class Store:
    def __init__(self):
        self.f = Fernet(_load_key())
        self.lock = threading.Lock()
        self.db = sqlite3.connect(os.path.join(APPDIR, "timeline.db"), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS events(start INTEGER, end INTEGER, process BLOB, title BLOB)")
        self.db.execute("CREATE INDEX IF NOT EXISTS i_start ON events(start)")
        self.db.execute("CREATE TABLE IF NOT EXISTS actions(ts INTEGER, text BLOB)")   # что просил пользователь
        self.db.execute("CREATE TABLE IF NOT EXISTS fixes(k TEXT PRIMARY KEY, typo BLOB, fix BLOB)")  # опечатки
        self.db.execute("CREATE TABLE IF NOT EXISTS words(k TEXT PRIMARY KEY, w BLOB)")             # свой словарь
        self.db.execute("CREATE TABLE IF NOT EXISTS reminders(id TEXT PRIMARY KEY, due INTEGER, text BLOB)")
        try:                                                    # миграция: правило повтора (старые базы)
            self.db.execute("ALTER TABLE reminders ADD COLUMN rule TEXT")
        except sqlite3.OperationalError:
            pass
        self.db.execute("CREATE TABLE IF NOT EXISTS feedback(ts INTEGER, kind TEXT, body BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS notes(ts INTEGER, text BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS index_items(k TEXT PRIMARY KEY, kind TEXT, name BLOB, path BLOB, mtime INTEGER, size INTEGER)")
        self.db.commit()

    def _enc(self, s: str) -> bytes:
        return self.f.encrypt(s.encode())

    def add(self, start, end, process, title):
        with self.lock:
            self.db.execute("INSERT INTO events VALUES(?,?,?,?)",
                            (int(start), int(end), self._enc(process), self._enc(title)))
            self.db.commit()

    def between(self, t0, t1):
        with self.lock:
            rows = self.db.execute(
                "SELECT start,end,process,title FROM events WHERE end>=? AND start<=? ORDER BY start",
                (int(t0), int(t1))).fetchall()
        return [(s, e, self.f.decrypt(p).decode(), self.f.decrypt(t).decode()) for s, e, p, t in rows]

    @staticmethod
    def _key(s):
        import hashlib
        return hashlib.sha256(s.encode()).hexdigest()

    def save_fix(self, typo, fix):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO fixes VALUES(?,?,?)",
                            (self._key(typo), self._enc(typo), self._enc(fix)))
            self.db.commit()

    def load_fixes(self):
        with self.lock:
            rows = self.db.execute("SELECT typo, fix FROM fixes").fetchall()
        return {self.f.decrypt(a).decode(): self.f.decrypt(b).decode() for a, b in rows}

    def save_word(self, w):
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO words VALUES(?,?)", (self._key(w), self._enc(w)))
            self.db.commit()

    def load_words(self):
        with self.lock:
            rows = self.db.execute("SELECT w FROM words").fetchall()
        return [self.f.decrypt(r[0]).decode() for r in rows]

    def add_note(self, ts, text):
        with self.lock:
            self.db.execute("INSERT INTO notes VALUES(?,?)", (int(ts), self._enc(text)))
            self.db.commit()

    def list_notes(self, limit=200):
        with self.lock:
            rows = self.db.execute("SELECT ts, text FROM notes ORDER BY ts DESC LIMIT ?", (int(limit),)).fetchall()
        return [{"ts": ts, "text": self.f.decrypt(t).decode()} for ts, t in reversed(rows)]

    def add_feedback(self, entry):
        """Отзыв зашифровывается целиком (текст, вопрос, ответ)."""
        import json as _json
        with self.lock:
            self.db.execute("INSERT INTO feedback VALUES(?,?,?)",
                            (int(entry.get("time", time.time())), entry["kind"],
                             self._enc(_json.dumps(entry, ensure_ascii=False))))
            self.db.commit()

    def list_feedback(self, limit=500):
        import json as _json
        with self.lock:
            rows = self.db.execute("SELECT body FROM feedback ORDER BY ts DESC LIMIT ?", (int(limit),)).fetchall()
        return [_json.loads(self.f.decrypt(r[0]).decode()) for r in rows]

    def replace_index(self, records):
        """Полностью заменяет индекс. Имена и пути шифруются."""
        with self.lock:
            self.db.execute("DELETE FROM index_items")
            self.db.executemany(
                "INSERT INTO index_items VALUES(?,?,?,?,?,?)",
                [(self._key(r["path"]), r["kind"], self._enc(r["name"]), self._enc(r["path"]),
                  int(r["mtime"]), int(r["size"])) for r in records])
            self.db.commit()

    def load_index(self):
        with self.lock:
            rows = self.db.execute("SELECT kind, name, path, mtime, size FROM index_items").fetchall()
        return [{"kind": k, "name": self.f.decrypt(n).decode(), "path": self.f.decrypt(p).decode(),
                 "mtime": m, "size": s} for k, n, p, m, s in rows]

    def add_reminder(self, rid, due, text, rule=None):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO reminders(id, due, text, rule) VALUES(?,?,?,?)",
                            (rid, int(due), self._enc(text), rule))
            self.db.commit()

    def list_reminders(self):
        with self.lock:
            rows = self.db.execute("SELECT id, due, text, rule FROM reminders ORDER BY due").fetchall()
        return [{"id": r[0], "due": r[1], "text": self.f.decrypt(r[2]).decode(), "rule": r[3]} for r in rows]

    def delete_reminder(self, rid):
        with self.lock:
            self.db.execute("DELETE FROM reminders WHERE id=?", (rid,))
            self.db.commit()

    def add_action(self, ts, text):
        with self.lock:
            self.db.execute("INSERT INTO actions VALUES(?,?)", (int(ts), self._enc(text[:300])))
            self.db.commit()

    def actions_between(self, t0, t1):
        with self.lock:
            rows = self.db.execute("SELECT ts,text FROM actions WHERE ts>=? AND ts<=? ORDER BY ts",
                                   (int(t0), int(t1))).fetchall()
        return [(ts, self.f.decrypt(t).decode()) for ts, t in rows]

    def forget(self, seconds):
        with self.lock:
            cut = int(time.time() - seconds)
            self.db.execute("DELETE FROM events WHERE end>=?", (cut,))
            self.db.execute("DELETE FROM actions WHERE ts>=?", (cut,))
            self.db.commit()

    def purge(self, days):
        if days <= 0:                 # 0 — хранить историю всегда
            return
        with self.lock:
            cut = int(time.time() - days * 86400)
            self.db.execute("DELETE FROM events WHERE end<?", (cut,))
            self.db.execute("DELETE FROM actions WHERE ts<?", (cut,))
            self.db.commit()

    def wipe(self):
        with self.lock:
            self.db.execute("DELETE FROM events")
            self.db.execute("DELETE FROM actions")
            self.db.execute("DELETE FROM fixes")
            self.db.execute("DELETE FROM words")
            self.db.execute("DELETE FROM reminders")
            self.db.execute("DELETE FROM index_items")
            self.db.execute("DELETE FROM feedback")
            self.db.execute("DELETE FROM notes")
            self.db.commit()
