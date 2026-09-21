from __future__ import annotations

from dataclasses import dataclass

from .compactor import compact_messages


@dataclass(frozen=True)
class BuiltContext:
    messages: list[dict[str, str]]
    compacted: bool = False
    compaction_level: str = "none"


def build_context(system: str, history: list[dict[str, str]], user_input: str, max_messages: int = 12) -> BuiltContext:
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": user_input}]
    result = compact_messages(messages, max_messages)
    return BuiltContext(result.messages, result.compacted, result.level)

