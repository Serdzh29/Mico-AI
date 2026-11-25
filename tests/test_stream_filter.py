"""Живой (потоковый) ответ: кусочки текста очищаются от рассуждений и меток настроения по мере генерации.
Проверяется поведение фильтра — что человек видит в чате, пока модель ещё пишет."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from llm.engine import ReplyFilter, clean_reply

TH_O = "<" + "think" + ">"
TH_C = "</" + "think" + ">"


def chunks(flt, parts):
    return "".join(flt.feed(p) for p in parts)


def test_plain_text_passes_through():
    f = ReplyFilter()
    assert chunks(f, ["При", "вет, дру", "г!"]) == "Привет, друг!"


def test_mood_tag_is_stripped_even_split_across_chunks():
    f = ReplyFilter()
    assert chunks(f, ["[hap", "py] Я рад тебя видеть!"]) == "Я рад тебя видеть!"


def test_literal_brackets_are_not_eaten():
    f = ReplyFilter()
    assert chunks(f, ["[12] хай"]) == "[12] хай"


def test_thinking_blocks_are_hidden():
    f = ReplyFilter()
    out = chunks(f, [TH_O, "хм, думаю", TH_C, "Отв", "ечаю!"])
    assert out == "Отвечаю!"


def test_opened_but_unclosed_thinking_hides_everything():
    f = ReplyFilter()
    assert chunks(f, [TH_O, "думаю очень долго"]) == ""


def test_pre_closing_tag_is_skipped():
    f = ReplyFilter()
    assert chunks(f, [TH_C, "Готово!"]) == "Готово!"


def test_english_reasoning_hides_until_mood_answer():
    f = ReplyFilter()
    out = chunks(f, ["Thinking Process:\n", "the user asked...\n", "[proud] Готово, включил!"])
    assert out == "Готово, включил!"


def test_final_answer_matches_clean_reply():
    # предпросмотр и финал согласованы: человек не видит «хвостов» после завершения
    raw = [TH_O, "размышляю", TH_C, "[happy] Всё получилось"]
    f = ReplyFilter()
    shown = chunks(f, raw)
    assert shown == "Всё получилось"
    assert clean_reply("".join(raw)).endswith("Всё получилось")


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK stream filter")
