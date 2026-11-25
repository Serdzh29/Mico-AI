from ui import theme
from ui import winter as winter_ui
"""Первый запуск Mico AI — живое знакомство-практика на весь экран.

Экран мягко затемняется, за Mico переливается сияние в его цветах, а сам Mico летает по экрану и ведёт человека
по шести сценам: привет (нажми на меня), выбор цвета, практика команд, режим агента с вопросом «да/нет»,
голос и «всё готово». Практика — тренировка: команды показываются анимацией и ничего в Windows не меняют
(всё, что меняет систему, делается только в настоящем чате). Показывается один раз; «Пропустить» и Esc — в любой момент."""
import math, random, threading, time

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, QEasingCurve, QPropertyAnimation, QVariantAnimation
from PyQt6.QtGui import (QFontMetricsF, QBrush, QColor, QCursor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath,
                         QPen, QPixmap, QPolygonF, QRadialGradient)
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton

import i18n

i18n.EN.update({
    "Это Mico Cloud: несколько ИИ-моделей в одном облаке. Спроси что угодно, и я передам вопрос самой подходящей. Попробуй сам!": "This is Mico Cloud: several AI models in one cloud. Ask anything and I'll pass your question to the best one. Try it yourself!",
    "Задай свой вопрос облаку Mico и нажми Enter": "Ask Mico Cloud your own question and press Enter",
    "НОВЫЙ ШАГ В БУДУЩЕЕ": "A NEW STEP INTO THE FUTURE",
    "16 лучших моделей в трёх уровнях: Mico сам выбирает, кому отдать твой вопрос. Ключи не нужны.": "16 top models in three tiers: Mico picks who gets your question. No keys needed.",
    "простые и быстрые": "simple and fast", "сильные модели": "strong models", "самые мощные": "the most powerful", "сам выбирает уровень": "picks the tier itself", "Авто": "Auto",
    "Докажи √2": "Prove √2", "Считаю остаток нейронов…": "Counting the neurons left…",
    "Выбери вопрос ниже или напиши свой. Ответ придёт от настоящих моделей, не заготовкой.": "Pick a question below or write your own. The answer comes from real models, not a template.",
    "Выбираю модель…": "Choosing a model…", "с": "s", "Ответила модель": "Answered by",
    "Попробуй другой вопрос: например, про код или стихи.": "Try another question: about code or poems, for example.",
    "Сколько 17 × 23?": "What is 17 × 23?", "Как работает Wi-Fi?": "How does Wi-Fi work?", "Стих про осень": "A poem about autumn", "Код на Python": "Python code",
    "Как мне отвечать?": "How should I answer?", "На этом компьютере": "On this computer", "Облако Mico": "Mico Cloud",
    "Работает без интернета, данные остаются на ПК. Нагружает процессор.": "Works offline, data stays on your PC. Uses the processor.",
    "Быстро и умно, без нагрузки на процессор. Ключи не нужны. Текст чата уходит на сервер Mico AI.": "Fast and smart, no load on the processor. No keys needed. Chat text goes to the Mico AI server.",
    "Офлайн": "Offline", "Рекомендуем": "Recommended", "Авто": "Auto", "Быстро": "Fast", "Умнее": "Smarter",
    "Отвечаю через облако Mico: быстро и без нагрузки на твой компьютер.": "I answer through Mico Cloud: fast and without loading your computer.",
    "Локальная модель ещё не скачана, поэтому пока я отвечаю через облако Mico.": "The local model isn't downloaded yet, so I answer through Mico Cloud for now.",
    "Режим «Авто» сам берёт быструю модель для простого и умную для сложного. Сменить можно в чате.": "“Auto” picks a fast model for simple things and a smart one for hard ones. You can change it in the chat.",
    "Работает без интернета, все данные остаются на твоём ПК.": "Works offline, all data stays on your PC.",
    "Отвечает быстрее. Текст чата уходит провайдеру, нужен интернет.": "Answers faster. Chat text goes to the provider; internet needed.",
    "Приватно": "Private", "Быстрее": "Faster", "Режим агента": "Agent mode",
    "Как мне отвечать? Выбери — это можно поменять в чате в любой момент.": "How should I answer? Pick one — you can change it in the chat any time.",
    "Буду думать прямо на твоём ПК — всё останется у тебя.": "I'll think right on your PC — everything stays with you.",
    "Если передумаешь, переключиться на облако можно в чате в любой момент.": "If you change your mind, you can switch to the cloud in the chat any time.",
    "Встречайте — режим агента! Это совсем новая моя функция (пока в BETA): я сам открою программу, напишу сообщение или включу видео.":
        "Meet agent mode! It's a brand-new feature of mine: I can open an app, write a message or play a video myself.",
    "Включить агента": "Turn on the agent", "Пока не надо": "Not now", "РЕЖИМ АГЕНТА": "AGENT MODE",
    "Написать маме": "Message Mom", "Включить видео": "Play a video", "Заполнить форму": "Fill in a form", "Найти письмо": "Find an email",
    "агент, напиши мамуле привет": "agent, text Mom hi", "агент, включи видео про котиков": "agent, play a video about cats",
    "агент, заполни форму записи": "agent, fill in the booking form", "агент, найди в почте счёт": "agent, find the invoice in my mail",
    "Открываю Telegram": "Opening Telegram", "Нахожу чат «Мамуля»": "Finding the chat “Mom”", "Пишу «Привет!»": "Typing “Hi!”",
    "Открываю YouTube": "Opening YouTube", "Ищу «котики»": "Searching “cats”", "Включаю первое видео": "Playing the first video",
    "Открываю сайт": "Opening the site", "Подставляю имя и телефон": "Filling in name and phone", "Нахожу «Записаться»": "Finding “Book”",
    "Открываю почту": "Opening mail", "Ищу «счёт»": "Searching “invoice”", "Открываю письмо": "Opening the email",
    "Отправить сообщение?": "Send the message?", "Нажать «Записаться»?": "Press “Book”?",
    "Отправлено (понарошку)": "Sent (just pretending)", "Не отправлено — ты сказал «нет»": "Not sent — you said no",
    "Видео играет (понарошку)": "Video playing (just pretending)", "Заявка отправлена (понарошку)": "Request sent (just pretending)",
    "Не нажал — ты сказал «нет»": "Didn't press — you said no", "Письмо найдено (понарошку)": "Email found (just pretending)",
    "Привет!": "Hi!", "Заявка": "Request", "Готово": "Done",
    "Выбери пример внизу — я покажу, как работаю:": "Pick an example below — I'll show how I work:",
    "Смотри, как я это делаю": "Watch how I do it",
    "Встречайте — режим агента! Это абсолютно новая моя функция: я сам открою программу, напишу сообщение или включу видео.":
        "Meet agent mode! It's a brand-new feature of mine: I can open an app, write a message or play a video myself.",
    "Нажимай на примеры — это тренировка, ничего не отправится. А давай сразу включим агента?":
        "Tap the examples — it's practice, nothing gets sent. Shall we turn the agent on right away?",
    "Агент включён! Перед отправкой, оплатой и удалением я всегда спрошу твоё «да».":
        "Agent is on! Before sending, paying or deleting I'll always ask for your “yes”.",
    "Хорошо. Включить агента можно в любой момент: ⚙ Настройки → «Агент».":
        "Okay. You can turn the agent on any time: ⚙ Settings → “Agent”.",
    "Отправил (понарошку). В настоящем режиме я так же пишу в Telegram, WhatsApp и MAX.":
        "Sent (just pretending). For real I write in Telegram, WhatsApp and MAX the same way.",
    "Хорошо, не отправляю. Решаешь всегда ты: без твоего «да» я ничего не отправляю, не плачу и не удаляю.":
        "Okay, not sending. You always decide: without your “yes” I send nothing, pay for nothing and delete nothing.",
    "Готово! Так же я включаю ролики в Rutube и VK Видео.": "Done! I play videos on Rutube and VK Video the same way.",
    "Нажал (понарошку). Имя и телефон я подставляю только после твоего «да», пароли — никогда.":
        "Pressed (just pretending). I fill in name and phone only after your “yes”, and never passwords.",
    "Хорошо, форму не отправляю. Перед важным я всегда спрашиваю.": "Okay, not submitting the form. I always ask before anything important.",
    "Нашёл! Читаю и ищу сам, а платежи и пароли не трогаю.": "Found it! I read and search by myself, but never touch payments or passwords.",
})

COLORS = [("#FFCFA3", "Персиковый"), ("#FFB3C6", "Розовый"), ("#B8C0FF", "Лавандовый"),
          ("#9FD3FF", "Небесный"), ("#A8E6CF", "Мятный"), ("#F6D365", "Солнечный")]

# Старые списки оставлены для совместимости: их может показывать подсказка «что ты умеешь».
ABILITIES = [
    ("Разговор", "Спрашивай что угодно. Ответ — рядом со мной.", "chat"),
    ("Компьютер", "Открою программу, найду файл, включу тёмную тему — если попросишь.", "app"),
    ("Напоминания", "Напомню о делах, таймере и перерыве. Можно одной фразой.", "bell"),
]
TIPS = [
    ("Нажми на меня — откроется чат", "chat"),
    ("Шестерёнка в чате — все настройки", "gear"),
    ("Спроси «что ты умеешь?», чтобы увидеть всё, что я могу", "bolt"),
]

# Практика: (демонстрация, что на кнопке, что Mico говорит после). Только настоящие команды Mico.
PRACTICE = [
    ("volume", "громкость 30", "Готово: громкость 30%. Так же работают яркость, Wi-Fi и Bluetooth."),
    ("timer", "таймер на 5 секунд", "Время вышло! Напоминания ставятся так же: «напомни через час»."),
    ("dark", "включи тёмную тему", "Тёмная тема включена. Я знаю больше 130 переключателей Windows."),
    ("notepad", "открой блокнот", "Открыл блокнот. Любую программу или сайт открою одной фразой."),
]
DEMO_SEC = {"volume": 1.6, "timer": 5.4, "dark": 1.5, "notepad": 2.6}
# слова, по которым введённый самим человеком текст попадает в одну из тренировок
DEMO_WORDS = {"volume": ("громк", "звук", "volume", "тише", "погромче"), "timer": ("таймер", "засек", "timer"),
              "dark": ("тёмн", "темн", "dark", "тема"), "notepad": ("блокнот", "notepad", "открой", "open")}
S_HELLO, S_COLOR, S_AI, S_CLOUD, S_PRACTICE, S_AGENT, S_VOICE, S_WINTER, S_DONE = range(9)   # сцены знакомства по порядку
SCENES = 9
AGENT_STEPS = ["Открываю Telegram", "Нахожу чат «Мамуля»", "Пишу «Привет!»"]
# примеры, которые можно «потыкать» в знакомстве (тренировка: ничего не отправляется)
AGENT_EXAMPLES = [
    {"kind": "msg", "label": "Написать маме", "ask": "агент, напиши мамуле привет", "steps": ["Открываю Telegram", "Нахожу чат «Мамуля»", "Пишу «Привет!»"],
     "q": "Отправить сообщение?", "ok": "Отправлено (понарошку)", "no": "Не отправлено — ты сказал «нет»", "fly": "Привет!",
     "say_yes": "Отправил (понарошку). В настоящем режиме я так же пишу в Telegram, WhatsApp и MAX.",
     "say_no": "Хорошо, не отправляю. Решаешь всегда ты: без твоего «да» я ничего не отправляю, не плачу и не удаляю."},
    {"kind": "video", "label": "Включить видео", "ask": "агент, включи видео про котиков", "steps": ["Открываю YouTube", "Ищу «котики»", "Включаю первое видео"],
     "q": None, "ok": "Видео играет (понарошку)", "say_done": "Готово! Так же я включаю ролики в Rutube и VK Видео."},
    {"kind": "form", "label": "Заполнить форму", "ask": "агент, заполни форму записи", "steps": ["Открываю сайт", "Подставляю имя и телефон", "Нахожу «Записаться»"],
     "q": "Нажать «Записаться»?", "ok": "Заявка отправлена (понарошку)", "no": "Не нажал — ты сказал «нет»", "fly": "Заявка",
     "say_yes": "Нажал (понарошку). Имя и телефон я подставляю только после твоего «да», пароли — никогда.",
     "say_no": "Хорошо, форму не отправляю. Перед важным я всегда спрашиваю."},
    {"kind": "mail", "label": "Найти письмо", "ask": "агент, найди в почте счёт", "steps": ["Открываю почту", "Ищу «счёт»", "Открываю письмо"],
     "q": None, "ok": "Письмо найдено (понарошку)", "say_done": "Нашёл! Читаю и ищу сам, а платежи и пароли не трогаю."},
]
# что ещё умеет агент: вылетают из Mico и встают вокруг карточки, как умения на сайте
AGENT_SKILLS = ["Telegram", "WhatsApp", "MAX", "Видео", "Сайты и формы", "Файлы", "Почта", "Календарь"]


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def _io(x):
    x = _clamp(x)
    return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def _out(x):
    x = _clamp(x)
    return 1 - (1 - x) ** 3


def _back(x, c=1.70158):
    x = _clamp(x)
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _mixc(a, b, t):
    a, b, t = QColor(a), QColor(b), _clamp(t)
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))


RAINBOW = ["#FF5D8F", "#FFB84D", "#FFE14D", "#5DE08A", "#4DC3FF", "#8C7CFF", "#FF7CE0"]


class RoundButton(QPushButton):
    """Кнопка знакомства. Рисует себя сама, поэтому она всегда круглая (таблетка), а не прямоугольная: стили Qt
    скругление на этих кнопках не давали. Плавное наведение, лёгкая «вдавленность» при нажатии."""
    SIZES = {"primary": (46, 36, 15), "primarySm": (34, 22, 13), "ghost": (34, 18, 12), "chip": (38, 20, 13)}   # высота, поля, шрифт

    def __init__(self, text, name, parent=None):
        super().__init__(text, parent)
        self.setObjectName(name)
        self._hover = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.valueChanged.connect(self._set_hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)
        f = QFont(theme.FONT_FAMILY)
        f.setPixelSize(self.SIZES.get(name, (36, 18, 13))[2])
        if name in ("primary", "primarySm"):
            f.setWeight(QFont.Weight.DemiBold)
        self.setFont(f)

    def _set_hover(self, v):
        self._hover = float(v)
        self.update()

    def _fade_to(self, v):
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(v)
        self._anim.start()

    def enterEvent(self, e):
        self._fade_to(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._fade_to(0.0)
        super().leaveEvent(e)

    def sizeHint(self):
        h, pad, _px = self.SIZES.get(self.objectName(), (36, 18, 13))
        w = QFontMetrics(self.font()).horizontalAdvance(self.text()) + 2 * pad
        return QSize(max(w, 132 if self.objectName() == "primary" else 64), h)

    def paintEvent(self, e):
        d = self.window()
        accent = QColor(getattr(d, "color", "#FFCFA3"))
        pal = getattr(d, "pal", None) or {"card": "#2b2b2b", "stroke": "#3a3a3a", "text": "#ffffff", "muted": "#a6a6a6"}
        name, hv, en = self.objectName(), self._hover, self.isEnabled()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if self.isDown():                                     # нажатая кнопка чуть уменьшается
            c = r.center()
            p.translate(c)
            p.scale(.97, .97)
            p.translate(-c)
        if name == "swatch":
            col = QColor(str(self.property("hex") or accent.name()))
            sel = str(self.property("hex") or "").lower() == accent.name().lower()
            p.setPen(QPen(QColor(255, 255, 255, 255 if (sel or hv > .4) else 100), 3 if (sel or hv > .4) else 2))
            p.setBrush(col)
            p.drawEllipse(r.adjusted(2, 2, -2, -2))
            p.end()
            return
        if name == "mic":
            p.setPen(Qt.PenStyle.NoPen)
            glow = QColor(accent)
            glow.setAlpha(int(50 + 60 * hv))
            p.setBrush(glow)
            p.drawEllipse(r.adjusted(-2, 1, 2, 5))
            p.setBrush(_mixc(accent, "#ffffff", .18 * hv))
            p.drawEllipse(r)
            ic = self.iconSize()
            box = QRect(0, 0, ic.width(), ic.height())
            box.moveCenter(self.rect().center())
            self.icon().paint(p, box)
            p.end()
            return
        rad = r.height() / 2
        if name in ("primary", "primarySm"):
            base = accent if en else _mixc(accent, pal["card"], .65)
            if en:
                sh = QColor(accent)
                sh.setAlpha(int(55 + 55 * hv))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(sh)
                p.drawRoundedRect(r.translated(0, 3).adjusted(3, 2, -3, -2), rad, rad)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(_mixc(base, "#ffffff", .16 * hv))
            p.drawRoundedRect(r, rad, rad)
            tc = QColor(theme.on_accent(accent.name())) if en else QColor(pal["muted"])
        elif name == "ghost":
            p.setPen(QPen(QColor(255, 255, 255, int(56 + 60 * hv)), 1.2))
            p.setBrush(QColor(255, 255, 255, int(26 + 34 * hv)))
            p.drawRoundedRect(r, rad, rad)
            tc = QColor("#ffffff")
        else:                                                 # chip
            done = bool(self.property("done"))
            edge = accent if (hv > .3 or done) and en else QColor(pal["stroke"])
            p.setPen(QPen(edge, 1.6 if (hv > .3 or done) else 1.1))
            p.setBrush(_mixc(pal["card"], accent.name(), .10 * hv))
            p.drawRoundedRect(r, rad, rad)
            tc = QColor(pal["text"] if en else pal["muted"])
        p.setPen(tc)
        p.setFont(self.font())
        p.drawText(r, int(Qt.AlignmentFlag.AlignCenter.value), self.text())
        p.end()


class RoundLineEdit(QLineEdit):
    """Поле ввода команды в форме таблетки: рамку рисуем сами, а сам текст — обычный QLineEdit без фона."""

    def paintEvent(self, e):
        d = self.window()
        pal = getattr(d, "pal", None) or {"card": "#2b2b2b", "stroke": "#3a3a3a"}
        accent = QColor(getattr(d, "color", "#FFCFA3"))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        focus = self.hasFocus()
        p.setPen(QPen(accent if focus else QColor(pal["stroke"]), 1.8 if focus else 1.2))
        p.setBrush(QColor(pal["card"]))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.end()
        super().paintEvent(e)


CLOUD_CARD = (590, 372)                                  # размер карточки Mico Cloud в знакомстве
# Модели Mico Cloud: имя, чем занимается, цвет. Имена совпадают с теми, что присылает шлюз.
CLOUD_MODELS = (("Lite", "простые и быстрые", "#7AD7FF"), ("Plus", "сильные модели", "#B9A2FF"),
                ("Max", "самые мощные", "#FFB3D9"), ("Авто", "сам выбирает уровень", "#8FF0B0"))
# Вопросы для пробы: каждый попадает к своей модели. (подпись на кнопке, сам вопрос)
CLOUD_QUESTIONS = (("Сколько 17 × 23?", "Сколько будет 17 умножить на 23? Ответь коротко."),
                   ("Докажи √2", "Докажи строго, что корень из двух иррационален."),
                   ("Как работает Wi-Fi?", "Объясни простыми словами, как работает Wi-Fi."),
                   ("Стих про осень", "Напиши короткий стих про осень на четыре строки."),
                   ("Код на Python", "Напиши функцию на Python, которая считает сумму списка чисел."))


class ExampleTile(QPushButton):
    """Плитка-пример возможностей агента: значок и подпись. Нарисована сама, плавно подсвечивается."""

    def __init__(self, kind, label, parent=None):
        super().__init__("", parent)
        self.kind, self.label = kind, label
        self._hv, self.selected = 0.0, False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(170)
        self._anim.valueChanged.connect(self._set_hv)
        self.setFixedSize(124, 82)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)

    def _set_hv(self, v):
        self._hv = float(v)
        self.update()

    def _fade(self, v):
        self._anim.stop()
        self._anim.setStartValue(self._hv)
        self._anim.setEndValue(v)
        self._anim.start()

    def enterEvent(self, e):
        self._fade(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._fade(0.0)
        super().leaveEvent(e)

    def set_selected(self, on):
        self.selected = bool(on)
        self.update()

    def paintEvent(self, e):
        d = self.window()
        accent = QColor(getattr(d, "color", "#FFCFA3"))
        pal = getattr(d, "pal", None) or {"card": "#2b2b2b", "stroke": "#3a3a3a", "text": "#ffffff", "muted": "#a6a6a6"}
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(.55)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -4)
        if self.isDown():
            p.translate(r.center())
            p.scale(.97, .97)
            p.translate(-r.center())
        sel = 1.0 if self.selected else 0.0
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        p.fillPath(path.translated(0, 4), QColor(0, 0, 0, 60))
        p.fillPath(path, _mixc(pal["card"], accent.name(), .08 * max(sel, self._hv)))
        p.setPen(QPen(_mixc(pal["stroke"], accent.name(), max(sel, .55 * self._hv)), 1.2 + .8 * sel))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        cx, cy = r.center().x(), r.top() + 27
        bg = QColor(accent)
        bg.setAlpha(int(40 + 40 * max(sel, self._hv)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawEllipse(QPointF(cx, cy), 17, 17)
        pen = QPen(accent, 1.9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(cx, cy)
        k = self.kind
        if k == "msg":                                     # бумажный самолётик
            pl = QPainterPath()
            pl.moveTo(-8, -7)
            pl.lineTo(9, 0)
            pl.lineTo(-8, 7)
            pl.lineTo(-4, 0)
            pl.closeSubpath()
            p.drawPath(pl)
            p.drawLine(QPointF(-4, 0), QPointF(3, 0))
        elif k == "video":                                 # экран с «играть»
            p.drawRoundedRect(QRectF(-9, -7, 18, 14), 3.5, 3.5)
            tri = QPainterPath()
            tri.moveTo(-2.5, -3.5)
            tri.lineTo(4, 0)
            tri.lineTo(-2.5, 3.5)
            tri.closeSubpath()
            p.setBrush(accent)
            p.drawPath(tri)
        elif k == "form":                                  # лист с полями
            p.drawRoundedRect(QRectF(-7, -9, 14, 18), 3, 3)
            for yy in (-4, 0):
                p.drawLine(QPointF(-3.5, yy), QPointF(3.5, yy))
            p.drawPolyline(QPolygonF([QPointF(-3.2, 5), QPointF(-1, 6.8), QPointF(3.4, 3.2)]))
        else:                                              # письмо
            p.drawRoundedRect(QRectF(-9, -6.5, 18, 13), 3, 3)
            p.drawPolyline(QPolygonF([QPointF(-8.5, -5.5), QPointF(0, 1.5), QPointF(8.5, -5.5)]))
        p.restore()
        p.setPen(QColor(pal["text"]))
        f = QFont(theme.FONT_FAMILY)
        f.setPixelSize(12)
        f.setWeight(QFont.Weight.DemiBold if self.selected else QFont.Weight.Normal)
        p.setFont(f)
        p.drawText(QRectF(r.left() + 4, r.top() + 48, r.width() - 8, 22), int(Qt.AlignmentFlag.AlignCenter.value), self.label)
        p.end()


class ModelPillLocal:
    """Есть ли на этом ПК скачанная локальная модель: без неё «На этом компьютере» выбрать нельзя."""

    @staticmethod
    def available():
        try:
            from llm import store as model_store
            return bool(model_store.installed_ids())
        except Exception:
            return False


class ChoiceCard(QPushButton):
    """Большая карточка выбора (где Mico будет думать): значок, название, описание, галочка у выбранной. Рисует себя сама."""

    def __init__(self, kind, title, desc, tag, parent=None):
        super().__init__("", parent)
        self.kind, self.title_t, self.desc, self.tag = kind, title, desc, tag
        self._sel, self._hover = 0.0, 0.0
        self._asel = QVariantAnimation(self)
        self._asel.setDuration(320)
        self._asel.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._asel.valueChanged.connect(lambda v: self._set("_sel", v))
        self._ahov = QVariantAnimation(self)
        self._ahov.setDuration(180)
        self._ahov.valueChanged.connect(lambda v: self._set("_hover", v))
        self.setFixedSize(480, 118)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFlat(True)

    def _set(self, name, v):
        setattr(self, name, float(v))
        self.update()

    def set_selected(self, on, animate=True):
        self._asel.stop()
        if not animate:
            self._set("_sel", 1.0 if on else 0.0)
            return
        self._asel.setStartValue(self._sel)
        self._asel.setEndValue(1.0 if on else 0.0)
        self._asel.start()

    def enterEvent(self, e):
        self._ahov.stop()
        self._ahov.setStartValue(self._hover)
        self._ahov.setEndValue(1.0)
        self._ahov.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._ahov.stop()
        self._ahov.setStartValue(self._hover)
        self._ahov.setEndValue(0.0)
        self._ahov.start()
        super().leaveEvent(e)

    def paintEvent(self, e):
        d = self.window()
        accent = QColor(getattr(d, "color", "#FFCFA3"))
        pal = getattr(d, "pal", None) or {"card": "#2b2b2b", "stroke": "#3a3a3a", "text": "#ffffff", "muted": "#a6a6a6"}
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        sel, hv = self._sel, self._hover
        path = QPainterPath()
        path.addRoundedRect(r, 22, 22)
        p.fillPath(path.translated(0, 6), QColor(0, 0, 0, 70))
        p.fillPath(path, _mixc(pal["card"], accent.name(), .10 * sel + .04 * hv))
        edge = _mixc(pal["stroke"], accent.name(), max(sel, .5 * hv))
        p.setPen(QPen(edge, 1.2 + 1.2 * sel))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        # значок в круглой плашке
        cx, cy = r.left() + 46, r.center().y()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_mixc(pal["stroke"], accent.name(), .35 + .4 * sel))
        p.drawEllipse(QPointF(cx, cy), 27, 27)
        ink = QColor(theme.on_accent(accent.name())) if sel > .5 else QColor(pal["text"])
        pen = QPen(ink, 2.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == "local":                          # монитор
            p.drawRoundedRect(QRectF(cx - 13, cy - 11, 26, 17), 3, 3)
            p.drawLine(QPointF(cx, cy + 6), QPointF(cx, cy + 11))
            p.drawLine(QPointF(cx - 7, cy + 11), QPointF(cx + 7, cy + 11))
        else:                                             # облако
            cl = QPainterPath()
            cl.moveTo(cx - 12, cy + 8)
            cl.cubicTo(cx - 20, cy + 8, cx - 20, cy - 3, cx - 11, cy - 3)
            cl.cubicTo(cx - 10, cy - 13, cx + 6, cy - 14, cx + 8, cy - 4)
            cl.cubicTo(cx + 18, cy - 4, cx + 18, cy + 8, cx + 10, cy + 8)
            cl.closeSubpath()
            p.drawPath(cl)
        # тексты
        tx = r.left() + 92
        f = QFont(theme.FONT_DISPLAY)
        f.setPixelSize(17)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(QColor(pal["text"]))
        p.drawText(QRectF(tx, r.top() + 14, r.width() - 150, 26), int(Qt.AlignmentFlag.AlignLeft.value | Qt.AlignmentFlag.AlignVCenter.value), self.title_t)
        f2 = QFont(theme.FONT_FAMILY)
        f2.setPixelSize(13)
        p.setFont(f2)
        p.setPen(QColor(pal["muted"]))
        p.drawText(QRectF(tx, r.top() + 44, r.width() - tx + r.left() - 18, r.height() - 54),
                   int((Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop).value) | int(Qt.TextFlag.TextWordWrap.value), self.desc)
        # метка и галочка
        f3 = QFont(theme.FONT_FAMILY)
        f3.setPixelSize(11)
        p.setFont(f3)
        tw = QFontMetrics(f3).horizontalAdvance(self.tag) + 18
        tag_r = QRectF(r.right() - tw - 52, r.top() + 17, tw, 20)
        p.setPen(QPen(_mixc(pal["stroke"], accent.name(), .6 * sel), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(tag_r, 10, 10)
        p.setPen(QColor(pal["muted"]))
        p.drawText(tag_r, int(Qt.AlignmentFlag.AlignCenter.value), self.tag)
        if sel > .01:
            kx, ky, kr = r.right() - 30, r.top() + 27, 12 * sel
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawEllipse(QPointF(kx, ky), kr, kr)
            pen2 = QPen(QColor(theme.on_accent(accent.name())), 2.2)
            pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            if sel > .6:
                p.drawPolyline(QPolygonF([QPointF(kx - 5, ky), QPointF(kx - 1.5, ky + 3.5), QPointF(kx + 5, ky - 4)]))
        p.end()


class OnboardingDialog(QDialog):
    """Знакомство на весь экран. Всё рисуется одним paintEvent (фон, Mico, облачко, карточки-демонстрации),
    а кнопки и поле ввода — настоящие виджеты поверх. Кадры Mico — тот же Blob, что на рабочем столе."""
    MICO = 300                                   # размер Mico на сцене, px (крупнее: на знакомстве он главный герой)

    def __init__(self, cfg, parent=None, on_color=None, desktop=None):
        super().__init__(parent)
        self.desktop = desktop                # Mico на рабочем столе: пока идёт знакомство, он спрятан (виден только Mico по центру)
        self._desktop_was_visible = False
        from ui import chatlook as chat_look            # через функцию: chatlook сам импортирует модули, которым нужен COLORS
        self.cfg = cfg
        self.dark = theme.is_dark(cfg)
        self.pal = chat_look.PALETTE[bool(self.dark)]
        self.setWindowTitle(i18n.t("Добро пожаловать в Mico AI"))
        self.setObjectName("onb")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        self.setGeometry(screen.geometry())          # весь экран: Mico летает по нему
        self.color = cfg.get("color") or COLORS[0][0]
        self.on_color = on_color              # сразу показываем выбранный цвет на Mico AI
        self.home = None                      # где живёт Mico на рабочем столе (глобальная точка): туда он улетает в конце
        from ui.blob import Blob, BASE_PX
        self._blob = Blob({"color": self.color, "scale": self.MICO / BASE_PX, "opacity": 1.0, "sleep_after_min": 0,
                           "assist_style": "classic", "placement": "manual", "sleep_corner": "br",
                           "anim_sleep_fps": 20})
        self._blob.can_sleep = lambda: False
        self._blob.timer.stop()                              # кадры двигаем сами
        self._blob.set_mood("happy", 999)
        self._pix = None
        self.scene = -1
        self._t0 = self._last = time.monotonic()
        self._mp = QPointF(self.width() + 200, self.height() + 200)   # где сейчас Mico (центр)
        self._move = None                     # (откуда, куда, изгиб, начало, длительность)
        self._size, self._size_to = 0.0, float(self.MICO)
        self._lean, self._land_t, self._trail = 0.0, -9.0, []
        self._say_full, self._say_t = "", 0.0
        self._hint = False                    # пульсирующие кольца «нажми на меня»
        self._sparks = []
        self._glow, self._glow_t = None, -1.0
        self._demo, self._demo_t, self._done = None, -9.0, set()
        self._card_t = -9.0                   # когда появилась карточка текущей сцены
        self._agent, self._agent_t = None, -9.0
        self._ag_phase, self._ag_t0, self._ag_play_t = None, -9.0, -9.0   # сцена агента: reveal — появление, play — примеры
        self._ex = None                      # выбранный пример агента
        self._ag_auto, self._ag_cur, self._ag_ask_t, self._ag_end_t, self._ag_seen = False, 0, 0.0, 0.0, 0   # автопоказ примеров
        self._ai = "local" if cfg.get("llm_backend") == "local" else "mico"   # где Mico будет думать: по умолчанию в облаке Mico
        self._ai_models, self._ai_result, self._ai_loading = [], None, False
        self._offer_done = False
        self._listen_t = -9.0
        self._swatch_t = -9.0
        self._closing = False
        self._build_widgets()
        self._style()
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    # ---------- виджеты поверх сцены ----------
    def _button(self, text, name, slot):
        b = RoundButton(i18n.t(text), name, self)
        b.clicked.connect(slot)
        b.setAutoDefault(False)                       # Enter в поле команды не жмёт кнопки
        b.hide()
        return b

    def _build_widgets(self):
        self.skip = self._button("Пропустить знакомство", "ghost", self._finish)
        self.next = self._button("Дальше", "primary", self._next)
        self.back = self._button("Назад", "ghost", lambda: self._enter(self._prev_scene()))
        self._swatches = {}
        for hex_color, name in COLORS:
            b = self._button("", "swatch", lambda _=False, c=hex_color: self._pick(c))
            b.setToolTip(i18n.t(name))
            b.setProperty("hex", hex_color)
            b.setFixedSize(54, 54)
            self._swatches[hex_color] = b
        self._chips = {}
        for kind, label, _after in PRACTICE:
            b = self._button("«" + i18n.t(label) + "»", "chip", lambda _=False, k=kind: self._run_demo(k))
            self._chips[kind] = b
        self.cmd = RoundLineEdit(self)
        self.cmd.setObjectName("cmd")
        self.cmd.setFixedHeight(48)
        self.cmd.setPlaceholderText(i18n.t("Напиши команду и нажми Enter…"))
        self.cmd.returnPressed.connect(self._typed)
        self.cmd.hide()
        self.yes = self._button("Да", "primarySm", lambda: self._agent_answer(True))
        self.no = self._button("Нет", "chip", lambda: self._agent_answer(False))
        self.ai_local = ChoiceCard("local", i18n.t("На этом компьютере"),
                                   i18n.t("Работает без интернета, данные остаются на ПК. Нагружает процессор."), i18n.t("Офлайн"), self)
        self.ai_cloud = ChoiceCard("cloud", i18n.t("Облако Mico"),
                                   i18n.t("Быстро и умно, без нагрузки на процессор. Ключи не нужны. Текст чата уходит на сервер Mico AI."), i18n.t("Рекомендуем"), self)
        self.ai_local.clicked.connect(lambda: self._ai_pick("local"))
        self.ai_cloud.clicked.connect(lambda: self._ai_pick("mico"))
        for w in (self.ai_local, self.ai_cloud):
            w.hide()
        self.ai_chips = [self._button("", "chip", lambda _=False, i=i: self._ai_model_pick(i)) for i in range(5)]
        self.ag_chips = []
        for i, ex in enumerate(AGENT_EXAMPLES):
            tile_w = ExampleTile(ex["kind"], i18n.t(ex["label"]), self)
            tile_w.clicked.connect(lambda _=False, k=i: self._start_example(k))
            tile_w.hide()
            self.ag_chips.append(tile_w)
        self.cl_in = RoundLineEdit(self)                      # свой вопрос облаку Mico в знакомстве
        self.cl_in.setPlaceholderText(i18n.t("Задай свой вопрос облаку Mico и нажми Enter"))
        self.cl_in.setMaxLength(300)
        self.cl_in.returnPressed.connect(lambda: self._cl_ask(self.cl_in.text()))
        self.cl_in.hide()
        self.cl_chips = [self._button(short, "chip", lambda _=False, q=full: self._cl_ask(q)) for short, full in CLOUD_QUESTIONS]
        self._cl_reset()
        self.wi_on = self._button("Включить зимний режим", "primary", lambda: self._sw_choose(True))
        self.wi_off = self._button("Без зимы", "ghost", lambda: self._sw_choose(False))
        self._sw_state, self._snow = "idle", None
        self.ag_on = self._button("Включить агента", "primary", lambda: self._ag_enable(True))
        self.ag_off = self._button("Пока не надо", "ghost", lambda: self._ag_enable(False))
        self.mic = self._button("", "mic", self._listen)
        self.mic.setFixedSize(76, 76)
        self._scene_widgets = [self.next, self.back, self.cmd, self.yes, self.no, self.mic, self.ag_on, self.ag_off,
                               self.ai_local, self.ai_cloud, self.cl_in, self.wi_on, self.wi_off] + self.ai_chips + self.ag_chips + self.cl_chips + \
            list(self._swatches.values()) + list(self._chips.values())

    def _style(self):
        p, c = self.pal, self.color
        on = theme.on_accent(c)
        hover = _mixc(c, "#ffffff", .18).name()
        self.setStyleSheet(theme.FONT_QSS + f"""
            QPushButton {{ font-family: "{theme.FONT_FAMILY}"; }}
            QPushButton#primary {{ background: {c}; color: {on}; border: none; border-radius: 22px; padding: 11px 34px;
                                  font-size: 14px; font-weight: 600; min-width: 120px; }}
            QPushButton#primary:hover {{ background: {hover}; }}
            QPushButton#primarySm {{ background: {c}; color: {on}; border: none; border-radius: 15px; padding: 6px 20px;
                                    font-size: 13px; font-weight: 600; }}
            QPushButton#primarySm:hover {{ background: {hover}; }}
            QPushButton#ghost {{ background: rgba(255,255,255,0.10); color: #ffffff; border: 1px solid rgba(255,255,255,0.22);
                                border-radius: 16px; padding: 7px 16px; font-size: 12px; }}
            QPushButton#ghost:hover {{ background: rgba(255,255,255,0.18); }}
            QPushButton#chip {{ background: {p['card']}; color: {p['text']}; border: 1px solid {p['stroke']}; border-radius: 18px;
                               padding: 8px 18px; font-size: 13px; }}
            QPushButton#chip:hover {{ border: 1px solid {c}; }}
            QPushButton#chip:disabled {{ color: {p['muted']}; }}
            QPushButton#chip[done="true"] {{ border: 1px solid {c}; }}
            QLineEdit#cmd {{ background: transparent; color: {p['text']}; border: none; padding: 0 26px; font-size: 14px;
                            selection-background-color: {c}; }}
            QPushButton#mic {{ background: {c}; border: none; border-radius: 38px; }}
            QPushButton#mic:hover {{ background: {hover}; }}""")
        for b in self.findChildren(RoundButton):
            b.update()                                    # кнопки рисуют себя сами: цвет мог смениться
        try:
            from ui import icons as uiicons
            from PyQt6.QtCore import QSize
            self.mic.setIcon(uiicons.icon("mic", on, 34, width=1.8))
            self.mic.setIconSize(QSize(34, 34))
        except Exception:
            pass

    # ---------- жизнь окна ----------
    def showEvent(self, e):
        super().showEvent(e)
        from ui import blob as blob_mod
        blob_mod.MODAL[0] += 1                       # пока окно открыто, Mico на рабочем столе не лезет поверх
        self._hide_desktop()
        self.raise_()
        self.activateWindow()
        if not getattr(self, "_faded", False):
            self._faded = True
            from ui import motion
            motion.window_fade_in(self, 420)
            self._timer.start()
            self._enter(0)

    def done(self, r):
        from ui import blob as blob_mod
        blob_mod.MODAL[0] = max(0, blob_mod.MODAL[0] - 1)
        self._timer.stop()
        self._restore_desktop()
        super().done(r)

    def _hide_desktop(self):
        """Нижний Mico (с рабочего стола) прячем: на знакомстве виден только Mico по центру, второго нет."""
        d = self.desktop
        if d is None:
            return
        try:
            self._desktop_was_visible = bool(d.isVisible())
            d.hide()
            d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)   # любой show() приложения больше не высвечивает его на экране
        except Exception:
            pass

    def _restore_desktop(self):
        d = self.desktop
        if d is None:
            return
        if not self._desktop_was_visible:
            try:
                d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            except Exception:
                pass
            return
        try:
            d.hide()
            d.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            d.show()
        except Exception:
            pass
        self._desktop_was_visible = False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._finish()
            return
        super().keyPressEvent(e)

    def _finish(self):
        """Окно мягко исчезает и закрывается."""
        if self._closing:
            return
        self._closing = True
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(320)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.accept)
        self._fade_out = anim
        anim.start()

    def _now(self):
        return time.monotonic() - self._t0

    # ---------- движение Mico и речь ----------
    def _fly(self, x, y, ms=900, arc=-140, size=None):
        """Mico летит по дуге в точку (x, y): плавный разгон и торможение, наклон по ходу, в конце пружинка."""
        self._move = (QPointF(self._mp), QPointF(x, y), arc, self._now(), ms / 1000.0)
        if size:
            self._size_to = float(size)

    def _say(self, text, mood=None, secs=3):
        self._say_full, self._say_t = i18n.t(text), self._now()
        if mood:
            self._blob.set_mood(mood, secs)

    def _burst(self, x, y, count=60, rainbow=False):
        cols = [QColor(c) for c in RAINBOW] if rainbow else [QColor(self.color)] + [QColor(c) for c, _n in COLORS]
        for i in range(count):
            a = random.uniform(0, 2 * math.pi)
            v = random.uniform(220, 760)
            self._sparks.append([x, y, math.cos(a) * v, math.sin(a) * v - 260, random.uniform(0, 360),
                                 random.uniform(-600, 600), 1.0, cols[i % len(cols)], random.choice((6, 8, 10))])

    def _mico_hit(self, pos):
        return (pos - self._mp).manhattanLength() < self._size * .55

    def mouseMoveEvent(self, e):
        over = self._mico_hit(e.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(e)

    def mousePressEvent(self, e):
        if self._mico_hit(e.position()):
            self._blob.jump(320)
            self._land_t = self._now() + .05
            if self.scene == S_AGENT and self._ag_phase == "reveal" and self._now() - self._ag_t0 > 1.4:
                self._ag_play()                      # вступление можно пропустить щелчком по Mico
            elif self.scene == 0 and self._hint:       # первая практика выполнена: человек нажал на Mico
                self._hint = False
                self._burst(self._mp.x(), self._mp.y())
                self._say("Ура! Так ты открываешь чат на рабочем столе. А теперь давай выберем мне цвет!", "love", 2.4)
                QTimer.singleShot(2300, lambda: self.scene == 0 and self._enter(1))
            else:
                self._blob.set_mood(random.choice(("happy", "laugh", "love", "playful")), 1.8)
                self._burst(self._mp.x(), self._mp.y(), 16)
        super().mousePressEvent(e)

    # ---------- сцены ----------
    def _place_next(self, text):
        """«Назад» и «Дальше» стоят одной парой строго по центру экрана, на одной высоте и с одинаковым зазором."""
        W, H = self.width(), self.height()
        self.next.setText(i18n.t(text))
        self.next.adjustSize()
        show_back = 0 < self.scene < SCENES - 1
        gap = 16
        y = int(H - 112)
        for b in (self.back, self.next):                 # прежние фиксированные размеры (после предложения про агента) сбрасываются
            b.setMinimumSize(0, 0)
            b.setMaximumSize(16777215, 16777215)
        self.next.adjustSize()
        if show_back:
            self.back.adjustSize()
            h = max(self.next.height(), self.back.height())
            bw = max(self.next.width(), self.back.width(), 132)
            self.next.setFixedSize(bw, h)
            self.back.setFixedSize(bw, h)
            total = self.back.width() + gap + self.next.width()
            x0 = int(W / 2 - total / 2)
            self.back.move(x0, y)
            self.next.move(x0 + self.back.width() + gap, y)
            self.back.show()
        else:
            self.next.setMinimumHeight(0)
            self.next.setMaximumHeight(16777215)
            self.next.move(int(W / 2 - self.next.width() / 2), y)
            self.back.hide()
        self.next.show()
        from ui import motion
        motion.fade_slide_in(self.next, dy=10, ms=300)

    def _enter(self, i):
        i = max(0, min(SCENES - 1, i))
        self.scene = i
        W, H = self.width(), self.height()
        for w in self._scene_widgets:
            w.hide()
        self._hint = False
        sn = getattr(self, "_sw_snow", None)
        if sn is not None and i != S_WINTER:                      # снег ночной сцены уходит вместе с ней
            try:
                sn.cfg["winter_ui"] = False
                sn.sync()
                sn.deleteLater()
            except RuntimeError:
                pass
            self._sw_snow = None
        self._ag_phase, self._ex = None, None
        self._demo, self._agent = None, None
        self.ag_on.hide()
        self.ag_off.hide()
        self._card_t = self._now()
        self.skip.adjustSize()
        self.skip.move(W - self.skip.width() - 28, 26)
        self.skip.setVisible(i < SCENES - 1)
        self._blob.set_listening(False)
        self._blob.set_speaking(False)
        if i == 0:                                       # привет: Mico влетает из-за края экрана
            self._mp = QPointF(W + 180, H * .92)
            self._size, self._size_to = 110.0, float(self.MICO)
            self._fly(W / 2, H * .44, 1400, arc=-320)
            self._say_full = ""

            def hello():
                if self.scene == 0:
                    self._say("Привет, я Mico! Я буду жить у тебя на рабочем столе. Давай покажу, что я умею. "
                              "Для начала — нажми на меня.", "happy", 3)
                    self._hint = True
            QTimer.singleShot(1100, hello)
        elif i == 1:                                     # цвет: шарики вылетают из Mico и встают дугой
            self._fly(W / 2, H * .36, 700, arc=-80, size=self.MICO)
            self._say("Выбери мне цвет — им окрасятся я, чат и переключатели. Поменять можно в любой момент.", "curious", 3)
            self._swatch_t = self._now() + .3
            for b in self._swatches.values():
                b.move(int(self._mp.x() - 27), int(self._mp.y() - 27))
                b.show()
            self._place_next("Дальше")
        elif i == S_AI:                                  # выбор, как отвечать: на ПК или через облако
            self._fly(self._mico_stage_x(), H * .40, 800, arc=-110, size=self.MICO)
            self._say("Как мне отвечать? Выбери — это можно поменять в чате в любой момент.", "curious", 3)
            self._ai_show()
            self._place_next("Дальше")
        elif i == S_CLOUD:                               # Mico Cloud: показываем модели и даём спросить по-настоящему
            self._fly(self._mico_stage_x(), H * .40, 800, arc=-110, size=self.MICO)
            self._cl_reset()
            try:
                from llm import cloud as cloud_api
                cloud_api.ensure_quota_async(5.0)                   # остаток нейронов подтянется, пока идёт вступление
            except Exception:
                pass
            self._cl_i0, self._cl_burst = self._now(), False         # вступление: вспышка, сетка, название появляется по буквам
            self._say_full = ""
            QTimer.singleShot(3000, lambda: self.scene == S_CLOUD and (self._place_cloud(), self._place_next("Дальше")))
            QTimer.singleShot(3100, lambda: self.scene == S_CLOUD and self._say("Это Mico Cloud: несколько ИИ-моделей в одном облаке. Спроси что угодно, и я передам вопрос самой подходящей. Попробуй сам!", "excited", 4))
        elif i == S_PRACTICE:                            # практика команд
            self._fly(self._mico_stage_x(), H * .40, 800, arc=-120, size=self.MICO)
            self._say("Теперь практика! Скажи мне что-нибудь: выбери команду или напиши свою. "
                      "Это тренировка — в Windows ничего не изменится.", "excited", 3)
            self._place_practice()
            if self._done:
                self._place_next("Дальше")
        elif i == S_AGENT:                               # режим агента: спокойное появление, потом примеры и предложение включить
            self._ag_phase, self._ag_t0, self._offer_done = "reveal", self._now(), False
            self._fly(W / 2, H * .55, 1000, arc=-120, size=self.MICO)
            self._say("Встречайте — режим агента! Это совсем новая моя функция (пока в BETA): я сам открою программу, "
                      "напишу сообщение или включу видео.", "happy", 4)
            QTimer.singleShot(4200, self._ag_play)
        elif i == S_VOICE:                               # голос
            self._fly(W / 2, H * .40, 800, arc=-100, size=self.MICO)
            self._say("Со мной можно говорить голосом: скажи «Мико!» или нажми на микрофон. Попробуй — нажми на кнопку.", "happy", 3)
            self.mic.move(int(W / 2 - 38), int(H * .40 + self.MICO * .66))
            self.mic.show()
            self._listen_t = -9.0
            QTimer.singleShot(5000, lambda: self.scene == S_VOICE and not self.next.isVisible() and self._place_next("Дальше"))
        elif i == S_WINTER:                              # Дед Мороз на санях задевает Mico и дарит ему колпак
            self._sw_start()
        else:                                            # готово: Mico улетает туда, где будет жить
            hx, hy = W - 150, H - 190
            if self.home is not None:
                try:
                    local = self.mapFromGlobal(self.home)
                    hx, hy = local.x(), local.y()
                except Exception:
                    pass
            hx, hy = max(170, min(W - 170, hx)), max(210, min(H - 190, hy))
            self._fly(hx, hy, 1200, arc=-220, size=250)       # в конце Mico крупный, а не крошечный
            self._say("Я буду жить вот здесь. Нажми на меня — откроется чат. Спроси «что ты умеешь?», и я покажу всё.", "love", 4)
            QTimer.singleShot(1250, lambda: self.scene == SCENES - 1 and self._burst(self._mp.x(), self._mp.y(), 50))
            self._place_next("Начать")
        self.update()

    def _prev_scene(self):
        """Назад: сцену про облако пропускаем, если ответы выбраны на этом компьютере."""
        i = self.scene - 1
        if i == S_CLOUD and self._ai != "mico":
            i = S_AI
        return i

    def _next(self):
        if self.scene < SCENES - 1:
            nxt = self.scene + 1
            if nxt == S_CLOUD and self._ai != "mico":          # про облако показываем только тем, кто его выбрал
                nxt = S_PRACTICE
            self._enter(nxt)
        else:
            self._finish()

    def _pick(self, hex_color):
        """Выбор цвета: Mico оборачивается и перекрашивается, вместе с ним — сцена, кнопки, чат на рабочем столе."""
        self.color = hex_color
        if self.on_color is not None:
            self.on_color(hex_color)          # Mico AI и его чат перекрашиваются сразу, без «Готово»
        self._blob.cfg["color"] = hex_color
        try:
            self._blob.pick_color(hex_color)             # та же смена цвета с поворотом, что на рабочем столе
        except Exception:
            pass
        self._blob.jump(240)
        name = dict(COLORS).get(hex_color, "")
        self._say(i18n.t(name) + " — " + i18n.t("отличный выбор! Теперь и чат в этом цвете."), "love", 2.2)
        self._burst(self._mp.x(), self._mp.y(), 30)
        self._glow = None
        self._style()

    # ---------- практика ----------
    def _place_practice(self):
        W, H = self.width(), self.height()
        chips = list(self._chips.values())
        for b in chips:
            b.adjustSize()
        gap = 12
        total = sum(b.width() for b in chips) + gap * (len(chips) - 1)
        x = W / 2 - total / 2
        for b in chips:
            b.move(int(x), int(H - 262))
            x += b.width() + gap
            b.setEnabled(True)
            b.show()
        self.cmd.setFixedWidth(min(580, W - 80))
        self.cmd.adjustSize()
        self.cmd.move(int(W / 2 - self.cmd.width() / 2), int(H - 204))
        self.cmd.show()
        self.cmd.setFocus()

    def _run_demo(self, kind):
        if self._demo_busy():
            return
        label = {k: l for k, l, _a in PRACTICE}[kind]
        for b in self._chips.values():
            b.setEnabled(False)
        self._typing, self._typing_n, self._typing_kind = i18n.t(label), 0, kind
        self.cmd.clear()
        if not hasattr(self, "_type_timer"):
            self._type_timer = QTimer(self)
            self._type_timer.setInterval(34)
            self._type_timer.timeout.connect(self._type_step)
        self._type_timer.start()

    def _type_step(self):
        self._typing_n += 1
        self.cmd.setText(self._typing[:self._typing_n])
        if self._typing_n >= len(self._typing):
            self._type_timer.stop()
            QTimer.singleShot(260, lambda: self._start_demo(self._typing_kind))

    def _demo_busy(self):
        return self._demo is not None and self._now() - self._demo_t < DEMO_SEC.get(self._demo, 0) + .2

    def _typed(self):
        """Человек написал сам: узнаём одну из тренировок по словам, иначе зовём в настоящий чат."""
        text = self.cmd.text().strip().lower()
        if not text or self._demo_busy():
            return
        for kind in ("timer", "volume", "dark", "notepad"):
            if any(w in text for w in DEMO_WORDS[kind]):
                self._start_demo(kind)
                return
        self.cmd.clear()
        self._say("Это я сделаю в настоящем чате — после знакомства просто напиши мне. А здесь попробуй одну из кнопок.", "curious", 2.6)

    def _start_demo(self, kind):
        self.cmd.clear()
        self._demo, self._demo_t = kind, self._now()
        for b in self._chips.values():
            b.setEnabled(False)
        self._blob.set_mood("thinking" if kind == "timer" else "excited", DEMO_SEC[kind])
        self._blob.jump(220)
        self._say(i18n.t("Делаю") + ": «" + i18n.t({k: l for k, l, _a in PRACTICE}[kind]) + "»…")
        QTimer.singleShot(int(DEMO_SEC[kind] * 1000) + 120, lambda k=kind: self._end_demo(k))

    def _end_demo(self, kind):
        if self.scene != S_PRACTICE or self._demo != kind:
            return
        self._done.add(kind)
        chip = self._chips[kind]
        chip.setText("✓ «" + i18n.t({k: l for k, l, _a in PRACTICE}[kind]) + "»")
        chip.setProperty("done", True)
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        for b in self._chips.values():
            b.setEnabled(True)
        self._place_practice()
        self._say({k: a for k, _l, a in PRACTICE}[kind], "happy", 2.6)
        self._blob.jump(280)
        if kind == "timer":
            self._burst(self.width() * .64, self.height() * .40, 40)
        if not self.next.isVisible():
            self._place_next("Дальше")

    # ---------- агент и голос ----------
    def _card_rect(self, w, h):
        W, H = self.width(), self.height()
        if self.scene == S_AGENT:                      # примеры агента — строго по центру экрана, Mico стоит слева от них
            return QRectF(W / 2 - w / 2, H * .41 - h / 2, w, h)
        # Mico стоит слева (в сценах 2 и 3); карточка всегда правее него, чтобы он её не перекрывал
        mico_right = self._mico_stage_x() + self.MICO * .5 + 36
        cx = max(W * .64, mico_right + w / 2)
        cx = min(cx, W - w / 2 - 24)
        return QRectF(cx - w / 2, H * .41 - h / 2, w, h)

    def _mico_stage_x(self):
        """Где стоит Mico слева в сценах практики и агента."""
        x = max(self.MICO * .5 + 40, self.width() * .27)
        if self.scene == S_AGENT:                      # карточка агента по центру: Mico не заходит на неё
            x = min(x, self.width() / 2 - 220 - 36 - self.MICO * .5)
            x = max(self.MICO * .5 + 16, x)
        return x

    def _place_yes_no(self):
        """«Да» и «Нет» — две круглые кнопки одной высоты, строго по центру строки вопроса и у её правого края."""
        r = self._card_rect(440, 320)
        for b in (self.yes, self.no):
            b.setMinimumWidth(0)
            b.setFixedHeight(34)
            b.adjustSize()
        bw = max(self.yes.width(), self.no.width(), 78)                  # «Да» и «Нет» одной ширины
        self.yes.setFixedWidth(bw)
        self.no.setFixedWidth(bw)
        row_top, row_h = r.top() + 250, 40
        y = int(row_top + (row_h - 34) / 2)
        self.yes.move(int(r.right() - 20 - 8 - self.yes.width()), y)
        self.no.move(int(self.yes.x() - 10 - self.no.width()), y)
        self.yes.show()
        self.no.show()
        self.yes.raise_()
        self.no.raise_()

    def _agent_answer(self, yes):
        ex = self._ex or AGENT_EXAMPLES[0]
        self.yes.hide()
        self.no.hide()
        self._agent, self._agent_t2 = ("sent" if yes else "no"), self._now()
        self._ag_end_t = self._agent_t2
        if yes:
            self._say(ex["say_yes"], "proud", 3)
            self._blob.jump(300)
            r = self._card_rect(440, 320)
            self._burst(r.center().x(), r.bottom() - 40, 22)
        else:
            self._say(ex["say_no"], "happy", 3)
        self._ag_examples_done()

    # ---------- сцена «Новый год»: Дед Мороз на санях задевает Mico и дарит колпак ----------
    SW_T0, SW_DUR = 1.8, 7.4                                 # когда выезжают сани и сколько они едут через экран (с)

    def _sw_start(self):
        W, H = self.width(), self.height()
        self._sw_t0 = self._now()
        self._sw_state = "wait"
        self._sw_mx, self._sw_my = W * .5, H * .30
        self._blob.cfg["winter_mico"] = False                 # колпака ещё нет: его подарит Дед Мороз
        self._fly(self._sw_mx, self._sw_my, 900, arc=-120, size=self.MICO * .9)
        self._say("Ой, что там внизу? Кто-то едет по экрану!", "curious", 3)
        self._hat_fly = None
        self.wi_on.hide()
        self.wi_off.hide()
        if getattr(self, "_sw_snow", None) is None:             # во время сцены идёт снег
            self._sw_snow = winter_ui.SnowOverlay(self, {"winter_ui": True})
            self._sw_snow.sync()

    def _sw_scale(self):
        return max(.7, min(1.4, self.height() / 760.0))

    def _sw_pos(self, u):
        """Где сани (x — тело саней, y — полозья). Они едут слева направо и на пути мимо Mico поднимаются к нему."""
        W, H = self.width(), self.height()
        s = self._sw_scale()
        x0, x1 = -420 * s, W + 140 * s
        x = x0 + (x1 - x0) * _clamp((u - self.SW_T0) / self.SW_DUR)
        ground = H * .84
        foot = self._sw_my + self.MICO * .9 * .36
        ypass = min(ground, foot + 150 * s)
        bump = math.exp(-((x - self._sw_mx) / (170 * s)) ** 2)
        return x, ground - (ground - ypass) * bump

    def _sw_tick(self, t):
        st = getattr(self, "_sw_state", "idle")
        if st in ("idle", "choose", "done"):
            return
        u = t - self._sw_t0
        s = self._sw_scale()
        x, y = self._sw_pos(u)
        mx = self._sw_mx
        if st == "wait" and u >= self.SW_T0:
            self._sw_state = st = "ride"
        if st in ("ride", "hit", "throw"):                       # Mico провожает сани взглядом
            try:
                self._blob.typing_until = time.time() + .25
                self._blob.look_at = self.mapToGlobal(QPoint(int(max(0, min(self.width(), x + 60 * s))), int(y)))
            except Exception:
                pass
        if st == "ride" and x >= mx - 40 * s:                     # сани задели Mico: он отскакивает и удивляется
            self._sw_state = "hit"
            self._blob.set_mood("surprised", 2.0)
            self._blob.jump(260)
            self._burst(mx, self._sw_my + self.MICO * .25, 22)
            self._fly(mx + 170 * s, self._sw_my - 70 * s, 650, arc=-210)
            self._say("Ой! Меня задел Дед Мороз!", "surprised", 2)
        elif st == "hit" and x >= mx + 70 * s:                    # Дед Мороз бросает колпак
            self._sw_state = "throw"
            self._hat_fly = (t, QPointF(x + 25 * s, y - 86 * s))
            self._say("Смотри-ка, он что-то бросает мне…", "curious", 2)
        elif st == "throw" and self._hat_fly and t - self._hat_fly[0] >= 1.05:
            self._sw_state = "landed"
            self._sw_t_land = t
            self._hat_fly = None
            self._blob.cfg["winter_mico"] = True                  # колпак на голове: появляется с лёгким «хлопком»
            self.cfg["winter_mico"] = True
            self._blob.set_mood("excited", 3.0)
            self._blob.jump(360)
            self._burst(self._mp.x(), self._mp.y() - self._size * .3, 50, rainbow=True)
            self._say("Ура! Дед Мороз подарил мне новогодний колпак!", "excited", 3)
        elif st == "landed" and t - self._sw_t_land >= 1.9:
            self._sw_state = "choose"
            self._fly(self.width() / 2, self.height() * .36, 800, arc=-100, size=self.MICO)
            self._say("Хочешь новогоднее настроение везде? Снег, ёлки и подарки в настройках и в чате.", "love", 4)
            self._place_wi_buttons()

    def _place_wi_buttons(self):
        """«Включить зимний режим» и «Без зимы»: одинакового размера, одной парой по центру."""
        W, H = self.width(), self.height()
        btns = [self.wi_off, self.wi_on]
        for b in btns:
            b.setMinimumSize(0, 0)
            b.setMaximumSize(16777215, 16777215)
            b.adjustSize()
        bw, bh = max(190, max(b.width() for b in btns)), 46
        gap = 14
        x = W / 2 - (bw * 2 + gap) / 2
        for b in btns:
            b.setFixedSize(bw, bh)
            b.move(int(x), int(H - 214))
            b.show()
            x += bw + gap

    def _sw_choose(self, on):
        """Выбор: включить зимний вид (снег, декор, колпак) или оставить как есть. Колпак без зимы снимается."""
        self._sw_state = "done"
        self.wi_on.hide()
        self.wi_off.hide()
        self.cfg["winter_ui"] = bool(on)
        self.cfg["winter_mico"] = bool(on)
        self._blob.cfg["winter_mico"] = bool(on)
        try:
            if on and self._snow is None:
                self._snow = winter_ui.SnowOverlay(self, self.cfg)
            winter_ui.refresh_all()
        except Exception:
            pass
        if on:
            self._blob.set_mood("love", 3)
            self._blob.jump(300)
            self._burst(self._mp.x(), self._mp.y(), 40, rainbow=True)
            self._say("С Новым годом! Всё это можно выключить в ⚙ Настройки → «Зима».", "happy", 4)
        else:
            self._say("Хорошо, без зимы. Включить её можно в ⚙ Настройки → «Зима».", "idle", 3)
        self._place_next("Дальше")

    def _paint_winter(self, p, t):
        """Сани с Дедом Морозом и оленями едут под Mico; за ними тянется след из искр."""
        st = getattr(self, "_sw_state", "idle")
        if st == "idle":
            return
        W, H = self.width(), self.height()
        winter_ui.draw_winter_night(p, W, H, t, _clamp((t - self._sw_t0) / 1.4))          # зимняя ночь на фоне: холмы, домики, луна, сияние
        if st == "wait":
            return
        u = t - self._sw_t0
        x, y = self._sw_pos(u)
        s = self._sw_scale()
        if x > self.width() + 460 * s:
            return
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        for k in range(30):                                      # искры за санями
            xx = x - 70 * s - k * 15 * s
            yy = y - 10 * s + math.sin(k * .7 + t * 6) * 9 * s
            a = max(0.0, 1 - k / 30.0)
            col = QColor(255, 236, 160) if k % 2 else QColor(255, 255, 255)
            col.setAlpha(int(200 * a))
            p.setBrush(col)
            rr = (1.2 + 2.6 * a) * s
            p.drawEllipse(QPointF(xx, yy), rr, rr)
        winter_ui.draw_sleigh(p, x, y, s, t)
        p.restore()

    def _paint_winter_fg(self, p, t):
        """Колпак летит от Деда Мороза к Mico по дуге и вертится."""
        if getattr(self, "_sw_state", "") != "throw" or not getattr(self, "_hat_fly", None):
            return
        t0, start = self._hat_fly
        k = _clamp((t - t0) / 1.05)
        end = QPointF(self._mp.x(), self._mp.y() - self._size * .34)
        e = _io(k)
        x = start.x() + (end.x() - start.x()) * e
        y = start.y() + (end.y() - start.y()) * e - math.sin(math.pi * e) * 150
        winter_ui.draw_hat_icon(p, x, y, .9 + .3 * k, rot=-30 + 380 * e)

    # ---------- сцена Mico Cloud: настоящая проба моделей ----------
    def _cl_reset(self):
        self._cl_q, self._cl_text, self._cl_state, self._cl_model, self._cl_err = "", "", "idle", "", ""
        self._cl_tier = ""
        self._cl_t0 = self._cl_dt = 0.0
        self._cl_react = False
        self._cl_token = getattr(self, "_cl_token", 0) + 1       # прошлый ответ, если он ещё идёт, больше ничего не обновит

    def _place_cloud(self):
        """Кнопки с вопросами под карточкой и поле для своего вопроса."""
        W, H = self.width(), self.height()
        r = self._card_rect(*CLOUD_CARD)
        for b in self.cl_chips:
            b.adjustSize()
        gap = 10
        total = sum(b.width() for b in self.cl_chips) + gap * (len(self.cl_chips) - 1)
        x = r.center().x() - total / 2
        y = int(r.bottom() + 18)
        for b in self.cl_chips:
            b.move(int(x), y)
            b.show()
            x += b.width() + gap
        self.cl_in.setFixedWidth(int(r.width()))
        self.cl_in.adjustSize()
        self.cl_in.move(int(r.left()), y + 50)
        self.cl_in.show()
        self.cl_in.setFocus()
        self._ai_place_models()                                  # прячет чипы режимов, они здесь не нужны

    def _cl_ask(self, question):
        """Настоящий вопрос облаку: ответ приходит от реальных моделей, текст появляется по мере генерации."""
        q = " ".join(str(question or "").split())[:300]
        if not q or self._cl_state in ("wait", "stream"):
            return
        self._cl_reset()
        self._cl_q, self._cl_state, self._cl_t0 = q, "wait", self._now()
        token = self._cl_token
        self.cl_in.clear()
        self._blob.set_mood("thinking", 2.5)
        lang = "Answer in English." if i18n.LANG == "en" else "Отвечай по-русски."

        def work():
            try:
                from llm import cloud as cloud_api
                cloud_api.LAST.update(mode="", model="")

                def on_delta(piece):
                    if token == self._cl_token:
                        self._cl_text += piece
                        self._cl_state = "stream"
                text = cloud_api.generate(cloud_api.PROVIDER, cloud_api.get_key(cloud_api.PROVIDER), [
                    {"role": "system", "content": "Ты Mico, дружелюбный помощник на рабочем столе. " + lang + " Отвечай коротко: до четырёх предложений, без списков."},
                    {"role": "user", "content": q}], model="auto", on_delta=on_delta)
                if token == self._cl_token:
                    self._cl_text = text
                    self._cl_model = cloud_api.LAST.get("model", "")
                    self._cl_tier = cloud_api.LAST.get("mode", "")
                    self._cl_dt = self._now() - self._cl_t0
                    self._cl_state = "done"
                    self._cl_react = True                          # реакцию Mico выполнит главный поток (в _tick)
            except Exception as e:
                if token == self._cl_token:
                    self._cl_err = str(e) or "Облако не ответило."
                    self._cl_state = "error"
        threading.Thread(target=work, daemon=True).start()

    def _cl_done_react(self):
        if self.scene != S_CLOUD:
            return
        self._blob.jump(200)
        name = self._cl_model or "облако Mico"
        self._say(i18n.t("Ответила модель") + " " + name + "! " + i18n.t("Попробуй другой вопрос: например, про код или стихи."), "happy", 3)

    def _cl_prepare(self, W, H):
        """Всё тяжёлое для вступления считаем один раз: траектории частиц и контуры букв. Тогда кадр рисуется быстро и плавно."""
        key = (W, H)
        if getattr(self, "_cl_cache_key", None) == key:
            return
        self._cl_cache_key = key
        rnd = random.Random(5)
        self._cl_parts = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(.55, .95) * max(W, H), 110 + rnd.uniform(-14, 22),
                           rnd.uniform(0, .5), 1.4 + 2.2 * (i % 3 == 0), i % 4, 1 if i % 2 else -1) for i in range(64)]
        title = "MICO CLOUD"
        f = QFont(theme.FONT_DISPLAY)
        f.setPixelSize(int(min(88, W * .07)))
        f.setWeight(QFont.Weight.Bold)
        fm = QFontMetricsF(f)
        gap = 9.0
        total = sum(fm.horizontalAdvance(ch) + gap for ch in title) - gap
        x = -total / 2
        letters = []
        for ch in title:
            path = QPainterPath()
            if ch != " ":
                path.addText(QPointF(0, 0), f, ch)
            letters.append((path, x))
            x += fm.horizontalAdvance(ch) + gap
        self._cl_letters, self._cl_total, self._cl_asc, self._cl_h = letters, total, fm.ascent(), fm.height()

    def _paint_cloud_intro(self, p, t):
        """Вступление Mico Cloud: вспышка, расходящиеся кольца, технологичная сетка, частицы слетаются в центр, название
        собирается по буквам с бегущим бликом, а под ним: «абсолютно новое технологичное решение». Потом всё плавно растворяется в карточке."""
        ti = t - getattr(self, "_cl_i0", -99.0)
        if ti < 0 or ti > 3.7:
            return
        W, H = self.width(), self.height()
        self._cl_prepare(W, H)
        r = self._card_rect(*CLOUD_CARD)
        c = r.center()
        fo = 1.0 - _io(_clamp((ti - 2.3) / 1.1))                  # к концу вступления всё мягко тает
        pal = (QColor(122, 215, 255), QColor(185, 162, 255), QColor(255, 179, 217), QColor(143, 240, 176))
        p.save()
        # мягкое свечение в центре
        gl = QRadialGradient(c, max(W, H) * .42)
        gl.setColorAt(0, QColor(150, 140, 255, int(86 * fo * _clamp(ti / .6))))
        gl.setColorAt(1, QColor(150, 140, 255, 0))
        p.fillRect(self.rect(), QBrush(gl))
        # сетка внутри расширяющегося окна
        ext = _io(_clamp(ti / 1.5)) * max(W, H) * .55
        p.setClipRect(QRectF(c.x() - ext, c.y() - ext * .72, ext * 2, ext * 1.44))
        p.setPen(QPen(QColor(122, 215, 255, int(30 * fo)), 1))
        step = 48
        off = (ti * 36) % step
        x = c.x() - ext - off
        while x < c.x() + ext + step:
            p.drawLine(QPointF(x, c.y() - ext), QPointF(x, c.y() + ext))
            x += step
        y = c.y() - ext * .72 - off * .6
        while y < c.y() + ext * .72 + step:
            p.drawLine(QPointF(c.x() - ext, y), QPointF(c.x() + ext, y))
            y += step
        p.setClipping(False)
        # кольца ударной волны
        for k, t0 in enumerate((0.15, 0.6, 1.05)):
            a = (ti - t0) / 1.5
            if 0 <= a <= 1:
                col = QColor(pal[k % 4])
                col.setAlpha(int(170 * (1 - a) * fo))
                p.setPen(QPen(col, 2.4 * (1 - a) + .6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                rr = _out(a) * max(W, H) * .5
                p.drawEllipse(c, rr, rr * .72)
        # частицы слетаются в кольцо вокруг центра
        p.setPen(Qt.PenStyle.NoPen)
        for ang, far, tgt, delay, sz, ci, spin in self._cl_parts:
            e = _io(_clamp((ti - delay) / 1.2))
            rr = far + (tgt - far) * e
            a2 = ang + e * 2.4 + ti * .5 * spin * e
            col = QColor(pal[ci])
            col.setAlpha(int((60 + 170 * e) * fo))
            p.setBrush(col)
            p.drawEllipse(QPointF(c.x() + math.cos(a2) * rr, c.y() + math.sin(a2) * rr * .72), sz, sz)
        # название по буквам
        base = c.y() + self._cl_asc * .32
        gx = QLinearGradient(c.x() - self._cl_total / 2, 0, c.x() + self._cl_total / 2, 0)
        gx.setColorAt(0, QColor(122, 215, 255))
        gx.setColorAt(.5, QColor(185, 162, 255))
        gx.setColorAt(1, QColor(255, 179, 217))
        brush = QBrush(gx)
        done = _clamp((ti - .5) / 1.2)
        tg = QRadialGradient(QPointF(c.x(), base - self._cl_asc * .3), self._cl_total * .55)
        tg.setColorAt(0, QColor(185, 162, 255, int(90 * done * fo)))
        tg.setColorAt(1, QColor(185, 162, 255, 0))
        p.fillRect(QRectF(c.x() - self._cl_total, base - self._cl_asc * 2, self._cl_total * 2, self._cl_asc * 4), QBrush(tg))
        for i, (path, lx) in enumerate(self._cl_letters):
            la = _clamp((ti - 0.5 - i * .09) / .34)
            if la <= 0 or path.isEmpty():
                continue
            p.save()
            p.setOpacity(la * fo)
            p.translate(c.x() + lx, base + (1 - _out(la)) * 24)
            p.fillPath(path, brush)
            p.restore()
        sweep = (ti - 1.5) / .9
        if 0 <= sweep <= 1:                                         # блик пробегает по названию
            sx = c.x() - self._cl_total / 2 - 40 + (self._cl_total + 80) * _io(sweep)
            g = QLinearGradient(sx - 50, 0, sx + 50, 0)
            g.setColorAt(0, QColor(255, 255, 255, 0))
            g.setColorAt(.5, QColor(255, 255, 255, int(190 * fo)))
            g.setColorAt(1, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(sx - 50, base - self._cl_asc, 100, self._cl_h), QBrush(g))
        if ti > 1.5 and not getattr(self, "_cl_burst", True):
            self._cl_burst = True
            self._burst(c.x(), c.y(), 36, rainbow=True)
        sa = _io(_clamp((ti - 1.35) / .6)) * fo
        if sa > 0:
            p.setFont(self._font(15, True))
            sub = i18n.t("АБСОЛЮТНО НОВОЕ ТЕХНОЛОГИЧНОЕ РЕШЕНИЕ")
            p.setPen(QColor(220, 210, 255, int(220 * sa)))
            p.drawText(QRectF(c.x() - 460, base + 26, 920, 30), self._flags(Qt.TextFlag.TextSingleLine, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter), " ".join(sub))
            lw = 380 * _out(_clamp((ti - 1.5) / .8))
            p.setPen(QPen(QColor(185, 162, 255, int(200 * sa)), 2))
            p.drawLine(QPointF(c.x() - lw / 2, base + 64), QPointF(c.x() + lw / 2, base + 64))
        p.restore()

    def _paint_cloud(self, p, t):
        r = self._card_rect(*CLOUD_CARD)
        u = t - getattr(self, "_cl_i0", self._card_t) - 2.3
        if u < 0:
            return
        acc, text, muted = QColor(self.color), self.pal["text"], self.pal["muted"]
        ink = QColor(theme.on_accent(self.color))
        k = _io(_clamp(u / .9))
        p.save()
        p.setOpacity(_io(_clamp(u / .7)))
        c = r.center()
        p.translate(c)
        p.scale(.93 + .07 * k, .93 + .07 * k)
        p.translate(-c)
        gl = QRadialGradient(QPointF(r.center().x(), r.top()), r.width() * .8)
        g0 = QColor(acc)
        g0.setAlpha(60)
        gl.setColorAt(0, g0)
        g0.setAlpha(0)
        gl.setColorAt(1, g0)
        p.fillRect(r.adjusted(-90, -70, 90, 80), QBrush(gl))
        self._panel(p, r, edge=_mixc(self.pal["stroke"], self.color, .55).name(), radius=24)
        # шапка
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawEllipse(QPointF(r.left() + 34, r.top() + 34), 13, 13)
        spark = QPainterPath()
        for i in range(8):
            a_ = math.pi / 4 * i - math.pi / 2 + t * .6
            rr = 7.0 if i % 2 == 0 else 2.6
            pt = QPointF(r.left() + 34 + math.cos(a_) * rr, r.top() + 34 + math.sin(a_) * rr)
            spark.moveTo(pt) if i == 0 else spark.lineTo(pt)
        spark.closeSubpath()
        p.setBrush(ink)
        p.drawPath(spark)
        self._text(p, r.left() + 56, r.top() + 41, "Mico Cloud", 19, text, True)
        bw = 156
        p.setBrush(QColor(acc.red(), acc.green(), acc.blue(), 40))
        p.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 140), 1))
        p.drawRoundedRect(QRectF(r.right() - 22 - bw, r.top() + 22, bw, 22), 11, 11)
        self._text(p, r.right() - 22 - bw, r.top() + 38, i18n.t("НОВЫЙ ШАГ В БУДУЩЕЕ"), 10, self.color, True, Qt.AlignmentFlag.AlignHCenter, bw)
        p.setFont(self._font(12.5))
        p.setPen(QColor(muted))
        p.drawText(QRectF(r.left() + 22, r.top() + 58, r.width() - 44, 36), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop),
                   i18n.t("16 лучших моделей в трёх уровнях: Mico сам выбирает, кому отдать твой вопрос. Ключи не нужны."))
        # четыре модели; та, что отвечает или ответила, подсвечена и дышит
        tier = self._cl_tier
        active = {"lite": "Lite", "plus": "Plus", "max": "Max"}.get(tier, "")
        wait = self._cl_state in ("wait", "stream")
        cw = (r.width() - 44 - 10) / 2
        for i, (name, role, col) in enumerate(CLOUD_MODELS):
            x = r.left() + 22 + (i % 2) * (cw + 10)
            y = r.top() + 102 + (i // 2) * 44
            on = name == active
            pulse = .5 + .5 * math.sin(t * 6 + i) if wait else 0.0
            cc = QColor(col)
            box = QRectF(x, y, cw, 36)
            pk = _clamp((u - .25 - i * .12) / .45)                    # модели выскакивают по очереди
            p.save()
            p.translate(box.center())
            p.scale(max(.01, _back(pk)), max(.01, _back(pk)))
            p.translate(-box.center())
            p.setOpacity(_clamp(u / .35) * _clamp(pk * 2.5))
            p.setPen(QPen(QColor(cc.red(), cc.green(), cc.blue(), int(70 + 185 * (1.0 if on else pulse * .8))), 1.4 if on else 1.0))
            fill = QColor(cc.red(), cc.green(), cc.blue(), int(18 + 46 * (1.0 if on else pulse * .5)))
            p.setBrush(fill)
            p.drawRoundedRect(box, 12, 12)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(cc)
            p.drawEllipse(QPointF(x + 16, y + 18), 5 + (1.5 * pulse if wait else 0), 5 + (1.5 * pulse if wait else 0))
            self._text(p, x + 30, y + 17, i18n.t(name), 13, text, True, w=cw - 36)
            self._text(p, x + 30, y + 32, i18n.t(role), 11, muted, w=cw - 36)
            p.restore()
        # беседа
        area = QRectF(r.left() + 22, r.top() + 198, r.width() - 44, r.height() - 198 - 36)
        from llm import cloud as cloud_api
        qs = cloud_api.quota_summary() or i18n.t("Считаю остаток нейронов…")
        p.setFont(self._font(11))
        p.setPen(QColor(muted))
        p.drawText(QRectF(r.left() + 22, r.bottom() - 30, r.width() - 44, 24), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter), qs)
        if self._cl_state == "idle":
            p.setFont(self._font(13))
            p.setPen(QColor(muted))
            p.drawText(area, self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignVCenter),
                       i18n.t("Выбери вопрос ниже или напиши свой. Ответ придёт от настоящих моделей, не заготовкой."))
            p.restore()
            return
        fq = self._font(13)
        p.setFont(fq)
        fm = QFontMetrics(fq)
        qr = fm.boundingRect(QRect(0, 0, int(area.width() * .78), 400), int(Qt.TextFlag.TextWordWrap.value), self._cl_q)
        qb = QRectF(area.right() - qr.width() - 26, area.top(), qr.width() + 26, qr.height() + 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawRoundedRect(qb, 14, 14)
        p.setPen(ink)
        p.drawText(qb.adjusted(13, 8, -13, -8), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), self._cl_q)
        ab = QRectF(area.left(), qb.bottom() + 10, area.width(), area.bottom() - qb.bottom() - 10)
        p.setPen(QPen(QColor(self.pal["stroke"]), 1))
        p.setBrush(QColor(self.pal["hover"]))
        p.drawRoundedRect(ab, 14, 14)
        if self._cl_state == "wait":
            for j in range(3):
                dy = -4 * max(0.0, math.sin(t * 7 - j * .7))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(acc)
                p.drawEllipse(QPointF(ab.left() + 26 + j * 14, ab.top() + 24 + dy), 4, 4)
            p.setFont(self._font(11.5))
            p.setPen(QColor(muted))
            p.drawText(QRectF(ab.left() + 72, ab.top() + 12, ab.width() - 84, 24), int(Qt.AlignmentFlag.AlignVCenter.value), i18n.t("Выбираю модель…"))
        elif self._cl_state == "error":
            p.setFont(self._font(12.5))
            p.setPen(QColor(229, 115, 124))
            p.drawText(ab.adjusted(14, 10, -14, -10), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), self._cl_err)
        else:
            p.setFont(self._font(13))
            p.setPen(QColor(text))
            foot = 22 if self._cl_state == "done" else 0
            p.drawText(ab.adjusted(14, 10, -14, -10 - foot), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), self._cl_text + ("▍" if self._cl_state == "stream" and int(t * 3) % 2 == 0 else ""))
            if self._cl_state == "done":
                tier_name = {"lite": "Lite", "plus": "Plus", "max": "Max"}.get(self._cl_tier, "")
                self._text(p, ab.left() + 14, ab.bottom() - 7, "✓ " + (self._cl_model or "Mico Cloud") + (" · " + tier_name if tier_name else "") + " · " + ("%.1f" % self._cl_dt).replace(".", ",") + " " + i18n.t("с"), 11.5, self.color, True, w=ab.width() - 28)
        p.restore()

    # ---------- сцена «Как мне отвечать» ----------
    def _ai_layout(self):
        W, H = self.width(), self.height()
        cw = 480
        cx = max(W * .62, self._mico_stage_x() + self.MICO * .5 + 40 + cw / 2)
        cx = min(cx, W - cw / 2 - 30)
        top = max(110.0, H * .40 - 160)
        r1 = QRectF(cx - cw / 2, top + 46, cw, 118)
        r2 = QRectF(cx - cw / 2, r1.bottom() + 16, cw, 118)
        return top, r1, r2, cx

    def _ai_show(self):
        from ui import motion
        top, r1, r2, cx = self._ai_layout()
        self.ai_cloud.move(int(r1.left()), int(r1.top()))          # облако Mico — рекомендованный вариант, он сверху
        self.ai_local.move(int(r2.left()), int(r2.top()))
        for i, w in enumerate((self.ai_cloud, self.ai_local)):
            w.show()
            motion.fade_slide_in(w, dy=16, ms=480, delay=140 * i)
        self.ai_local.set_selected(self._ai == "local", animate=False)
        self.ai_cloud.set_selected(self._ai == "mico", animate=False)
        self._ai_apply(self._ai, say=False)

    def _ai_pick(self, kind):
        if kind == self._ai:
            return
        self._ai_apply(kind, say=True)

    def _ai_apply(self, kind, say):
        if kind == "local" and not ModelPillLocal.available():
            kind = "mico"                                     # локальной модели на ПК нет: остаёмся на облаке и честно говорим об этом
            if say:
                self._say("Локальная модель ещё не скачана, поэтому пока я отвечаю через облако Mico.", "curious", 3)
                say = False
        self._ai = kind
        self.cfg["llm_backend"] = kind
        self.ai_local.set_selected(kind == "local")
        self.ai_cloud.set_selected(kind == "mico")
        if kind == "mico":
            from llm import cloud as cloud_api
            self.cfg["cloud_model"] = cloud_api.normalize_mode(self.cfg.get("cloud_model"))
            self._ai_load_models()
        self._ai_place_models()
        if say:
            self._blob.jump(220)
            if kind == "local":
                self._say("Буду думать прямо на твоём ПК — всё останется у тебя.", "happy", 3)
            else:
                self._say("Отвечаю через облако Mico: быстро и без нагрузки на твой компьютер.", "happy", 3)

    def _ai_load_models(self):
        """Режимы облака зашиты в программу: ждать сети не нужно, плитки режимов появляются сразу."""
        from llm import cloud as cloud_api
        self._ai_models = list(cloud_api.MODE_IDS)

    def _ai_place_models(self):
        """Под карточками — выбор режима облака (Авто, Быстро, Умнее), если выбрано облако Mico."""
        for b in self.ai_chips:
            b.hide()
        if self.scene != S_AI or self._ai != "mico" or not self._ai_models:
            return
        top, r1, r2, cx = self._ai_layout()
        cur = str(self.cfg.get("cloud_model") or "")
        x0, y = r2.left(), r2.bottom() + 14
        x = x0
        for i, m in enumerate(self._ai_models[:5]):
            b = self.ai_chips[i]
            from llm import cloud as cloud_api
            b.setText(i18n.t(cloud_api.mode_label(m)))
            b.setProperty("done", str(m) == cur)
            b.adjustSize()
            if x + b.width() > r2.right() + 4 and x > x0:
                x, y = x0, y + b.height() + 8
            b.move(int(x), int(y))
            b.show()
            b.update()
            x += b.width() + 8

    def _ai_model_pick(self, i):
        if i < len(self._ai_models):
            self.cfg["cloud_model"] = self._ai_models[i]
            self._blob.jump(160)
            self._ai_place_models()

    def _paint_ai(self, p, t):
        top, r1, r2, cx = self._ai_layout()
        text, muted = self.pal["text"], self.pal["muted"]
        self._text(p, r1.left() + 4, top + 28, i18n.t("Как мне отвечать?"), 22, "#ffffff", True, w=r1.width())
        if self._ai == "mico":
            note = i18n.t("Режим «Авто» сам берёт быструю модель для простого и умную для сложного. Сменить можно в чате.")
        else:
            note = i18n.t("Если передумаешь, переключиться на облако можно в чате в любой момент.")
        ny = r2.bottom() + (14 + (46 if (self._ai == "mico" and self._ai_models) else 0) + 28)
        p.setFont(self._font(12))
        p.setPen(QColor(255, 255, 255, 150))
        p.drawText(QRectF(r1.left() + 4, ny, r1.width() - 8, 40), self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), note)

    # ---------- сцена агента: появление, примеры, предложение включить ----------
    def _ag_play(self):
        """Вступление закончилось: Mico уходит влево, под карточкой — примеры, внизу — предложение включить агента."""
        if self.scene != S_AGENT or self._ag_phase != "reveal":
            return
        W, H = self.width(), self.height()
        self._ag_phase, self._ag_play_t = "play", self._now()
        self._fly(self._mico_stage_x(), H * .40, 800, arc=-120, size=self.MICO)
        self._say("Нажимай на примеры — это тренировка, ничего не отправится. А давай сразу включим агента?", "happy", 3)
        self._place_ag_chips()
        self._place_offer()
        self._ag_auto, self._ag_seen = True, 0
        QTimer.singleShot(2600, self._ag_auto_next)

    def _place_ag_chips(self):
        """Четыре плитки-примера под карточкой агента: в один ряд, а на узком экране два на два."""
        W, H = self.width(), self.height()
        r = self._card_rect(440, 320)
        gap = 12
        tw, th = self.ag_chips[0].width(), self.ag_chips[0].height()
        one_row = 4 * tw + 3 * gap <= W - 60
        cols = 4 if one_row else 2
        rows = 1 if one_row else 2
        total_w = cols * tw + (cols - 1) * gap
        x0 = r.center().x() - total_w / 2
        y0 = min(r.bottom() + 26, H - 130 - rows * th - (rows - 1) * gap)
        from ui import motion
        for i, b in enumerate(self.ag_chips):
            col, row = i % cols, i // cols
            b.move(int(x0 + col * (tw + gap)), int(y0 + row * (th + gap)))
            b.setEnabled(True)
            b.show()
            motion.fade_slide_in(b, dy=14, ms=420, delay=110 * i)

    def _place_offer(self):
        """«Назад», «Пока не надо» и «Включить агента» — одним рядом по центру, все три одного размера."""
        W, H = self.width(), self.height()
        btns = [self.back, self.ag_off, self.ag_on]
        for b in btns:
            b.adjustSize()
        bw, bh = max(160, max(b.width() for b in btns)), 46
        gap = 14
        total = bw * len(btns) + gap * (len(btns) - 1)
        x = W / 2 - total / 2
        from ui import motion
        for b in btns:
            b.setFixedSize(bw, bh)
            b.move(int(x), int(H - 112))
            b.show()
            x += bw + gap
        for b in btns:
            motion.fade_slide_in(b, dy=8, ms=420)

    def _start_example(self, i, auto=False):
        if self.scene != S_AGENT or self._ag_phase != "play" or (self._agent in ("run", "ask")):
            return
        if not auto:
            self._ag_auto = False                           # человек сам нажал на пример — автопоказ выключается
        for j, tile_w in enumerate(self.ag_chips):
            tile_w.set_selected(j == i)
        self._ag_cur = i
        self._ex = AGENT_EXAMPLES[i]
        self._agent, self._agent_t = "run", self._now()
        self.yes.hide()
        self.no.hide()
        for b in self.ag_chips:
            b.setEnabled(False)
        self._blob.set_mood("thinking", 3)
        self._blob.jump(220)
        self._say(i18n.t("Смотри, как я это делаю") + ": «" + i18n.t(self._ex["ask"]) + "»", "thinking", 3)

    def _ag_auto_next(self):
        """Автопоказ: пока человек ничего не нажал, агент сам по очереди показывает свои примеры (один круг)."""
        if not self._ag_auto or self.scene != S_AGENT or self._ag_phase != "play" or self._agent in ("run", "ask"):
            return
        if self._ag_seen >= len(AGENT_EXAMPLES):
            self._ag_auto = False
            return
        i = self._ag_seen
        self._ag_seen += 1
        self._start_example(i, auto=True)

    def _ag_examples_done(self):
        for b in self.ag_chips:
            b.setEnabled(True)

    def _ag_enable(self, on):
        """Предложение включить агента: «Включить» сразу меняет настройку, «Пока не надо» оставляет как есть."""
        self._offer_done = True
        self.ag_on.hide()
        self.ag_off.hide()
        if on:
            self.cfg["agent_mode"] = True
            self._say("Агент включён! Перед отправкой, оплатой и удалением я всегда спрошу твоё «да».", "love", 3)
            self._burst(self._mp.x(), self._mp.y(), 26)
            self._blob.jump(320)
        else:
            self._say("Хорошо. Включить агента можно в любой момент: ⚙ Настройки → «Агент».", "happy", 3)
        self._place_next("Дальше")

    def _listen(self):
        if self._now() - self._listen_t < 4.5:
            return
        self._listen_t = self._now()
        self._blob.set_listening(True)
        self._say("Слушаю…", "curious", 2)

        def answer():
            if self.scene != S_VOICE:
                return
            self._blob.set_listening(False)
            self._blob.set_speaking(True)
            self._say("Слышу тебя! Так работает голосовой режим: я отвечаю голосом, а твои слова появляются на экране, пока ты говоришь.", "happy", 3)
            QTimer.singleShot(3200, lambda: self._blob.set_speaking(False))
            if not self.next.isVisible():
                self._place_next("Дальше")
        QTimer.singleShot(1900, answer)

    # ---------- кадр ----------
    def _tick(self):
        now = time.monotonic()
        dt = min(0.05, now - self._last)
        self._last = now
        t = self._now()
        k = 1 - math.pow(0.002, dt)
        if self._move is not None:
            p0, p1, arc, t0, d = self._move
            e = _io((t - t0) / d)
            cx, cy = (p0.x() + p1.x()) / 2, min(p0.y(), p1.y()) + arc
            x = (1 - e) ** 2 * p0.x() + 2 * (1 - e) * e * cx + e * e * p1.x()
            y = (1 - e) ** 2 * p0.y() + 2 * (1 - e) * e * cy + e * e * p1.y()
            self._lean += (_clamp((x - self._mp.x()) * 1.3, -16, 16) - self._lean) * min(1.0, dt * 10)
            self._trail.append((x, y, t))
            self._mp = QPointF(x, y)
            if t - t0 >= d:
                self._move = None
                self._land_t = t
        else:
            self._lean += -self._lean * min(1.0, dt * 6)
        self._trail = [q for q in self._trail if t - q[2] < .32]
        self._size += (self._size_to - self._size) * k
        try:                                            # Mico смотрит на курсор: блоб стоит там же, где его рисунок
            bw, bh = self._blob.width(), self._blob.height()
            self._blob.move(self.mapToGlobal(QPoint(int(self._mp.x() - bw / 2), int(self._mp.y() - bh / 2))))
            self._blob.set_look(QCursor.pos())
        except Exception:
            pass
        self._blob.tick()
        pix = QPixmap(self._blob.width(), self._blob.height())
        pix.fill(Qt.GlobalColor.transparent)
        self._blob.render(pix)
        self._pix = pix
        for s in self._sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 900 * dt
            s[2] *= math.pow(0.4, dt)
            s[4] += s[5] * dt
            s[6] -= dt * .7
        self._sparks = [s for s in self._sparks if s[6] > 0]
        if self.scene == S_WINTER:
            self._sw_tick(t)
        if getattr(self, "_cl_react", False):
            self._cl_react = False
            self._cl_done_react()
        if self.scene == 0 and self._hint:
            self._hint_step(t)                           # палец касается Mico, а он отзывается
        if self._ag_auto and self.scene == S_AGENT:       # автопоказ: сам отвечает «да» и переходит к следующему примеру
            if self._agent == "ask" and t - self._ag_ask_t > 1.9:
                self._ag_end_t = t
                self._agent_answer(True)
            elif self._agent in ("sent", "no", "done") and self._ag_end_t and t - self._ag_end_t > 2.9:
                self._ag_end_t = 0.0
                self._ag_auto_next()
        if self.scene == 1:                              # шарики цвета держатся дугой под Mico и догоняют его
            n = len(self._swatches)
            R = self.MICO * .98
            for j, b in enumerate(self._swatches.values()):
                a = math.radians(160 - j * 140 / (n - 1))
                u = _back((t - self._swatch_t - j * .06) / .5)
                tx, ty = self._mp.x() + math.cos(a) * R, self._mp.y() + math.sin(a) * R * .82 + 40
                x = self._mp.x() + (tx - self._mp.x()) * u
                y = self._mp.y() + (ty - self._mp.y()) * u + 3 * math.sin(t * 2.2 + j)
                b.move(int(x - 27), int(y - 27))
        if self.scene == S_AGENT and self._ag_phase == "play" and self._agent == "run" and self._ex is not None:
            ex = self._ex
            if t - self._agent_t > 1.6 + len(ex["steps"]) * .9 + .9:
                if ex.get("q"):                          # нужно «да»: кнопки встают точно в строку вопроса
                    self._agent = "ask"
                    self._ag_ask_t = t
                    self._place_yes_no()
                    self._blob.set_mood("curious", 3)
                else:                                    # без вопроса: готово
                    self._agent, self._agent_t2 = "done", t
                    self._ag_end_t = t
                    self._say(ex["say_done"], "proud", 3)
                    self._blob.jump(280)
                    r = self._card_rect(440, 320)
                    self._burst(r.center().x(), r.bottom() - 40, 18)
                    self._ag_examples_done()
        self.update()

    # ---------- рисование ----------
    @staticmethod
    def _flags(*items):
        out = 0
        for f in items:
            out |= int(f.value)
        return out

    def _font(self, px, bold=False):
        f = QFont(theme.FONT_DISPLAY if bold else theme.FONT_FAMILY)
        f.setPixelSize(int(px))
        if bold:
            f.setWeight(QFont.Weight.DemiBold)
        return f

    def _text(self, p, x, y, text, px, color, bold=False, align=None, w=600):
        p.setFont(self._font(px, bold))
        p.setPen(QColor(color))
        al = align or Qt.AlignmentFlag.AlignLeft
        p.drawText(QRectF(x, y - px, w, px * 1.6), self._flags(al, Qt.AlignmentFlag.AlignVCenter), text)

    def _panel(self, p, r, fill=None, edge=None, radius=20):
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path.translated(0, 10), QColor(0, 0, 0, 70))
        p.fillPath(path, QColor(fill or self.pal["card"]))
        p.setPen(QPen(QColor(edge or self.pal["stroke"]), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def _paint_glow(self, p, W, H, t):
        """Сияние в цветах Mico. Рисуется в маленькую картинку раз в 60 мс и растягивается: на весь экран так не тормозит."""
        if self._glow is None or t - self._glow_t > .06:
            gw, gh = max(1, W // 4), max(1, H // 4)
            img = QPixmap(gw, gh)
            img.fill(Qt.GlobalColor.transparent)
            q = QPainter(img)
            for i, col in enumerate((self.color, "#FFB3C6", "#B8C0FF", "#9FD3FF")):
                if i == 0:                               # главное пятно идёт за Mico
                    gx, gy, r = self._mp.x() / 4, self._mp.y() / 4, max(gw, gh) * .4
                else:
                    ph = i * 1.9
                    gx, gy = gw * (.5 + .42 * math.sin(t * .17 + ph)), gh * (.5 + .38 * math.cos(t * .21 + ph))
                    r = max(gw, gh) * .36
                g = QRadialGradient(QPointF(gx, gy), r)
                c0, c1 = QColor(col), QColor(col)
                c0.setAlpha(120 if i == 0 else 64)
                c1.setAlpha(0)
                g.setColorAt(0, c0)
                g.setColorAt(1, c1)
                q.fillRect(img.rect(), QBrush(g))
            q.end()
            self._glow, self._glow_t = img, t
        p.drawPixmap(self.rect(), self._glow)

    def _paint_mico(self, p, t):
        if self._pix is None:
            return
        for x, y, tt in self._trail:                     # след в полёте
            a = 1 - (t - tt) / .32
            c = QColor(self.color)
            c.setAlpha(int(70 * a))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y), self._size * .2 * a, self._size * .2 * a)
        s = self._size / self.MICO
        lt = t - self._land_t
        sq = math.sin(lt * 18) * math.exp(-lt * 6) * .12 if 0 <= lt < 1.2 else 0.0   # пружинка после посадки
        foot = self._mp.y() + self._size * .36
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(QPointF(self._mp.x(), foot + 6), self._size * .26, self._size * .045)
        p.save()
        p.translate(self._mp.x(), foot)
        p.rotate(self._lean)
        p.scale(s * (1 + sq), s * (1 - sq))
        pw, ph = self._pix.width(), self._pix.height()
        p.drawPixmap(QPointF(-pw / 2, -ph * .86), self._pix)
        p.restore()

    def _paint_bubble(self, p, W, H, t):
        if not self._say_full:
            return
        n = int((t - self._say_t) * 55)
        text = self._say_full[:max(0, n)]
        if not text:
            return
        f = self._font(16)
        fm = QFontMetrics(f)
        maxw = 380
        flags = self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop)   # те же флаги, что при рисовании
        br = fm.boundingRect(QRect(0, 0, maxw, 2000), flags, self._say_full)
        bw, bh = br.width() + 40 + 14, br.height() + 30 + 12        # запас: раньше последняя строка не влезала и обрезалась
        mx, my, ms = self._mp.x(), self._mp.y(), self._size
        right = mx < W * .6
        bx = mx + ms * .5 if right else mx - ms * .5 - bw
        by = my - ms * .62 - bh * .3
        limit = W - 20.0
        if self.scene in (S_PRACTICE, S_AI, S_CLOUD) or (self.scene == S_AGENT and self._ag_phase == "play"):   # справа карточка (демо или агент): облачко держится левее её края
            limit = (self._ai_layout()[1].left() if self.scene == S_AI else self._card_rect(*(CLOUD_CARD if self.scene == S_CLOUD else (440, 320))).left()) - 24
            if my - ms * .55 - bh - 14 >= 70:          # места хватает — облачко над головой Mico
                bx, by = mx - bw / 2, my - ms * .55 - bh - 14
            else:
                by = my + ms * .5 - bh * .1
        bx = max(20.0, min(limit - bw, bx))
        by = max(70.0, min(H - bh - 20.0, by))
        k = _back((t - self._say_t) / .38)
        ax = bx if right else bx + bw
        ay = by + bh * .72
        p.save()
        p.translate(ax, ay)
        p.scale(.6 + .4 * k, .6 + .4 * k)
        p.translate(-ax, -ay)
        p.setOpacity(_clamp((t - self._say_t) / .2))
        path = QPainterPath()
        path.addRoundedRect(QRectF(bx, by, bw, bh), 18, 18)
        tail = QPainterPath()
        if right:
            tail.moveTo(bx + 4, by + bh * .5)
            tail.lineTo(bx - 16, by + bh * .92)
            tail.lineTo(bx + 22, by + bh * .78)
        else:
            tail.moveTo(bx + bw - 4, by + bh * .5)
            tail.lineTo(bx + bw + 16, by + bh * .92)
            tail.lineTo(bx + bw - 22, by + bh * .78)
        tail.closeSubpath()
        path = path.united(tail)
        p.fillPath(path.translated(0, 8), QColor(0, 0, 0, 80))
        p.fillPath(path, QColor(self.pal["card"]))
        p.setPen(QPen(QColor(self.color), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setFont(f)
        p.setPen(QColor(self.pal["text"]))
        p.drawText(QRectF(bx + 20, by + 15, bw - 40, bh - 30),
                   self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), text)
        p.restore()

    def _paint_demo(self, p, t):
        kind = self._demo
        u = t - self._demo_t
        r = self._card_rect(400, 220)
        k = _back(u / .42)
        p.save()
        p.setOpacity(_clamp(u / .25))
        c = r.center()
        p.translate(c)
        p.scale(.88 + .12 * k, .88 + .12 * k)
        p.translate(-c)
        acc, text, muted = QColor(self.color), self.pal["text"], self.pal["muted"]
        if kind == "dark":                               # окно перетекает из светлой темы в тёмную
            e = _io((u - .35) / .8)
            bg, bar, line, ink = (_mixc("#ffffff", "#202020", e), _mixc("#f0f0f0", "#2b2b2b", e),
                                  _mixc("#dddddd", "#3d3d3d", e), _mixc("#1a1a1a", "#ffffff", e))
            self._panel(p, r, bg.name(), _mixc("#e0e0e0", "#3a3a3a", e).name(), 14)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bar)
            p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, r.width() - 2, 34), 13, 13)
            self._text(p, r.left() + 18, r.top() + 24, i18n.t("Персонализация"), 12, ink.name())
            for j in range(3):
                p.setBrush(line)
                p.drawRoundedRect(QRectF(r.left() + 22, r.top() + 58 + j * 22, 180 - j * 40, 9), 4, 4)
            self._text(p, r.left() + 22, r.bottom() - 34, i18n.t("Тёмная тема"), 15, ink.name(), True)
            sw = QRectF(r.right() - 84, r.bottom() - 52, 56, 28)
            p.setBrush(_mixc("#c8c8c8", self.color, e))
            p.drawRoundedRect(sw, 14, 14)
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(QPointF(sw.left() + 14 + 28 * e, sw.center().y()), 10, 10)
        elif kind == "notepad":                          # окно блокнота раскрывается и в нём печатается текст
            self._panel(p, r, "#ffffff" if not self.dark else "#272727", None, 12)
            ink = "#1a1a1a" if not self.dark else "#ffffff"
            self._text(p, r.left() + 16, r.top() + 24, i18n.t("Безымянный — Блокнот"), 12, muted)
            for j, gl in enumerate(("—", "□", "✕")):
                self._text(p, r.right() - 78 + j * 24, r.top() + 24, gl, 12, muted)
            p.setPen(QPen(QColor(self.pal["stroke"]), 1))
            p.drawLine(QPointF(r.left(), r.top() + 40), QPointF(r.right(), r.top() + 40))
            msg = i18n.t("Привет! Это Mico. Я открыл блокнот по твоей просьбе.")
            shown = msg[:max(0, int((u - .55) * 26))]
            if int(t * 2) % 2:
                shown += "|"
            p.setFont(self._font(15))
            p.setPen(QColor(ink))
            p.drawText(QRectF(r.left() + 18, r.top() + 54, r.width() - 36, r.height() - 70),
                       self._flags(Qt.TextFlag.TextWordWrap, Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignTop), shown)
        else:
            self._panel(p, r, None, None, 20)
            if kind == "volume":                         # ползунок громкости едет с 70% на 30%
                self._text(p, r.left() + 26, r.top() + 42, i18n.t("Громкость"), 17, text, True)
                v = 70 + (30 - 70) * _io((u - .35) / .9)
                y = r.center().y() + 24
                sx = r.left() + 30
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(text))
                path = QPainterPath()
                path.moveTo(sx, y - 7)
                path.lineTo(sx + 9, y - 7)
                path.lineTo(sx + 19, y - 15)
                path.lineTo(sx + 19, y + 15)
                path.lineTo(sx + 9, y + 7)
                path.lineTo(sx, y + 7)
                path.closeSubpath()
                p.drawPath(path)
                pen = QPen(acc, 2.4)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                for rr in (10, 17):
                    p.drawArc(QRectF(sx + 14 - rr, y - rr, rr * 2, rr * 2), -40 * 16, 80 * 16)
                tr = QRectF(sx + 52, y - 4, r.width() - 170, 8)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(self.pal["stroke"]))
                p.drawRoundedRect(tr, 4, 4)
                p.setBrush(acc)
                p.drawRoundedRect(QRectF(tr.left(), tr.top(), tr.width() * v / 100, 8), 4, 4)
                p.setPen(QPen(QColor("#ffffff"), 3))
                p.drawEllipse(QPointF(tr.left() + tr.width() * v / 100, y), 11, 11)
                self._text(p, r.right() - 82, y + 9, f"{int(round(v))}%", 24, text, True)
            elif kind == "timer":                        # кольцо таймера тает, цифры идут вниз
                left = max(0.0, 5 - max(0.0, u - .3))
                self._text(p, r.left() + 26, r.top() + 42, i18n.t("Таймер"), 17, text, True)
                cx, cy, R = r.right() - 110, r.center().y() + 6, 62
                base = QPen(QColor(self.pal["stroke"]), 9)
                base.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(base)
                p.drawEllipse(QPointF(cx, cy), R, R)
                arc = QPen(acc, 9)
                arc.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(arc)
                p.drawArc(QRectF(cx - R, cy - R, 2 * R, 2 * R), 90 * 16, int(left / 5 * 360 * 16))
                num = str(int(math.ceil(left))) if left > 0 else "0"
                p.setFont(self._font(38, True))
                p.setPen(QColor(text))
                p.drawText(QRectF(cx - R, cy - R, 2 * R, 2 * R), self._flags(Qt.AlignmentFlag.AlignCenter), num)
                self._text(p, r.left() + 26, r.center().y() + 30, f"0:0{int(math.ceil(left))}", 30, text, True)
                self._text(p, r.left() + 26, r.bottom() - 30, i18n.t("время вышло!") if left <= 0 else i18n.t("идёт отсчёт…"), 13, muted)
        p.restore()

    def _paint_agent_idle(self, p, t):
        """До выбора примера: карточка агента ждёт — перечень того, что можно попробовать."""
        r = self._card_rect(440, 320)
        u = t - self._ag_play_t
        p.save()
        p.setOpacity(_clamp(u / .6))
        k = _out(u / .7)
        c = r.center()
        p.translate(c)
        p.scale(.95 + .05 * k, .95 + .05 * k)
        p.translate(-c)
        self._panel(p, r)
        acc, text, muted = QColor(self.color), self.pal["text"], self.pal["muted"]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawEllipse(QPointF(r.left() + 30, r.top() + 32), 7, 7)
        self._text(p, r.left() + 46, r.top() + 38, i18n.t("Агент Mico"), 15, text, True)
        self._text(p, r.left() + 26, r.top() + 82, i18n.t("Выбери пример внизу — я покажу, как работаю:"), 13, muted, w=r.width() - 40)
        for j, ex in enumerate(AGENT_EXAMPLES):
            y = r.top() + 130 + j * 46
            pulse = .5 + .5 * math.sin(t * 2.4 + j * .9)
            dot = QColor(self.color)
            dot.setAlpha(int(140 + 100 * pulse))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(dot)
            p.drawEllipse(QPointF(r.left() + 36, y - 4), 6 + 1.5 * pulse, 6 + 1.5 * pulse)
            self._text(p, r.left() + 54, y + 2, "«" + i18n.t(ex["ask"]) + "»", 14, text, w=r.width() - 70)
        p.restore()

    def _paint_reveal_bg(self, p, t):
        """Появление агента: одно мягкое кольцо света от Mico — без лучей, вспышек и радуги."""
        if self._ag_phase != "reveal":
            return
        u = t - self._ag_t0
        age = (u - .9) / 1.6
        if 0 <= age <= 1:
            col = QColor(self.color)
            col.setAlpha(int(90 * (1 - age)))
            p.setPen(QPen(col, 2.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            rr_ = _out(age) * self.MICO * 1.5
            p.drawEllipse(self._mp, rr_, rr_ * .9)

    def _paint_reveal_fg(self, p, t):
        """Название «Режим агента» мягко проявляется над Mico, рядом — небольшая отметка «Новое»; затем всё плавно уезжает наверх."""
        if self._ag_phase is None:
            return
        W, H = self.width(), self.height()
        u = t - self._ag_t0
        tp = _io((t - self._ag_play_t) / .8) if self._ag_phase == "play" else 0.0
        if self._ag_phase == "reveal":
            self._title_y0 = max(96.0, self._mp.y() - self._size * .70)
        y = getattr(self, "_title_y0", 110.0) * (1 - tp) + 82 * tp
        px = 44 - 10 * tp
        fade = _clamp((u - .3) / .8)
        y += (1 - _out((u - .3) / .8)) * 16
        text = i18n.t("Режим агента")
        f = self._font(px, True)
        fm = QFontMetrics(f)
        tw = fm.horizontalAdvance(text)
        pw = 78
        total = tw + 14 + pw
        x0 = W / 2 - total / 2
        p.save()
        p.setOpacity(fade)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, 80))
        p.drawText(QRectF(x0, y - px + 2, tw + 8, px * 1.6), int(Qt.AlignmentFlag.AlignLeft.value), text)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(x0, y - px, tw + 8, px * 1.6), int(Qt.AlignmentFlag.AlignLeft.value), text)
        kb = _out((u - .9) / .6)                            # отметка «Новое» плавно увеличивается
        if kb > 0:
            ph = 26
            bx, by = x0 + tw + 14, y - px * .55
            p.translate(bx + pw / 2, by)
            p.scale(kb, kb)
            p.translate(-(bx + pw / 2), -by)
            p.setOpacity(fade * kb)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(self.color))
            p.drawRoundedRect(QRectF(bx, by - ph / 2, pw, ph), ph / 2, ph / 2)
            p.setFont(self._font(13, True))
            p.setPen(QColor(theme.on_accent(self.color)))
            p.drawText(QRectF(bx, by - ph / 2, pw, ph), int(Qt.AlignmentFlag.AlignCenter.value), "BETA")
        p.restore()

    def _paint_agent(self, p, t):
        r = self._card_rect(440, 320)
        u = t - self._agent_t
        if u < 0:
            return
        acc, text, muted = QColor(self.color), self.pal["text"], self.pal["muted"]
        ink = QColor(theme.on_accent(self.color))
        k = _out(u / .6)
        p.save()
        p.setOpacity(_clamp(u / .4))
        c = r.center()
        p.translate(c)
        p.scale(.95 + .05 * k, .95 + .05 * k)
        p.translate(-c)
        # мягкое свечение под карточкой и сама панель с цветной кромкой
        gl = QRadialGradient(QPointF(r.center().x(), r.bottom() - 40), r.width() * .75)
        g0 = QColor(acc)
        g0.setAlpha(46)
        gl.setColorAt(0, g0)
        g0.setAlpha(0)
        gl.setColorAt(1, g0)
        p.fillRect(r.adjusted(-90, -60, 90, 120), QBrush(gl))
        self._panel(p, r, edge=_mixc(self.pal["stroke"], self.color, .55).name(), radius=24)
        # шапка: значок-искра, название и пометка BETA
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawEllipse(QPointF(r.left() + 34, r.top() + 32), 13, 13)
        spark = QPainterPath()
        for i in range(8):
            a_ = math.pi / 4 * i - math.pi / 2
            rr = 7.0 if i % 2 == 0 else 2.6
            pt = QPointF(r.left() + 34 + math.cos(a_) * rr, r.top() + 32 + math.sin(a_) * rr)
            spark.moveTo(pt) if i == 0 else spark.lineTo(pt)
        spark.closeSubpath()
        p.setBrush(ink)
        p.drawPath(spark)
        self._text(p, r.left() + 56, r.top() + 38, i18n.t("Агент Mico"), 16, text, True)
        bw = 46
        p.setBrush(QColor(acc.red(), acc.green(), acc.blue(), 40))
        p.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 140), 1))
        p.drawRoundedRect(QRectF(r.right() - 24 - bw, r.top() + 22, bw, 20), 10, 10)
        self._text(p, r.right() - 24 - bw, r.top() + 36, "BETA", 11, self.color, True, Qt.AlignmentFlag.AlignHCenter, bw)
        ex = self._ex or AGENT_EXAMPLES[0]
        steps = ex["steps"]
        n = len(steps)
        # полоска общего хода: заполняется по мере выполнения шагов
        done_f = 0.0
        for j in range(n):
            st = 1.6 + j * .9
            done_f += _clamp((u - st) / .65)
        trk = QRectF(r.left() + 24, r.top() + 56, r.width() - 48, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 22))
        p.drawRoundedRect(trk, 1.5, 1.5)
        p.setBrush(acc)
        p.drawRoundedRect(QRectF(trk.left(), trk.top(), trk.width() * (done_f / max(1, n)), trk.height()), 1.5, 1.5)
        # поле команды: текст печатается, мигает курсор, справа кнопка отправки
        box = QRectF(r.left() + 20, r.top() + 70, r.width() - 40, 44)
        p.setBrush(QColor(self.pal["hover"]))
        p.setPen(QPen(QColor(self.pal["stroke"]), 1))
        p.drawRoundedRect(box, 22, 22)
        ask = i18n.t(ex["ask"])
        typed = ask[:max(0, int(u * 26))]
        caret = "|" if (len(typed) < len(ask) or int(t * 2) % 2 == 0) and u < 1.6 else ""
        self._text(p, box.left() + 18, box.center().y() + 7, typed + caret, 14, text, w=box.width() - 70)
        sb = QPointF(box.right() - 22, box.center().y())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(acc)
        p.drawEllipse(sb, 15, 15)
        pl = QPainterPath()
        pl.moveTo(sb.x() - 6, sb.y() - 5.5)
        pl.lineTo(sb.x() + 7, sb.y())
        pl.lineTo(sb.x() - 6, sb.y() + 5.5)
        pl.lineTo(sb.x() - 3, sb.y())
        pl.closeSubpath()
        pen = QPen(ink, 1.7)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(pl)
        # шаги: вертикальная линия соединяет их, активный крутит кольцо, готовый — галочка
        x0 = r.left() + 36
        ys = [r.top() + 146 + j * 36 for j in range(n)]
        for j in range(n - 1):
            st0, st1 = 1.6 + j * .9, 1.6 + (j + 1) * .9
            if u > st0 + .2:
                y0, y1 = ys[j] + 14, ys[j + 1] - 14
                p.setPen(QPen(QColor(255, 255, 255, 28), 2))
                p.drawLine(QPointF(x0, y0), QPointF(x0, y1))
                fill = _clamp((u - (st0 + .65)) / .25)
                if fill > 0:
                    p.setPen(QPen(acc, 2))
                    p.drawLine(QPointF(x0, y0), QPointF(x0, y0 + (y1 - y0) * fill))
        for j, step in enumerate(steps):
            st = 1.6 + j * .9
            if u < st:
                continue
            a = _clamp((u - st) / .3)
            y = ys[j]
            ok = u > st + .65
            p.setOpacity(_clamp(u / .3) * a)
            if ok:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(acc)
                p.drawEllipse(QPointF(x0, y), 11, 11)
                pen = QPen(ink, 2.1)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.drawPolyline(QPolygonF([QPointF(x0 - 4.8, y), QPointF(x0 - 1.4, y + 3.6), QPointF(x0 + 5, y - 3.6)]))
            else:
                p.setPen(QPen(QColor(acc.red(), acc.green(), acc.blue(), 70), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(x0, y), 11, 11)
                sp = QPen(acc, 2.4)
                sp.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(sp)
                p.drawArc(QRectF(x0 - 11, y - 11, 22, 22), int(-t * 300 * 16), 100 * 16)
            self._text(p, x0 + 24 + 10 * (1 - a), y + 6, i18n.t(step), 14, text if ok else muted, ok)
        p.setOpacity(_clamp(u / .3))
        if self._agent in ("ask", "sent", "no", "done"):
            row = QRectF(r.left() + 20, r.top() + 250, r.width() - 40, 40)
            ra = _out((t - (self._ag_ask_t if self._agent == "ask" else self._agent_t2)) / .35)
            p.setOpacity(_clamp(u / .3) * _clamp(ra + .2))
            p.setPen(QPen(acc, 1.3))
            col = QColor(self.color)
            col.setAlpha(30)
            p.setBrush(col)
            p.drawRoundedRect(row, 20, 20)
            good = self._agent in ("sent", "done")
            if self._agent == "ask":
                msg = i18n.t(ex["q"])
            elif good:
                msg = i18n.t(ex["ok"])
            else:
                msg = i18n.t(ex["no"])
            ix = row.left() + 22
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(acc if self._agent != "no" else QColor(229, 115, 124))
            p.drawEllipse(QPointF(ix, row.center().y()), 10, 10)
            pen = QPen(ink if self._agent != "no" else QColor("#ffffff"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            cy_ = row.center().y()
            if self._agent == "ask":
                p.drawLine(QPointF(ix, cy_ - 4), QPointF(ix, cy_ + 1))
                p.drawPoint(QPointF(ix, cy_ + 4.5))
            elif good:
                p.drawPolyline(QPolygonF([QPointF(ix - 4, cy_), QPointF(ix - 1.2, cy_ + 3), QPointF(ix + 4.4, cy_ - 3)]))
            else:
                p.drawLine(QPointF(ix - 3.4, cy_ - 3.4), QPointF(ix + 3.4, cy_ + 3.4))
                p.drawLine(QPointF(ix + 3.4, cy_ - 3.4), QPointF(ix - 3.4, cy_ + 3.4))
            self._text(p, row.left() + 42, row.center().y() + 7, msg, 14, text, self._agent == "ask", w=row.width() - 160 if self._agent == "ask" else row.width() - 52)
            if self._agent == "sent":                    # сообщение улетает вверх
                v = _out((t - self._agent_t2) / .7)
                bx, by = r.right() - 130, row.top() - 10 - 190 * v
                p.setOpacity(1 - _clamp((t - self._agent_t2 - .5) / .5))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(acc)
                p.drawRoundedRect(QRectF(bx, by, 110, 34), 17, 17)
                self._text(p, bx + 18, by + 23, i18n.t(ex.get("fly", "Готово")), 14, theme.on_accent(self.color), True)
        p.restore()

    def _paint_voice(self, p, t):
        u = t - self._listen_t
        listening = 0 <= u < 1.9
        speaking = 1.9 <= u < 5.1
        if not (listening or speaking):
            return
        for j in range(4):                               # волны звука вокруг Mico
            ph = (t * (1.4 if listening else .9) + j / 4) % 1
            R = self._size * .5 + ph * self._size * .75
            c = QColor(self.color)
            c.setAlpha(int(170 * (1 - ph)))
            p.setPen(QPen(c, 3 if listening else 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(self._mp, R, R)
        cx, cy = self.mic.x() + 38, self.mic.y() - 26   # столбики громкости голоса над кнопкой
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        for j in range(9):
            hgt = 6 + 20 * abs(math.sin(t * 9 + j * .8)) * (1 if listening else .5)
            p.drawRoundedRect(QRectF(cx - 40 + j * 9, cy - hgt / 2, 5, hgt), 2.5, 2.5)

    HINT_T = 2.1                                       # длина одного «тыка» пальцем, с

    def _hint_point(self):
        """Куда палец жмёт на Mico: на тело чуть ниже лица, чтобы не закрывать глаза."""
        return QPointF(self._mp.x() + self._size * .07, self._mp.y() + self._size * .14)

    def _hint_phase(self, t):
        T = self.HINT_T
        return int(t / T), (t % T) / T

    def _hint_step(self, t):
        """Каждый раз, когда палец касается Mico, тот отзывается: проседает пружинкой, меняет настроение, от касания идёт круг."""
        idx, u = self._hint_phase(t)
        if u >= .56 and idx != getattr(self, "_hint_done", -1):
            self._hint_done = idx
            tp = self._hint_point()
            self._taps = [(x, y, tt) for x, y, tt in getattr(self, "_taps", []) if t - tt < 1.0] + [(tp.x(), tp.y(), t)]
            self._land_t = t                                # пружинка тела, как после посадки
            self._blob.set_mood(("surprised", "happy", "playful", "laugh")[idx % 4], 1.1)
            self._blob.jump(140)

    def _paint_hint(self, p, t):
        if not self._hint:
            return
        for j in range(3):                               # «нажми на меня»: кольца расходятся от Mico
            ph = (t * .8 + j / 3) % 1
            R = self._size * .48 + ph * self._size * .55
            c = QColor(self.color)
            c.setAlpha(int(110 * (1 - ph)))
            p.setPen(QPen(c, 2.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(self._mp, R, R * .96)
        for x, y, tt in getattr(self, "_taps", []):         # круги от касаний
            a = (t - tt) / .9
            if 0 <= a <= 1:
                c = QColor(255, 255, 255, int(190 * (1 - a)))
                p.setPen(QPen(c, 2.4 * (1 - a) + .6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                rr = 8 + a * self._size * .22
                p.drawEllipse(QPointF(x, y), rr, rr)
        # рука рисуется отдельно, поверх Mico: _paint_hint_hand

    def _paint_hint_hand(self, p, t):
        """Рука с вытянутым пальцем: жёлтая, как человеческая («👆»). Рисуется поверх Mico: сперва подлетает, потом касается его тела
        кончиком пальца, потом отлетает. Кончик пальца считаем по положению значка, чтобы он попадал ровно на тело."""
        if not self._hint:
            return
        idx, u = self._hint_phase(t)
        tip = self._hint_point()
        if u < .56:
            dist, press = (1 - _out(u / .56)) * self._size * .55, 0.0
        elif u < .70:
            dist, press = 0.0, math.sin((u - .56) / .14 * math.pi)       # лёгкое вдавливание в момент касания
        else:
            dist, press = _io((u - .70) / .30) * self._size * .55, 0.0
        alpha = _clamp(u / .15) * (1 - _clamp((u - .88) / .12))
        tilt = -18.0                                                     # рука чуть наклонена влево, как будто тянется справа снизу
        ang = math.radians(tilt)
        px = max(40.0, self._size * .30)                                # размер значка рядом с размером Mico
        tip_dx, tip_dy = 0.0, -px * .46                                  # где у значка «👆» кончик пальца относительно центра
        c, s_ = math.cos(ang), math.sin(ang)
        off = QPointF(tip_dx * c - tip_dy * s_, tip_dx * s_ + tip_dy * c)   # смещение кончика после наклона
        back = QPointF(math.sin(-ang) * dist, math.cos(ang) * dist)         # откуда подлетает: вдоль пальца, снизу справа
        centre = QPointF(tip.x() - off.x() + back.x() + press * 3, tip.y() - off.y() + back.y() + press * 6)
        p.save()
        p.setOpacity(alpha)
        p.translate(centre)
        p.rotate(tilt)
        sc = 1.0 - .05 * press
        p.scale(sc, sc)
        f = QFont(theme.FONT_FAMILY)
        f.setFamilies(["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", theme.FONT_FAMILY])
        f.setPixelSize(int(px))
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(-px, -px, px * 2, px * 2), int(Qt.AlignmentFlag.AlignCenter.value), "\U0001F446")
        p.restore()

    def _paint_dots(self, p, W, H):
        x = W / 2 - (SCENES * 14 + 14) / 2
        y = H - 44
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(SCENES):
            if i == self.scene:
                p.setBrush(QColor(self.color))
                p.drawRoundedRect(QRectF(x, y, 24, 7), 3.5, 3.5)
                x += 32
            else:
                p.setBrush(QColor(255, 255, 255, 90 if i > self.scene else 170))
                p.drawEllipse(QRectF(x, y, 7, 7))
                x += 15

    def paintEvent(self, e):
        W, H = self.width(), self.height()
        t = self._now()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.fillRect(self.rect(), QColor(8, 7, 10, 182))  # экран мягко затемнён
        self._paint_glow(p, W, H, t)
        if self.scene == S_PRACTICE and self._demo:
            self._paint_demo(p, t)
        if self.scene == S_AI:
            self._paint_ai(p, t)
        if self.scene == S_CLOUD:
            self._paint_cloud(p, t)
        if self.scene == S_WINTER:
            self._paint_winter(p, t)
        if self.scene == S_AGENT:
            self._paint_reveal_bg(p, t)
            if self._ag_phase == "play":
                if self._agent:
                    self._paint_agent(p, t)
                else:
                    self._paint_agent_idle(p, t)
        if self.scene == S_VOICE:
            self._paint_voice(p, t)
        self._paint_hint(p, t)
        self._paint_mico(p, t)
        self._paint_hint_hand(p, t)
        if self.scene == S_WINTER:
            self._paint_winter_fg(p, t)
        if self.scene == S_CLOUD:
            self._paint_cloud_intro(p, t)
        if self.scene == S_AGENT:
            self._paint_reveal_fg(p, t)
        self._paint_bubble(p, W, H, t)
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, _vx, _vy, rot, _vr, life, col, size in self._sparks:
            p.save()
            p.translate(x, y)
            p.rotate(rot)
            p.setOpacity(_clamp(life))
            p.setBrush(col)
            p.drawRoundedRect(QRectF(-size / 2, -size / 4, size, size / 2), 2, 2)
            p.restore()
        p.setOpacity(1.0)
        self._paint_dots(p, W, H)
        p.end()
