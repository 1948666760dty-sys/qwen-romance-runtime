from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BackendConfig:
    base_url: str


@dataclass
class RuntimeConfig:
    backend: str = "auto"
    ollama: BackendConfig = field(default_factory=lambda: BackendConfig("http://127.0.0.1:11434"))
    lmstudio: BackendConfig = field(default_factory=lambda: BackendConfig("http://127.0.0.1:1234"))
    llamacpp: BackendConfig = field(default_factory=lambda: BackendConfig("http://127.0.0.1:8080"))


@dataclass
class GenerationConfig:
    max_internal_chunks: int = 4
    interactive_default: str = "long"
    novel_default: str = "very_long"
    context_safety_ratio: float = 0.15
    minimum_reserve_tokens: int = 256
    chunk_retry_count: int = 1
    minimum_chunk_tokens: int = 128


@dataclass
class TimeoutConfig:
    connect_seconds: float = 10
    stream_idle_seconds: float = 120
    chunk_max_seconds: float = 1200


@dataclass
class AppConfig:
    server_host: str = "127.0.0.1"
    server_port: int = 8765
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    database: Path = Path("./data/runtime.db")
    skill_cache_dir: Path = Path("./data/cache/skills")
    skill_source: str = "https://raw.githubusercontent.com/1948666760dty-sys/agent-skills/main/skills/qwen-romance"


def _section(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def load_config(path: str | Path | None = None) -> AppConfig:
    config = AppConfig()
    if path is None:
        path = Path("config.yaml")
    path = Path(path)
    if not path.exists():
        return config
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError("配置文件需要安装 PyYAML，或删除 config.yaml 使用默认配置") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    server = _section(data, "server")
    config.server_host = str(server.get("host", config.server_host))
    config.server_port = int(server.get("port", config.server_port))
    runtime = _section(data, "runtime")
    config.runtime.backend = str(runtime.get("backend", config.runtime.backend))
    for name in ("ollama", "lmstudio", "llamacpp"):
        section = _section(runtime, name)
        current = getattr(config.runtime, name)
        setattr(config.runtime, name, BackendConfig(str(section.get("base_url", current.base_url))))
    generation = _section(data, "generation")
    for key in ("max_internal_chunks", "minimum_reserve_tokens", "chunk_retry_count", "minimum_chunk_tokens"):
        if key in generation:
            setattr(config.generation, key, int(generation[key]))
    for key in ("interactive_default", "novel_default"):
        if key in generation:
            setattr(config.generation, key, str(generation[key]))
    if "context_safety_ratio" in generation:
        config.generation.context_safety_ratio = float(generation["context_safety_ratio"])
    timeout = _section(data, "timeout")
    for key in ("connect_seconds", "stream_idle_seconds", "chunk_max_seconds"):
        if key in timeout:
            setattr(config.timeout, key, float(timeout[key]))
    state = _section(data, "state")
    if "database" in state:
        config.database = Path(str(state["database"]))
    skills = _section(data, "skills")
    if "cache_dir" in skills:
        config.skill_cache_dir = Path(str(skills["cache_dir"]))
    return config

