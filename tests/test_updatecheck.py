"""Проверка новой версии: сравнение номеров, разбор ответа GitHub, работа без сети, раз в сутки.
Сеть подменена, поэтому тесты работают без интернета."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)

import requests
import updatecheck as U
import version

NOW = 1_800_000_000.0


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


# --- номера ---
check(U.version_of("v2026.10.1231") == "2026.10.1231")
check(U.version_of("2026.10.1230") == "2026.10.1230")
check(U.version_of("release-1") is None)
check(U.version_of("3.29") is None)
check(U.version_of("") is None)

check(U.is_newer("2026.10.1231", "2026.10.1230"))
check(U.is_newer("2026.11.0101", "2026.10.1230"))          # другой месяц
check(not U.is_newer("2026.10.1230", "2026.10.1230"))      # та же версия — не предлагаем
check(not U.is_newer("2026.10.1229", "2026.10.1230"))      # откат — не предлагаем

# --- разбор ответа GitHub ---
class _Resp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data
    def json(self):
        return self._data

def fake_get(answer):
    def get(*a, **k):
        if isinstance(answer, Exception):
            raise answer
        return _Resp(200, answer)
    return get

def with_get(answer, fn):
    old = requests.get
    requests.get = fake_get(answer)
    try:
        return fn()
    finally:
        requests.get = old

good = {"tag_name": "v2026.10.1231", "html_url": "https://github.com/Serdzh29/Mico-AI/releases/tag/v2026.10.1231",
        "body": "Новое\nвторая строка", "draft": False, "prerelease": False}
info = with_get(good, lambda: U.fetch_latest())
check(info and info["tag"] == "v2026.10.1231" and info["url"].endswith("v2026.10.1231"), info)
check(with_get(dict(good, draft=True), lambda: U.fetch_latest()) is None, "черновик не должен предлагаться")
check(with_get(dict(good, prerelease=True), lambda: U.fetch_latest()) is None, "предварительный выпуск не предлагаем")
check(with_get({"message": "Not Found"}, lambda: U.fetch_latest()) is None, "нет tag_name — ничего")
check(with_get(requests.ConnectionError("нет сети"), lambda: U.fetch_latest()) is None, "без сети тихо None")

# --- check(): предлагаем, когда есть новее ---
cfg = {"update_check": True, "update_channel": "stable", "update_checked_at": 0}
calls = []
def fetch_newer():
    calls.append(1)
    return {"tag": "v2026.10.1231", "url": version.RELEASE_PAGE_URL, "notes": "Исправления"}
res = U.check(cfg, now=NOW, fetch=fetch_newer, local="2026.10.1230")
check(res and res["version"] == "2026.10.1231", res)
check(cfg["update_checked_at"] == NOW, "дата проверки записана")

# --- не чаще раза в сутки ---
res = U.check(cfg, now=NOW + 3600, fetch=fetch_newer, local="2026.10.1230")
check(res is None and len(calls) == 1, "внутри суток повторно не спрашиваем")
res = U.check(cfg, now=NOW + U.DAY + 1, fetch=fetch_newer, local="2026.10.1230")
check(res is not None and len(calls) == 2, "через сутки снова проверяем")

# --- ничего нового ---
cfg2 = {"update_check": True, "update_channel": "stable", "update_checked_at": 0}
same = lambda: {"tag": "v2026.10.1230", "url": "u", "notes": ""}
check(U.check(cfg2, now=NOW, fetch=same, local="2026.10.1230") is None, "та же версия — молчим")
check(cfg2["update_checked_at"] == NOW, "проверка прошла, дата записана")

# --- без сети: не отмечаем проверку, спросим в следующий запуск ---
cfg3 = {"update_check": True, "update_channel": "stable", "update_checked_at": 0}
check(U.check(cfg3, now=NOW, fetch=lambda: None, local="2026.10.1230") is None)
check(cfg3["update_checked_at"] == 0, "без сети дату не трогаем")

# --- выключатели ---
off = {"update_check": False, "update_channel": "stable", "update_checked_at": 0}
check(U.check(off, now=NOW, fetch=fetch_newer, local="2026.10.1230") is None and len(calls) == 2,
      "при выключенной проверке сеть не трогаем")
beta = {"update_check": True, "update_channel": "beta", "update_checked_at": 0}
check(U.check(beta, now=NOW, fetch=fetch_newer, local="2026.10.1230") is None and len(calls) == 2,
      "на бета-канале своя схема обновлений")

# --- текст предложения ---
txt = U.offer_text({"version": "2026.10.1231", "notes": "Первая строка\nвторая"})
check("2026.10.1231" in txt and "Первая строка" in txt and "ничего не скачивает" in txt, txt)
check("вторая" not in txt, "в предложении только первая строка заметок")

print("ALL OK")
