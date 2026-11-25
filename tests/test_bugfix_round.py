"""Раунд исправлений агента и настроек: проверка кода без Windows и Qt."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_agent_model_call_uses_cloud_and_schema():
    src = read("core/brain.py")
    seg = src[src.index("def _agent_request"):src.index("def _agent_notify")]
    assert "allow_cloud=True" in seg and "json_schema=agent.model_schema()" in seg


def test_agent_request_checked_before_multi_step():
    src = read("core/brain.py")
    assert src.index("agent_req = agent.request(q)") < src.index("multi_step.is_multi_step(q)")
    assert src.count("agent_req = agent.request(q)") == 1


def test_agent_prefix_is_a_start_request():
    from win import agent
    assert agent.request("агент, открой телеграм и напиши маме привет")[0] == "start"


def test_model_schema_lists_catalog():
    import json
    from win import agent
    assert set(json.loads(agent.model_schema())["properties"]["action"]["enum"]) == set(agent.CATALOG)


def test_confirm_ttl_and_undo_only_when_possible():
    c, b = read("win/commands.py"), read("core/brain.py")
    assert "ttl=30" in c and "time.time() + ttl" in c
    assert "ttl=agent.CONFIRM_SEC" in b and "run.undo_plan()[0]" in b


def test_window_search_uses_aliases_and_tokens():
    w = read("win/agentwin.py")
    assert "def window_tokens" in w and '"ватсап": "whatsapp"' in w and '"макс"' in w and '"тимс": "teams"' in w
    assert "find_windows([args" not in w
    assert "agentwin.window_tokens(app)" in read("win/agent.py")


def test_snapshot_is_base64_utf8_and_filtered():
    w = read("win/agentwin.py")
    assert "TrueCondition" not in w and "OrCondition" in w
    assert "ToBase64String([Text.Encoding]::UTF8" in w and "b64decode" in w


def test_typing_uses_unicode_sendinput():
    w = read("win/agentwin.py")
    assert "0x0004" in w and "SendInput" in w and "_TYPE.replace" in w and "SendWait($esc)" not in w


def test_settings_card_no_fade_and_instant_neighbours():
    s = read("ui/settingslook.py")
    seg = s[s.index("def set_expanded"):s.index("def _turn_chevron")]
    assert "fade_slide_in" not in seg and "ANIM_MAX_PX" in seg
    assert "c.set_expanded(False)" in s and "c.set_expanded(False, animate=True)" not in s


def test_winter_uses_dirty_rects_sprites_and_pause():
    w = read("ui/winter.py")
    assert "self.update(old)" in w and "def _sprite" in w and "motion.busy()" in w
    assert "_static_pixmap" in w and 'part="bulbs"' in w and "setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)" in w


def test_garland_parts_and_motion_hold():
    from importlib import util
    m = read("ui/motion.py")
    assert "def hold" in m and "def busy" in m
    assert "motion.hold(PAGE_MS" in read("ui/sidetabs.py")


def test_privacy_mentions_agent_cloud():
    assert "названия кнопок и полей активного окна уходят в облако" in read("PRIVACY.md")


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_") and callable(fn):
            fn()
            print("OK", n)
