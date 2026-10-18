@echo off
rem Starts Mico. A window appears only if something is wrong.
cd /d "%~dp0"
set "APP=%~dp0main.py"
set "DIR=%APPDATA%\Mico"
set "LOG=%DIR%\launch.log"
if not exist "%DIR%" mkdir "%DIR%"
echo %date% %time% start requested from %~dp0 >> "%LOG%"
if not exist "%APP%" (
  echo main.py was not found next to Mico.bat.
  echo Folder: %~dp0
  echo Put Mico.bat in the same folder as main.py and run it again.
  pause
  exit /b 1
)
where py >nul 2>nul && (set "PY=py -3" & goto find)
where python >nul 2>nul && (set "PY=python" & goto find)
echo Python was not found.
echo Install Python 3.10 or newer from python.org and tick 'Add python.exe to PATH'.
pause
exit /b 1
:find
for /f "usebackq delims=" %%P in (`%PY% -c "import sys,os;print(sys.executable)"`) do set "PYEXE=%%P"
set "PYWEXE=%PYEXE:python.exe=pythonw.exe%"
if not exist "%PYWEXE%" set "PYWEXE=%PYEXE%"
%PYEXE% -c "import PyQt6, win32gui, win32crypt, psutil, mss, PIL, requests, cryptography" 2>"%LOG%"
if errorlevel 1 (
  echo.
  echo Some libraries are missing. Run this in the Mico folder:
  echo     pip install -r requirements.txt
  echo Details are in: %LOG%
  echo If Python is not really installed (Microsoft Store opens instead), install it from python.org
  echo and turn off 'python.exe' under Settings - App execution aliases.
  pause
  exit /b 1
)
echo launching "%PYWEXE%" "%APP%" >> "%LOG%"
start "" "%PYWEXE%" "%APP%"
exit /b 0
