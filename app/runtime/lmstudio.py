from __future__ import annotations

from .openai_compat import OpenAICompatibleAdapter
from .base import RuntimeInfo


class LMStudioAdapter(OpenAICompatibleAdapter):
    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        super().__init__(base_url, "lmstudio", timeout_seconds)

    async def probe(self) -> RuntimeInfo:
        info = await super().probe()
        # LM Studio may expose architecture/context in /api/v0/models. A missing optional endpoint
        # must not turn a confirmed local endpoint into an assumed Qwen model.
        try:
            payload = await self._json("GET", "/api/v0/models")
            item = (payload.get("data") or [None])[0]
            if item:
                from .base import normalize_family
                family = normalize_family(item.get("architecture") or item.get("type"), item.get("id"))
                context = int(item.get("max_context_length") or item.get("context_length") or info.context_length)
                self._context_length = context
                if self._model:
                    self._model = type(self._model)(self._model.model_id, family, item.get("architecture"), context)
                info = RuntimeInfo(info.backend, info.base_url, info.runtime_version, info.model_id, family, True, context, True, info.capabilities + ("native_model_info",))
        except Exception:
            pass
        return info

    async def count_tokens(self, messages):
        try:
            payload = await self._json("POST", "/api/v0/tokenize", json={"model": self._model.model_id if self._model else None, "text": "\n".join(m.get("content", "") for m in messages)})
            tokens = payload.get("tokens")
            if isinstance(tokens, list):
                return len(tokens)
            if isinstance(tokens, int):
                return tokens
        except Exception:
            pass
        return await super().count_tokens(messages)

