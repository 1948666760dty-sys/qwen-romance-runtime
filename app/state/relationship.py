from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemporaryDelta:
    updates: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)


def merge_deltas(deltas: list[TemporaryDelta]) -> TemporaryDelta:
    result = TemporaryDelta()
    seen: set[str] = set()
    for delta in deltas:
        result.updates.update(delta.updates)
        for event in delta.events:
            key = str(event.get("event_id", ""))
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            result.events.append(event)
    return result

