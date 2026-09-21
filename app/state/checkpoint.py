from .store import StateStore


def save_lightweight_checkpoint(store: StateStore, session_id: str, message_id: str | None = None) -> None:
    store.checkpoint(session_id, message_id)

