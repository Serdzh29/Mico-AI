"""Безопасность: модель не открывает программы и скрипты; опасные действия требуют подтверждения."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import osagent as O

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def test_executables_and_scripts_detected():
    for p in [r"C:\Users\u\Downloads\setup.exe", r"C:\x\run.BAT", r"C:\x\a.ps1", r"C:\x\b.vbs", r"C:\x\c.lnk"]:
        check(O.is_executable(p), p)
    for p in [r"C:\Users\u\Downloads\отчёт.pdf", r"C:\Users\u\Documents\папка", r"C:\x\фото.png"]:
        check(not O.is_executable(p), p)

def test_model_cannot_open_executable():
    for p in [r"C:\x\evil.exe", r"C:\x\run.bat"]:
        try:
            O.validate({"action": "open_file", "args": {"path": p}})
        except ValueError:
            continue
        raise AssertionError("исполняемый файл не должен открываться: " + p)

def test_model_can_open_documents_and_confirm_rules():
    name, args = O.validate({"action": "open_file", "args": {"path": r"C:\Users\u\Documents\отчёт.pdf"}})
    check(name == "open_file")
    check(O.needs_confirm("run_powershell") and O.needs_confirm("set_service"), "опасное требует «да»")
    check(O.is_executable("x.exe") and not O.is_executable("x.pdf"), "различаем программы и документы")

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
