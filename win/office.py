"""Офисные программы: Word, Excel, Блокнот с поиском информации через облако Mico.
Открывает программу, получает информацию через LLM и красиво оформляет в документе.
Работает только на Windows, но логика проверяется без Windows."""
import re
import time
import json

# requests грузим только при обращении к облаку — запуск Mico не ждёт сетевой библиотеки

try:
    import win32clipboard
except ImportError:
    win32clipboard = None

# Паттерны для распознавания команд
OFFICE_WRITE = re.compile(
    r"(?:открой|открыть|запусти|запустить)\s+(?P<app>блокнот|ворд|word|эксель|excel|екселъ)\s+"
    r"(?:и\s+)?(?:напиши|написать|создай|создать|введи|ввести)\s+(?P<topic>.+)",
    re.IGNORECASE)

APP_ALIASES = {
    "блокнот": "notepad",
    "ворд": "winword",
    "word": "winword",
    "эксель": "excel",
    "excel": "excel",
    "екселъ": "excel",
}


def parse_office_command(text):
    """Разбирает команду записи в офисную программу.
    Возвращает {'app': 'notepad'|'winword'|'excel', 'topic': str} или None."""
    s = " ".join((text or "").strip().split())
    m = OFFICE_WRITE.search(s)
    if not m:
        return None

    app_raw = m.group("app").lower().replace("ё", "е")
    app = APP_ALIASES.get(app_raw)
    if not app:
        return None

    topic = m.group("topic").strip()[:300]
    if not topic:
        return None

    return {"app": app, "topic": topic}


def search_with_cloud(query, api_key=None, model="smart", max_tokens=1000):
    """Информация для записи в Word, Excel или Блокнот: ответ берём у облака Mico (ключей нет).
    Возвращает текст ответа или None при ошибке."""
    try:
        from llm import cloud as cloud_api
        return cloud_api.generate(cloud_api.PROVIDER, cloud_api.get_key(cloud_api.PROVIDER), [
            {"role": "system", "content": "Ты помощник, который даёт краткие и полезные ответы на русском языке."},
            {"role": "user", "content": query}], model=model)
    except Exception:
        return None


search_with_groq = search_with_cloud                    # старое имя оставлено для совместимости


def set_clipboard(text):
    """Помещает текст в буфер обмена Windows."""
    if win32clipboard is None:
        return False
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        return False


def write_to_notepad(text):
    """Записывает текст в Блокнот через буфер обмена.
    Возвращает True при успехе, False при ошибке."""
    try:
        import subprocess
        import pyautogui

        # Открываем Блокнот
        subprocess.Popen(["notepad.exe"])
        time.sleep(1.5)

        # Помещаем текст в буфер обмена
        if not set_clipboard(text):
            return False

        # Вставляем через Ctrl+V
        pyautogui.hotkey('ctrl', 'v')
        return True
    except Exception:
        return False


def write_to_word(text, topic):
    """Записывает текст в Word через COM API с форматированием.
    Возвращает True при успехе, False при ошибке."""
    try:
        import win32com.client
        import subprocess

        # Открываем Word
        subprocess.Popen(["winword.exe"])
        time.sleep(2)

        # Подключаемся к Word через COM
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = True

        # Создаём новый документ
        word.Documents.Add()
        selection = word.Selection

        # Заголовок
        selection.Font.Size = 16
        selection.Font.Bold = True
        selection.TypeText(topic)
        selection.TypeParagraph()
        selection.TypeParagraph()

        # Основной текст
        selection.Font.Size = 12
        selection.Font.Bold = False
        selection.TypeText(text)

        return True
    except Exception:
        return False


def write_to_excel(text, topic):
    """Записывает текст в Excel через COM API.
    Возвращает True при успехе, False при ошибке."""
    try:
        import win32com.client
        import subprocess

        # Открываем Excel
        subprocess.Popen(["excel.exe"])
        time.sleep(2)

        # Подключаемся к Excel через COM
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = True

        # Создаём новую книгу
        workbook = excel.Workbooks.Add()
        sheet = workbook.ActiveSheet

        # Заголовок в первой ячейке
        sheet.Cells(1, 1).Value = topic
        sheet.Cells(1, 1).Font.Size = 14
        sheet.Cells(1, 1).Font.Bold = True

        # Разбиваем текст на строки и записываем в ячейки
        lines = text.split('\n')
        for i, line in enumerate(lines[:100], start=3):  # Начинаем с 3-й строки, макс 100 строк
            if line.strip():
                sheet.Cells(i, 1).Value = line.strip()

        # Автоподбор ширины первой колонки
        sheet.Columns(1).AutoFit()

        return True
    except Exception:
        return False


def process_office_command(app, topic, api_key):
    """Обрабатывает команду записи в офисную программу:
    1. Получает информацию из облака Mico
    2. Открывает программу
    3. Записывает текст с форматированием

    Возвращает (success: bool, message: str)."""

    # Формируем запрос для LLM
    query = f"Напиши краткую информацию о: {topic}. Ответ должен быть структурированным и полезным."

    # Получаем информацию из облака Mico
    llm_response = search_with_cloud(query)
    if not llm_response:
        return False, "Не удалось получить информацию через API"

    # Записываем в соответствующую программу
    success = False
    if app == "notepad":
        success = write_to_notepad(llm_response)
    elif app == "winword":
        success = write_to_word(llm_response, topic)
    elif app == "excel":
        success = write_to_excel(llm_response, topic)

    if success:
        return True, f"Открыл {app} и записал информацию о: {topic}"
    else:
        return False, f"Не удалось записать в {app}"
