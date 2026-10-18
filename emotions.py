"""Определение эмоций по тексту (без зависимостей)."""
import re

# порядок важен: более точные эмоции проверяются раньше общих
LEX = [
    ("love", ["люблю", "обожаю", "❤", "💛", "💕", "ты лучший", "ты милый", "милашка", "красавчик", "нравишься"]),
    ("proud", ["молодец", "умница", "умничк", "ты крут", "ты классн", "ты умный", "горжусь",
              "отличная работа", "хорошая работа", "здорово справ", "классно справ", "ты супер"]),
    ("laugh", ["ахах", "хаха", "лол", "ржу", "смешно", "😂", "🤣"]),
    ("scared", ["боюсь", "страшно", "испуг", "жутко", "ужас", "😱", "😨"]),
    ("angry", ["злюсь", "бесит", "раздраж", "возмут", "😠", "😡"]),
    ("shy", ["смущ", "смутил", "стесня", "неловко", "краснею", "🙈", "😳"]),
    ("confused", ["не понимаю", "запутал", "непонятно", "странно", "🤔", "😕"]),
    ("excited", ["ура", "восторг", "потрясающ", "ух ты", "🎉", "🤩"]),
    ("sad", ["грустно", "печально", "плохо", "устал", "одиноко", "тоска", "обидно", "😢", "😭", "депресс"]),
    ("worried", ["проблем", "ошибк", "не работает", "тревож", "срочно"]),
    ("surprised", ["вау", "ого", "офигеть", "неужели", "серьёзно", "серьезно", "шок", "😮", "😲"]),
    ("playful", ["хитр", "подмигива", "шалю", "озорн", "шучу", "😉", "😜", ";)"]),
    ("happy", ["спасибо", "круто", "супер", "отлично", "класс", "здорово", "привет",
               "здравствуй", "добрый", "хорошо", "👍", "😊", "😀", "😄"]),
]
VALID = {"idle", "happy", "love", "sad", "surprised", "laugh", "curious", "worried", "thinking", "sleepy",
         "scared", "angry", "shy", "confused", "excited", "proud", "playful"}
# синонимы, которые может написать модель
ALIASES = {"neutral": "idle", "joy": "happy", "fear": "scared", "anger": "angry", "sadness": "sad",
           "surprise": "surprised", "embarrassed": "shy", "bashful": "shy", "puzzled": "confused",
           "delighted": "excited", "pride": "proud", "gratified": "proud", "tired": "sleepy", "mischievous": "playful",
           "wink": "playful", "joking": "playful", "frustrated": "angry", "annoyed": "angry", "afraid": "scared",
           "amazed": "surprised", "grateful": "love", "thankful": "happy", "bored": "idle", "calm": "idle"}


def detect_emotion(text):
    low = text.lower()
    for mood, words in LEX:
        if any(w in low for w in words):
            return mood
    return "curious" if "?" in low else None


def split_mood(answer):
    """'[happy] Привет!' -> ('happy', 'Привет!')"""
    m = re.match(r"\s*\[(\w+)\]\s*", answer)
    if not m:
        return None, answer
    tag = m.group(1).lower()
    mood = ALIASES.get(tag, tag)
    return (mood if mood in VALID else None), answer[m.end():]
