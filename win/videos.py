"""Видео-сервисы: поиск и команды плеера (YouTube, Rutube, VK Видео, Яндекс Видео).
Чистая логика: адреса поиска, горячие клавиши плеера, разбор фраз и выбор видео из выдачи —
проверяется в tests/test_video_and_messengers.py без Windows и без сети.
Нажатия и клики делает win/agentwin. Субтитры переключаются клавишей c — состояние помним в рамках сессии."""
import re
from urllib.parse import quote

# сервисы: ключ → название и адрес поиска ({q} — запрос)
SERVICES = {
    "youtube": {"title": "YouTube", "home": "https://www.youtube.com",
               "search": "https://www.youtube.com/results?search_query={q}"},
    "rutube": {"title": "Rutube", "home": "https://rutube.ru",
              "search": "https://rutube.ru/search/?query={q}"},
    "vk": {"title": "VK Видео", "home": "https://vkvideo.ru",
          "search": "https://vkvideo.ru?q={q}"},
    "ya": {"title": "Яндекс Видео", "home": "https://yandex.ru/video",
          "search": "https://yandex.ru/video/search?text={q}"},
}
DEFAULT_SERVICE = "youtube"      # без названия сервиса ищем на YouTube: просят чаще всего

# как сервис зовут в речи → ключ («ё» уже заменена на «е»)
NAMES = {
    "youtube": "youtube", "ютуб": "youtube", "ютьюб": "youtube", "youtu": "youtube",
    "rutube": "rutube", "рутуб": "rutube", "рутюб": "rutube",
    "vk": "vk", "вк": "vk", "vk видео": "vk", "вк видео": "vk", "vkvideo": "vk",
    "яндекс видео": "ya", "яндекс.видео": "ya", "я.видео": "ya",
}

# клавиши плеера: работают, когда страница с видео в фокусе (YouTube-раскладка, её поддерживают и другие)
PLAYER_KEYS = {
    "play_pause": "k", "fullscreen": "f", "theater": "t", "mute": "m",
    "next": "shift+n", "prev": "shift+p", "close_video": "ctrl+w",
    "seek_back": "j", "seek_fwd": "l", "subtitles": "c",
}
# кнопки плеера, которые нажимаются мышью: названия на русском и английском
CLICK_BUTTONS = {
    "like": ("Нравится", "Like"),
    "dislike": ("Не нравится", "Dislike"),
    "subscribe": ("Подписаться", "Subscribe"),
}
# по заголовку окна понимаем, что это страница с видео, а не случайное окно
PLAYER_HINTS = ("youtube", "rutube", "vkvideo", "vk видео", "вк видео", "яндекс видео", "видео")

# служебные подписи в выдаче и интерфейсе — это не видео
NOISE = {"еще", "меню", "поиск", "назад", "вперед", "поделиться", "скачать", "смотреть позже",
         "подписаться", "все", "фильтры", "сортировка", "очистить", "настройки", "войти", "выйти"}

MAX_VIDEOS = 10                  # «открой 10 видео» — берём до десятого из выдачи


def _norm(s):
    return " ".join(str(s or "").lower().replace("ё", "е").split())


def service_key(name):
    """Название сервиса из речи → ключ. Незнакомое — YouTube."""
    s = _norm(name)
    for alias, key in sorted(NAMES.items(), key=lambda kv: -len(kv[0])):
        if alias in s:
            return key
    return DEFAULT_SERVICE


def search_url(site, query):
    """Адрес поиска видео. Пустой запрос — главная страница сервиса."""
    key = site if site in SERVICES else service_key(site)
    q = _norm(query)
    if not q:
        return SERVICES[key]["home"]          # без темы — главная страница сервиса
    return SERVICES[key]["search"].format(q=quote(q))


def player_key(action):
    """Клавиша плеера для действия. None — такое действие не нажимается клавишей."""
    return PLAYER_KEYS.get(action)


def click_names(action):
    """Названия кнопки плеера для нажатия мышью (русская и английская версии)."""
    return CLICK_BUTTONS.get(action, ())


def looks_like_player(title):
    """Окно похоже на страницу с видео: туда имеет смысл слать клавиши плеера."""
    t = _norm(title)
    return any(h in t for h in PLAYER_HINTS)


# субтитры в плеере переключаются одной клавишей: помним, какими были, чтобы не щёлкать зря
_SUBTITLES = {}


def subtitles_press(want):
    """Нажимать ли клавишу субтитров: True — состояние неизвестно или отличается от нужного."""
    key = "subtitles"
    cur = _SUBTITLES.get(key)
    _SUBTITLES[key] = bool(want)
    return cur != bool(want)


def is_subscribed(buttons):
    """Уже подписан на канал: кнопка сменила название — повторное нажатие бы отписало."""
    for b in buttons or []:
        low = _norm(b)
        if "вы подписаны" in low or "subscribed" in low or "отписаться" in low:
            return True
    return False


def pick_video(buttons, query, count=1):
    """Какое видео из выдачи нажимать: count-е подходящее по названию (1 — первое).
    Из списка подписей (кнопки и ссылки страницы) берём длинные названия роликов."""
    words = [w for w in re.findall(r"[а-яa-z0-9]+", _norm(query)) if len(w) >= 3]
    cands = []
    for b in buttons or []:
        name = " ".join(str(b or "").split())
        low = _norm(name)
        if len(name) < 10 or low in NOISE:
            continue
        score = sum(1 for w in words if w in low)
        if words and score == 0:
            continue                          # тема названа — берём только подходящие по теме
        cands.append((name, score))
    if not cands:
        return None
    cands.sort(key=lambda c: -c[1])           # лучшее совпадение — первым; порядок страницы сохраняется
    count = max(1, min(MAX_VIDEOS, int(count or 1)))
    return cands[count - 1][0] if len(cands) >= count else None


def video_request(q):
    """«открой на ютубе 1 видео в полноэкранном режиме» → {site, query, count, fullscreen} или None."""
    s = _norm(q)
    if not re.search(r"видео|ролик|клип", s):
        return None
    if not re.search(r"открой|открыть|включи|включить|запусти|запустить|найди", s):
        return None
    site = service_key(s)
    m = re.search(r"\b(\d+)\b", s)
    count = max(1, min(MAX_VIDEOS, int(m.group(1)))) if m else 1
    fullscreen = bool(re.search(r"полн\w*экран\w*|на весь экран|фулскрин|fullscreen", s))
    # тема: слова после «про», либо всё, что осталось от фразы без служебных слов
    topic = re.search(r"\bпро\s+(.+)$", s)
    if topic:
        query = topic.group(1)
    else:
        query = re.sub(r"\b(открой|открыть|включи|включить|запусти|запустить|найди|и|а|потом)\b", " ", s)
        query = re.sub(r"\b(видео|ролик|клип)\b", " ", query)
        query = re.sub(r"\b(на|в)\s+\S+", " ", query)          # «на ютубе», «в полном экране»
        query = re.sub(r"\b(полн\w*экран\w*|фулскрин|fullscreen|\d+)\b", " ", query)
    query = " ".join(query.split(" ,.:!-"))
    return {"site": site, "query": query[:80], "count": count, "fullscreen": fullscreen}


def commands(q):
    """Детерминированные видео-команды без модели: список вызовов для osagent или None.
    Разбираем: «отключи субтитры», «поставь лайк», «следующее видео», «открой 1 видео…» и т.п."""
    s = _norm(q)
    if not s:
        return None
    if re.search(r"субтитр", s):
        off = bool(re.search(r"отключ|выключ|убер|скро|выруб", s))
        return [("player", {"action": "subtitles_off" if off else "subtitles_on"})]
    if re.search(r"(поставь|нажми|кликни)\W*(дизлайк|не нравится)|\bдизлайк\b", s):
        return [("video_vote", {"action": "dislike"})]
    if re.search(r"(поставь|нажми|кликни|лайкни)\W*лайк|\bлайк\s*[!.]*$", s):
        return [("video_vote", {"action": "like"})]
    if re.search(r"подпишись|подписаться|подписаться на канал|оформи подписку", s):
        return [("video_subscribe", {})]
    if re.search(r"закрой видео|закрыть видео|закрой ролик|закрой вкладку", s):
        return [("video_close", {})]
    if re.search(r"следующ\w*\s+(видео|ролик|серия)", s):
        return [("player", {"action": "next"})]
    if re.search(r"предыдущ\w*\s+(видео|ролик|серия)", s):
        return [("player", {"action": "prev"})]
    if re.search(r"на пауз|поставь\w*\s+пауз|возобнови|продолжи смотреть|смотри дальше|стоп видео|останови видео", s):
        return [("player", {"action": "play_pause"})]
    if re.search(r"выключи звук|без звука|звук выключ|беззвучно", s):
        return [("player", {"action": "mute"})]
    if re.search(r"включи звук|звук включ|со звуком", s):
        return [("player", {"action": "mute"})]      # m — переключатель звука
    req = video_request(q)
    if req:
        return [("video_open", {"site": req["site"], "query": req["query"],
                                "count": req["count"], "fullscreen": req["fullscreen"]})]
    return None
