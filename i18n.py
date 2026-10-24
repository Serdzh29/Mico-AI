"""Язык интерфейса: русский или английский.

Русский текст в коде — и есть ключ. t("Сохранить") вернёт «Save», если выбран английский,
а для русского вернёт текст как есть. Если перевода нет, показывается русский текст.
"""

import i18n_hints
from i18n_installer_en import INSTALLER_EN
from i18n_ui_en import UI_EN

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
