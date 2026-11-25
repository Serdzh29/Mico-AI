"""Язык интерфейса: русский или английский.

Русский текст в коде — и есть ключ. t("Сохранить") вернёт «Save», если выбран английский,
а для русского вернёт текст как есть. Если перевода нет, показывается русский текст.
"""

from i18n import hints as i18n_hints
from i18n.setup_en import INSTALLER_EN
from i18n.ui_en import UI_EN

LANG = "en"
LANGUAGES = (("en", "English"), ("ru", "Русский"))

EN = {
    # вкладки окна настроек
    "Вид": "Look",
    "Mico AI": "Mico AI",
    "Чат и помощь": "Chat and help",
    "Голос": "Voice",
    "Модели": "Models",
    "Система": "System",
    "Модель для ответов — нажми, чтобы сменить": "Answer model — click to change",
    "Локальная модель": "Local model",
    "Локальная модель — работает офлайн": "Local model — works offline",
    "Добро пожаловать в Mico AI": "Welcome to Mico AI",
    "Привет, я Mico": "Hi, I'm Mico",
    "Выбери цвет": "Pick a color",
    "Всё готово!": "You're all set!",
    "Твой ИИ-компаньон на рабочем столе. Работаю прямо на твоём ПК.": "Your AI companion on the desktop. I run right on your PC.",
    "Им окрасятся Mico, чат и переключатели. Поменять можно в настройках в любой момент.": "Mico, the chat and the switches will take this color. You can change it in settings any time.",
    "Вот что стоит знать для начала.": "A few things to know to get started.",
    "Начать": "Get started",
    "Дальше": "Next",
    "Разговор": "Chat",
    "Спрашивай что угодно. Ответ — рядом со мной.": "Ask anything. The answer appears right next to me.",
    "Компьютер": "Your PC",
    "Открою программу, найду файл, включу тёмную тему — если попросишь.": "I can open an app, find a file or turn on dark mode when you ask.",
    "Напоминания": "Reminders",
    "Напомню о делах, таймере и перерыве. Можно одной фразой.": "I'll remind you about tasks, timers and breaks. One phrase is enough.",
    "Нажми на меня — откроется чат": "Click me to open the chat",
    "Шестерёнка в чате — все настройки": "The gear in the chat opens all settings",
    "Спроси «что ты умеешь?», чтобы увидеть всё, что я могу": "Ask “what can you do?” to see everything I can do",
    "Персиковый": "Peach",
    "Розовый": "Pink",
    "Лавандовый": "Lavender",
    "Небесный": "Sky",
    "Мятный": "Mint",
    "Солнечный": "Sunny",
    "Здоровается и сам подсказывает": "Greets me and suggests things",
    "Здоровается, дальше ждёт меня": "Greets me, then waits for me",
    "Молчит, пока я не напишу": "Stays silent until I write",
    "Режим тишины: без подсказок": "Quiet mode: no suggestions",
    "Когда Mico говорит первым": "When Mico speaks first",
    "Обводки вокруг окна чата и поля ввода": "Outlines around the chat window and input",
    "Помогать с ошибками: текст в буфере, зависшие программы и окна с ошибкой": "Help with errors: clipboard text, frozen apps and error windows",
    "Выбери стиль общения": "Choose a conversation style",
    "Более\nтворческий": "More\nCreative",
    "Более\nсбалансированный": "More\nBalanced",
    "Более\nточный": "More\nPrecise",
    "Вот что Mico может сделать для тебя": "Here are some things Mico can help you do",
    "Твои частые действия": "Your frequent actions",
    "Mico использует ИИ для ответов, поэтому возможны ошибки.": "Mico uses AI to respond, so mistakes are possible.",
    "Подробнее": "Learn more",
    "Условия использования": "Terms of use",
    "Конфиденциальность": "Privacy statement",
    "Понятно": "Got it",
    "Общение": "Conversation",
    "Внешний вид": "Appearance",
    "Mico на экране": "Mico on screen",
    "Действия на ПК": "Actions on PC",
    "Модели и ключи": "Models and keys",
    "Данные": "Data",
    "Быстрые действия": "Quick actions",
    "Источник ответов": "Answer source",
    "Готово": "Done",
    "Отменить изменения": "Discard changes",
    "Твои частые действия:": "Your frequent actions:",
    # разделы
    "Цвет и тема": "Color and theme",
    "Размер и прозрачность": "Size and transparency",
    "Обводки и подсветка": "Outlines and glow",
    "Полоска Mico AI": "Mico AI bar",
    "Положение и сон": "Position and sleep",
    "Запуск и поведение": "Startup and behavior",
    "История и поиск": "History and search",
    "Меню по правому щелчку": "Right-click menu",
    "Тишина и загрузка": "Quiet hours and load",
    "Свои фразы": "Custom phrases",
    "Кнопки под чатом": "Buttons under the chat",
    "Погода и приветствие": "Weather and greeting",
    "Память и перерывы": "Memory and breaks",
    "Помощь по буферу и ошибкам": "Clipboard and error help",
    "Модели для общения и экрана": "Chat and screen models",
    "Скачивание и удаление": "Download and delete",
    # кнопки и подписи
    "Сохранить": "Save",
    "Отмена": "Cancel",
    "Сбросить настройки": "Reset settings",
    "О программе": "About",
    "Язык": "Language",
    "Язык меняется после перезапуска Mico AI.": "The language changes after Mico AI restarts.",
}


EN.update(i18n_hints.EN_HINTS)          # описания настроек
EN.update(INSTALLER_EN)                 # мастер установки и удаления
EN.update(UI_EN)                        # главное окно, чат, настройки


def set_language(code):
    global LANG
    LANG = "ru" if code == "ru" else "en"


def t(text):
    """Текст на выбранном языке. Для русского — сам текст; для английского — перевод или русский, если перевода нет."""
    if LANG == "en":
        return EN.get(text, text)
    return text
