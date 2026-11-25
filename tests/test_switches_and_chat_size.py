"""Переключатели в установщике — как в настройках (пилюля, а не квадратик), стандартный размер чата меньше.
Проверяется по исходникам, без Qt."""
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


def test_switch_lives_in_shared_module_for_settings_and_installer():
    sw = read("ui/controls.py")
    check("class Switch(QAbstractButton)" in sw and "class WrapCheck(QWidget)" in sw, "переключатель общий")
    check("from switch_ui import ClickLabel, Switch, WrapCheck" in read("mico.py"), "настройки берут его оттуда")
    check("from switch_ui import Switch, WrapCheck" in read("setup/installer.py"), "установщик берёт его оттуда")


def test_installer_options_use_switches_not_checkboxes():
    ins = read("setup/installer.py")
    check("self.opt_auto = WrapCheck(" in ins and "self.opt_short = WrapCheck(" in ins, "параметры — переключатели")
    check("self.run_cb = WrapCheck(" in ins, "«Запустить Mico AI» — переключатель")
    check("box = WrapCheck(i18n.t(title))" in ins, "выбор при удалении — переключатель")
    check("QCheckBox(i18n.t(" not in ins, "квадратных галочек в установщике больше нет")
    check("Switch.ON, Switch.OFF = c[\"accent\"]" in ins, "цвет переключателей — цвет установщика")


def test_standard_chat_is_smaller():
    m = read("mico.py")
    check(re.search(r"CHAT_W, CHAT_H = 560, 520", m) is not None, "главный чат 560×520 с боковым меню")
    check("self.setFixedSize(round(CHAT_W * k), round(CHAT_H * k))" in m, "размер берётся из стандартного")
    check("self.grid = QHBoxLayout(self.chips_inner)" in m and "self.chips_box = QScrollArea()" in m,
          "подсказки — полоса с прокруткой, а не сетка с обрезанными подписями")
    check("b = QPushButton(c.label)" in m, "подписи полные")
    w = read("assist/chat.py")
    check("MAX_HEIGHT = 480" in w and "BASE_H = 430" in w and "WIDTH = 390" in w, "чат Intelligence стал уже и выше: 390×430")
    check("self.side.settings.connect" not in w, "кнопка «Настройки Mico AI» из бокового меню убрана")


def test_chat_drawer_messages_and_profile_are_consistent():
    chat = read("assist/chat.py")
    look = read("ui/chatlook.py")
    check("self.menu_btn.clicked.connect(lambda: self._toggle_side())" in chat,
          "три полоски открывают список недавних чатов")
    check("self.side.setMaximumWidth(0)" in chat and "QPropertyAnimation(self.side, b\"maximumWidth\", self)" in chat,
          "боковая панель по умолчанию скрыта и выезжает плавно")
    check('QLabel("Текущий чат")' not in chat, "надпись «Текущий чат» убрана")
    check("body.setContentsMargins(1, 1, 1, 1)" in chat and "border-radius:22px" in chat,
          "содержимое не перекрывает скруглённую обводку окна")
    check("def _fit_messages(self):" in chat and "QTimer.singleShot(0, self._fade_history)" in chat,
          "сообщения пересчитывают перенос и плавно проявляются при смене чата")
    check("QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred" in look,
          "у пузыря сообщения нет ограничения, обрезающего текст")
    check("Qt.AlignmentFlag.AlignTop" in look, "иконка Mico выровнена по верхнему краю сообщения")
    check('pill = QLabel("Pro")' in look, "в профиле показан статус подписки Pro")
    check("self.height() * 0.86" in look, "лицо Mico в профиле остаётся различимым")


def test_compact_chat_has_no_file_input_or_decorative_mico():
    chat = read("assist/chat.py")
    look = read("ui/chatlook.py")
    main = read("mico.py")
    check("attach_requested" not in chat and "clip_btn" not in chat and "set_file" not in chat,
          "в текстовом чате нет скрепки и прикрепления")
    check("file_chip" not in main and "_pick_file" not in main and "dropped.connect" not in main,
          "обычный чат и перетаскивание файлов отключены")
    check('self._letter = name[0].upper() if name else "П"' in look,
          "у пустого профиля есть аватар с буквой П")
    check('return ""' in look.split("def user_title", 1)[1].split("class AvatarButton", 1)[0],
          "надпись «Приступим» убрана")
    check("Greeting(" in chat and "set_suggest_visible" in chat,
          "пустой чат — как Windows Copilot: приветствие с кнопками действий на ПК")
    check("_update_greeting" in chat and "self.greeting.fade_out()" in chat,
          "кнопки действий уходят, когда человек пишет запрос")
    check("self.mico_icon" not in look.split("class MessageRow", 1)[1].split("class ProfileCard", 1)[0],
          "у ответов и индикатора печати нет фигуры Mico")
    check("profile_requested = pyqtSignal()" in main and "open_settings(\"profile\")" in main and 'i18n.t("Профиль"), "profile"' in main,
          "профиль открывается отдельной анимированной страницей настроек")
    check("self.side.profile.connect" not in main and "self.side.profile.connect" not in chat,
          "в боковом меню чата нет профиля")
    check('self._save_msg("user", q)' in main and "shown" not in main.split("def submit(self, q):", 1)[1].split("def _run", 1)[0],
          "отправка сообщения не ссылается на удалённое вложение")
