"""Дымовой тест Qt: запускает голосовую полоску и Mico без экрана (offscreen) и ловит исключения.
Запуск: python tests/smoke_qt.py  (нужны PyQt6 и numpy из requirements.txt).
Не проверяет вид и плавность — только что окна создаются, переходы не падают, есть скриншоты.
Скриншоты пишутся в smoke_out/ (в CI — артефакт)."""
import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "smoke_out")
os.makedirs(OUT, exist_ok=True)

from PyQt6.QtWidgets import QApplication  # noqa: E402

failures = []


def step(name, fn):
    try:
        fn()
        print(f"OK   {name}")
    except Exception:
        failures.append(name)
        print(f"FAIL {name}")
        traceback.print_exc()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    cfg = {"scale": 1.0, "opacity": 1.0, "voice_subs": False, "voice_name": "irina", "voice_on": False}

    from voice import dock as voice_dock
    from ui import blob as blob_mod

    b = blob_mod.Blob(cfg)
    dock = voice_dock.VoiceDock(cfg)
    step("создать окно Mico", lambda: b.show())
    step("создать полоску", lambda: dock.show())

    def enter():
        dock.show_stage(b)
        app.processEvents()
        dock.grab().save(os.path.join(OUT, "bar_full.png"))
    step("вход в голосовой бар", enter)

    def detach():
        dock.toggle_detach()
        app.processEvents()
        dock.grab().save(os.path.join(OUT, "bar_controls.png"))
    step("вынуть Mico (только кнопки)", detach)

    step("вернуть Mico в бар", lambda: (dock.toggle_detach(), app.processEvents()))
    step("сон в обводке", lambda: (dock.sleep_pill(), app.processEvents()))
    step("пробуждение из обводки", lambda: (dock.expand_pill(), app.processEvents()))
    step("субтитры включены", lambda: (cfg.update(voice_subs=True), dock.refresh(False), dock.show_mico("Проверка субтитров"), app.processEvents()))
    step("панель голоса открыта", lambda: (dock._show_section(dock.settings), app.processEvents()))
    step("панель цвета открыта", lambda: (dock._show_section(dock.colors), app.processEvents()))
    step("закрыть полоску", lambda: dock.dismiss(return_to=None, after=None))

    if failures:
        print(f"\nупали шаги: {', '.join(failures)}")
        return 1
    print("\nвсе шаги прошли; скриншоты в smoke_out/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
