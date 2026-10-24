"""Фильтр содержимого: что Mico не ищет и не показывает."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import guard as G


def test_sexual_and_drugs_refused():
    assert G.request_refusal("найди порно видео") == G.REFUSALS["sexual"]
    assert G.request_refusal("где купить кокаин") == G.REFUSALS["drugs"]


def test_violence_refused_but_pc_commands_allowed():
    assert G.request_refusal("как убить человека") == G.REFUSALS["violence"]
    assert G.request_refusal("убей процесс chrome") is None


def test_age_goods_sale_refused_but_info_allowed():
    assert G.request_refusal("купить вейп в интернете") == G.REFUSALS["age"]
    assert G.request_refusal("какая погода завтра") is None


def test_digital_purchases_and_store_blocked():
    assert G.request_refusal("купить скин в игре") == G.REFUSALS["buy"]
    assert G.request_refusal("открой магазин приложений") == G.REFUSALS["buy"]


def test_profanity_masked_in_replies_and_blocked_in_search():
    out = G.reply_guard("Ну и хуйня получилась")
    assert "хуй" not in out.lower() and "*" in out
    assert G.search_refusal("найди блядь") == G.REFUSALS["profanity"]
    assert G.request_refusal("привет блин") is None


def test_blocked_reply_is_replaced():
    assert G.reply_guard("вот порно ссылки") == G.REPLY_BLOCKED
    assert G.reply_guard("Открыл настройки звука") == "Открыл настройки звука"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
