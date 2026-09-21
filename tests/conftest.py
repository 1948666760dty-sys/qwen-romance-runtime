from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def make_cache(tmp_path: Path) -> Path:
    root = tmp_path / "cache" / "qwen-romance"
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text("version: 0.2.0\nqwen romance prompt rules", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256((root / "SKILL.md").read_bytes()).hexdigest()
    (tmp_path / "cache" / "manifest.json").write_text(json.dumps({"qwen-romance": {"version": "0.2.0", "sha256": digest}}), encoding="utf-8")
    return tmp_path / "cache"

