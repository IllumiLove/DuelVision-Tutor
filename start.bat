@echo off
cd /d "%~dp0"
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
".venv\Scripts\python.exe" -m src.main
pause
