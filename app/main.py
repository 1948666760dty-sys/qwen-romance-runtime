from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .runtime.probe import adapters, probe_all, select_adapter
from .generation.controller import ChatRequest, LongOutputController
from .skills.loader import SkillLoader
from .state.store import StateStore


def create_app(config: AppConfig | None = None):
    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Web UI 需要安装 requirements.txt；核心模块和测试不依赖 FastAPI") from exc

    cfg = config or load_config(os.getenv("QRR_CONFIG"))
    store = StateStore(cfg.database)
    loader = SkillLoader(cfg.skill_cache_dir)
    app = FastAPI(title="Qwen Romance Runtime", version="0.1.0")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web"), name="static")
    app.state.config = cfg
    app.state.store = store
    app.state.loader = loader
    app.state.controllers: dict[str, LongOutputController] = {}

    class SessionRequest(BaseModel):
        title: str = "Qwen Romance Session"
        run_mode: str = "interactive"

    class ChatRequestBody(BaseModel):
        session_id: str
        message: str = Field(min_length=1)
        length: str | None = None
        run_mode: str = "interactive"

    async def controller_for(session_id: str) -> LongOutputController:
        controller = app.state.controllers.get(session_id)
        if controller:
            return controller
        adapter, _ = await select_adapter(cfg.runtime, cfg.timeout)
        controller = LongOutputController(adapter, store, loader, cfg.generation)
        app.state.controllers[session_id] = controller
        return controller

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "qwen-romance-runtime", "version": "0.1.0"}

    @app.get("/api/runtime/probe")
    async def runtime_probe():
        results = await probe_all(cfg.runtime, cfg.timeout)
        return {"results": [{"backend": r.backend, "info": r.info.__dict__ if r.info else None, "error": r.error} for r in results]}

    @app.post("/api/sessions")
    async def create_session(body: dict[str, Any] = Body(default_factory=dict)):
        title = str(body.get("title", "Qwen Romance Session"))
        run_mode = str(body.get("run_mode", "interactive"))
        return store.create_session(run_mode, title).__dict__

    @app.get("/api/sessions/{session_id}")
    async def get_session(session_id: str):
        session = store.get_session(session_id)
        if not session:
            raise HTTPException(404, "SESSION_NOT_FOUND")
        return session.__dict__

    @app.post("/api/chat")
    async def chat(body: dict[str, Any] = Body(...)):
        if not body.get("session_id") or not body.get("message"):
            raise HTTPException(422, "session_id and message are required")
        try:
            controller = await controller_for(str(body["session_id"]))
            result = await controller.generate(ChatRequest(str(body["session_id"]), str(body["message"]), str(body.get("run_mode", "interactive")), body.get("length")))
            return result.__dict__
        except PermissionError as exc:
            raise HTTPException(409, str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, f"RUNTIME_ERROR: {exc}") from exc

    @app.post("/v1/chat/completions")
    async def openai_compatible_chat(body: dict[str, Any] = Body(...)):
        """OpenAI-shaped local compatibility endpoint; it never changes provider=local/family=qwen."""
        messages = body.get("messages") or []
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            raise HTTPException(422, "messages must contain a user message")
        session_id = body.get("session_id")
        if not session_id:
            session_id = store.create_session(str(body.get("run_mode", "interactive")), "OpenAI-compatible Qwen session").id
        prompt = str(user_messages[-1].get("content", ""))
        try:
            controller = await controller_for(str(session_id))
            result = await controller.generate(ChatRequest(str(session_id), prompt, str(body.get("run_mode", "interactive")), body.get("length")))
        except PermissionError as exc:
            raise HTTPException(409, str(exc)) from exc
        except Exception as exc:
            raise HTTPException(502, f"RUNTIME_ERROR: {exc}") from exc
        return {
            "id": result.message_id,
            "object": "chat.completion",
            "model": body.get("model", "local-qwen"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": result.text}, "finish_reason": "stop" if not result.partial else "length"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": result.generated_tokens, "total_tokens": result.generated_tokens},
            "qwen_runtime": {"provider": "local", "family": "qwen", "chunks": result.chunks, "chars": result.chars, "partial": result.partial},
        }

    @app.post("/api/generation/{job_id}/cancel")
    async def cancel(job_id: str):
        for controller in app.state.controllers.values():
            if await controller.cancel(job_id):
                return {"cancelled": True, "job_id": job_id}
        raise HTTPException(404, "JOB_NOT_FOUND")

    @app.get("/")
    async def index():
        return FileResponse(Path(__file__).parent / "web" / "index.html")

    return app


app = create_app() if os.getenv("QRR_DISABLE_APP") != "1" else None
