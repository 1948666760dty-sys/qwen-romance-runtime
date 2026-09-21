$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.12 -m venv .venv }
& .venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path 'config.yaml')) { Copy-Item config.example.yaml config.yaml }
& .venv\Scripts\python.exe scripts\sync_skills.py
& .venv\Scripts\python.exe scripts\doctor.py
& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765

