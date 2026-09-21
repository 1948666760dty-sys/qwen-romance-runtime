from app.commands.parser import parse_length_command, resolve_profile
from app.runtime.base import RuntimeInfo
from app.skills.qwen_gate import qwen_model_gate


def info(family: str, local: bool = True):
    return RuntimeInfo("test", "http://test", None, "model", family, local, 32768, True)


def test_gate_is_fail_closed():
    assert qwen_model_gate(info("qwen")).allowed
    assert not qwen_model_gate(info("gpt")).allowed
    assert not qwen_model_gate(info("unknown")).allowed
    assert not qwen_model_gate(info("qwen", local=False)).allowed


def test_length_commands_are_task_scoped():
    assert parse_length_command("/length very_long").profile == "very_long"
    assert parse_length_command("这次写长一点").profile == "long"
    assert resolve_profile("继续小说模式", "autonomous_novel")[0] == "very_long"
    assert resolve_profile("几点了？", "interactive")[0] == "long"

