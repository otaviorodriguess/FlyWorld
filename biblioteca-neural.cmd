@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m flyworld --mode demo --library %*
if errorlevel 1 pause
