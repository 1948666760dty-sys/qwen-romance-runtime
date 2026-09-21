#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import load_config
from app.generation.controller import ChatRequest, LongOutputController
from app.runtime.probe import select_adapter
from app.skills.loader import SkillLoader
from app.state.store import StateStore


async def main(config_path: str | None = None) -> int:
    cfg = load_config(config_path)
    try:
        adapter, info = await select_adapter(cfg.runtime, cfg.timeout)
    except Exception as exc:
        payload = {"status": "LIVE_QWEN_REQUIRED", "message": "未发现可用的本地 Qwen Runtime；请启动 Ollama、LM Studio 或 llama.cpp 后重试。", "error": str(exc)}
        Path("data").mkdir(exist_ok=True)
        Path("data/smoke-result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 4
    if info.model_family != "qwen":
        print(json.dumps({"status": "MODEL_NOT_QWEN", "info": info.__dict__}, ensure_ascii=False, indent=2))
        return 2
    store = StateStore(cfg.database)
    session = store.create_session("interactive", "Live Qwen Smoke")
    controller = LongOutputController(adapter, store, SkillLoader(cfg.skill_cache_dir), cfg.generation)
    result = await controller.generate(ChatRequest(session.id, "写一个尚未结束的长场景，并保持人物和场景连续。", "interactive", "long"))
    payload = {"status": "PASS" if result.text and not result.partial else "PARTIAL", "info": info.__dict__, "result": result.__dict__}
    Path("data").mkdir(exist_ok=True)
    Path("data/smoke-result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "PASS" else 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.config)))
