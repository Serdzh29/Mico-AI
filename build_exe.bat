@echo off
rem Builds Mico.exe: one file, no console. Put a picture into assets\mico.png (optional).
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (echo Could not install requirements. & pause & exit /b 1)
set "DATA="
set "ICON="
if exist "assets\mico.ico" set "ICON=--icon assets\mico.ico"
if exist "assets" set "DATA=%DATA% --add-data assets;assets"
if exist "knowledge" set "DATA=%DATA% --add-data knowledge;knowledge"
if exist "data" set "DATA=%DATA% --add-data data;data"
python -m PyInstaller --noconsole --onefile --clean --name Mico %DATA% %ICON% ^
  --hidden-import win32crypt --hidden-import win32com.client --hidden-import pythoncom ^
  --hidden-import pywintypes --collect-all vosk --collect-all sounddevice --exclude-module tkinter main.py
if errorlevel 1 (echo Build failed. See the messages above. & pause & exit /b 1)
echo.
echo Done: dist\Mico.exe
pause
