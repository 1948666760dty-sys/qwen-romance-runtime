import asyncio

from app.generation.closure_guard import premature_closure, sentence_open
from app.generation.seam_merger import merge_chunks
from app.generation.token_budget import ContextExhausted, calculate_budget


class Adapter:
    async def context_length(self): return 1000
    async def count_tokens(self, messages): return 600


def test_dynamic_budget_keeps_reserve():
    budget = asyncio.run(calculate_budget(Adapter(), [{"role":"user","content":"x"}], 800, 0.15, 100, 50))
    assert budget.reserved_tokens == 150
    assert budget.available_generation_tokens == 250


def test_budget_fails_before_overflow():
    class Tiny(Adapter):
        async def count_tokens(self, messages): return 900
    try:
        asyncio.run(calculate_budget(Tiny(), [], 100, 0.15, 100, 50))
    except ContextExhausted:
        return
    assert False, "expected ContextExhausted"


def test_overlap_removed():
    result = merge_chunks("他走到门口。", "他走到门口。然后回头。")
    assert result.text == "他走到门口。然后回头。"
    assert result.correction_count == 1


def test_closure_and_sentence_guard():
    assert premature_closure("这一章就此。", True, 2500)
    assert sentence_open("他抬起手")

