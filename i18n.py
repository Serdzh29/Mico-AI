"""Язык интерфейса: русский или английский.

Русский текст в коде — и есть ключ. t("Сохранить") вернёт «Save», если выбран английский,
а для русского вернёт текст как есть. Если перевода нет, показывается русский текст.
"""

import i18n_hints

LANG = "ru"
LANGUAGES = (("ru", "Русский"), ("en", "English"))

EN = {
    # вкладки окна настроек
    "Вид": "Look",
    "Основные": "General",
    "Функции": "Features",
    "Модели": "Models",
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


def set_language(code):
    global LANG
    LANG = "en" if code == "en" else "ru"


def t(text):
    """Текст на выбранном языке. Для русского — сам текст; для английского — перевод или русский, если перевода нет."""
    if LANG == "en":
        return EN.get(text, text)
    return text
