import pytest
import respx
from httpx import Response

from app.runtime.llamacpp import LlamaCppAdapter
from app.runtime.lmstudio import LMStudioAdapter
from app.runtime.ollama import OllamaAdapter


@pytest.mark.asyncio
@respx.mock
async def test_lmstudio_probe_normalizes_qwen():
    respx.get("http://lm/v1/models").mock(return_value=Response(200, json={"data": [{"id": "Qwen3-14B"}]}))
    respx.get("http://lm/api/v0/models").mock(return_value=Response(200, json={"data": [{"id": "Qwen3-14B", "architecture": "qwen3", "max_context_length": 32768}]}))
    info = await LMStudioAdapter("http://lm").probe()
    assert info.model_family == "qwen"
    assert info.context_length == 32768


@pytest.mark.asyncio
@respx.mock
async def test_llamacpp_props_and_tokenize():
    respx.get("http://llama/v1/models").mock(return_value=Response(200, json={"data": [{"id": "local-qwen"}]}))
    respx.get("http://llama/props").mock(return_value=Response(200, json={"model_path": "Qwen3.gguf", "n_ctx": 16384, "architecture": "qwen3"}))
    respx.post("http://llama/apply-template").mock(return_value=Response(200, json={"prompt": "<|user|>x"}))
    respx.post("http://llama/tokenize").mock(return_value=Response(200, json={"tokens": [1, 2, 3]}))
    adapter = LlamaCppAdapter("http://llama")
    info = await adapter.probe()
    assert info.model_family == "qwen"
    assert await adapter.count_tokens([{"role": "user", "content": "x"}]) == 3


@pytest.mark.asyncio
@respx.mock
async def test_llamacpp_uses_n_predict():
    respx.get("http://llama2/v1/models").mock(return_value=Response(200, json={"data": [{"id": "Qwen3"}]}))
    respx.get("http://llama2/props").mock(return_value=Response(200, json={"model_path": "Qwen3.gguf", "n_ctx": 8192, "architecture": "qwen3"}))
    route = respx.post("http://llama2/v1/chat/completions").mock(return_value=Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {"completion_tokens": 2}}))
    adapter = LlamaCppAdapter("http://llama2")
    await adapter.generate([{"role": "user", "content": "hi"}], 123)
    assert '"n_predict":123' in route.calls.last.request.content.decode().replace(" ", "")


@pytest.mark.asyncio
@respx.mock
async def test_ollama_maps_num_predict_and_stats():
    respx.get("http://ollama/api/tags").mock(return_value=Response(200, json={"models": [{"name": "qwen3:8b"}]}))
    respx.post("http://ollama/api/show").mock(return_value=Response(200, json={"details": {"family": "qwen"}, "model_info": {"context_length": 8192}}))
    route = respx.post("http://ollama/api/chat").mock(return_value=Response(200, json={"message": {"content": "ok"}, "done_reason": "stop", "prompt_eval_count": 4, "eval_count": 2}))
    adapter = OllamaAdapter("http://ollama")
    result = await adapter.generate([{"role": "user", "content": "hi"}], 123)
    assert result.text == "ok"
    assert result.generated_tokens == 2
    assert route.called
    assert route.calls.last.request.content.decode().find("num_predict") >= 0
