from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeInfo:
    backend: str
    base_url: str
    runtime_version: str | None
    model_id: str | None
    model_family: str
    local: bool
    context_length: int
    tokenizer_exact: bool
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelInfo:
    model_id: str
    family: str
    architecture: str | None = None
    context_length: int | None = None


@dataclass(frozen=True)
class GenerationResult:
    text: str
    prompt_tokens: int
    generated_tokens: int
    stop_reason: str
    truncated: bool = False
    duration_ms: int = 0
    error: str | None = None


class RuntimeAdapter(ABC):
    backend = "unknown"

    def __init__(self, base_url: str, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._active_cancel: asyncio.Event | None = None

    @abstractmethod
    async def probe(self) -> RuntimeInfo:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        raise NotImplementedError

    @abstractmethod
    async def count_tokens(self, messages: list[dict[str, str]]) -> int:
        raise NotImplementedError

    async def context_length(self) -> int:
        return (await self.probe()).context_length

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int,
        sampling: dict[str, Any] | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> GenerationResult:
        raise NotImplementedError

    async def close_generation(self) -> None:
        self._active_cancel and self._active_cancel.set()


def normalize_family(value: str | None, architecture: str | None = None) -> str:
    raw = f"{value or ''} {architecture or ''}".lower().replace("-", "_")
    if any(part in raw for part in ("qwen", "qwen2", "qwen3")):
        return "qwen"
    if raw.strip():
        return "non_qwen"
    return "unknown"

