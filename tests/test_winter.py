"""Зима: настройки, снег, колпак Mico с живым помпоном и сцена Mico Cloud в знакомстве. Без Windows и Qt: проверяем код и связи."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_settings_have_winter_page_with_two_switches():
    src = read("mico.py")
    assert 'i18n.t("Зима"), "s_snow"' in src
    for key in ("winter_ui", "winter_mico"):
        assert f'"{key}": False' in src, key
        assert f'{key}=self.' in src, "сохранение " + key
    assert "def reject(self)" in src and "_winter_orig" in src, "отмена возвращает прежний вид"


def test_hat_follows_head_and_has_live_pompom():
    blob = read("ui/blob.py")
    assert 'self.cfg.get("winter_mico")' in blob and "def _draw_hat" in blob
    hat = blob[blob.index("def _draw_hat"):blob.index("def _look(")]
    assert "p.transform()" in hat and "self._hat_st" in hat, "хвост с помпоном — цепочка с физикой, привязанная к повороту головы"
    i_hat, i_rot = blob.index("self._draw_hat(p,"), blob.index("p.rotate(head + shake + spin_turn)")
    assert i_hat > i_rot, "колпак рисуется внутри поворота головы"


def test_winter_layers_ignore_mouse_and_cover_chat_and_settings():
    w = read("ui/winter.py")
    assert "WA_TransparentForMouseEvents" in w and "def refresh_all" in w
    assert "winter_ui.install(self, self.cfg, festive=True" in read("mico.py")
    assert "_winter.install(self.card" in read("assist/chat.py")
    st = read("ui/sidetabs.py")
    assert "def set_winter" in st and "winter.ICE" in st


def test_snow_icon_is_registered_and_animated():
    ic = read("ui/icons.py")
    assert '"s_snow": _s_snow' in ic and '"s_snow": (_t_spin' in ic


def test_cloud_scene_is_in_onboarding_and_skipped_for_local_choice():
    ob = read("ui/onboarding.py")
    assert "S_AI, S_CLOUD, S_PRACTICE" in ob and "SCENES = 9" in ob
    assert "if nxt == S_CLOUD and self._ai != \"mico\"" in ob
    assert "cloud_api.generate(" in ob[ob.index("def _cl_ask"):ob.index("def _cl_done_react")], "настоящий запрос облаку, а не заготовка"
    for name in ("Lite", "Plus", "Max", "Авто"):
        assert f'("{name}",' in ob, "в карточке облака есть уровень " + name


def test_santa_scene_and_cloud_intro_exist():
    ob = read("ui/onboarding.py")
    assert "S_VOICE, S_WINTER, S_DONE" in ob and "def _sw_tick" in ob and "def _sw_choose" in ob
    assert "winter_ui.draw_sleigh" in ob and "draw_hat_icon" in ob and 'self._blob.cfg["winter_mico"] = True' in ob
    assert "def _paint_cloud_intro" in ob and "MICO CLOUD" in ob
    assert "def draw_sleigh" in read("ui/winter.py") and "def draw_garland" in read("ui/winter.py")


def test_hand_is_the_yellow_emoji_drawn_over_mico():
    ob = read("ui/onboarding.py")
    assert "U0001F446" in ob and "def _paint_hint_hand" in ob
    assert ob.index("self._paint_mico(p, t)\n        self._paint_hint_hand(p, t)") > 0, "рука рисуется после Mico, то есть поверх него"


def test_side_menu_animation_does_not_die_on_deleted_veil():
    st = read("ui/sidetabs.py")
    assert "except RuntimeError" in st[st.index("def _veil_in"):st.index("def _prewarm")], "удалённая завеса не должна ронять переключение"
    assert "self._animate_icon(row)" in st and "self._veil = None" in st


def test_no_snow_caps_on_icons():
    st = read("ui/sidetabs.py")
    assert "snowy_icon" not in st


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
