"""Проверка версии по сайту: номер читается из JSON и страницы, при сбое чат не блокируется, новее — блокируется."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from setup import sitecheck as S


def test_parse_json_and_html():
    assert S.parse_build('{"version": 2512}') == 2512
    assert S.parse_build('{"latest": "v2513"}') == 2513
    assert S.parse_build('2512') == 2512
    assert S.parse_build('<html><body><h1>Mico AI</h1><p>Последняя версия: 2512</p><footer>2026</footer></body></html>') == 2512
    assert S.parse_build('<meta name="version" content="2514"><title>x</title>') == 2514
    assert S.parse_build('<p>Version 2512 released 22.11.2026</p>') == 2512


def test_parse_ambiguous_is_none():
    assert S.parse_build('') is None
    assert S.parse_build('<p>© 2026 Mico</p>') is None                  # год — не версия
    assert S.parse_build('<p>2512 и 2600</p>') is None                  # два кандидата без подписи: не гадаем


def test_check_blocks_only_when_site_is_newer():
    assert S.check(local=2512, fetch=lambda: 2512) is None            # та же версия — пускаем
    assert S.check(local=2512, fetch=lambda: None) is None            # сайт не ответил — пускаем
    assert S.check(local=2513, fetch=lambda: 2512) is None            # сборка новее сайта — пускаем
    info = S.check(local=2512, fetch=lambda: 2513)
    assert info and info["latest"] == 2513 and info["url"].startswith("https://serdzh29.github.io/Mico-AI")


if __name__ == "__main__":
    test_parse_json_and_html(); test_parse_ambiguous_is_none(); test_check_blocks_only_when_site_is_newer()
    print("ok")
