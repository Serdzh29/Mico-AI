"""Mico в мастере установки меняет выражение по шагам и плавно; при удалении грустит. Без Qt — по исходникам."""
import os as _os
import sys

ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(_os.path.join(ROOT, name), encoding="utf-8").read()


def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)


def test_installer_draws_live_mico_not_one_static_picture():
    ins = read("installer.py")
    check("class MicoAvatar(QLabel):" in ins, "аватар рисуется программой")
    check("assets" not in ins.split("class MicoAvatar")[1].split("def _asset")[0], "аватар не берёт одну картинку")
    check("def render_mico" not in ins, "старой одной картинки больше нет")
    check("self.avatar.set_mood(self.PAGE_MOOD[i])" in ins and "self.avatar.set_mood(mood)" in ins,
          "настроение меняется по страницам и по шагам установки")


def test_mood_change_is_a_smooth_crossfade():
    ins = read("installer.py")
    check("FADE_MS = 520" in ins and "self._fade = min(1.0, self._fade + self.FRAME_MS / self.FADE_MS)" in ins,
          "старое лицо плавно уходит в новое")
    check("p.setOpacity(1.0 - t)" in ins and "p.setOpacity(t)" in ins, "переход — смешивание двух кадров")


def test_uninstall_mico_is_sad():
    ins = read("installer.py")
    check('self.avatar.set_mood({0: "worried", 1: "sad", 2: "sad"}[i])' in ins, "при удалении Mico грустит")


def test_sad_face_has_frown_and_tear():
    b = read("blob.py")
    check('elif mood == "sad":' in b and "frown.quadTo" in b, "грусть: рот домиком")
    check("int(170 * (1 - f) + 60)" in b, "слезинка видна почти всё время")
