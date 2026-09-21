from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LengthMode = Literal["short", "normal", "long", "very_long"]


@dataclass(frozen=True)
class LengthPreference:
    profile: LengthMode | None
    scope: str = "current_reply"


_WORDS = {
    "写短点": "short", "短一点": "short", "正常长度": "normal",
    "写长一点": "long", "多写一点": "long", "这次写长": "long",
    "一次多生成": "long", "一次多写一点": "long", "尽量一次多写": "long",
    "写很长": "very_long", "这次写很长": "very_long", "继续小说模式": "very_long",
}


def parse_length_command(message: str) -> LengthPreference:
    stripped = message.strip().lower()
    if stripped.startswith("/length "):
        value = stripped.split(None, 1)[1].strip()
        if value in {"short", "normal", "long", "very_long"}:
            return LengthPreference(value)  # type: ignore[arg-type]
    for phrase, profile in sorted(_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if phrase in message:
            return LengthPreference(profile)  # type: ignore[arg-type]
    return LengthPreference(None)


PROFILES: dict[str, dict[str, int]] = {
    "short": {"soft_min_chars": 300, "preferred_chars": 800, "ceiling_chars": 1500},
    "normal": {"soft_min_chars": 1200, "preferred_chars": 2200, "ceiling_chars": 3500},
    "long": {"soft_min_chars": 2500, "preferred_chars": 4000, "ceiling_chars": 6500},
    "very_long": {"soft_min_chars": 5000, "preferred_chars": 8000, "ceiling_chars": 12000},
}


def resolve_profile(message: str, run_mode: str, default_interactive: str = "long", default_novel: str = "very_long") -> tuple[str, dict[str, int]]:
    preference = parse_length_command(message)
    mode = preference.profile or (default_novel if run_mode == "autonomous_novel" else default_interactive)
    return mode, PROFILES[mode]

