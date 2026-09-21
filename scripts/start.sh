#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then python3.12 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
[[ -f config.yaml ]] || cp config.example.yaml config.yaml
.venv/bin/python scripts/sync_skills.py
.venv/bin/python scripts/doctor.py
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8765

