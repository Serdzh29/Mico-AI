"""Обновляет файлы значка (assets/mico.png и assets/mico.ico) по настоящему Mico из приложения.

Запуск (на Windows, из папки проекта):  python tools/export_icon.py [#цвет]
Внутри программы значок окон, панели задач и настроек и так рисуется с живого Mico на лету; этот скрипт нужен только для
файла значка самого Mico.exe и ярлыков — их Windows берёт из .ico при сборке (build_exe.bat)."""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from PyQt6.QtWidgets import QApplication  # noqa: E402

from ui import appicon  # noqa: E402


def main():
    app = QApplication(sys.argv)
    color = sys.argv[1] if len(sys.argv) > 1 else "#FFCFA3"
    pm = appicon.blob_pixmap(256, color)
    if pm is None:
        print("Не получилось нарисовать Mico")
        return 1
    out = os.path.join(HERE, "assets")
    pm.save(os.path.join(out, "mico.png"), "PNG")
    ok = pm.save(os.path.join(out, "mico.ico"), "ICO")
    print("Готово: assets/mico.png" + (" и assets/mico.ico" if ok else " (ICO не записался — сохрани PNG в .ico любым конвертером)"))
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
