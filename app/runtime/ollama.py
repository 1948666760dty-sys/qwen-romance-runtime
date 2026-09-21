from __future__ import annotations

import asyncio
import time
from typing import Any

from .base import GenerationResult, ModelInfo, RuntimeAdapter, RuntimeInfo, normalize_family


class OllamaAdapter(RuntimeAdapter):
    backend = "ollama"

    async def _json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_models(self) -> list[ModelInfo]:
        payload = await self._json("GET", "/api/tags")
        result = []
        for item in payload.get("models", []):
            model_id = str(item.get("name") or item.get("model") or "")
            result.append(ModelInfo(model_id=model_id, family=normalize_family(model_id)))
        return result

    async def _show(self, model: str | None = None) -> dict[str, Any]:
        models = await self.list_models()
        selected = model or (models[0].model_id if models else None)
        if not selected:
            return {}
        return await self._json("POST", "/api/show", json={"name": selected})

    async def probe(self) -> RuntimeInfo:
        models = await self.list_models()
        selected = models[0] if models else ModelInfo("", "unknown")
        details = await self._show(selected.model_id) if selected.model_id else {}
        model_info = details.get("details", {})
        family = normalize_family(model_info.get("family"), selected.model_id)
        context = int(details.get("model_info", {}).get("context_length", 32768) or 32768)
        return RuntimeInfo(self.backend, self.base_url, None, selected.model_id or None, family, True, context, False, ("chat", "show"))

    async def count_tokens(self, messages: list[dict[str, str]]) -> int:
        # Ollama's public API does not provide a stable preflight tokenizer on all versions.
        # This conservative estimate is surfaced by tokenizer_exact=false in probe().
        text = "\n".join(f"{m.get('role','')}: {m.get('content','')}" for m in messages)
        return max(1, int(len(text) * 1.2 / 2.0))

    async def generate(self, messages, max_new_tokens, sampling=None, cancel_event=None) -> GenerationResult:
        if cancel_event and cancel_event.is_set():
            return GenerationResult("", 0, 0, "cancel", truncated=False)
        info = await self.probe()
        started = time.monotonic()
        payload: dict[str, Any] = {"model": info.model_id, "messages": messages, "stream": False,
                                   "options": {"num_predict": max_new_tokens, "num_ctx": info.context_length}}
        if sampling:
            payload["options"].update(sampling)
        data = await self._json("POST", "/api/chat", json=payload)
        if cancel_event and cancel_event.is_set():
            return GenerationResult(data.get("message", {}).get("content", ""), int(data.get("prompt_eval_count", 0) or 0), int(data.get("eval_count", 0) or 0), "cancel")
        done_reason = str(data.get("done_reason", "stop"))
        reason = "limit" if done_reason in {"length", "limit"} else "stop"
        return GenerationResult(data.get("message", {}).get("content", ""), int(data.get("prompt_eval_count", 0) or 0), int(data.get("eval_count", 0) or 0), reason, reason == "limit", int((time.monotonic() - started) * 1000))

