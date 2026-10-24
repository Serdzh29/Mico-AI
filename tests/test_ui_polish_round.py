"""Полировка интерфейса: «мико!» вместо «слушать мико», шапка с «⋯», полоса подсказок, отклики на нажатия,
общие значения интерфейса, без эмодзи в надписях. Проверяется по исходникам."""
import os as _os
import re
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_listen_to_mico_option_is_gone_everywhere_and_wake_is_off_by_default():
    for f in ("main.py", "aichat.py", "intel_ui.py", "voice_settings.py", "voice_ctl.py"):
        s = read(f)
        check("Слушать «мико»" not in s and "Слушать мико" not in s, f"«слушать мико» осталось в {f}")
        check("wake_toggle" not in s, f"переключатель «слушать» осталось в {f}")
    check('"voice_wake": False' in read("main.py"), "голосовой запуск выключен по умолчанию")
    vs = read("voice_settings.py")
    check('WrapCheck(i18n.t("Голосовой чат по слову «мико!»"))' in vs, "один переключатель «мико!»")
    check("voice_wake_words\"].setText" not in vs, "слова пробуждения больше не редактируются")


def test_mico_word_opens_voice_mode_directly():
    iu = read("intel_ui.py")
    check("self.voice.woke.connect(self._on_wake)" in iu, "«мико!» подключён к входу в голосовой режим")
    body = re.search(r"def _on_wake\(self, rest\):(.*?)\n    def ", iu, re.S).group(1)
    check("self.enter_voice_mode()" in body, "сразу открывается голосовой чат")
    check("self._on_send(rest)" in body, "вопрос из той же фразы уходит ответом")
    check("self._wake_active" not in iu, "в голосовом режиме имя не слушаем")
    vc = read("voice_ctl.py")
    check("and not self._session" in vc and "self._mode = \"off\"" in vc, "в голосовом режиме режим ожидания закрыт")


def test_chat_header_is_name_dots_and_close():
    w = read("aichat.py")
    check("self.side.settings.connect" not in w, "в боковом меню нет кнопки «Настройки Mico AI»")
    for name in ("Модель: ", "Цвет Mico AI…", "Озвучивать ответы", "\"Голос\"", "\"Тишина\""):
        check(name in w, f"в меню «⋯» есть {name}")
    top = w[w.index("        top = QHBoxLayout()"):w.index("        hb.addLayout(top)")]
    check(top.count("addWidget(") == 3, "в шапке только ≡, поиск и крестик")


def test_quick_chips_are_one_scrolling_strip_with_full_labels():
    m = read("main.py")
    check("self.grid = QHBoxLayout(self.chips_inner)" in m and "self.chips_box = QScrollArea()" in m, "полоса с прокруткой")
    check("b = QPushButton(c.label)" in m and "label[:13]" not in m, "подписи полные, не обрезаются")
    check("CHIP_COLS" not in m, "сетка из колонок убрана")


def test_buttons_answer_with_small_animation():
    ua = read("ui_anim.py")
    check("class DotsButton(QPushButton)" in ua and "def mousePressEvent" in ua, "«⋯» подпрыгивает при нажатии")
    check("def pulse_icon" in ua and "anim.setKeyValueAt(0.4" in ua, "значок пульсирует при нажатии")
    sw = read("switch_ui.py")
    check("self._slide" in sw and "CheckPop" not in sw, "ручка переключателя едет, галочки рядом нет")
    vd = read("voice_dock.py")
    check("pulse_icon(btn)" in vd, "кнопки голосовой панели отвечают на нажатие")


def test_shared_values_used_by_new_surfaces():
    tk = read("theme_tokens.py")
    check("RADIUS" in tk and "MOTION" in tk and "TEXT" in tk, "общие скругления, размеры текста и анимации")
    vd = read("voice_dock.py")
    check("pal = theme.fluent(dark)" in vd and "from theme_tokens import RADIUS" in vd,
          "голосовая панель использует общую палитру и скругления")
    check("rgba(28,28,30,238)" not in vd, "своих цветов в панели больше нет")


def test_no_emoji_in_interface_labels_but_mico_speech_keeps_them():
    chips = read("chips.py")
    labels = re.findall(r'Chip\("[\w:]+", "([^"]*)"', chips)
    check(labels and all(not re.match(r"[^\wА-Яа-яЁё]", l) for l in labels), "подсказки без эмодзи")
    menu = read("menu_items.py")
    check("⚙" not in menu and "🔕" not in menu, "пункты меню без эмодзи")
    check("TOGGLE_EMOJI" not in chips, "эмодзи переключателей больше не нужны")
    check('"👀 "' in read("main.py"), "Mico по-прежнему говорит с эмодзи")
