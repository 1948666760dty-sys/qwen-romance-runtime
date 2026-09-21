from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemoryLayers:
    hard_rules: list[str]
    canon: list[str]
    character_state: list[str]
    relationship_state: list[str]
    high_importance_events: list[str]
    arc_summary: list[str]
    chapter_summary: list[str]
    recent_messages: list[dict[str, str]]

