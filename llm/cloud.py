"""Mico Cloud: ответы чата через шлюз Mico AI на Cloudflare. Ключей в программе нет совсем.

Как это устроено. При первом обращении программа просит у шлюза (сайт Mico AI, путь /api/register) личный токен
установки и прячет его в защищённом хранилище Windows. Дальше каждый вопрос уходит на /api/chat с этим токеном, а
шлюз сам обращается к ИИ Cloudflare, ведёт дневные лимиты и выбирает модель: быструю для простого и умную для сложного.
Раньше здесь лежал встроенный ключ стороннего сервиса. Его мог достать любой, кто откроет файлы программы."""
import json
import os
import re
import tempfile
import time

# requests грузим по требованию (только при обращении к облаку): запуск Mico быстрее


def __getattr__(name):
    """Ленивая загрузка requests: модуль доступен и как cloud_api.requests (на него подменяют запросы в проверках)."""
    if name == "requests":
        import requests
        globals()["requests"] = requests
        return requests
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


APPDIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Mico")
KEYS_PATH = os.path.join(APPDIR, "api_keys.bin")
PROVIDER = "mico"
PROVIDERS = (PROVIDER,)                               # единственный облачный источник: Mico Cloud
STORED = PROVIDERS
# Режимы ответа вместо списка моделей: какую модель взять, решает шлюз. «Авто» сам выбирает уровень по вопросу; Lite: простые и
# дешёвые модели, Plus: сильные, Max: самые мощные и дорогие.
MODES = (("auto", "Авто"), ("lite", "Lite"), ("plus", "Plus"), ("max", "Max"))
MODE_IDS = tuple(m for m, _ in MODES)
DEFAULT_MODE = "auto"
LEGACY_MODES = {"fast": "lite", "smart": "plus", "text": "plus", "code": "plus", "basic": "lite", "pro": "plus", "ultra": "max"}   # режимы прошлых версий программы
# Остаток «нейронов» (единица расчёта Cloudflare). Заполняется ответами шлюза и пересчитывается после каждого запроса.
# left: сколько осталось сегодня (меньшее из доли установки и общей доли облака); stamp: когда обновлено.
QUOTA = {"left": None, "install_left": None, "global_left": None, "install_limit": None, "stamp": 0.0}
DEFAULT_TIER_COST = {"lite": 17, "plus": 101, "max": 238}        # цена «обычного» запроса (1500 токенов на входе, 300 на выходе), пока шлюз не прислал свою
TIER_COST = dict(DEFAULT_TIER_COST)
MODELS = []                                                        # каталог моделей шлюза: [{key, name, tier, cost}], приходит с /api/quota
GROQ_MODEL = DEFAULT_MODE                             # старое имя: оставлено, чтобы старые обращения не падали
TIMEOUT = 25
STREAM_TIMEOUT = 45                                   # живой ответ может идти дольше: ждём между кусочками, а не весь ответ


class APIError(RuntimeError):
    """Ошибка облака, объяснённая безопасным для показа текстом."""


def mode_label(mode):
    return dict(MODES).get(mode, dict(MODES)[DEFAULT_MODE])


def normalize_mode(value):
    """Старые режимы («Быстро», «Умнее», Basic, Pro, Ultra) становятся Lite, Plus и Max, а названия моделей прошлого облака превращаются в «Авто»."""
    value = LEGACY_MODES.get(value, value)
    return value if value in MODE_IDS else DEFAULT_MODE


def requests_left(tier, left=None):
    """Примерно на сколько «обычных» запросов уровня хватит остатка. None: остаток ещё не известен."""
    left = QUOTA["left"] if left is None else left
    cost = TIER_COST.get(tier)
    if left is None or not cost:
        return None
    return int(max(0, left) // cost)


def quota_summary():
    """Короткая строка для окна: сколько осталось нейронов и на сколько запросов каждого уровня этого хватит."""
    left = QUOTA["left"]
    if left is None:
        return ""
    import i18n
    parts = ", ".join("%s ~%d" % (mode_label(t), requests_left(t)) for t in ("lite", "plus", "max"))
    return i18n.t("Осталось около {n} нейронов на сегодня. Хватит примерно на запросы:").format(n=left) + " " + parts + "."


def _update_quota(left=None, install_left=None, global_left=None, install_limit=None):
    def _n(v):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None
    left, il, gl, lim = _n(left), _n(install_left), _n(global_left), _n(install_limit)
    if left is None and il is not None and gl is not None:
        left = min(il, gl)
    if left is None:
        return
    QUOTA.update(left=left, install_left=il, global_left=gl, install_limit=lim, stamp=time.time())


def _quota_from_headers(headers):
    try:
        _update_quota(headers.get("x-mico-left"), headers.get("x-mico-install-left"), headers.get("x-mico-global-left"), headers.get("x-mico-install-limit"))
    except Exception:
        pass


def fetch_quota(base=None, timeout=8):
    """Спрашивает у шлюза остаток и таблицу моделей. Возвращает True, если получилось. Безопасно вызывать из любого потока."""
    try:
        requests = _requests()
        token = _token()
        if not token:
            token = register(base)
        r = requests.get(base_url(base) + "/api/quota", headers={"Authorization": "Bearer " + token, "User-Agent": "Mico/cloud"}, timeout=timeout)
        if r.status_code == 401:
            token = register(base)
            r = requests.get(base_url(base) + "/api/quota", headers={"Authorization": "Bearer " + token, "User-Agent": "Mico/cloud"}, timeout=timeout)
        if r.status_code != 200:
            return False
        d = r.json()
        _update_quota(d.get("left"), d.get("install_left"), d.get("global_left"), d.get("install_limit"))
        for tier, info in (d.get("tiers") or {}).items():
            if tier in TIER_COST and isinstance(info, dict) and info.get("cost"):
                TIER_COST[tier] = int(info["cost"])
        MODELS[:] = [m for m in (d.get("models") or []) if isinstance(m, dict) and m.get("name")]
        return True
    except Exception:
        return False


_QUOTA_BUSY = [False]


def ensure_quota_async(max_age=45.0):
    """Фоном обновляет остаток, если он давно не обновлялся. Окно при этом не ждёт сети."""
    if _QUOTA_BUSY[0] or time.time() - QUOTA["stamp"] < max_age:
        return
    _QUOTA_BUSY[0] = True

    def work():
        try:
            fetch_quota()
        finally:
            _QUOTA_BUSY[0] = False
    import threading
    threading.Thread(target=work, daemon=True).start()


def base_url(value=None):
    """Адрес шлюза. Пусто: шлюз Mico Cloud (CLOUD_URL). Только https: токен не должен уйти открытым текстом."""
    from setup import version
    base = str(value or "").strip().rstrip("/") or version.CLOUD_URL.rstrip("/")
    if not base.startswith("https://"):
        raise APIError("Адрес облака должен начинаться с https://.")
    return base


# ---------- защищённое хранилище токена установки ----------
def _crypt(data, protect):
    if os.name != "nt":
        raise RuntimeError("Защищённое хранилище доступно только в Windows.")
    try:
        import win32crypt
        if protect:
            return win32crypt.CryptProtectData(data, "Mico cloud token", None, None, None, 0)
        return win32crypt.CryptUnprotectData(data, None, None, None, 0)[1]
    except Exception as e:
        raise RuntimeError("Windows не смогла защитить или прочитать токен облака. Проверь учётную запись Windows.") from e


def load_keys():
    if not os.path.exists(KEYS_PATH):
        return {}
    try:
        raw = _crypt(open(KEYS_PATH, "rb").read(), False)
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError("Не получилось прочитать токен облака. Mico запросит новый.") from e


def get_key(provider=PROVIDER):
    """Токен установки или пустая строка: тогда generate() сам запросит новый у шлюза."""
    if provider != PROVIDER:
        return ""
    try:
        return str(load_keys().get(PROVIDER) or "")
    except Exception:
        return ""


def set_key(provider, key):
    if provider not in STORED:
        raise ValueError("Неизвестный облачный источник.")
    try:
        data = load_keys()
    except RuntimeError:
        data = {}
    data.pop("gemini", None)
    data.pop("groq", None)                            # ключ прошлого облака больше не хранится
    if key:
        data[provider] = str(key).strip()
    else:
        data.pop(provider, None)
    os.makedirs(APPDIR, exist_ok=True)
    if not data:
        try:
            os.remove(KEYS_PATH)
        except FileNotFoundError:
            pass
        return
    encrypted = _crypt(json.dumps(data, ensure_ascii=False).encode("utf-8"), True)
    fd, tmp = tempfile.mkstemp(prefix="api_keys_", dir=APPDIR)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(encrypted)
        os.replace(tmp, KEYS_PATH)
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass


# ---------- запросы к шлюзу ----------
def _detail(response):
    try:
        data = response.json()
    except Exception:
        return ""
    return " ".join(str((data or {}).get("message") or "").split())[:300] if isinstance(data, dict) else ""


def _raise_response(response):
    code = response.status_code
    detail = _detail(response)
    if code == 429:
        raise APIError(detail or "Дневная доля облака Mico закончилась. Она обновится завтра, а пока работают команды "
                                  "для компьютера и локальная модель, если она скачана.")
    if code in (502, 503, 504):
        raise APIError(detail or "Облако Mico сейчас не отвечает. Повтори чуть позже.")
    if code in (404, 405):
        raise APIError("Шлюз Mico Cloud ещё не развёрнут на сайте Mico AI (ошибка %d). Нужно выполнить «npx wrangler deploy» "
                       "из папки mico-cloud; пока отвечают команды для компьютера и локальная модель, если она скачана." % code)
    if code in (401, 403):
        raise APIError("Облако не приняло токен этой установки.")
    if code == 413 or code == 400:
        raise APIError(detail or "Облако не приняло запрос: он слишком большой.")
    raise APIError(detail or f"Облако Mico вернуло ошибку {code}.")


def _requests():
    import requests
    return requests


def register(base=None, timeout=TIMEOUT):
    """Получает у шлюза токен новой установки и сохраняет его. Возвращает токен."""
    requests = _requests()
    url = base_url(base) + "/api/register"
    try:
        response = requests.post(url, json={}, headers={"User-Agent": "Mico/cloud"}, timeout=timeout)
    except requests.Timeout as e:
        raise APIError("Облако Mico не ответило. Проверь интернет и повтори.") from e
    except requests.RequestException as e:
        raise APIError("Не получилось подключиться к облаку Mico. Проверь интернет.") from e
    if response.status_code != 200:
        _raise_response(response)
    try:
        token = str(response.json().get("token") or "")
    except Exception:
        token = ""
    if not re.fullmatch(r"[0-9a-f]{32}\.[0-9a-f]{64}", token):
        raise APIError("Облако Mico вернуло непонятный токен.")
    try:
        set_key(PROVIDER, token)
    except Exception:
        pass                                          # без защищённого хранилища токен живёт только до выхода из программы
    _MEMORY["token"] = token
    return token


_MEMORY = {}
LAST = {"mode": "", "model": "", "downgraded": False}                # какая модель ответила в последний раз (показывает знакомство и чат)


def _token(key=None):
    return str(key or _MEMORY.get("token") or get_key(PROVIDER) or "")


def _messages(messages):
    roles = {"mico": "assistant", "model": "assistant"}
    return [{"role": roles.get(m.get("role"), m.get("role")), "content": str(m.get("content") or "")}
            for m in messages if m.get("role") in ("system", "user", "assistant", "mico", "model")]


def _delta_of(data):
    """Кусочек текста из строки потока: формат Workers AI ({"response": …}) или OpenAI (choices[0].delta.content)."""
    if not isinstance(data, dict):
        return ""
    if isinstance(data.get("response"), str):
        return data["response"]
    if data.get("type") == "response.output_text.delta" and isinstance(data.get("delta"), str):
        return data["delta"]                          # поток формата Responses API (модели gpt-oss)
    try:
        return str(data["choices"][0]["delta"].get("content") or "")
    except (KeyError, IndexError, TypeError, AttributeError):
        return ""


def _post_chat(token, body, base, timeout, stream):
    requests = _requests()
    url = base_url(base) + "/api/chat"
    try:
        return requests.post(url, json=body, headers={"Authorization": "Bearer " + token, "User-Agent": "Mico/cloud"},
                             timeout=timeout, stream=stream)
    except requests.Timeout as e:
        raise APIError("Облако Mico не ответило вовремя. Повтори чуть позже.") from e
    except requests.RequestException as e:
        raise APIError("Не получилось подключиться к облаку Mico. Проверь интернет.") from e


def generate(provider, key, messages, timeout=TIMEOUT, model=None, base=None, temperature=None, on_delta=None):
    """Ответ облака. model: режим «auto», «fast» или «smart». on_delta получает текст кусочками, пока он приходит."""
    if provider not in PROVIDERS:
        raise APIError("Выбран неизвестный облачный источник.")
    token = _token(key) or register(base)
    _MEMORY["token"] = token
    stream = on_delta is not None
    body = {"messages": _messages(messages), "mode": normalize_mode(model), "max_tokens": 700, "stream": stream,
            "temperature": 0.7 if temperature is None else float(temperature)}
    response = _post_chat(token, body, base, STREAM_TIMEOUT if stream else timeout, stream)
    if response.status_code == 401:                    # токен не подошёл (ключ шлюза сменили): получаем новый и пробуем один раз
        token = register(base)
        response = _post_chat(token, body, base, STREAM_TIMEOUT if stream else timeout, stream)
    if response.status_code != 200:
        _raise_response(response)
    if not stream:
        try:
            data = response.json()
            text = str(data.get("text") or "").strip()
            LAST.update(mode=str(data.get("mode") or ""), model=str(data.get("model") or ""), downgraded=bool(data.get("downgraded")))
            qd = data.get("quota") or {}
            _update_quota(qd.get("left"), qd.get("install_left"), qd.get("global_left"), qd.get("install_limit"))
        except Exception:
            text = ""
        if not text:
            raise APIError("Облако Mico ответило пусто.")
        return text
    parts = []
    try:
        hdr = getattr(response, "headers", None) or {}
        LAST.update(mode=str(hdr.get("x-mico-model") or ""), model=str(hdr.get("x-mico-name") or ""), downgraded=str(hdr.get("x-mico-down")) == "1")
        _quota_from_headers(hdr)
    except Exception:
        pass
    try:
        for raw in response.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            chunk = raw[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                piece = _delta_of(json.loads(chunk))
            except ValueError:
                continue
            if piece:
                parts.append(piece)
                try:
                    on_delta(piece)
                except Exception:
                    pass                                # живой предпросмотр не должен ронять ответ
    except Exception as e:
        if not parts:
            raise APIError("Связь с облаком Mico оборвалась. Повтори вопрос.") from e
    text = "".join(parts).strip()
    if not text:
        raise APIError("Облако Mico ответило пусто.")
    try:
        fetch_quota(base, timeout=5)                  # после потока уточняем остаток: цена запроса известна шлюзу точно
    except Exception:
        pass
    return text


def generate_vision(provider, key, text, image_url, model=None, base=None, timeout=TIMEOUT):
    """Снимок экрана в облако Mico не уходит: рассматривать экран через чужие серверы я не буду."""
    raise APIError("Экран я пока не рассматриваю: снимки не отправляются в облако. Опиши словами, что на экране.")


def list_models(key=None, base=None, timeout=TIMEOUT):
    """Режимы ответа Mico Cloud. Сети не нужно: список зашит в программе."""
    return list(MODE_IDS)
