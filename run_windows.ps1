$ErrorActionPreference = "Stop"

$pythonCommand = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $pythonCommand -m venv .venv
}

$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --disable-pip-version-check --upgrade pip
& $python -m pip install --disable-pip-version-check -r requirements.txt
& $python app.py
