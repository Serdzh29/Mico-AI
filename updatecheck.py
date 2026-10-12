"""Проверка новой версии Mico. При запуске, не чаще раза в сутки, один запрос к GitHub.
Mico ничего не скачивает и не ставит сам: он сообщает о новой версии и открывает страницу релизов,
а решение за пользователем. Без сети или при ошибке проверка молча пропускается."""
import re
import time

import requests

import version

DAY = 24 * 3600
TIMEOUT = 6
_VERSION = re.compile(r"\d{4}\.\d{2}\.\d{4}")       # ГГГГ.ММ.ДДNN, как в version.APP_VERSION


def fetch_latest(api_url=None, timeout=TIMEOUT):
    """Последний опубликованный (не черновик и не предварительный) релиз: {'tag', 'url', 'notes'}.
    None — если сети нет, сервер ответил ошибкой или релиза ещё нет."""
    try:
        r = requests.get(api_url or version.RELEASE_API_URL, timeout=timeout,
                         headers={"Accept": "application/vnd.github+json", "User-Agent": "Mico-update-check"})
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = str(data.get("tag_name") or "").strip()
    if not tag:
        return None
    return {"tag": tag, "url": str(data.get("html_url") or version.RELEASE_PAGE_URL),
            "notes": str(data.get("body") or "").strip()[:600]}


def version_of(tag):
    """'v2026.10.1231' → '2026.10.1231'. None, если это не номер Mico."""
    s = str(tag or "").strip().lstrip("vV").strip()
    return s if _VERSION.fullmatch(s) else None


def is_newer(remote, local):
    return version._vt(remote) > version._vt(local)


def should_check(cfg, now):
    if not cfg.get("update_check", True):
        return False
    if cfg.get("update_channel", "stable") == "beta":       # на бета-канале обновления идут своим путём
        return False
    return now - float(cfg.get("update_checked_at") or 0) >= DAY


def check(cfg, now=None, fetch=fetch_latest, local=None):
    """Есть ли версия новее установленной. Возвращает {'version', 'tag', 'url', 'notes'} или None.
    Меняет cfg['update_checked_at'] только если сервер ответил: без сети проверим в следующий запуск."""
    now = time.time() if now is None else now
    if not should_check(cfg, now):
        return None
    info = fetch()
    if not info:
        return None
    cfg["update_checked_at"] = now
    remote = version_of(info["tag"])
    if not remote or not is_newer(remote, local or version.APP_VERSION):
        return None
    return {**info, "version": remote}


def offer_text(info):
    lines = [f"Вышла новая версия Mico: {info['version']}. У тебя {version.APP_VERSION}.", ""]
    if info.get("notes"):
        lines += [info["notes"].splitlines()[0][:200], ""]
    lines.append("Mico ничего не скачивает сам. Открыть страницу, чтобы скачать?")
    return "\n".join(lines)
