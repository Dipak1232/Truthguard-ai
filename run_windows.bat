@echo off
setlocal

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set PYTHON_COMMAND=py
) else (
  set PYTHON_COMMAND=python
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON_COMMAND% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --disable-pip-version-check --upgrade pip
python -m pip install --disable-pip-version-check -r requirements.txt
python app.py
