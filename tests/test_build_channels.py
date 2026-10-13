"""Две сборки: стабильная и бета. Помодоро — в обеих, остальные бета-функции — только в бете."""
import os as _os
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)

import features
import version
import capabilities

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

BETA_CFG = {"update_channel": "beta"}
STABLE_CFG = {"update_channel": "stable"}

# помодоро — стабильная функция
check(not features.is_beta("pomodoro"), "помодоро должно быть стабильным")
for name in ("planner", "initiative", "recurring"):
    check(features.is_beta(name), f"{name} должна оставаться бета-функцией")

saved = version.BUILD_CHANNEL
try:
    # стабильная сборка
    version.BUILD_CHANNEL = "stable"
    check(features.enabled("pomodoro", STABLE_CFG), "помодоро есть в стабильной сборке")
    check(features.enabled("pomodoro", BETA_CFG) is True, "помодоро работает и при любом канале")
    check(not features.enabled("planner", BETA_CFG), "в стабильной сборке бета-функции выключены, даже если канал beta")
    check(not features.enabled("initiative", BETA_CFG), "инициатива не работает в стабильной сборке")
    check(features.channel(BETA_CFG) == "stable", "стабильная сборка не переключается на бету из настроек")

    # бета-сборка
    version.BUILD_CHANNEL = "beta"
    check(features.enabled("pomodoro", STABLE_CFG), "помодоро есть и в бете")
    check(features.enabled("planner", BETA_CFG), "в бете бета-функции доступны на бета-канале")
    check(not features.enabled("planner", STABLE_CFG), "на стабильном канале бета-функции выключены")
    check(features.channel(BETA_CFG) == "beta", "бета-сборка работает на выбранном канале")
finally:
    version.BUILD_CHANNEL = saved

# помодоро не помечено бета-фразой
check("помодоро" not in capabilities.BETA_PHRASES, "помодоро больше не бета-фраза")
check(version.BUILD_CHANNEL == "stable", "в репозитории стоит стабильная сборка")
print("ALL OK")
