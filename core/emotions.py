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
    ("sad", ["грустно", "печально", "одиноко", "тоска", "обидно", "😢", "😭", "депресс"]),   # «плохо», «устал» — слишком общие
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


# для ответов без явной эмоции: по смыслу, а не «радость по умолчанию»
_OK_WORDS = ("👌", "👍", "✓", "готов", "записал", "запланир", "открыл", "сделано", "вернул",
             "удалил", "очистил", "запомнил", "поставил", "включил", "выключил", "сохранил")
_BAD_WORDS = ("не получилось", "не могу", "не найд", "не удалось", "не работает", "нет доступа",
              "ошибка", "не смог")


def for_reply(text):
    """Эмоция ответа без метки: ошибка — тревога, подтверждение — радость, вопрос — любопытство, иначе — спокойствие."""
    low = (text or "").lower()
    m = detect_emotion(text)
    if m:
        return m
    if any(w in low for w in _BAD_WORDS):
        return "worried"
    if any(w in low for w in _OK_WORDS):
        return "happy"
    return "idle"


def split_mood(answer):
    """'[happy] Привет!' -> ('happy', 'Привет!')"""
    m = re.match(r"\s*\[(\w+)\]\s*", answer)
    if not m:
        return None, answer
    tag = m.group(1).lower()
    mood = ALIASES.get(tag, tag)
    return (mood if mood in VALID else None), answer[m.end():]
