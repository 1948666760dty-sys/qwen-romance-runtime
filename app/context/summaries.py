from __future__ import annotations


def create_summary(messages: list[dict[str, str]], max_chars: int = 1800) -> str:
    text = "\n".join(f"{m.get('role')}: {m.get('content','')}" for m in messages)
    return text[-max_chars:]

