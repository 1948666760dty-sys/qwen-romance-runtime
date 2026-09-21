from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from ..commands.parser import PROFILES, resolve_profile
from ..config import GenerationConfig
from ..skills.loader import SkillLoader
from ..skills.prompt_composer import compose_prompt
from ..skills.qwen_gate import qwen_model_gate
from ..state.store import StateStore
from .continuation import decide
from .closure_guard import sentence_open
from .seam_merger import final_seam_audit, merge_chunks
from .token_budget import ContextExhausted, calculate_budget


@dataclass(frozen=True)
class ChatRequest:
    session_id: str
    message: str
    run_mode: str = "interactive"
    length: str | None = None


@dataclass(frozen=True)
class ChatResponse:
    message_id: str
    text: str
    partial: bool
    chunks: int
    chars: int
    generated_tokens: int
    seam_corrections: int
    mode: str
    error: str | None = None


@dataclass
class GenerationJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    partial: bool = False


class LongOutputController:
    def __init__(self, adapter, store: StateStore, skill_loader: SkillLoader, generation: GenerationConfig | None = None):
        self.adapter = adapter
        self.store = store
        self.skill_loader = skill_loader
        self.generation = generation or GenerationConfig()
        self.semaphore = asyncio.Semaphore(1)
        self.jobs: dict[str, GenerationJob] = {}

    async def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if not job:
            return False
        job.cancel_event.set()
        await self.adapter.close_generation()
        return True

    async def generate(self, request: ChatRequest, state_extractor: Callable[[str], dict[str, Any]] | None = None) -> ChatResponse:
        async with self.semaphore:
            return await self._generate_locked(request, state_extractor)

    async def _generate_locked(self, request: ChatRequest, state_extractor=None) -> ChatResponse:
        info = await self.adapter.probe()
        gate = qwen_model_gate(info)
        if not gate.allowed:
            raise PermissionError("MODEL_NOT_QWEN: Qwen Romance Runtime 只接受本地 Qwen 模型")
        skill = self.skill_loader.load_qwen_bundle(gate)
        session = self.store.get_session(request.session_id)
        if not session:
            raise KeyError(f"SESSION_NOT_FOUND: {request.session_id}")
        mode, profile = resolve_profile(request.message, request.run_mode, self.generation.interactive_default, self.generation.novel_default)
        if request.length in {"short", "normal", "long", "very_long"}:
            mode, profile = request.length, PROFILES[request.length]
        history_rows = self.store.db.execute("SELECT role,content FROM messages WHERE session_id=? ORDER BY created_at", (session.id,)).fetchall()
        history = [{"role": row["role"], "content": row["content"]} for row in history_rows]
        job = GenerationJob()
        self.jobs[job.id] = job
        visible = ""
        seam_corrections = 0
        generated_tokens = 0
        chunk_count = 0
        partial = False
        last_reason = "stop"
        try:
            for index in range(self.generation.max_internal_chunks):
                if job.cancel_event.is_set():
                    partial = True
                    break
                prompt = compose_prompt(request.message, history, skill, session.scene_state, session.relationship_state,
                                        continuation=index > 0, previous_text=visible)
                try:
                    budget = await calculate_budget(self.adapter, prompt.messages, self._requested_tokens(profile), self.generation.context_safety_ratio,
                                                    self.generation.minimum_reserve_tokens, self.generation.minimum_chunk_tokens)
                except ContextExhausted:
                    # Compact only low-priority recent history, then retry the budget once.
                    history = history[-6:]
                    prompt = compose_prompt(request.message, history, skill, session.scene_state, session.relationship_state,
                                            continuation=index > 0, previous_text=visible)
                    budget = await calculate_budget(self.adapter, prompt.messages, self._requested_tokens(profile), self.generation.context_safety_ratio,
                                                    self.generation.minimum_reserve_tokens, self.generation.minimum_chunk_tokens)
                result = None
                last_error: Exception | None = None
                for retry in range(self.generation.chunk_retry_count + 1):
                    try:
                        result = await self.adapter.generate(prompt.messages, budget.available_generation_tokens,
                                                             sampling={"temperature": 0.8}, cancel_event=job.cancel_event)
                        if result.error:
                            raise RuntimeError(result.error)
                        break
                    except Exception as exc:
                        last_error = exc
                        if retry < self.generation.chunk_retry_count:
                            budget = type(budget)(budget.context_window, budget.prompt_tokens, budget.reserved_tokens,
                                                  max(self.generation.minimum_chunk_tokens, int(budget.available_generation_tokens * 0.75)),
                                                  budget.requested_tokens, budget.exact)
                if result is None:
                    if visible:
                        partial = True
                        break
                    raise RuntimeError(f"GENERATION_FAILED: {last_error}")
                merged = merge_chunks(visible, result.text)
                visible, seam_corrections = merged.text, seam_corrections + merged.correction_count
                chunk_count += 1
                generated_tokens += result.generated_tokens
                last_reason = result.stop_reason
                history = [*history, {"role": "assistant", "content": result.text}]
                scene_is_open = not (result.stop_reason == "stop" and not sentence_open(visible))
                decision = decide(visible, result.stop_reason, index, profile, self.generation.max_internal_chunks, scene_open=scene_is_open, user_paused=False)
                if not decision.continue_generation:
                    break
            if job.cancel_event.is_set():
                partial = True
            visible = final_seam_audit(visible)
            message_id = str(uuid.uuid4())
            updates = state_extractor(visible) if state_extractor else {}
            with self.store.transaction():
                self.store.append_message(session.id, message_id, "user", request.message, False, 0)
                self.store.append_message(session.id, message_id + ":assistant", "assistant", visible, partial, chunk_count)
                if updates:
                    self.store.update_relationship(session.id, updates)
                self.store.checkpoint(session.id, message_id + ":assistant")
            return ChatResponse(message_id + ":assistant", visible, partial, chunk_count, len(visible), generated_tokens, seam_corrections, mode)
        finally:
            self.jobs.pop(job.id, None)

    @staticmethod
    def _requested_tokens(profile: dict[str, int]) -> int:
        # Character goals are not tokens; this is only a conservative per-Chunk request.
        return max(256, int(profile["preferred_chars"] * 1.4))
