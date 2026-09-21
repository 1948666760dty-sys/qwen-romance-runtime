from __future__ import annotations

import uuid


def event_id(session_id: str, event_type: str, actor_a: str, actor_b: str, source_reply_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, ":".join((session_id, event_type, actor_a, actor_b, source_reply_id))))

