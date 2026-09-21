from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompactionResult:
    messages: list[dict[str, str]]
    compacted: bool
    level: str


def compact_messages(messages: list[dict[str, str]], max_messages: int = 12) -> CompactionResult:
    if len(messages) <= max_messages:
        return CompactionResult(messages, False, "none")
    # Keep the system rule, recent raw messages, and a deterministic marker for the omitted range.
    kept = [messages[0], {"role": "system", "content": f"[Working Context compressed: omitted {len(messages)-max_messages} low-priority messages]"}]
    kept.extend(messages[-(max_messages - 2):])
    return CompactionResult(kept, True, "recent_raw")

