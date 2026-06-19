@echo off
cd /d "%~dp0"
if exist "deskflow.exe" (
    echo Starting Deskflow...
    start "" "deskflow.exe"
) else (
    echo Deskflow.exe not found in this folder. Starting only clipboard sync...
)
powershell -STA -ExecutionPolicy Bypass -File "%~dp0clipsync.ps1"
