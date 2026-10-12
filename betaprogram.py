"""Программа предварительной оценки (бета). Здесь только логика без окон: какую сборку считать бетой,
когда показывать приветствие и что в нём сказать, как поставить бету на место старой программы.
Окна, скачивание и запуск — в main.py и installer.py."""
import json
import os
import shutil
import subprocess
import tempfile
import time

import features
import updates

TITLE = "Программа предварительной оценки"
JOIN_FLAG = "--beta-install"                    # временная копия с этим флагом ставит бету на место старой
DETACHED = 0x00000008 | 0x00000200              # CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS (Windows)


class BetaUnavailable(Exception):
    """Бету нельзя поставить. Текст — для человека."""


def beta_build(text):
    """Бета-сборка из файла обновлений. Берётся только явный канал beta: если его нет, бета
    не подменяется стабильной сборкой."""
    data = json.loads(text)
    chans = data.get("channels") if isinstance(data, dict) else None
    if not isinstance(chans, dict) or not isinstance(chans.get("beta"), dict):
        raise BetaUnavailable("бета-сборка пока не опубликована")
    info = updates.parse(json.dumps(chans["beta"]))
    if not info["url"].startswith("https://"):
        raise BetaUnavailable("в файле обновлений нет безопасной ссылки на бета-сборку")
    if not info["sha256"]:
        raise BetaUnavailable("у бета-сборки нет контрольной суммы, ставить её не буду")
    return info


def download_path(build_version):
    return os.path.join(tempfile.gettempdir(), f"Mico-beta-{build_version}.exe")


def is_join_request(argv):
    return JOIN_FLAG in argv


def consent_given(cfg):
    return cfg.get("beta_consent_version") == features.BETA_CONSENT_VERSION


def needs_welcome(cfg):
    """Приветствие — один раз на каждую бета-установку."""
    return cfg.get("update_channel") == "beta" and cfg.get("beta_welcome_version") != features.BETA_WELCOME_VERSION


def beta_feature_list():
    return [(key, item) for key, item in features.FEATURES.items() if features.is_beta(key)]


def welcome_lines(app_version):
    """Реплики приветствия по одной. Перечисляем каждую бета-функцию и то, что она делает."""
    lines = [f"Ура! Я теперь на бета-версии {app_version}! Сейчас покручусь от радости.",
             "В бете появились новые функции. Вот что каждая из них делает:"]
    for _, item in beta_feature_list():
        lines.append(f"• {item['title']}: {item['explain']}")
    lines.append("Бета может сбоить. Если что-то пошло не так, нажми в меню «🐞 Сохранить отчёт об ошибке» — "
                 "письмо разработчику откроется с готовым текстом.")
    lines.append("Передумаешь — в ⚙ Настройки → Бета снимешь галочку, и я вернусь на стабильный канал.")
    return lines


def replace_when_free(src, dest, tries=120, pause=0.5, sleep=time.sleep):
    """Копирует новый Mico.exe на место старого. Windows не даёт писать в запущенный exe,
    поэтому ждём, пока старая копия закроется. True — копия на месте."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    for _ in range(tries):
        try:
            with open(dest, "ab"):              # занят — PermissionError; свободен — можно копировать
                pass
            shutil.copy2(src, dest)
            return True
        except OSError:
            sleep(pause)
    return False


def launch(path, args=()):
    """Запускает программу отдельно от текущей: она переживёт закрытие этой копии."""
    subprocess.Popen([path, *args], close_fds=True, creationflags=DETACHED)
