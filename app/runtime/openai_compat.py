from __future__ import annotations

import asyncio
import time
from typing import Any

from .base import GenerationResult, ModelInfo, RuntimeAdapter, RuntimeInfo, normalize_family


class OpenAICompatibleAdapter(RuntimeAdapter):
    def __init__(self, base_url: str, backend: str, timeout_seconds: float = 10.0):
        super().__init__(base_url, timeout_seconds)
        self.backend = backend
        self._model: ModelInfo | None = None
        self._context_length = 32768

    async def _json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

    async def list_models(self) -> list[ModelInfo]:
        payload = await self._json("GET", "/v1/models")
        models = []
        for item in payload.get("data", []):
            model_id = str(item.get("id", ""))
            family = normalize_family(item.get("family") or item.get("architecture"), model_id)
            models.append(ModelInfo(model_id, family, item.get("architecture"), item.get("context_length")))
        return models

    async def probe(self) -> RuntimeInfo:
        models = await self.list_models()
        self._model = models[0] if models else None
        if self._model and self._model.context_length:
            self._context_length = int(self._model.context_length)
        return RuntimeInfo(self.backend, self.base_url, None, self._model.model_id if self._model else None,
                           self._model.family if self._model else "unknown", True, self._context_length, False,
                           ("chat_completions", "models"))

    async def count_tokens(self, messages: list[dict[str, str]]) -> int:
        # LM Studio and llama.cpp adapters override this when their native endpoint exists.
        text = "\n".join(m.get("content", "") for m in messages)
        return max(1, int(len(text) * 1.2 / 2.0))

    async def generate(self, messages, max_new_tokens, sampling=None, cancel_event=None) -> GenerationResult:
        if cancel_event and cancel_event.is_set():
            return GenerationResult("", 0, 0, "cancel")
        if not self._model:
            await self.probe()
        started = time.monotonic()
        body: dict[str, Any] = {"model": self._model.model_id if self._model else None, "messages": messages,
                                "stream": False, "max_tokens": max_new_tokens}
        if sampling:
            body.update(sampling)
        data = await self._json("POST", "/v1/chat/completions", json=body)
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "")
        usage = data.get("usage") or {}
        reason = str(choice.get("finish_reason") or "stop")
        reason = "limit" if reason in {"length", "limit"} else "stop"
        if cancel_event and cancel_event.is_set():
            reason = "cancel"
        return GenerationResult(text, int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0), reason, reason == "limit", int((time.monotonic() - started) * 1000))

