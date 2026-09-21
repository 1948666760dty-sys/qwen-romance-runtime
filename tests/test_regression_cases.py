import pytest

from app.commands.parser import parse_length_command
from app.generation.closure_guard import premature_closure
from app.generation.seam_merger import merge_chunks
from app.context.compactor import compact_messages
from app.runtime.base import RuntimeInfo
from app.skills.qwen_gate import qwen_model_gate


@pytest.mark.parametrize("text,expected", [
    ("/length short", "short"), ("/length normal", "normal"), ("/length long", "long"),
    ("/length very_long", "very_long"), ("写短点", "short"), ("短一点", "short"),
    ("正常长度", "normal"), ("写长一点", "long"), ("多写一点", "long"),
    ("一次多生成", "long"), ("这次写很长", "very_long"), ("继续小说模式", "very_long"),
])
def test_length_profile_regressions(text, expected):
    assert parse_length_command(text).profile == expected


@pytest.mark.parametrize("text", [
    "这一章就此。", "至于未来……", "一切仍在继续。", "故事才刚刚开始。", "属于他们的故事才刚刚开始。",
])
def test_premature_closure_only_for_open_short_scene(text):
    assert premature_closure(text, True, 2500)
    assert not premature_closure(text, False, 2500)
    assert not premature_closure(text + "补充" * 2000, True, 2500)


@pytest.mark.parametrize("first,second", [
    ("他走到门口。", "他走到门口。然后回头。"),
    ("她合上书。", "她合上书。窗外开始下雨。"),
    ("灯亮了。", "灯亮了。他才看清桌面。"),
    ("周铭点头。", "周铭点头。随后把单据收回。"),
    ("你停在柜台。", "你停在柜台。没有碰收银箱。"),
])
def test_exact_boundary_overlap_is_removed(first, second):
    merged = merge_chunks(first, second)
    assert merged.correction_count == 1
    assert merged.text.count(first) == 1


@pytest.mark.parametrize("family,local,allowed", [
    ("qwen", True, True), ("qwen", False, False), ("gpt", True, False),
    ("gpt", False, False), ("llama", True, False), ("deepseek", True, False),
    ("unknown", True, False), ("", True, False), ("mistral", False, False), ("gemma", True, False),
])
def test_model_gate_regressions(family, local, allowed):
    info = RuntimeInfo("test", "http://test", None, "model", family or "unknown", local, 32768, True)
    assert qwen_model_gate(info).allowed is allowed


@pytest.mark.parametrize("count,limit", [(13, 12), (14, 12), (20, 12), (30, 12), (50, 12), (12, 12), (11, 12), (16, 10), (9, 8), (8, 8)])
def test_context_compaction_regressions(count, limit):
    messages = [{"role": "user", "content": str(i)} for i in range(count)]
    result = compact_messages(messages, limit)
    assert len(result.messages) <= limit
    assert result.compacted is (count > limit)
