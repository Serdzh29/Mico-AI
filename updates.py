"""Файл бета-сборки и контрольная сумма SHA-256. Файл содержит каналы:
{"channels": {"beta": {"version": "…", "url": "https://…/Mico.exe", "sha256": "…", "notes": "…"}}}.
Адрес файла задаёт разработчик (version.BETA_INFO_URL), пользователь его не меняет."""
import json


def parse(text):
    data = json.loads(text)
    if not isinstance(data, dict) or not str(data.get("version", "")).strip():
        raise ValueError("в файле обновлений нет номера версии")
    return {"version": str(data["version"]).strip(), "url": str(data.get("url", "")).strip(),
            "notes": str(data.get("notes", "")).strip(), "sha256": str(data.get("sha256", "")).strip()}


def verify_sha256(path, expected):
    """Совпадает ли файл с контрольной суммой из файла обновлений (SHA-256, в любом регистре)."""
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().lower() == str(expected or "").strip().lower()
