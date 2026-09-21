from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass(frozen=True)
class MergeResult:
    text: str
    correction_count: int
    overlaps_removed: list[str]


def _ratio(a: str, b: str) -> float:
    try:
        from rapidfuzz.fuzz import ratio  # type: ignore
        return ratio(a, b) / 100.0
    except ImportError:
        return difflib.SequenceMatcher(None, a, b).ratio()


def merge_chunks(previous: str, new: str, window: int = 800, threshold: float = 0.92) -> MergeResult:
    if not previous:
        return MergeResult(new, 0, [])
    left = previous[-window:]
    right = new[:window]
    best = 0
    for size in range(min(len(left), len(right)), 3, -1):
        if left[-size:] == right[:size]:
            best = size
            break
    if not best:
        for size in range(min(len(left), len(right)), 80, -20):
            if _ratio(left[-size:], right[:size]) >= threshold:
                best = size
                break
    if best:
        return MergeResult(previous + new[best:], 1, [new[:best]])
    return MergeResult(previous + new, 0, [])


def final_seam_audit(text: str) -> str:
    # Do not aggressively rewrite user prose; boundary-level correction is performed during merge.
    return text.strip()
