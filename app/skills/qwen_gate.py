from __future__ import annotations

from dataclasses import dataclass

from ..runtime.base import RuntimeInfo


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str


def qwen_model_gate(info: RuntimeInfo, enabled: bool = True) -> GateResult:
    if not enabled:
        return GateResult(False, "disabled")
    if info.local is not True:
        return GateResult(False, "runtime_not_local")
    if info.model_family != "qwen":
        return GateResult(False, "model_not_qwen")
    return GateResult(True, "local_qwen")

