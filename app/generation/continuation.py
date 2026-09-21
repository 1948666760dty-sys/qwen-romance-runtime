from __future__ import annotations

from dataclasses import dataclass

from .closure_guard import premature_closure, sentence_open


@dataclass(frozen=True)
class ContinuationDecision:
    continue_generation: bool
    reason: str
    scene_complete: bool
    premature_closure: bool


def decide(text: str, stop_reason: str, chunk_index: int, target: dict[str, int], max_chunks: int,
           scene_open: bool = True, user_paused: bool = False) -> ContinuationDecision:
    if user_paused:
        return ContinuationDecision(False, "user_paused", True, False)
    if chunk_index >= max_chunks - 1:
        return ContinuationDecision(False, "max_internal_chunks", False, False)
    if stop_reason == "cancel":
        return ContinuationDecision(False, "cancelled", False, False)
    closure = premature_closure(text, scene_open, target["soft_min_chars"])
    open_sentence = sentence_open(text)
    if not scene_open:
        return ContinuationDecision(False, "scene_complete", True, False)
    if closure or open_sentence or stop_reason == "limit" or len(text) < target["soft_min_chars"]:
        return ContinuationDecision(True, "scene_open", False, closure)
    if len(text) < target["preferred_chars"]:
        return ContinuationDecision(True, "below_preferred", False, False)
    return ContinuationDecision(False, "target_reached", False, False)

