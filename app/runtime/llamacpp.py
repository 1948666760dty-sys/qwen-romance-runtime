from __future__ import annotations

from .openai_compat import OpenAICompatibleAdapter
from .base import RuntimeInfo


class LlamaCppAdapter(OpenAICompatibleAdapter):
    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        super().__init__(base_url, "llamacpp", timeout_seconds)

    async def probe(self) -> RuntimeInfo:
        info = await super().probe()
        try:
            props = await self._json("GET", "/props")
            model = props.get("model_path") or props.get("model") or info.model_id
            context = int(props.get("default_generation_settings", {}).get("n_ctx") or props.get("n_ctx") or info.context_length)
            arch = str(props.get("model_info", {}).get("general.architecture") or props.get("architecture") or model or "")
            from .base import normalize_family
            family = normalize_family(arch, model)
            self._context_length = context
            if self._model:
                self._model = type(self._model)(self._model.model_id, family, arch, context)
            return RuntimeInfo(info.backend, info.base_url, info.runtime_version, model, family, True, context, True, info.capabilities + ("props", "stop_type"))
        except Exception:
            return info

    async def count_tokens(self, messages):
        try:
            prompt = "\n".join(f"{m.get('role','user')}: {m.get('content','')}" for m in messages)
            payload = await self._json("POST", "/tokenize", json={"content": prompt})
            tokens = payload.get("tokens")
            if isinstance(tokens, list):
                return len(tokens)
        except Exception:
            pass
        return await super().count_tokens(messages)

    async def generate(self, messages, max_new_tokens, sampling=None, cancel_event=None):
        result = await super().generate(messages, max_new_tokens, sampling, cancel_event)
        return result

