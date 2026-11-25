"""Поиск в интернете с коротким ответом: разбор фраз, выдача, тексты страниц, запрос к модели. Без сети."""
import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
from web import search as WS

PAGE = '''
<div class="result results_links results_links_deep web-result ">
<h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.gov36.ru%2Fpage&amp;rut=x">Правительство <b>Воронежской</b> области</a></h2>
<a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.gov36.ru%2Fpage">Официальный сайт <b>правительства</b> &amp; администрации.</a>
</div>
<div class="result results_links results_links_deep web-result ">
<h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fx">Второй сайт</a></h2>
</div>
'''
ARTICLE = ("<html><head><title>Губернатор</title><style>p{}</style></head><body><script>var x=1;</script>"
           "<h1>Губернатор области</h1><p>" + "Текст статьи о губернаторе и власти. " * 20 + "</p></body></html>")


def test_request_recognises_internet_queries():
    assert WS.request("найди в интернете рецепт борща") == {
        "query": "рецепт борща", "question": "найди в интернете рецепт борща"}
    assert WS.request("расскажи в интернете, что такое квант")["query"] == "что такое квант"
    assert WS.request("какие сейчас новости?")["query"] == "новости сегодня"


def test_request_leaves_browser_and_plain_chat_alone():
    assert WS.request("загугли сайт правительства") is None      # webfind открывает браузер
    assert WS.request("погугли в яндексе погоду") is None
    assert WS.request("что такое квант") is None                 # без слов про интернет — обычный чат
    assert WS.request("в интернете") is None


def test_parse_results_title_url_host_snippet():
    res = WS.parse_results(PAGE)
    assert res[0]["title"] == "Правительство Воронежской области"
    assert res[0]["url"] == "https://www.gov36.ru/page" and res[0]["host"] == "gov36.ru"
    assert res[0]["snippet"] == "Официальный сайт правительства & администрации."
    assert res[1]["snippet"] == ""


def test_search_none_on_network_failure_empty_when_nothing_found():
    assert WS.search("x", fetch=lambda url: "") is None
    assert WS.search("x", fetch=lambda url: "<html></html>") == []
    assert len(WS.search("x", fetch=lambda url: PAGE)) == 2


def test_page_text_drops_scripts_styles_and_tags():
    text = WS.page_text(ARTICLE)
    assert "Губернатор области" in text and "var x" not in text and "p{}" not in text and "<" not in text
    assert len(WS.page_text(ARTICLE, limit=50)) <= 50


def test_excerpts_skip_unavailable_and_thin_pages():
    res = WS.parse_results(PAGE)
    pages = {"https://www.gov36.ru/page": ARTICLE}
    got = WS.excerpts(res, fetch=lambda url: pages.get(url, ""))
    assert [i for i, _ in got] == [1]                           # второй адрес недоступен — пропущен


def test_answer_prompt_asks_for_short_sourced_answer():
    res = WS.parse_results(PAGE)
    prompt = WS.answer_prompt("кто губернатор?", res, [(1, "Губернатор — Александр Гусев.")])
    assert "2–4 коротких предложения" in prompt and "[1] Правительство" in prompt
    assert "Текст страницы: Губернатор — Александр Гусев." in prompt and "[2] Второй сайт" in prompt
    assert "Вопрос: кто губернатор?" in prompt and "не придумывай" in prompt


def test_fallback_and_sources():
    res = WS.parse_results(PAGE)
    assert WS.fallback_text(res).endswith("[1]") and "Официальный сайт" in WS.fallback_text(res)
    assert WS.fallback_text([]) == ""
    assert WS.sources_text(res).startswith("Источники:\n[1] https://www.gov36.ru/page")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("test_websearch: все проверки прошли")
