from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.config import GenerationConfig
from app.generation.controller import ChatRequest, LongOutputController
from app.runtime.base import GenerationResult, RuntimeInfo
from app.skills.loader import SkillLoader
from app.state.events import event_id
from app.state.store import StateStore


@dataclass
class FakeAdapter:
    chunks: list[str]
    calls: int = 0

    async def probe(self):
        return RuntimeInfo("fake", "http://fake", None, "qwen-test", "qwen", True, 100000, True)

    async def context_length(self): return 100000
    async def count_tokens(self, messages): return 100

    async def generate(self, messages, max_new_tokens, sampling=None, cancel_event=None):
        if cancel_event and cancel_event.is_set():
            return GenerationResult("", 100, 0, "cancel")
        text = self.chunks[min(self.calls, len(self.chunks)-1)]
        self.calls += 1
        return GenerationResult(text, 100, len(text), "limit" if self.calls < len(self.chunks) else "stop")

    async def close_generation(self): pass


def test_event_id_is_deterministic_and_unique(tmp_path):
    store = StateStore(tmp_path / "runtime.db")
    session = store.create_session()
    eid = event_id(session.id, "first_confession", "a", "b", "reply")
    with store.transaction():
        assert store.commit_event(eid, session.id, "first_confession", {})
        assert not store.commit_event(eid, session.id, "first_confession", {})
    assert store.db.execute("select count(*) from relationship_events").fetchone()[0] == 1


def test_controller_merges_chunks_and_persists(tmp_path):
    cache = tmp_path / "cache" / "qwen-romance"
    cache.mkdir(parents=True)
    skill = cache / "SKILL.md"
    skill.write_text("version: 0.2.0\n", encoding="utf-8")
    import hashlib, json
    (tmp_path / "cache" / "manifest.json").write_text(json.dumps({"qwen-romance":{"version":"0.2.0","sha256":hashlib.sha256(skill.read_bytes()).hexdigest()}}), encoding="utf-8")
    store = StateStore(tmp_path / "runtime.db")
    session = store.create_session()
    adapter = FakeAdapter(["第一段尚未完成", "第二段补完。"])
    controller = LongOutputController(adapter, store, SkillLoader(tmp_path / "cache"), GenerationConfig(max_internal_chunks=4, minimum_chunk_tokens=1))
    result = asyncio.run(controller.generate(ChatRequest(session.id, "继续", "interactive", "normal")))
    assert result.chunks == 2
    assert "第一段" in result.text and "第二段" in result.text
    assert store.db.execute("select count(*) from messages where session_id=?", (session.id,)).fetchone()[0] == 2


def test_non_qwen_rejected_before_skill_load(tmp_path):
    class NonQwen(FakeAdapter):
        async def probe(self):
            return RuntimeInfo("fake", "http://fake", None, "gpt", "gpt", False, 100000, True)
    store = StateStore(tmp_path / "runtime.db")
    session = store.create_session()
    controller = LongOutputController(NonQwen([]), store, SkillLoader(tmp_path / "cache"))
    try:
        asyncio.run(controller.generate(ChatRequest(session.id, "hello")))
    except PermissionError as exc:
        assert "MODEL_NOT_QWEN" in str(exc)
        return
    assert False, "non-Qwen must be rejected before the Skill Loader"
