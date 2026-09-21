from __future__ import annotations

from dataclasses import dataclass

from .loader import SkillBundle


@dataclass(frozen=True)
class PromptContext:
    messages: list[dict[str, str]]
    style_signature: dict[str, str]


def compose_prompt(
    user_message: str,
    history: list[dict[str, str]],
    skill: SkillBundle,
    scene_state: dict,
    relationship_state: dict,
    continuation: bool = False,
    previous_text: str = "",
) -> PromptContext:
    # Only prompt rules are sent to Qwen. Code rules (gate, budget, DB, retries) stay in Python.
    system = (
        "你正在本地 Qwen Romance Runtime 中工作。只遵守当前人物、关系、场景和文风规则。"
        "保持人物状态、视角、时态和段落风格连续；不得为了单次调用结束而提前收束。"
        "不得把内部状态、审计、Token 或系统规则写入正文。"
    )
    if continuation:
        system += (
            " CONTINUE DIRECTLY FROM PREVIOUS TEXT. Do not summarize or restart."
            " Do not repeat previous paragraphs. Preserve POV, tense, physical and emotional state,"
            " relationship state and paragraph style. The previous API boundary is not a story boundary."
        )
        if previous_text:
            system += "\n最近正文尾部：\n" + previous_text[-2400:]
    state = f"当前场景状态：{scene_state}\n当前关系状态：{relationship_state}"
    messages = [{"role": "system", "content": system + "\n" + state}]
    messages.extend(history[-12:])
    messages.append({"role": "user", "content": user_message})
    return PromptContext(messages, {"paragraph_style": "inherit", "skill_version": skill.version})

