"""Проверка версии по сайту Mico AI при каждом запуске.

Сайт отдаёт номер последней версии (сейчас 2512). Если он больше номера этой сборки (setup.version.UPDATE_BUILD), Mico
не пускает в чат и просит обновиться. Без сети, при ошибке сайта или если номер на странице не удалось прочитать,
Mico работает как обычно: из-за неполадок сайта пользователь не должен остаться без помощника."""
import json
import re

from setup import version

TIMEOUT = 6
_KEYS = ("version", "latest", "latest_version", "build", "ver", "v")
_NUM = re.compile(r"\d{3,5}")
_LABELLED = re.compile(r"(?:верси[яию]|version|build|сборк[аи]|latest)\s*[:=#\"'>\s-]{0,12}(?:M|v)?\s*(\d{3,5})(?![\d.])", re.I)
_META = re.compile(r"<meta[^>]+name=[\"']?(?:version|build)[\"']?[^>]+content=[\"']?(\d{3,5})", re.I)
_LONE = re.compile(r"(?<![\d.\-/:])(2[1-9]\d\d|[3-9]\d{3})(?![\d.\-/:])")      # 2100…9999: годы 2020–2099 сюда не попадают


def parse_build(text):
    """Номер последней версии из ответа сайта (JSON или страница). None — не нашли однозначно."""
    text = str(text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, (int, float)):
        return int(data)
    if isinstance(data, dict):
        for k in _KEYS:
            if k in data:
                m = _NUM.search(str(data[k]))
                if m:
                    return int(m.group())
    m = _META.search(text)
    if m:
        return int(m.group(1))
    plain = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    plain = re.sub(r"<[^>]+>", " ", plain)
    found = {int(x) for x in _LABELLED.findall(plain)}
    if len(found) == 1:
        return found.pop()
    lone = {int(x) for x in _LONE.findall(plain)}
    if len(lone) == 1:
        return lone.pop()
    return None


def fetch_latest(url=None, timeout=TIMEOUT):
    """Номер последней версии с сайта или None, если сети нет или номер не нашёлся."""
    base = (url or version.SITE_URL).rstrip("/") + "/"
    try:
        import requests
    except Exception:
        return None
    for path in ("", "version", "version.json", "api/version"):
        try:
            r = requests.get(base + path, timeout=timeout, headers={"User-Agent": "Mico-update-check"})
        except Exception:
            if not path:
                return None                      # главная не открылась — сети нет, остальное не пробуем
            continue
        if r.status_code != 200:
            continue
        build = parse_build(r.text)
        if build:
            return build
    return None


def check(local=None, fetch=fetch_latest):
    """{'latest': 2512, 'url': сайт}, если на сайте версия новее этой сборки. Иначе None."""
    local = int(local if local is not None else version.UPDATE_BUILD)
    latest = fetch()
    if not latest or latest <= local:
        return None
    return {"latest": latest, "local": local, "url": version.SITE_URL}
