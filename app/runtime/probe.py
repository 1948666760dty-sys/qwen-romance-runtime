from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ..config import RuntimeConfig, TimeoutConfig
from .base import RuntimeAdapter, RuntimeInfo
from .llamacpp import LlamaCppAdapter
from .lmstudio import LMStudioAdapter
from .ollama import OllamaAdapter


@dataclass(frozen=True)
class ProbeResult:
    backend: str
    info: RuntimeInfo | None
    error: str | None = None


def adapters(config: RuntimeConfig, timeout: TimeoutConfig) -> dict[str, RuntimeAdapter]:
    return {
        "ollama": OllamaAdapter(config.ollama.base_url, timeout.connect_seconds),
        "lmstudio": LMStudioAdapter(config.lmstudio.base_url, timeout.connect_seconds),
        "llamacpp": LlamaCppAdapter(config.llamacpp.base_url, timeout.connect_seconds),
    }


async def probe_all(config: RuntimeConfig, timeout: TimeoutConfig) -> list[ProbeResult]:
    async def one(name: str, adapter: RuntimeAdapter) -> ProbeResult:
        try:
            return ProbeResult(name, await adapter.probe())
        except Exception as exc:
            return ProbeResult(name, None, f"{type(exc).__name__}: {exc}")

    return await asyncio.gather(*(one(name, adapter) for name, adapter in adapters(config, timeout).items()))


async def select_adapter(config: RuntimeConfig, timeout: TimeoutConfig) -> tuple[RuntimeAdapter, RuntimeInfo]:
    available = adapters(config, timeout)
    names = [config.backend] if config.backend != "auto" else ["lmstudio", "llamacpp", "ollama"]
    errors: list[str] = []
    for name in names:
        adapter = available.get(name)
        if not adapter:
            continue
        try:
            info = await adapter.probe()
            return adapter, info
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    raise RuntimeError("未发现可用的本地 Runtime；" + "；".join(errors))

