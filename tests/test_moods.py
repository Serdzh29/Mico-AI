"""Каждая эмоция, которую можно выбрать (теги модели и текст), должна быть нарисована в blob.py."""
import os as _os, sys as _sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, ROOT)
import emotions as E


def test_every_valid_mood_is_drawn():
    src = open(_os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    missing = [m for m in sorted(E.VALID) if f'"{m}"' not in src]
    assert not missing, missing


def test_prompt_tags_are_valid_moods():
    tags = ["happy", "love", "sad", "surprised", "laugh", "curious", "worried", "scared", "angry",
            "shy", "confused", "excited", "idle"]
    assert all(t in E.VALID for t in tags)


def test_text_detection_covers_new_moods():
    cases = {"боюсь, что опоздаю": "scared", "я злюсь на это": "angry", "я смутился": "shy",
             "не понимаю, что делать": "confused", "ура, получилось": "excited"}
    for text, mood in cases.items():
        assert E.detect_emotion(text) == mood, (text, E.detect_emotion(text))


def test_praise_makes_mico_proud():
    for text in ["ты молодец!", "ты умница", "горжусь тобой", "отличная работа, Мико", "ты супер"]:
        assert E.detect_emotion(text) == "proud", (text, E.detect_emotion(text))
    assert E.detect_emotion("спасибо большое") == "happy"
    assert E.split_mood("[proud] Спасибо, стараюсь!") == ("proud", "Спасибо, стараюсь!")


def test_blob_uses_the_same_moods_as_emotions():
    src = open(_os.path.join(ROOT, "blob.py"), encoding="utf-8").read()
    assert "from emotions import VALID as MOODS" in src
    for m in ["shy", "scared", "angry", "confused", "excited", "proud"]:
        assert m in E.VALID


def test_heart_is_symmetric_and_soft():
    import shapes
    pts = shapes.HEART
    n = len(pts)
    for i in range(n):
        x, y = pts[i]
        xm, ym = pts[(n // 2 - i) % n]
        assert abs(x + xm) < 1e-6 and abs(y - ym) < 1e-6, i   # зеркально по вертикали
    # кончик мягче, чем у исходной формулы: радиус у низа не уходит в острие
    raw_tip = min(p[1] for p in shapes.heart_points(n, 0.01))
    soft_tip = min(p[1] for p in pts)
    assert soft_tip > raw_tip


if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
