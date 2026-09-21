from fastapi.testclient import TestClient

from app.config import AppConfig
from app.main import create_app


def test_health_and_session_routes(tmp_path):
    config = AppConfig(database=tmp_path / "runtime.db", skill_cache_dir=tmp_path / "cache")
    client = TestClient(create_app(config))
    assert client.get("/health").json()["status"] == "ok"
    session = client.post("/api/sessions", json={"title": "test"})
    assert session.status_code == 200
    session_id = session.json()["id"]
    loaded = client.get(f"/api/sessions/{session_id}")
    assert loaded.status_code == 200
    assert loaded.json()["title"] == "test"


def test_openai_compatible_endpoint_requires_user_message(tmp_path):
    config = AppConfig(database=tmp_path / "runtime.db", skill_cache_dir=tmp_path / "cache")
    client = TestClient(create_app(config))
    response = client.post("/v1/chat/completions", json={"messages": [{"role": "system", "content": "x"}]})
    assert response.status_code == 422

