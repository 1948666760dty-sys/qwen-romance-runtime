from __future__ import annotations

from dataclasses import dataclass


class ContextExhausted(RuntimeError):
    pass


@dataclass(frozen=True)
class TokenBudget:
    context_window: int
    prompt_tokens: int
    reserved_tokens: int
    available_generation_tokens: int
    requested_tokens: int
    exact: bool


async def calculate_budget(adapter, messages, requested_tokens: int, safety_ratio: float = 0.15,
                           minimum_reserve: int = 256, minimum_chunk_tokens: int = 128) -> TokenBudget:
    context_window = await adapter.context_length()
    prompt_tokens = await adapter.count_tokens(messages)
    reserve = max(minimum_reserve, int(context_window * safety_ratio))
    available = context_window - prompt_tokens - reserve
    if available < minimum_chunk_tokens:
        raise ContextExhausted(f"上下文预算不足：window={context_window}, prompt={prompt_tokens}, reserve={reserve}")
    return TokenBudget(context_window, prompt_tokens, reserve, min(requested_tokens, available), requested_tokens, True)

