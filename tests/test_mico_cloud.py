"""Mico Cloud: ключей в программе нет, токен берётся у шлюза, ответы идут через /api/chat; экран в облако не уходит.
Без Windows и сети: запросы подменяются."""
import glob, io, json, os, re, sys, types
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import stubs_for_tests   # noqa: E402
stubs_for_tests.install()
from llm import cloud as cloud_api   # noqa: E402
from win import screen   # noqa: E402

TOKEN = "a" * 32 + "." + "b" * 64


class _Resp:
    def __init__(self, status=200, payload=None, lines=None):
        self.status_code, self._p, self._lines = status, payload or {}, lines or []

    def json(self):
        return self._p

    def iter_lines(self, decode_unicode=True):
        return iter(self._lines)


class _Net:
    """Подмена requests.post: запоминаем вызовы и отвечаем по очереди."""
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, json=None, headers=None, timeout=None, stream=False):
        self.calls.append({"url": url, "json": json, "headers": headers or {}, "stream": stream})
        return self.responses.pop(0)


def _with_net(net, fn):
    fake = types.SimpleNamespace(post=net.post, get=getattr(net, "get", None), Timeout=type("T", (Exception,), {}), RequestException=type("R", (Exception,), {}))
    keep = dict(cloud_api._MEMORY)
    cloud_api._MEMORY.clear()
    saved = []
    with mock.patch.object(cloud_api, "_requests", lambda: fake), \
         mock.patch.object(cloud_api, "get_key", lambda p="mico": ""), \
         mock.patch.object(cloud_api, "set_key", lambda p, k: saved.append(k)):
        try:
            return fn(saved)
        finally:
            cloud_api._MEMORY.clear()
            cloud_api._MEMORY.update(keep)


def test_no_builtin_key_anywhere_in_the_program():
    for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        if os.sep + "tests" + os.sep in path:
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        assert not re.search(r"gsk_[0-9A-Za-z]{20,}", text), "в " + path + " остался ключ"
    assert not hasattr(cloud_api, "BUILTIN_GROQ_KEY")


def test_first_request_registers_then_chats_with_token():
    net = _Net(_Resp(200, {"token": TOKEN}), _Resp(200, {"text": "Привет!", "mode": "fast"}))

    def run(saved):
        text = cloud_api.generate("mico", "", [{"role": "system", "content": "s"}, {"role": "user", "content": "привет"}], model="lite")
        assert text == "Привет!"
        assert saved == [TOKEN], "токен сохраняется в защищённое хранилище"
    _with_net(net, run)
    assert net.calls[0]["url"].endswith("/api/register")
    assert net.calls[1]["url"].endswith("/api/chat") and net.calls[1]["headers"]["Authorization"] == "Bearer " + TOKEN
    assert net.calls[1]["json"]["mode"] == "lite" and net.calls[1]["json"]["stream"] is False


def test_unknown_old_model_name_becomes_auto():
    assert cloud_api.normalize_mode("openai/gpt-oss-120b") == "auto"
    assert cloud_api.normalize_mode("smart") == "plus" and cloud_api.normalize_mode("fast") == "lite", "старые режимы переезжают на уровни"
    assert cloud_api.normalize_mode("pro") == "plus" and cloud_api.normalize_mode("basic") == "lite" and cloud_api.normalize_mode("ultra") == "max" and cloud_api.normalize_mode("max") == "max"
    assert cloud_api.normalize_mode("ultra") == "max" and cloud_api.normalize_mode("max") == "max"
    net = _Net(_Resp(200, {"token": TOKEN}), _Resp(200, {"text": "ок"}))
    _with_net(net, lambda s: cloud_api.generate("mico", "", [{"role": "user", "content": "x"}], model="openai/gpt-oss-120b"))
    assert net.calls[1]["json"]["mode"] == "auto"


def test_stream_pieces_reach_on_delta():
    lines = ['data: {"response":"При"}', "", 'data: {"response":"вет"}', 'data: {"choices":[{"delta":{"content":"!"}}]}', "data: [DONE]"]
    net = _Net(_Resp(200, lines=lines))
    got = []
    text = _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}], on_delta=got.append))
    assert text == "Привет!" and got == ["При", "вет", "!"] and net.calls[0]["stream"] is True


def test_rejected_token_is_replaced_once():
    net = _Net(_Resp(401), _Resp(200, {"token": TOKEN}), _Resp(200, {"text": "ответ"}))
    text = _with_net(net, lambda s: cloud_api.generate("mico", "x" * 10, [{"role": "user", "content": "x"}]))
    assert text == "ответ" and [c["url"].rsplit("/", 1)[1] for c in net.calls] == ["chat", "register", "chat"]


def test_limit_and_outage_have_readable_messages():
    net = _Net(_Resp(429, {"error": "limit", "message": "Ты использовал дневную долю облака Mico."}))
    try:
        _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}]))
        assert False
    except cloud_api.APIError as e:
        assert "дневную долю" in str(e)
    net = _Net(_Resp(503, {}))
    try:
        _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}]))
        assert False
    except cloud_api.APIError as e:
        assert "не отвечает" in str(e)


def test_screenshot_never_goes_to_the_cloud():
    try:
        cloud_api.generate_vision("mico", "", "что тут", "data:image/jpeg;base64,AAAA")
        assert False
    except cloud_api.APIError as e:
        assert "не отправляются" in str(e)
    from core import brain
    b = brain.Brain({"llm_backend": "mico", "memory_on": False, "text_model": "x"}, mock.MagicMock(), mock.MagicMock())
    assert "не рассматриваю" in b.ask("что на экране?").text


def test_quota_is_recounted_after_each_answer_and_gives_request_counts():
    cloud_api.QUOTA.update(left=None, stamp=0.0)
    assert cloud_api.requests_left("plus") is None and cloud_api.quota_summary() == ""
    net = _Net(_Resp(200, {"text": "ок", "mode": "plus", "model": "Llama 3.3 70B", "downgraded": False,
                           "quota": {"left": 900, "install_left": 900, "global_left": 8000, "install_limit": 1000}}))
    _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}], model="plus"))
    assert cloud_api.QUOTA["left"] == 900, "остаток взят из ответа шлюза"
    assert cloud_api.requests_left("lite") == 900 // cloud_api.TIER_COST["lite"]
    assert cloud_api.requests_left("max") < cloud_api.requests_left("plus") < cloud_api.requests_left("lite"), "дорогой уровень даёт меньше запросов"
    first = cloud_api.requests_left("plus")
    net = _Net(_Resp(200, {"text": "ок", "mode": "plus", "model": "m", "quota": {"left": 500, "install_left": 500, "global_left": 8000, "install_limit": 1000}}))
    _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}], model="plus"))
    assert cloud_api.requests_left("plus") < first, "после запроса запросов стало меньше"
    assert "Lite ~" in cloud_api.quota_summary() and "Max ~" in cloud_api.quota_summary()
    assert cloud_api.LAST["model"] == "m" and cloud_api.LAST["mode"] == "plus"


def test_stream_headers_update_quota_and_fetch_quota_loads_the_catalog():
    cloud_api.QUOTA.update(left=None, stamp=0.0)
    resp = _Resp(200, lines=['data: {"response":"ок"}', "data: [DONE]"])
    resp.headers = {"x-mico-left": "420", "x-mico-install-left": "420", "x-mico-global-left": "7000", "x-mico-name": "Kimi K2.6", "x-mico-model": "max", "x-mico-down": "1"}
    net = _Net(resp)
    net.get = lambda url, headers=None, timeout=None: _Resp(200, {"left": 400, "install_left": 400, "global_left": 7000, "install_limit": 1000,
                                                                  "tiers": {"lite": {"cost": 20}, "plus": {"cost": 100}, "max": {"cost": 250}},
                                                                  "models": [{"key": "k26", "name": "Kimi K2.6", "tier": "max", "cost": 250}]})
    _with_net(net, lambda s: cloud_api.generate("mico", TOKEN, [{"role": "user", "content": "x"}], on_delta=lambda s_: None))
    assert cloud_api.LAST["model"] == "Kimi K2.6" and cloud_api.LAST["downgraded"] is True
    assert cloud_api.QUOTA["left"] == 400, "после потока остаток уточнён у шлюза"
    assert cloud_api.TIER_COST["max"] == 250 and cloud_api.MODELS and cloud_api.MODELS[0]["name"] == "Kimi K2.6"
    cloud_api.TIER_COST.update(cloud_api.DEFAULT_TIER_COST)


def test_cloud_base_must_be_https():
    for bad in ("http://example.com", "ftp://x"):
        try:
            cloud_api.base_url(bad)
            assert False, bad
        except cloud_api.APIError:
            pass
    assert cloud_api.base_url("").startswith("https://") and cloud_api.base_url("https://x.dev/").endswith("x.dev")


def test_screen_helpers_still_work():
    assert screen.is_question("что на экране?") and not screen.is_question("сделай скриншот")
    from PIL import Image
    noisy = Image.frombytes("RGB", (1920, 1080), os.urandom(1920 * 1080 * 3))
    assert len(screen.encode_jpeg(noisy)) <= screen.MAX_BYTES


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("OK", name)
    print("OK mico cloud")
