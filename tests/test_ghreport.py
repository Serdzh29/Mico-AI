"""Отзывы бета-тестеров через GitHub: маскировка путей, текст отчёта, ссылка на обсуждение,
согласие версии 3, подсчёт использования. Без сети и без Windows."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys, types, tempfile
from urllib.parse import unquote, urlparse, parse_qs
sys.path.insert(0, ROOT)
_TMP = tempfile.mkdtemp()
_os.environ["APPDATA"] = _TMP
for m in ["mss", "psutil", "win32gui", "win32process", "win32con", "requests", "PIL", "PIL.Image", "pyautogui"]:
    sys.modules.setdefault(m, types.ModuleType(m))
sys.modules["mss"].mss = object
sys.modules["PIL"].Image = types.SimpleNamespace()
class _RE(Exception):
    pass
sys.modules["requests"].RequestException = _RE

import ghreport as G
import features
import version
import brain as B
import storage
import winctl as W

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

# --- пути не попадают в отчёт ---
check(G.mask_paths(r"Файл C:\Users\serge\Documents\договор.pdf и D:\Игры\a.exe") == "Файл <путь> и <путь>")
check("serge" not in G.mask_paths(r"Ошибка в C:\Users\serge\x.py"), "имя пользователя скрыто")

# --- текст отчёта: ошибка и отзыв ---
bug = G.build_body("bug", "2026.10.1303", "beta", "Windows, сборка 10.0.26340",
                   {"workspace": 2, "clipboard_search": 0}, log_tail=r"Error at C:\Users\serge\a.py")
check("2026.10.1303 (beta)" in bug and "Рабочее место — 2" in bug, bug)
check("История копирования" not in bug, "нулевые счётчики не выводим")
check("serge" not in bug and "<путь>" in bug, "журнал без путей")
check("## Что случилось" in bug and "## Как воспроизвести" in bug, bug)
check("Журнал ошибок" not in G.build_body("bug", "v", "beta", "w", {}), "журнал только по выбору")

usage = G.build_body("usage", "2026.10.1303", "beta", "w", {"day_summary": 5}, log_tail="ничего не должно попасть")
check("Итог дня — 5" in usage and "## Что мешает" in usage, usage)
check("ничего не должно попасть" not in usage, "журнал не добавляется в отзыв об использовании")

# --- ссылка на новое обсуждение ---
url = G.issue_url(version.ISSUES_REPO, "bug", bug)
parsed = urlparse(url)
check(parsed.netloc == "github.com" and parsed.path == "/Serdzh29/Mico-AI/issues/new", url)
q = parse_qs(parsed.query)
check(q["template"] == ["beta_bug.md"] and q["title"] == ["[БЕТА] Ошибка"], q)
check(q["body"][0] == bug, "текст в ссылке совпадает с отчётом")
long_body = "x" * (G.MAX_BODY + 500)
check(G.is_too_long(long_body) and "обрезан" in parse_qs(urlparse(G.issue_url("a/b", "usage", long_body)).query)["body"][0])
check(parse_qs(urlparse(G.issue_url("a/b", "usage", "коротко")).query)["template"] == ["beta_usage.md"])

# --- согласие: версия 3, публичность сказана прямо ---
check(features.BETA_CONSENT_VERSION == 3, "при изменении текста согласия версия растёт")
check("публичны" in features.BETA_CONSENT_TEXT and "GitHub" in features.BETA_CONSENT_TEXT, "сказано, что отзывы публичны")
check("по твоему действию" in features.BETA_CONSENT_TEXT, "отправка только по действию пользователя")

# --- подсчёт использования: только число, через фразу в чате ---
version.BUILD_CHANNEL = "beta"
cfg = {"update_channel": "beta"}
b = B.Brain.__new__(B.Brain)
b.cfg, b.store, b.save_cfg = cfg, storage.Store(), (lambda: None)
W.visible_apps = lambda: []
b._beta_command("итог дня", "итог дня")
b._beta_command("итог дня", "итог дня")
b._beta_command("найди что я копировал про договор", "найди что я копировал про договор")
check(cfg["beta_usage"] == {"day_summary": 2, "clipboard_search": 1}, cfg.get("beta_usage"))
check(all(isinstance(v, int) for v in cfg["beta_usage"].values()), "только числа, без текста")
b._beta_command("какая погода", "какая погода")
check(cfg["beta_usage"] == {"day_summary": 2, "clipboard_search": 1}, "обычные фразы не считаем")

# --- в стабильной сборке счётчиков нет ---
version.BUILD_CHANNEL = "stable"
cfg2 = {"update_channel": "beta"}
b.cfg = cfg2
b._beta_command("итог дня", "итог дня")
check("beta_usage" not in cfg2, "стабильная сборка ничего не считает")
version.BUILD_CHANNEL = "beta"

print("ALL OK")
