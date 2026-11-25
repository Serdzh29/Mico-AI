"""Поиск в интернете: разбор фраз, разбор страниц DuckDuckGo и YouTube, порядок действий. Без сети и Windows."""
import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from web import find as W

DDG_PAGE = '''
<div class="result results_links"><div class="result__body">
<h2 class="result__title"><a rel="nofollow" class="result__a" href="https://duckduckgo.com/y.js?ad=1">Реклама <b>сайт</b></a></h2></div></div>
<div class="result"><h2 class="result__title">
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.govvrn.ru%2F&amp;rut=abc">Правительство <b>Воронежской</b> области</a>
</h2></div>
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fx">Второй</a>
'''

YT_PAGE = ('{"videoRenderer":{"videoId":"AAAAAAAAAAA","thumbnail":{},"title":{"runs":[{"text":"Коты \\u0026 собаки"}]}},'
           '"videoRenderer":{"videoId":"BBBBBBBBBBB","title":{"runs":[{"text":"Второе видео"}]}},'
           '"videoRenderer":{"videoId":"AAAAAAAAAAA"}}')


def test_request_google_with_open_first():
    s = W.request("загугли сайт правительства воронежской области и открой первый сайт")
    assert s == {"kind": "google", "query": "правительства воронежской области", "open_first": True}


def test_request_google_without_open():
    assert W.request("Погугли погоду!") == {"kind": "google", "query": "погоду", "open_first": False}


def test_request_youtube_no_topic_and_topic():
    assert W.request("открой ютуб и включи 1 видео") == {"kind": "youtube", "query": "", "count": 1}
    assert W.request("включи 2 видео про котов на ютубе") == {"kind": "youtube", "query": "котов", "count": 2}
    assert W.request("найди видео про котов на youtube")["query"] == "котов"


def test_request_ignores_other_phrases():
    assert W.request("открой ютуб") is None                 # просто открыть сайт — прежнее поведение
    assert W.request("включи видео про котов") is None      # не сказано «ютуб»
    assert W.request("открой блокнот и напиши привет") is None
    assert W.request("загугли") is None


def test_parse_ddg_skips_ads_and_unwraps_redirect():
    res = W.parse_ddg(DDG_PAGE)
    assert res[0] == ("Правительство Воронежской области", "https://www.govvrn.ru/")
    assert res[1] == ("Второй", "https://example.org/x")
    assert all("duckduckgo" not in url for _, url in res)


def test_parse_youtube_first_videos_with_titles_and_no_duplicates():
    vids = W.parse_youtube(YT_PAGE)
    assert vids == [("AAAAAAAAAAA", "Коты & собаки"), ("BBBBBBBBBBB", "Второе видео")]


def _fake(pages):
    return lambda url: pages.get(url, "")


def test_google_open_first_clicks_title_and_does_not_open_direct():
    opened, clicked = [], []
    text = W.run({"kind": "google", "query": "правительство", "open_first": True},
                 click=lambda name: clicked.append(name) or True,
                 fetch=_fake({W.ddg_url("правительство"): DDG_PAGE}),
                 opener=opened.append, sleep=lambda s: None)
    assert opened == [W.google_url("правительство")]
    assert clicked == ["Правительство Воронежской области"[:30]]
    assert "Открыл первый результат" in text


def test_google_click_failure_opens_link_directly():
    opened = []
    W.run({"kind": "google", "query": "правительство", "open_first": True},
          click=lambda name: False, fetch=_fake({W.ddg_url("правительство"): DDG_PAGE}),
          opener=opened.append, sleep=lambda s: None)
    assert opened[-1] == "https://www.govvrn.ru/"


def test_google_without_results_opens_search_page():
    opened = []
    text = W.run({"kind": "google", "query": "ничего", "open_first": True},
                 click=lambda name: True, fetch=_fake({}), opener=opened.append, sleep=lambda s: None)
    assert opened == [W.google_url("ничего")] and "Первый результат не нашёл" in text


def test_youtube_single_video_clicks_then_falls_back():
    opened, clicked = [], []
    url = W.youtube_search_url("коты")
    W.run({"kind": "youtube", "query": "коты", "count": 1}, click=lambda n: clicked.append(n) or False,
          fetch=_fake({url: YT_PAGE}), opener=opened.append, sleep=lambda s: None)
    assert clicked == ["Коты & собаки"]
    assert opened[-1] == W.watch_url("AAAAAAAAAAA")


def test_youtube_two_videos_open_links_without_click():
    opened, clicked = [], []
    url = W.youtube_search_url("коты")
    W.run({"kind": "youtube", "query": "коты", "count": 2}, click=lambda n: clicked.append(n) or True,
          fetch=_fake({url: YT_PAGE}), opener=opened.append, sleep=lambda s: None)
    assert clicked == []
    assert opened == [W.watch_url("AAAAAAAAAAA"), W.watch_url("BBBBBBBBBBB")]


def test_youtube_without_topic_uses_home_page():
    opened = []
    W.run({"kind": "youtube", "query": "", "count": 1}, click=lambda n: True,
          fetch=_fake({"https://www.youtube.com/": YT_PAGE}), opener=opened.append, sleep=lambda s: None)
    assert opened == [W.watch_url("AAAAAAAAAAA")]


def test_network_failure_is_quiet():
    opened = []
    text = W.run({"kind": "youtube", "query": "коты", "count": 1}, click=lambda n: True,
                 fetch=_fake({}), opener=opened.append, sleep=lambda s: None)
    assert opened == [W.youtube_search_url("коты")] and "Не нашёл видео" in text


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("test_webfind: все проверки прошли")
