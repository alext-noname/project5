@echo off
setlocal
cd /d "%~dp0"

where python.exe >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or newer with Tkinter is required.
    pause
    exit /b 1
)

python.exe -c "import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or newer with Tkinter is required.
    pause
    exit /b 1
)

where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0app.py"
    exit /b 0
)

python.exe "%~dp0app.py"
