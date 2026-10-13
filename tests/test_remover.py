"""Скрипт удаления Mico: содержит все шаги и только ASCII (cmd не должен ломаться на кодировке)."""
import os as _os, sys
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import remover

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

t = remover.script(r"C:\Mico", r"C:\Data\Mico")
check(all(ord(c) < 128 for c in t), "скрипт должен быть ASCII")
for key in ["taskkill /IM Mico.exe", "schtasks /Delete /TN Mico", "CurrentVersion\\Run", "Uninstall\\Mico",
            "Mico.lnk", "choice /c YN", "errorlevel 2", "Remove-Item -Recurse -Force -LiteralPath"]:
    check(key in t, key)
check("Start-Sleep" in t and "Mico.exe --uninstall" not in t, "удаление не должно запускать Mico.exe")
print("ALL OK")
