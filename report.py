"""Отчёт об ошибке для баг-репорта: журналы, настройки без секретов и личных данных, версия и сборка Windows.
Журнал окон, история команд и напоминания в отчёт не попадают. Ничего не отправляется само."""
import json, os, platform, time, zipfile

from settings_io import PERSONAL_KEYS, SECRET_KEYS

LOGS = ["startup.log", "crash.log", "native_crash.log", "launch.log"]
README = """Отчёт Mico для разработчика.
Внутри: журналы запуска и сбоев (если есть), настройки без ключей и личных данных, сведения о системе.
Журналы могут содержать пути к файлам на твоём ПК. Перед отправкой проверь файлы.
Отправь этот zip тому, кто тестирует Mico. Сам Mico ничего никуда не отправляет.
"""


def build_report(appdir, dest_dir, app_version, cfg, windows_build=None, extra=None):
    os.makedirs(dest_dir, exist_ok=True)
    name = time.strftime("Mico_report_%Y%m%d_%H%M%S.zip")
    path = os.path.join(dest_dir, name)
    clean = {k: v for k, v in cfg.items() if k not in SECRET_KEYS | PERSONAL_KEYS}
    info = {"mico_version": str(app_version), "windows_build": windows_build,
            "system": platform.platform(), "python": platform.python_version(),
            "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    included = []
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("README.txt", README)
        z.writestr("info.json", json.dumps(info, ensure_ascii=False, indent=2))
        z.writestr("settings.json", json.dumps(clean, ensure_ascii=False, indent=2))
        for fname, body in (extra or {}).items():     # например, отзывы — только если человек согласился
            z.writestr(fname, body)
            included.append(fname)
        for log in LOGS:
            p = os.path.join(appdir, log)
            if os.path.exists(p):
                z.write(p, arcname=log)
                included.append(log)
    return path, included
