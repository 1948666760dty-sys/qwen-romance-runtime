from __future__ import annotations

import re

PATTERNS = (
    "这一章就此", "至于未来", "一切仍在继续", "故事才刚刚开始", "属于他们的故事才刚刚开始",
)


def premature_closure(text: str, scene_open: bool, soft_min_chars: int) -> bool:
    if not scene_open or len(text) >= soft_min_chars:
        return False
    tail = text[-1200:]
    return any(pattern in tail for pattern in PATTERNS)


def sentence_open(text: str) -> bool:
    if not text.strip():
        return True
    return text.rstrip()[-1] not in "。！？!?\n”\"'）)】』"

