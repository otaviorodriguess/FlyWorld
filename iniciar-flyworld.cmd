@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Crie o ambiente seguindo FLYWORLD_README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m flyworld %*
if errorlevel 1 pause
