"""Многошаговые сценарии без модели: типовые задачи выполняются по заранее заданным шагам.
Мессенджеры, браузер с кликами, офисные программы с AI-поиском."""
import re
import time
import threading

from win import messenger
from win import browser
from win import office
from llm import cloud as cloud_api


# Паттерны для распознавания команд
MESSENGER_PATTERN = re.compile(
    r"(?:открой|запусти|зайди в)\s+(?P<app>телеграм|telegram|тг|майкрософт\s+teams|teams|тимс|max|макс|ватсап|whatsapp|discord|дискорд)\s+"
    r"(?:и\s+)?(?:напиши|отправь)\s+(?P<who>[^\s:,]+)(?:\s*[:,]\s*|\s+)(?P<text>.+)",
    re.IGNORECASE)

BROWSER_CLICK_PATTERN = re.compile(
    r"(?:открой|загугли|найди)\s+.+?\s+(?:и\s+)?(?:открой|нажми|кликни|включи)\s+(?P<nth>\d+|первый|второй|третий)",
    re.IGNORECASE)

OFFICE_WRITE_PATTERN = re.compile(
    r"(?:открой|запусти)\s+(?P<app>блокнот|ворд|word|эксель|excel)\s+(?:и\s+)?(?:напиши|создай)\s+(?P<topic>.+)",
    re.IGNORECASE)


class MultiStepRunner:
    """Выполнитель многошаговых сценариев."""

    def __init__(self, notify_callback=None, ask=None):
        self.notify = notify_callback or (lambda t: None)
        self.ask = ask or (lambda q: False)   # без «да» ничего не отправляем
        self.running = False
        self.thread = None

    def is_multi_step_command(self, text):
        """Проверяет, является ли команда многошаговой."""
        s = " ".join((text or "").strip().split())
        return bool(
            MESSENGER_PATTERN.search(s) or
            BROWSER_CLICK_PATTERN.search(s) or
            OFFICE_WRITE_PATTERN.search(s)
        )

    def parse_command(self, text):
        """Разбирает команду и возвращает тип сценария и параметры.
        Возвращает (type, params) или (None, None)."""
        # Мессенджеры
        msg_data = messenger.parse(text)
        if msg_data:
            return "messenger", msg_data

        # Браузер с кликами
        click_data = browser.parse_click_command(text)
        if click_data:
            return "browser_click", click_data

        # Офисные программы
        office_data = office.parse_office_command(text)
        if office_data:
            return "office_write", office_data

        return None, None

    def execute_async(self, scenario_type, params):
        """Запускает сценарий в фоновом потоке."""
        if self.running:
            return False, "Уже выполняется другой сценарий"

        self.running = True
        self.thread = threading.Thread(
            target=self._run_scenario,
            args=(scenario_type, params),
            daemon=True
        )
        self.thread.start()
        return True, "Запустил сценарий"

    def _run_scenario(self, scenario_type, params):
        """Внутренний метод для выполнения сценария в фоновом потоке."""
        try:
            if scenario_type == "messenger":
                self._run_messenger_scenario(params)
            elif scenario_type == "browser_click":
                self._run_browser_click_scenario(params)
            elif scenario_type == "office_write":
                self._run_office_write_scenario(params)
        except Exception as e:
            self.notify(f"Ошибка: {str(e)}")
        finally:
            self.running = False

    def _run_messenger_scenario(self, params):
        """Отправка в мессенджере: тот же надёжный путь, что и в режиме агента
        (окно → поиск → контакт → «да» → текст → Enter). Без pyautogui и слепых нажатий.
        Запуск мессенджера знает про установки «для себя» (Telegram, MAX, WhatsApp, Discord)."""
        from win import agent as agent_mod
        from win import agentwin
        drv = agentwin.WinDriver(notify=self.notify)
        run = agent_mod.Runner(f"напиши {params['app']}", lambda p: "", drv, self.ask, self.notify)
        out = run._messenger(params)
        self.notify(out)

    def _run_browser_click_scenario(self, params):
        """Сценарий клика по результату поиска в браузере.
        1. Открыть браузер с поиском
        2. Дождаться загрузки результатов
        3. Кликнуть на N-й результат"""
        try:
            from win import system as winctl
        except ImportError:
            self.notify("Ошибка импорта модулей")
            return

        site = params["site"]
        query = params.get("query")
        nth = params["nth"]

        if site == "youtube":
            self.notify("Открываю YouTube...")
            url = "https://www.youtube.com"
            if query:
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            winctl.open_url(url)

            time.sleep(4)  # Ждём загрузки YouTube

            self.notify(f"Кликаю на {nth}-е видео...")
            success = browser.click_youtube_result(None, nth, timeout=2)

            if success:
                self.notify("Готово!")
            else:
                self.notify("Не удалось кликнуть на видео")

        elif site == "google":
            if not query:
                self.notify("Не указан поисковый запрос")
                return

            self.notify(f"Ищу в Google: {query}...")
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            winctl.open_url(url)

            time.sleep(3)  # Ждём загрузки результатов

            self.notify(f"Кликаю на {nth}-й результат...")
            success = browser.click_google_result(None, nth, timeout=1)

            if success:
                self.notify("Готово!")
            else:
                self.notify("Не удалось кликнуть на результат")

    def _run_office_write_scenario(self, params):
        """Сценарий записи в офисную программу с AI-поиском.
        1. Получить информацию из облака Mico
        2. Открыть программу
        3. Записать текст с форматированием"""

        app = params["app"]
        topic = params["topic"]

        self.notify(f"Ищу информацию о: {topic}...")

        # Выполняем сценарий: текст для программы берётся из облака Mico, ключи не нужны
        success, message = office.process_office_command(app, topic, None)
        self.notify(message)


# Глобальный экземпляр runner
_runner = None


def get_runner(notify_callback=None, ask=None):
    """Возвращает глобальный экземпляр runner."""
    global _runner
    if _runner is None:
        _runner = MultiStepRunner(notify_callback, ask)
    else:
        if notify_callback is not None:
            _runner.notify = notify_callback
        if ask is not None:
            _runner.ask = ask
    return _runner


def is_multi_step(text):
    """Проверяет, является ли команда многошаговой."""
    runner = get_runner()
    return runner.is_multi_step_command(text)


def execute(text, notify_callback=None, ask=None):
    """Разбирает и выполняет многошаговую команду.
    Возвращает (success: bool, message: str)."""
    runner = get_runner(notify_callback, ask)

    scenario_type, params = runner.parse_command(text)
    if not scenario_type:
        return False, "Не удалось разобрать команду"

    return runner.execute_async(scenario_type, params)
