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
        self.db.execute("CREATE TABLE IF NOT EXISTS clips(ts INTEGER, text BLOB)")      # история копирования (бета)
        self.db.execute("CREATE TABLE IF NOT EXISTS chat(ts INTEGER, role TEXT, text BLOB)")  # журнал разговора
        self.db.execute("CREATE INDEX IF NOT EXISTS i_chat ON chat(ts)")
        self.db.execute("CREATE TABLE IF NOT EXISTS day_summary(day TEXT PRIMARY KEY, text BLOB, ts INTEGER)")  # пересказ дня
        self.db.execute("CREATE TABLE IF NOT EXISTS todos(id INTEGER PRIMARY KEY AUTOINCREMENT, text BLOB, done INTEGER, ts INTEGER)")
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

    def add_chat(self, ts, role, text):
        """Реплика разговора: role — 'user' (ты) или 'mico'. Текст шифруется, как и остальной журнал."""
        with self.lock:
            self.db.execute("INSERT INTO chat VALUES(?,?,?)", (int(ts), str(role), self._enc(text[:2000])))
            self.db.commit()

    def chats_between(self, t0, t1, limit=400):
        """Реплики за период, от старых к новым (не больше limit последних)."""
        with self.lock:
            rows = self.db.execute("SELECT ts, role, text FROM chat WHERE ts>=? AND ts<? "
                                   "ORDER BY ts DESC LIMIT ?", (int(t0), int(t1), int(limit))).fetchall()
        return [(ts, role, self.f.decrypt(t).decode()) for ts, role, t in reversed(rows)]

    def count_chat(self, t0, t1):
        with self.lock:
            return self.db.execute("SELECT COUNT(*) FROM chat WHERE ts>=? AND ts<?",
                                   (int(t0), int(t1))).fetchone()[0]

    def add_day_summary(self, day, text, ts):
        """Пересказ дня: day — ключ «ГГГГ-ММ-ДД». Текст шифруется, как и журнал."""
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO day_summary VALUES(?,?,?)", (day, self._enc(text), int(ts)))
            self.db.commit()

    def has_day_summary(self, day):
        with self.lock:
            return self.db.execute("SELECT 1 FROM day_summary WHERE day=?", (day,)).fetchone() is not None

    def day_summaries(self, k0, k1):
        """Пересказы дней от k0 (включая) до k1 (не включая) → {ключ: текст}."""
        with self.lock:
            rows = self.db.execute("SELECT day, text FROM day_summary WHERE day>=? AND day<? ORDER BY day",
                                   (k0, k1)).fetchall()
        return {day: self.f.decrypt(t).decode() for day, t in rows}

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

    def add_todo(self, ts, text):
        with self.lock:
            cur = self.db.execute("INSERT INTO todos(text, done, ts) VALUES(?,0,?)", (self._enc(text[:300]), int(ts)))
            self.db.commit()
            return cur.lastrowid

    def list_todos(self):
        """[(id, текст, выполнено)] — сначала открытые, потом выполненные."""
        with self.lock:
            rows = self.db.execute("SELECT id, text, done FROM todos ORDER BY done, id").fetchall()
        return [(i, self.f.decrypt(t).decode(), bool(d)) for i, t, d in rows]

    def set_todo_done(self, tid, done=True):
        with self.lock:
            self.db.execute("UPDATE todos SET done=? WHERE id=?", (1 if done else 0, tid))
            self.db.commit()

    def clear_done_todos(self):
        with self.lock:
            cur = self.db.execute("DELETE FROM todos WHERE done=1")
            self.db.commit()
            return cur.rowcount

    def add_clip(self, ts, text):
        import clipbuf
        with self.lock:
            self.db.execute("INSERT INTO clips VALUES(?,?)", (int(ts), self._enc(text[:clipbuf.MAX_LEN])))
            self.db.execute("DELETE FROM clips WHERE rowid NOT IN "
                            "(SELECT rowid FROM clips ORDER BY ts DESC LIMIT ?)", (clipbuf.KEEP,))
            self.db.commit()

    def list_clips(self):
        """Последние копии, от новых к старым: [(ts, текст)]."""
        with self.lock:
            rows = self.db.execute("SELECT ts, text FROM clips ORDER BY ts DESC").fetchall()
        return [(ts, self.f.decrypt(t).decode()) for ts, t in rows]

    def forget_clips(self):
        with self.lock:
            self.db.execute("DELETE FROM clips")
            self.db.execute("DELETE FROM todos")
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
            self.db.execute("DELETE FROM chat WHERE ts>=?", (cut,))
            self.db.execute("DELETE FROM day_summary WHERE day>=?", (time.strftime("%Y-%m-%d", time.localtime(cut)),))
            self.db.commit()

    def purge(self, days):
        if days <= 0:                 # 0 — хранить историю всегда
            return
        with self.lock:
            cut = int(time.time() - days * 86400)
            self.db.execute("DELETE FROM events WHERE end<?", (cut,))
            self.db.execute("DELETE FROM actions WHERE ts<?", (cut,))
            self.db.execute("DELETE FROM chat WHERE ts<?", (cut,))
            self.db.execute("DELETE FROM day_summary WHERE day<?", (time.strftime("%Y-%m-%d", time.localtime(cut)),))
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
            self.db.execute("DELETE FROM clips")
            self.db.execute("DELETE FROM chat")
            self.db.execute("DELETE FROM day_summary")
            self.db.commit()
