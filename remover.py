"""Скрипт удаления Mico (remove_mico.cmd). Не запускает Mico.exe, поэтому работает, даже если сам Mico
не стартует из-за запроса прав («требует повышения»). Не требует прав администратора."""


def script(install_dir, appdata_dir):
    """Текст .cmd. Только ASCII: cmd читает такие файлы одинаково на любой кодовой странице."""
    lines = [
        "@echo off",
        "echo Removing Mico...",
        "taskkill /IM Mico.exe /F >nul 2>&1",
        "schtasks /Delete /TN Mico /F >nul 2>&1",
        'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v Mico /f >nul 2>&1',
        'reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Mico" /f >nul 2>&1',
        'del /f /q "%USERPROFILE%\\Desktop\\Mico.lnk" >nul 2>&1',
        "choice /c YN /n /m \"Also delete history and settings? [Y/N] \"",
        "if errorlevel 2 (",
        f"  start \"\" powershell -NoProfile -WindowStyle Hidden -Command \"Start-Sleep 3; "
        f"Remove-Item -Recurse -Force -LiteralPath '{install_dir}'\"",
        ") else (",
        f"  start \"\" powershell -NoProfile -WindowStyle Hidden -Command \"Start-Sleep 3; "
        f"Remove-Item -Recurse -Force -LiteralPath '{install_dir}','{appdata_dir}'\"",
        ")",
        "echo Done. Mico is removed.",
    ]
    return "\r\n".join(lines) + "\r\n"
