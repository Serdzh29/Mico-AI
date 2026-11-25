"""Видео-команды, мессенджеры и зоны агента: разбор фраз и выбор видео — чистая логика.
Проверяется поведение (какие вызовы получит osagent), а не строки исходников. Без Windows и без сети."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from win import videos as V
from win import messenger as M
from win import agent as A

# ---------- видео: сервисы и адреса ----------
def test_service_key_understands_speech_names():
    assert V.service_key("ютуб") == "youtube" and V.service_key("YouTube") == "youtube"
    assert V.service_key("на rutube") == "rutube" and V.service_key("рутуб") == "rutube"
    assert V.service_key("вк видео") == "vk" and V.service_key("яндекс видео") == "ya"
    assert V.service_key("где-то") == "youtube", "без названия — YouTube"


def test_search_url_builds_service_search():
    from urllib.parse import quote
    assert V.search_url("youtube", "cats") == "https://www.youtube.com/results?search_query=cats"
    assert quote("котики") in V.search_url("youtube", "котики"), "кириллица кодируется в адресе"
    assert V.search_url("rutube", "") == "https://rutube.ru", "без запроса — главная страница сервиса"
    assert V.search_url("youtube", "") == "https://www.youtube.com", "и у YouTube — тоже главная"


def test_player_keys_are_keyboard_shortcuts():
    assert V.player_key("play_pause") == "k" and V.player_key("fullscreen") == "f"
    assert V.player_key("next") == "shift+n" and V.player_key("close_video") == "ctrl+w"
    assert V.player_key("нет такого") is None


def test_looks_like_player_matches_video_pages():
    assert V.looks_like_player("котики — YouTube") and V.looks_like_player("Rutube")
    assert V.looks_like_player("Документ1 — Word") is False


# ---------- видео: разбор команд (без модели) ----------
def test_subtitles_command_is_parsed():
    assert V.commands("отключи субтитры") == [("player", {"action": "subtitles_off"})]
    assert V.commands("субтитры выключи") == [("player", {"action": "subtitles_off"})]
    assert V.commands("включи субтитры") == [("player", {"action": "subtitles_on"})]


def test_open_video_request_is_parsed():
    got = V.commands("открой на ютубе 1 видео в полноэкранном режиме")
    assert got and got[0][0] == "video_open", got
    a = got[0][1]
    assert a["site"] == "youtube" and a["count"] == 1 and a["fullscreen"] is True, a


def test_open_video_with_topic_and_service():
    got = V.commands("включи на rutube видео про котов")
    a = got[0][1]
    assert a["site"] == "rutube" and "кот" in a["query"] and a["count"] == 1, a
    got = V.commands("открой 3 видео про python")
    assert got[0][1]["count"] == 3, got


def test_like_dislike_subscribe_close():
    assert V.commands("поставь лайк") == [("video_vote", {"action": "like"})]
    assert V.commands("поставь дизлайк") == [("video_vote", {"action": "dislike"})]
    assert V.commands("подпишись на канал") == [("video_subscribe", {})]
    assert V.commands("закрой видео") == [("video_close", {})]


def test_ordinary_chat_is_not_a_video_command():
    for q in ["что такое пауза", "мне не нравится этот ответ", "привет, как дела?",
              "объясни, что такое видео", "напиши стих про весну"]:
        assert V.commands(q) is None, q


def test_pick_video_prefers_matching_and_nth():
    buttons = ["Ещё", "котики на прогулке смотреть весь", "другое видео про собак очень интересное",
               "котики дома милые моменты"]
    assert V.pick_video(buttons, "котики", 1) == "котики на прогулке смотреть весь"
    assert V.pick_video(buttons, "котики", 2) == "котики дома милые моменты"
    assert V.pick_video(["Ещё", "Меню"], "котики") is None, "служебные подписи — не видео"


def test_subtitles_state_remembers():
    assert V.subtitles_press(False) is True, "первый раз — состояние неизвестно, жмём"
    assert V.subtitles_press(False) is False, "повторно не щёлкаем"
    assert V.subtitles_press(True) is True


def test_is_subscribed_detects_button_state():
    assert V.is_subscribed(["Вы подписаны", "Колокольчик"]) and V.is_subscribed(["Subscribed"])
    assert not V.is_subscribed(["Подписаться", "Поделиться"])


# ---------- мессенджеры: пять сервисов ----------
def test_all_five_messengers_are_supported():
    for app in ("телеграм", "max", "whatsapp", "teams", "discord"):
        assert app in M.MESSENGERS, app
    assert M.parse("открой teams и напиши олегу привет")["who"] == "олегу"
    assert M.parse("открой max и напиши мамуле: привет!")["text"] == "привет!"


def test_search_hotkey_differs_per_app():
    assert M.search_hotkey("телеграм") == "ctrl+f" and M.search_hotkey("whatsapp") == "ctrl+f"
    assert M.search_hotkey("discord") == "ctrl+k" and M.search_hotkey("teams") == "ctrl+e"


# ---------- зоны агента ----------
def test_zone_of_splits_tasks():
    assert A.zone_of("открой телеграм и напиши мамуле привет") == "messenger"
    assert A.zone_of("открой ютуб и включи видео") == "video"
    assert A.zone_of("открой блокнот и напиши привет") == "apps"


class FakeDriver:
    """Окно мессенджера для тестов: шаги записываются, всё «получается»."""
    def __init__(self, launch_ok=True):
        self.done, self.buttons, self.fields = [], ["Мама"], ["Поиск", "Введите сообщение"]
        self.launch_ok = launch_ok

    def snapshot(self):
        return {"title": "Telegram", "buttons": self.buttons, "fields": self.fields}

    def do(self, name, args):
        self.done.append((name, args))
        if name == "launch" and not self.launch_ok:
            return False, "нет в каталоге"
        return True, ""


def test_launch_paths_finds_known_installs_without_guessing():
    # пути бывают только реальные: не нашли — пусто, ничего не выдумываем
    for app in ("телеграм", "макс", "discord", "teams"):
        for p in M.launch_paths(app):
            assert os.path.isabs(p) and p.lower().endswith(".exe"), p
    assert M.launch_paths("одноклассники") == []


def test_messenger_launch_fails_honestly_when_not_found():
    """Каталог «Пуск» не нашёл и путей нет — честная ошибка вместо слепых нажатий."""
    from win import agent as A
    saved = M.launch_paths
    try:
        M.launch_paths = lambda app: []
        drv = FakeDriver(launch_ok=False)
        run = A.Runner("напиши телеграм", lambda p: "", drv, lambda q: True, lambda t: None)
        out = run._messenger({"app": "телеграм", "who": "мама", "text": "привет",
                              "candidates": ["мама"], "search": "мама"})
        assert "Не открыл" in out, out
    finally:
        M.launch_paths = saved


def test_messenger_uses_install_path_fallback_and_sends():
    """Нет в каталоге «Пуск» → пробуем известную установку → контакт → «да» → отправка."""
    from win import agent as A
    saved_paths, saved_popen = M.launch_paths, A.subprocess.Popen
    try:
        M.launch_paths = lambda app: [r"C:\fake\Telegram.exe"]
        A.subprocess.Popen = lambda p: object()             # «программа запустилась»
        drv = FakeDriver()
        drv.buttons = ["Мама", "Папа"]
        drv.fields = ["Поиск", "Введите сообщение"]
        asks = []
        run = A.Runner("напиши телеграм", lambda p: "", drv, lambda q: asks.append(q) or True, lambda t: None)
        out = run._messenger({"app": "телеграм", "who": "мама", "text": "привет",
                              "candidates": ["мама"], "search": "мама"})
        assert "Мама" in out and "Отправил" in out, out
        assert any("Отправлю" in q for q in asks), asks     # отправка — только после вопроса
        assert any(d[0] == A.PRESS and d[1].get("key") == "enter" for d in drv.done), drv.done
    finally:
        M.launch_paths, A.subprocess.Popen = saved_paths, saved_popen


def test_multistep_never_sends_without_yes():
    """Простой сценарий без подтверждения не отправляет — как и агент."""
    from win import multistep
    runner = multistep.MultiStepRunner(lambda t: None)
    assert runner.ask("Отправить?") is False, "по умолчанию отправка запрещена"
    assert multistep.is_multi_step("открой телеграм и напиши маме привет")


if __name__ == "__main__":
    for n, fn in sorted(list(globals().items())):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
    print("ALL OK video and messengers")
