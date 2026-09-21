# Qwen Romance Runtime

`agent-skills` defines the Qwen Romance rules. This repository is the executable local host: it probes a local Qwen runtime, applies the fail-closed gate, composes a compact prompt, manages token budget, generates multiple internal Chunks, merges them into one Visible Reply, and persists state in SQLite.

The first release is intentionally a small FastAPI service with a static browser UI. It supports adapters for Ollama, llama.cpp server, and LM Studio's OpenAI-compatible endpoint. Adapter field names are kept inside the adapter; the controller only receives a normalized `GenerationResult`.

## Current boundary

The runtime is complete at the code and mock-integration layer. A real local-Qwen smoke test is environment-dependent: run `python scripts/doctor.py` first. The service must identify a local model as `family=qwen`; otherwise it returns `MODEL_NOT_QWEN` before loading the Skill. No GPT or unknown model can activate Qwen Romance.

The default profiles are task-scoped:

| Profile | Soft minimum | Preferred | Ceiling |
| --- | ---: | ---: | ---: |
| short | 300 | 800 | 1500 |
| normal | 1200 | 2200 | 3500 |
| long | 2500 | 4000 | 6500 |
| very_long | 5000 | 8000 | 12000 |

Interactive mode defaults to `long`; autonomous novel mode defaults to `very_long`. A scene can stop below a soft minimum when it naturally completes. An open scene is eligible for automatic continuation, up to four internal Chunks by default.

## Start on Windows

```powershell
Copy-Item config.example.yaml config.yaml
.\scripts\start.ps1
```

The script creates a virtual environment, installs dependencies, syncs the canonical `qwen-romance` Skill into the verified local cache, probes the three supported local backends, then starts `http://127.0.0.1:8765`.

To inspect without starting the server:

```powershell
python scripts/doctor.py
python scripts/smoke_test.py
```

`smoke_test.py` only reports a live PASS when a real local Qwen endpoint is found and the request completes. It never treats a mock as a live result.

## HTTP API

- `GET /health`
- `GET /api/runtime/probe`
- `POST /api/sessions` with `{ "title": "...", "run_mode": "interactive" }`
- `GET /api/sessions/{id}`
- `POST /api/chat` with `{ "session_id": "...", "message": "继续", "length": "long", "run_mode": "interactive" }`
- `POST /api/generation/{job_id}/cancel`

The controller uses one `asyncio.Semaphore` for model work. Chunk retry, partial output retention, cancellation, boundary overlap removal, context budget reserve, and SQLite checkpointing are code paths rather than prompt promises.

## Tests

```powershell
python -m pytest
```

The unit and mock-integration tests cover model gating, task-scoped length commands, dynamic budget failure before overflow, overlap merging, premature closure detection, deterministic event IDs, SQLite uniqueness, multi-Chunk persistence, and non-Qwen Skill-loader isolation. Live tests are intentionally separate and only run when a local endpoint is present.

The rules remain canonical in [`agent-skills`](https://github.com/1948666760dty-sys/agent-skills); this runtime reads the cached copy instead of requesting GitHub on every generation.

