"""Клики по результатам поиска в браузере: Google, YouTube и другие.
Через UI Automation находит N-й результат и кликает на него.
Работает только на Windows, но логика проверяется без Windows."""
import re
import time

# Паттерны для распознавания команд клика по результатам
YOUTUBE_CLICK = re.compile(
    r"(?:открой|открыть|запусти|зайди на|перейди на|включи|загугли|загугл[ие])\s+(?:ютуб|youtube|ютюб)\s+"
    r"(?:и\s+)?(?:включи|открой|нажми|кликни|выбери)\s+(?P<nth>\d+|первый|второй|третий|четвертый|пятый)(?:\s+видео)?",
    re.IGNORECASE)

GOOGLE_CLICK = re.compile(
    r"(?:загугли|загугл[ие]|найди в гугле|найди|ищи|поищи)\s+(?P<query>.+?)\s+"
    r"(?:и\s+)?(?:открой|открыть|перейди|зайди на|нажми|кликни)\s+(?P<nth>\d+|первый|второй|третий|четвертый|пятый)(?:\s+(?:сайт|результат|ссылк[уа]))?",
    re.IGNORECASE)

# Порядковые числительные -> число
ORDINAL = {
    "первый": 1, "первое": 1, "первую": 1,
    "второй": 2, "второе": 2, "вторую": 2,
    "третий": 3, "третье": 3, "третью": 3,
    "четвертый": 4, "четвёртый": 4, "четвертое": 4, "четвёртое": 4,
    "пятый": 5, "пятое": 5, "пятую": 5,
}


def parse_click_command(text):
    """Разбирает команду клика по результату поиска.
    Возвращает {'site': 'youtube'|'google', 'query': str|None, 'nth': int} или None."""
    s = " ".join((text or "").strip().split())

    # YouTube
    m = YOUTUBE_CLICK.search(s)
    if m:
        nth_str = m.group("nth").lower()
        nth = int(nth_str) if nth_str.isdigit() else ORDINAL.get(nth_str, 1)
        return {"site": "youtube", "query": None, "nth": max(1, min(nth, 10))}

    # Google
    m = GOOGLE_CLICK.search(s)
    if m:
        query = m.group("query").strip()
        nth_str = m.group("nth").lower()
        nth = int(nth_str) if nth_str.isdigit() else ORDINAL.get(nth_str, 1)
        return {"site": "google", "query": query[:200], "nth": max(1, min(nth, 10))}

    return None


def click_youtube_result(driver, nth=1, timeout=5):
    """Кликает на N-й результат в YouTube (требует Windows и pywinauto).
    driver — функция driver() из agent_win.py.
    Возвращает True при успехе, False при ошибке."""
    try:
        from pywinauto import Desktop
        from pywinauto.findwindows import ElementNotFoundError

        # Ждём, пока браузер откроется и загрузится
        time.sleep(timeout)

        # Ищем окно браузера
        desktop = Desktop(backend="uia")
        browsers = ["Chrome", "Edge", "Firefox", "Opera", "Brave", "Яндекс"]
        window = None
        for browser_name in browsers:
            try:
                window = desktop.window(title_re=f".*{browser_name}.*")
                break
            except ElementNotFoundError:
                continue

        if not window:
            return False

        # Ищем все ссылки на видео (обычно имеют role="link" и содержат текст названия)
        # В YouTube результаты — это элементы с role="link" внутри ytd-video-renderer
        links = window.descendants(control_type="Hyperlink")

        # Фильтруем: берём только те, что похожи на результаты поиска (не меню, не кнопки)
        video_links = []
        for link in links:
            try:
                name = link.window_text()
                # Пропускаем служебные ссылки
                if name and len(name) > 5 and "subscribe" not in name.lower():
                    video_links.append(link)
            except:
                continue

        if len(video_links) < nth:
            return False

        # Кликаем на N-й результат (нумерация с 1)
        target = video_links[nth - 1]
        target.click_input()
        return True
    except Exception:
        return False


def click_google_result(driver, nth=1, timeout=3):
    """Кликает на N-й результат в Google (требует Windows и pywinauto).
    driver — функция driver() из agent_win.py.
    Возвращает True при успехе, False при ошибке."""
    try:
        from pywinauto import Desktop
        from pywinauto.findwindows import ElementNotFoundError

        # Ждём, пока браузер откроется и результаты загрузятся
        time.sleep(timeout)

        # Ищем окно браузера
        desktop = Desktop(backend="uia")
        browsers = ["Chrome", "Edge", "Firefox", "Opera", "Brave", "Яндекс"]
        window = None
        for browser_name in browsers:
            try:
                window = desktop.window(title_re=f".*{browser_name}.*")
                break
            except ElementNotFoundError:
                continue

        if not window:
            return False

        # Ищем все ссылки результатов поиска
        # В Google это обычно <a> с <h3> внутри
        links = window.descendants(control_type="Hyperlink")

        # Фильтруем: берём только основные результаты (не рекламу, не навигацию)
        search_results = []
        for link in links:
            try:
                name = link.window_text()
                # Основные результаты обычно имеют осмысленный текст длиной > 10 символов
                if name and len(name) > 10:
                    # Пропускаем навигационные элементы
                    if not any(x in name.lower() for x in ["картинки", "видео", "новости", "карты",
                                                            "images", "videos", "news", "maps", "shopping"]):
                        search_results.append(link)
            except:
                continue

        if len(search_results) < nth:
            return False

        # Кликаем на N-й результат (нумерация с 1)
        target = search_results[nth - 1]
        target.click_input()
        return True
    except Exception:
        return False
