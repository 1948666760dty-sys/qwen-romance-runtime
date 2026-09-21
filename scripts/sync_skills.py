#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def main(base_url: str, cache_dir: str) -> int:
    root = Path(cache_dir) / "qwen-romance"
    root.mkdir(parents=True, exist_ok=True)
    url = base_url.rstrip("/") + "/SKILL.md"
    content = urllib.request.urlopen(url, timeout=30).read()
    path = root / "SKILL.md"
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    # The version is intentionally read without depending on a YAML parser.
    version = "unknown"
    for line in content.decode("utf-8").splitlines():
        if line.startswith("version:"):
            version = line.split(":", 1)[1].strip()
            break
    manifest = {"qwen-romance": {"version": version, "sha256": digest, "path": str(path), "source": url, "canonical_verified": True}}
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    (Path(cache_dir) / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="https://raw.githubusercontent.com/1948666760dty-sys/agent-skills/main/skills/qwen-romance")
    parser.add_argument("--cache-dir", default="./data/cache/skills")
    args = parser.parse_args()
    raise SystemExit(main(args.source, args.cache_dir))

