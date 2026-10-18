@echo off
rem Manual cleanup of Mico when the normal uninstall does not work.
rem Removes: running Mico processes, the program folder, the desktop shortcut,
rem autostart entry and the "Installed apps" entry. Does NOT touch Ollama, models or Mico data
rem unless you answer Y to the last question. No administrator rights are needed.
echo Stopping Mico...
taskkill /f /im Mico.exe >nul 2>&1
echo Removing program folder...
rmdir /s /q "%LOCALAPPDATA%\Programs\Mico" >nul 2>&1
echo Removing desktop shortcut...
del /f /q "%USERPROFILE%\Desktop\Mico.lnk" >nul 2>&1
echo Removing autostart entry...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v Mico /f >nul 2>&1
echo Removing entry from Installed apps...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\Mico" /f >nul 2>&1
echo.
set /p ANSWER=Also delete Mico history, settings and reminders in %APPDATA%\Mico? [Y/N]: 
if /i "%ANSWER%"=="Y" (
  rmdir /s /q "%APPDATA%\Mico" >nul 2>&1
  echo Mico data deleted.
) else (
  echo Mico data kept.
)
echo.
echo Done. Mico is removed from the program folder and from autostart.
pause
