from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .models import Session, now_iso


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT NOT NULL, run_mode TEXT NOT NULL, scene_state TEXT NOT NULL, relationship_state TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, partial INTEGER NOT NULL DEFAULT 0, chunks INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS relationship_events (event_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, event_type TEXT NOT NULL, actor_a TEXT, actor_b TEXT, source_message_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS generation_jobs (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, status TEXT NOT NULL, partial INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, finished_at TEXT);
CREATE TABLE IF NOT EXISTS checkpoints (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, last_message_id TEXT, snapshot TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS summaries (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, source_message_start TEXT, source_message_end TEXT, content TEXT NOT NULL, created_at TEXT NOT NULL);
"""


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self):
        try:
            yield self.db
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def create_session(self, run_mode: str = "interactive", title: str = "Qwen Romance Session") -> Session:
        session = Session(title=title, run_mode=run_mode)
        self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?)", (session.id, session.title, session.run_mode, "{}", "{}", session.created_at))
        self.db.commit()
        return session

    def get_session(self, session_id: str) -> Session | None:
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            return None
        return Session(row["id"], row["title"], row["run_mode"], json.loads(row["scene_state"]), json.loads(row["relationship_state"]), row["created_at"])

    def append_message(self, session_id: str, message_id: str, role: str, content: str, partial: bool, chunks: int) -> None:
        self.db.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?)", (message_id, session_id, role, content, int(partial), chunks, now_iso()))

    def update_relationship(self, session_id: str, state: dict[str, Any]) -> None:
        self.db.execute("UPDATE sessions SET relationship_state=? WHERE id=?", (json.dumps(state, ensure_ascii=False), session_id))

    def commit_event(self, event_id: str, session_id: str, event_type: str, payload: dict[str, Any], actor_a: str = "", actor_b: str = "", source_message_id: str = "") -> bool:
        cursor = self.db.execute("INSERT OR IGNORE INTO relationship_events VALUES (?,?,?,?,?,?,?,?)", (event_id, session_id, event_type, actor_a, actor_b, source_message_id, json.dumps(payload, ensure_ascii=False), now_iso()))
        return cursor.rowcount == 1

    def checkpoint(self, session_id: str, last_message_id: str | None = None) -> None:
        session = self.get_session(session_id)
        snapshot = {"scene_state": session.scene_state if session else {}, "relationship_state": session.relationship_state if session else {}}
        self.db.execute("INSERT INTO checkpoints(session_id,last_message_id,snapshot,created_at) VALUES(?,?,?,?)", (session_id, last_message_id, json.dumps(snapshot, ensure_ascii=False), now_iso()))

