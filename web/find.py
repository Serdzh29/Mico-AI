"""Поиск в интернете и открытие результата: «загугли сайт …», «открой ютуб и включи 1 видео».

Как работает:
- фраза разбирается в request(): поиск Google или видео YouTube;
- результаты берутся из страниц DuckDuckGo (сайты) и YouTube (видео) — это единственный запрос в сеть;
- страница поиска открывается в браузере, через CLICK агента нажимается первый результат;
  если нажать не вышло — ссылка открывается напрямую.

Чистая логика (разбор фразы и страниц) не зависит от ОС и тестируется на Linux. Сеть, браузер и клик
передаются снаружи (run), поэтому тесты обходятся без интернета и Windows."""
import html, json, re, threading, time, urllib.parse, webbrowser

# requests грузим по требованию — запуск Mico не ждёт сетевой библиотеки

TIMEOUT = 8               # секунд на страницу результатов
CLICK_WAIT = 3.0          # сколько ждём загрузки страницы поиска, прежде чем нажимать
MAX_VIDEOS = 3            # больше трёх вкладок с видео не открываем
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# «загугли сайт правительства воронежской области и открой первый сайт», «погугли погоду»
_GOOGLE = re.compile(
    r"^(?:загугли|погугли|гугли|найди в гугле|найди в google|поищи в гугле)\s+(?P<q>.+?)"
    r"(?:\s+и\s+(?P<open>открой|открыть|перейди|зайди)\s+первый(?:\s+(?:сайт|результат|ссылку|страницу))?)?\W*$")
# «открой ютуб и включи 1 видео», «включи 2 видео про котов на ютубе», «найди видео про котов»
_YOUTUBE = re.compile(
    r"^(?:(?P<open>открой|открыть|зайди на|запусти)\s+(?:ютуб|youtube)\s+(?:и\s+)?)?"
    r"(?:включи|найди|поставь|покажи|запусти|посмотреть|смотреть)\s+"
    r"(?:(?P<n>\d{1,2})\s+)?видео(?:\s+на\s+(?:ютуб\w*|youtube))?\s*(?:про\s+|с\s+|о\s+)?"
    r"(?P<q>.*?)(?:\s+на\s+(?:ютуб\w*|youtube))?\W*$")
_DDG_LINK = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S)
_DDG_HREF = re.compile(r'href="([^"]+)"')
_VIDEO_ID = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')
_VIDEO_TITLE = re.compile(r'"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"')


def request(text):
    """Фраза пользователя → {'kind': 'google'|'youtube', ...} или None, если это не просьба поискать."""
    s = " ".join(str(text or "").lower().replace("ё", "е").split()).strip(" .!")
    m = _GOOGLE.match(s)
    if m:
        q = re.sub(r"^сайт\s+", "", m.group("q")).strip()
        if not q:
            return None
        return {"kind": "google", "query": q, "open_first": bool(m.group("open"))}
    m = _YOUTUBE.match(s)
    if m and (m.group("open") or re.search(r"ютуб|youtube", s)):   # «видео» без «ютуба» не трогаем
        n = int(m.group("n") or 1)
        return {"kind": "youtube", "query": m.group("q").strip(), "count": max(1, min(n, MAX_VIDEOS))}
    return None


def ack(spec):
    """Короткий ответ сразу, пока поиск идёт в фоне."""
    if spec["kind"] == "google":
        return f"Ищу «{spec['query']}» 🔎" + (", открою первый результат" if spec["open_first"] else "")
    if not spec["query"]:
        return "Включаю первое видео с главной страницы YouTube 🎬"
    return f"Ищу видео «{spec['query']}» на YouTube 🎬"


def ddg_url(q):
    return "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})


def google_url(q):
    return "https://www.google.com/search?" + urllib.parse.urlencode({"q": q})


def youtube_search_url(q):
    return "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": q})


def watch_url(video_id):
    return "https://www.youtube.com/watch?v=" + video_id


def _ddg_target(href):
    """DuckDuckGo отдаёт ссылку через свой переход /l/?uddg=адрес — достаём настоящий адрес."""
    if href.startswith("//"):
        href = "https:" + href
    parts = urllib.parse.urlsplit(href)
    if "duckduckgo.com" in parts.netloc and parts.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parts.query).get("uddg")
        return target[0] if target else ""
    return href


def parse_ddg(page, limit=5):
    """Страница DuckDuckGo (HTML) → [(заголовок, адрес)] в порядке выдачи. Реклама и служебные ссылки пропускаем."""
    out = []
    for attrs, inner in _DDG_LINK.findall(page or ""):
        if 'class="result__a"' not in attrs:
            continue
        m = _DDG_HREF.search(attrs)
        if not m:
            continue
        url = _ddg_target(html.unescape(m.group(1)))
        title = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        if title and url.startswith(("http://", "https://")) and "duckduckgo.com" not in url:
            out.append((title, url))
            if len(out) >= limit:
                break
    return out


def _unescape_json(raw):
    try:
        return json.loads('"' + raw + '"')
    except ValueError:
        return raw


def parse_youtube(page, limit=5):
    """Страница YouTube → [(id видео, название)] по порядку. Название ищем сразу за id, в той же карточке."""
    out, seen = [], set()
    text = page or ""
    for m in _VIDEO_ID.finditer(text):
        vid = m.group(1)
        if vid in seen:
            continue
        seen.add(vid)
        t = _VIDEO_TITLE.search(text, m.end(), m.end() + 4000)
        out.append((vid, _unescape_json(t.group(1)) if t else ""))
        if len(out) >= limit:
            break
    return out


def _fetch(url):
    """Страница как текст. Ошибка сети или не 200 — пусто, а не исключение."""
    try:
        import requests
        # CONSENT: для адресов из Европы YouTube без этого cookie отдаёт страницу согласия, а не выдачу
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"},
                         cookies={"CONSENT": "YES+1"}, timeout=TIMEOUT)
        return r.text if r.status_code == 200 else ""
    except requests.RequestException:
        return ""


def run(spec, click, fetch=_fetch, opener=webbrowser.open, sleep=time.sleep):
    """Выполняет поиск. click(название) -> bool нажимает ссылку в браузере. Возвращает текст для пользователя.
    fetch, opener, sleep подменяются в тестах."""
    if spec["kind"] == "google":
        return _run_google(spec, click, fetch, opener, sleep)
    return _run_youtube(spec, click, fetch, opener, sleep)


def _run_google(spec, click, fetch, opener, sleep):
    q = spec["query"]
    if not spec["open_first"]:
        opener(google_url(q))
        return f"Открыл поиск Google по запросу «{q}» 🔎"
    results = parse_ddg(fetch(ddg_url(q)))
    opener(google_url(q))
    if not results:
        return f"Первый результат не нашёл, открыл поиск Google по запросу «{q}» 🔎"
    title, url = results[0]
    sleep(CLICK_WAIT)
    if click(title[:30]):
        return f"Открыл первый результат: {title[:80]} 🔗"
    opener(url)
    return f"Не смог нажать ссылку в браузере, открыл её напрямую: {title[:80]} 🔗"


def _run_youtube(spec, click, fetch, opener, sleep):
    q, count = spec["query"], spec["count"]
    if not q:                                             # «включи 1 видео» без темы — первое с главной
        videos = parse_youtube(fetch("https://www.youtube.com/"), limit=1)
        if not videos:
            opener("https://www.youtube.com/")
            return "Не нашёл видео на главной, открыл YouTube 🎬"
        opener(watch_url(videos[0][0]))
        return "Включаю первое видео с главной страницы YouTube 🎬"
    videos = parse_youtube(fetch(youtube_search_url(q)), limit=count)
    if not videos:
        opener(youtube_search_url(q))
        return f"Не нашёл видео по запросу «{q}», открыл поиск YouTube 🎬"
    if count > 1 or not videos[0][1]:                     # несколько видео — открываем ссылками, без клика
        for vid, _ in videos:
            opener(watch_url(vid))
        return f"Открыл видео по запросу «{q}»: {len(videos)} шт. 🎬"
    vid, title = videos[0]
    opener(youtube_search_url(q))
    sleep(CLICK_WAIT)
    if click(title[:40]):
        return f"Включаю: {title[:80]} 🎬"
    opener(watch_url(vid))
    return f"Не смог нажать видео, открыл его напрямую: {title[:80]} 🎬"


def browser_click(name):
    """Нажать элемент с таким названием в активном окне браузера (Windows, через агента). False — не вышло."""
    try:
        from win import agent
        from win import agentwin as agent_win
        ok, _ = agent_win.WinDriver().do(agent.CLICK, {"name": name})
        return bool(ok)
    except Exception:
        return False


def start(spec, click, notify):
    """Запускает run() в фоновом потоке и отдаёт результат через notify(текст). Ошибка не роняет Mico."""
    def work():
        try:
            text = run(spec, click)
        except Exception as e:
            text = f"Поиск не получился: {e}"
        notify(text)
    threading.Thread(target=work, daemon=True).start()
