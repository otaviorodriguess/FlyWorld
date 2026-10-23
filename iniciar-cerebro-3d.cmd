@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Crie o ambiente seguindo FLYWORLD_README.md.
  pause
  exit /b 1
)
pushd web
call npm run build
if errorlevel 1 (
  popd
  pause
  exit /b 1
)
popd
".venv\Scripts\python.exe" -m flyworld.neural_service %*
if errorlevel 1 pause
