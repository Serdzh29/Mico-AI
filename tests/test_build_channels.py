"""Канал сборки: беты больше нет, все функции стабильные в любом канале."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)

from core import features
from setup import version
from core import capabilities

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

BETA_CFG = {"update_channel": "beta"}
STABLE_CFG = {"update_channel": "stable"}

# помодоро — стабильная функция
check(not features.is_beta("pomodoro"), "помодоро должно быть стабильным")
for name in ("planner", "recurring"):
    check(not features.is_beta(name), f"{name}: бета-функций больше нет")

saved = version.BUILD_CHANNEL
try:
    # стабильная сборка
    version.BUILD_CHANNEL = "stable"
    check(features.enabled("pomodoro", STABLE_CFG), "помодоро есть в стабильной сборке")
    check(features.enabled("pomodoro", BETA_CFG) is True, "помодоро работает и при любом канале")
    check(features.enabled("planner", BETA_CFG), "беты нет: все функции стабильные")
    pass  # канал больше не выбирают: беты нет

    # бета-сборка
    version.BUILD_CHANNEL = "beta"
    check(features.enabled("pomodoro", STABLE_CFG), "помодоро есть и в бете")
    check(features.enabled("planner", BETA_CFG), "в бете бета-функции доступны на бета-канале")
    check(features.enabled("planner", STABLE_CFG), "все функции доступны на стабильном канале")
    pass  # канал больше не выбирают: беты нет
finally:
    version.BUILD_CHANNEL = saved

# бета-фраз больше нет: помодоро и так стабильно
check(not hasattr(capabilities, "BETA_PHRASES"), "бета-фраз в возможностях больше нет")
check(version.BUILD_CHANNEL == "stable", "в репозитории стоит стабильная сборка")
print("ALL OK")
