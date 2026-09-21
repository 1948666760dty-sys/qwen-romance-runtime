#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import load_config
from app.runtime.probe import probe_all


async def main(path: str | None = None) -> int:
    cfg = load_config(path)
    results = await probe_all(cfg.runtime, cfg.timeout)
    payload = []
    for result in results:
        payload.append({"backend": result.backend, "found": result.info is not None,
                        "info": result.info.__dict__ if result.info else None, "error": result.error})
        if result.info:
            print(f"{result.backend}: FOUND model={result.info.model_id} family={result.info.model_family} context={result.info.context_length} tokenizer_exact={result.info.tokenizer_exact}")
        else:
            print(f"{result.backend}: not running ({result.error})")
    Path("data").mkdir(exist_ok=True)
    Path("data/doctor.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.config)))

