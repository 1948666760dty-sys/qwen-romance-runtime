from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .qwen_gate import GateResult


@dataclass(frozen=True)
class SkillBundle:
    name: str
    version: str
    content: str
    sha256: str
    canonical_verified: bool


class SkillLoader:
    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load_qwen_bundle(self, gate: GateResult) -> SkillBundle:
        if not gate.allowed:
            raise PermissionError("Qwen Romance Skill Loader 在 Model Gate 失败时不得执行")
        skill_path = self.cache_dir / "qwen-romance" / "SKILL.md"
        manifest_path = self.cache_dir / "manifest.json"
        if not skill_path.exists():
            raise FileNotFoundError(f"未找到已缓存的 qwen-romance Skill：{skill_path}，请先运行 sync_skills.py")
        content = skill_path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        entry = manifest.get("qwen-romance", {})
        verified = bool(entry.get("sha256") == digest)
        return SkillBundle("qwen-romance", str(entry.get("version", "unknown")), content, digest, verified)

