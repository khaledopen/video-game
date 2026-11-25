@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Premiere utilisation : installation de Python et des dependances dans ce dossier...
    powershell -ExecutionPolicy Bypass -File "%~dp0installer.ps1"
    if errorlevel 1 (
        echo L'installation a echoue.
        pause
        exit /b 1
    )
)
start "" ".venv\Scripts\pythonw.exe" main.py %*
