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
    sw = read("switch_ui.py")
    check("class Switch(QAbstractButton)" in sw and "class WrapCheck(QWidget)" in sw, "переключатель общий")
    check("from switch_ui import ClickLabel, Switch, WrapCheck" in read("main.py"), "настройки берут его оттуда")
    check("from switch_ui import Switch, WrapCheck" in read("installer.py"), "установщик берёт его оттуда")


def test_installer_options_use_switches_not_checkboxes():
    ins = read("installer.py")
    check("self.opt_auto = WrapCheck(" in ins and "self.opt_short = WrapCheck(" in ins, "параметры — переключатели")
    check("self.run_cb = WrapCheck(" in ins, "«Запустить Mico AI» — переключатель")
    check("box = WrapCheck(i18n.t(title))" in ins, "выбор при удалении — переключатель")
    check("QCheckBox(i18n.t(" not in ins, "квадратных галочек в установщике больше нет")
    check("Switch.ON, Switch.OFF = c[\"accent\"]" in ins, "цвет переключателей — цвет установщика")


def test_standard_chat_is_smaller():
    m = read("main.py")
    check(re.search(r"CHAT_W, CHAT_H = 560, 520", m) is not None, "главный чат 560×520 с боковым меню")
    check("self.setFixedSize(round(CHAT_W * k), round(CHAT_H * k))" in m, "размер берётся из стандартного")
    check("self.grid = QHBoxLayout(self.chips_inner)" in m and "self.chips_box = QScrollArea()" in m,
          "подсказки — полоса с прокруткой, а не сетка с обрезанными подписями")
    check("b = QPushButton(c.label)" in m, "подписи полные")
    w = read("aichat.py")
    check("MAX_HEIGHT = 560" in w and "BASE_H = 520" in w and "WIDTH = 560" in w, "чат Intelligence: с боковым меню 560×520")
    check("self.side.settings.connect" not in w, "кнопка «Настройки Mico AI» из бокового меню убрана")
