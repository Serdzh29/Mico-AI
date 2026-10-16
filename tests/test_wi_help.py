"""Проверки для WI: помощник по буферу, реакция на ошибки, файлы, таймлайн дня."""
import os, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["APPDATA"] = tempfile.mkdtemp()

import clipbuf, daysum, errwatch, filereader, intel, journal


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_clipboard_offers_help_only_for_error_like_text():
    check(clipbuf.looks_like_error("Traceback (most recent call last):\n  File \"a.py\", line 3"), "трассировка")
    check(clipbuf.looks_like_error("Ошибка: не удалось подключиться к серверу"), "русская ошибка")
    check(clipbuf.looks_like_error("Access is denied. 0x80070005"), "код ошибки Windows")
    check(not clipbuf.looks_like_error("Привет, как дела сегодня?"), "обычный текст — не ошибка")
    check(not clipbuf.looks_like_error("ок"), "короткий — нет")
    check(not clipbuf.looks_like_error("Ошибка пароль: qwe123!rty"), "секрет не предлагаем даже при слове «ошибка»")
    check(not clipbuf.looks_like_error("x" * 4000), "слишком длинный — нет")


def test_error_window_detection_and_no_repeats():
    check(errwatch.is_error_dialog("#32770", "Ошибка приложения"), "окно сообщения с ошибкой")
    check(errwatch.is_error_dialog("#32770", "Warning: disk"), "предупреждение — тоже")
    check(not errwatch.is_error_dialog("#32770", "Сохранить файл"), "обычный диалог — нет")
    check(not errwatch.is_error_dialog("Chrome_WidgetWin_1", "Ошибка"), "не окно сообщения — нет")
    check(errwatch.due(None, 100) and not errwatch.due(100, 200) and errwatch.due(100, 100 + errwatch.COOLDOWN_SEC))


def test_hung_program_is_reported_once_after_confirmation():
    t = errwatch.HangTracker()
    results = [t.observe(42, True, 1000 + k * 2) for k in range(5)]
    check(results == [False, False, True, False, False], results)      # подтвердили на третьей проверке, потом молчим
    check(t.observe(42, False, 1012) is False)                           # ожило — счётчик сброшен
    check(t.observe(42, True, 1014) is False and t.observe(42, True, 1016) is False)
    check(t.observe(42, True, 1018) is False, "повтор в пределах cooldown — молчим")
    check(t.observe(42, True, 1000 + errwatch.COOLDOWN_SEC + 100) is True, "через cooldown — снова можно")


def test_dialog_text_is_clean_and_bounded():
    txt = errwatch.joined_text(["  Не удалось  сохранить ", "", "Не удалось сохранить", "Код 5"])
    check(txt == "Не удалось сохранить\nКод 5", repr(txt))
    check(len(errwatch.joined_text(["я" * 5000])) <= errwatch.MAX_TEXT)


def test_file_kinds_and_text_reading():
    check(filereader.kind("a.TXT") == "text" and filereader.kind("b.py") == "text")
    check(filereader.kind("c.PNG") == "image" and filereader.kind("d.pdf") == "unsupported")
    d = tempfile.mkdtemp()
    p = os.path.join(d, "x.txt")
    with open(p, "wb") as f:
        f.write("Привет, мир".encode("utf-8"))
    check(filereader.read_text(p) == "Привет, мир")
    p2 = os.path.join(d, "y.txt")
    with open(p2, "wb") as f:
        f.write("Привет".encode("cp1251"))
    check(filereader.read_text(p2) == "Привет", "cp1251 тоже читаем")
    big = os.path.join(d, "big.txt")
    with open(big, "wb") as f:
        f.write(b"a" * (filereader.MAX_BYTES * 2))
    check(len(filereader.read_text(big)) == filereader.MAX_BYTES, "больше 60 КБ не читаем")
    check(filereader.read_text(os.path.join(d, "нет.txt")) == "", "нет файла — пусто")


def test_journal_merges_skips_and_keeps_titles_out():
    t0 = daysum.day_start(time.time())
    events = [
        (t0 + 100, t0 + 400, "chrome.exe", "Секретная страница банка"),
        (t0 + 420, t0 + 900, "chrome.exe", "Другая вкладка"),              # та же программа через 20 с — один отрезок
        (t0 + 1000, t0 + 1002, "code.exe", "мелькнуло"),                    # короче минимума — не показываем
        (t0 + 1200, t0 + 1800, "explorer.exe", "Пуск"),                     # системная — пропускаем
        (t0 + 2000, t0 + 2600, "code.exe", "main.py"),
    ]
    chats = [(t0 + 500, "user", "как настроить принтер"), (t0 + 510, "mico", "Открой «Принтеры»")]
    clips = [(t0 + 300, "какой-то текст из буфера")]
    rows = journal.rows(events, chats, clips, t0, t0 + 3600)
    apps = [r for r in rows if r["kind"] == "app"]
    check([a["label"] for a in apps] == ["chrome", "code"], [a["label"] for a in apps])
    check(apps[0]["secs"] == 300 + 480, apps[0]["secs"])               # 100–400 и 420–900
    check(abs(sum(a["share"] for a in apps) - 1.0) < 1e-9, "доли дают целое")
    check([r["ts"] for r in rows] == sorted(r["ts"] for r in rows), "лента по времени")
    text = repr(rows)
    check("Секретная страница" not in text and "Другая вкладка" not in text and "main.py" not in text,
          "заголовки окон в ленте не показываем")
    check("какой-то текст" not in text and "знаков" in text, "копия — только размер")
    check(any(r["kind"] == "chat" and r["label"] == "Ты" for r in rows), "реплики есть")
    check(journal.colour_for("chrome.exe") == journal.colour_for("chrome.exe"), "цвет программы постоянный")
    check("разговоров: 2" in journal.summary(rows), journal.summary(rows))
    check(journal.summary([]) == "За компьютером пока ничего не записано.")


def test_prompts_are_bounded_and_name_the_file():
    check(len(intel.explain_prompt("е" * 9000)) < 1700)
    check("«main.py»" in intel.file_prompt("main.py", "print(1)"))
    check("Не выдумывай" in intel.explain_prompt("ошибка"), "модель не выдумывает причину")
    check("программа" in intel.hung_prompt("") and "x.exe" in intel.hung_prompt("x.exe"))


def test_wi_help_is_wired_and_only_in_wi():
    ui = read("intel_ui.py")
    main = read("main.py")
    brain = read("brain.py")
    blob = read("blob.py")
    check("self.panel.brain.quick_answer(prompt, image)" in ui, "быстрый ответ идёт мимо памяти диалога")
    check("dialog.add" not in brain[brain.index("def quick_answer"):brain.index("def _agent_call")],
          "быстрый ответ не пишет в память разговора")
    check("pyqtSignal(list)" in blob and "self.dropped.emit(paths)" in blob and "setAcceptDrops(True)" in blob,
          "файл на Mico принимается")
    check("blob.dropped.connect(intel_ctl.file_dropped)" in main, "файл читает WI")
    check("if not intel_ctl.on():\n            return\n        now = time.time()" in main, "помощник — только в WI")
    check("errwatch.probe(os.getpid(), W.process_of)" in main, "окно на переднем плане проверяем без Qt-зависимостей")
    check('"wi_clip_help": True, "wi_error_help": True' in main, "переключатели по умолчанию включены")
    check("Что делать?" in ui and "Объяснить" in ui and "act_btn" in ui, "кнопка помощи над Mico")
    check("self.wichat.journal.connect(self.show_journal)" in ui and "def show_timeline" in read("wichat.py"),
          "таймлайн открывается в чате WI")
    check("ERROR_CHECK_MS" in ui or "intel.ERROR_CHECK_MS" in main, "интервал проверки один")
    check("self.gate()" in ui[ui.index("def file_dropped"):ui.index("def show_journal")], "файлы — только в WI")


def test_quiet_hours_work_across_midnight_and_ignore_bad_input():
    def at(h, m):
        return time.mktime((2026, 10, 14, h, m, 0, 0, 0, -1))
    check(intel.in_quiet_hours(at(23, 30), "23:00", "08:00"), "23:30 в тихом часе")
    check(intel.in_quiet_hours(at(7, 59), "23:00", "08:00"), "07:59 в тихом часе")
    check(not intel.in_quiet_hours(at(8, 0), "23:00", "08:00"), "08:00 уже можно")
    check(not intel.in_quiet_hours(at(12, 0), "23:00", "08:00"), "полдень — можно")
    check(intel.in_quiet_hours(at(13, 0), "12:00", "14:00") and not intel.in_quiet_hours(at(14, 0), "12:00", "14:00"),
          "дневной тихий час")
    check(not intel.in_quiet_hours(at(23, 30), "23:00", "08:00", on=False), "выключен — не тихий")
    check(not intel.in_quiet_hours(at(23, 30), "23:00", "23:00"), "равные границы — тихого часа нет")
    check(not intel.in_quiet_hours(at(23, 30), "мусор", "08:00"), "неверное время — тихого часа нет")
    check(intel.minutes_of("7:05") == 425 and intel.minutes_of("24:00") is None and intel.minutes_of("") is None)


def test_load_is_clamped_and_hour_line_names_top_apps():
    check(intel.load_percent(150) == 100 and intel.load_percent(-3) == 0 and intel.load_percent("x") == 0.0)
    t0 = daysum.day_start(time.time())
    events = [(t0, t0 + 3000, "code.exe", "a"), (t0 + 3000, t0 + 3600, "chrome.exe", "b")]
    rows = journal.rows(events, [(t0 + 100, "user", "вопрос")], [], t0, t0 + 3600)
    line = journal.hour_line(rows)
    check(line.startswith("За последний час: code — 50 мин, chrome — 10 мин"), line)
    check("Разговоров: 1" in line, line)
    check(journal.hour_line([]) == "За последний час записей нет.")


def test_news_shows_only_wi_changes_newest_first():
    import version
    items = version.wi_changes()
    check(items and all("WI" in line for _, line in items), "в «что нового» только WI")
    keys = [k for k, _ in items]
    check(keys == sorted(keys, reverse=True), "от свежих к старым")


def test_rewrite_and_file_chat_stay_out_of_memory_and_use_the_right_prompt():
    ui = read("intel_ui.py")
    brain = read("brain.py")
    check("intel.REWRITE_PROMPTS[mode]" in ui or "intel.REWRITE_PROMPTS[mode] +" in ui, "короче/подробнее — свои тексты")
    check(set(intel.REWRITE_PROMPTS) == {"short", "long"} and set(intel.REWRITE_LABELS) == {"short", "long"})
    check("{question}" in intel.FILE_CHAT_PROMPT and "{text}" in intel.FILE_CHAT_PROMPT, "вопрос по файлу получает текст")
    check("Если в файле ответа нет" in intel.FILE_CHAT_PROMPT, "модель не выдумывает ответ из файла")
    check("self.panel.brain.quick_answer(prompt, image)" in ui, "вопросы по файлу идут мимо памяти")
    check(intel.FILE_TTL_SEC == 30 * 60, "файл держим полчаса")
    check(brain.index("def quick_answer") < brain.index("def _agent_call"), "быстрый ответ есть в мозге Mico")


def test_proactive_messages_respect_hushed_and_questions_do_not():
    ui = read("intel_ui.py")
    for fn in ("def clip_seen", "def watch_errors", "def check_system"):
        body = ui[ui.index(fn):ui.index("\n    def ", ui.index(fn) + 5)]
        check("hushed()" in body, f"{fn} молчит в тишине")
    notify = ui[ui.index("    def notify"):ui.index("    def greet")]
    check("self.hushed()" in notify, "напоминания и наблюдение молчат в тишине")
    answer = ui[ui.index("    def answer"):ui.index("    def notify")]
    check("hushed()" not in answer, "ответ на вопрос тишина не блокирует")
    check("def set_dnd" in ui and "DND_CHOICES" in read("wichat.py"), "«не беспокоить» на время")


def test_wi_settings_look_and_tabs_only_in_wi():
    main = read("main.py")
    check("wi_on = intel.style_of(cfg.get(\"assist_style\")) == intel.INTELLIGENCE" in main, "вид — только в WI")
    check("theme.wi_settings_qss(self.cfg[\"color\"]" in main and "theme.settings_qss(self.cfg[\"color\"]" in main,
          "обычный вид сохранён")
    check("tabs.insertTab(0, page((self._wi_rhythm_box(cfg)" in main and "tabs.addTab(self._news_page()" in main,
          "вкладки WI только в режиме WI")
    check("version.wi_changes()" in main, "что нового — из журнала, только WI")
    check('"wi_quiet_on": False' in main and '"wi_load_bar": False' in main, "тихий час и загрузка выключены по умолчанию")
    check("psutil.cpu_percent(interval=None)" in main and "intel_ctl.expire_file(now)" in main, "загрузка и файлы — в таймере")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("OK test_wi_help")
