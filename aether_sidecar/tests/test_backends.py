import httpx
import pytest

from aether_sidecar.backends import BackendUnavailableError, OllamaBackend
from aether_sidecar.models import Subsystem


class _FakeResponse:
    def __init__(self, data: dict[str, str], status_code: int = 200):
        self._data = data
        self.status_code = status_code
        self.text = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://example.com")
            response = httpx.Response(self.status_code, request=request, text="error")
            raise httpx.HTTPStatusError("status error", request=request, response=response)

    def json(self) -> dict[str, str]:
        return self._data


class _FakeAsyncClient:
    def __init__(self, responses_by_url, calls):
        self.responses_by_url = responses_by_url
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json):
        self.calls.append(url)
        action = self.responses_by_url.get(url)
        if isinstance(action, Exception):
            raise action
        return action


@pytest.mark.anyio
async def test_candidate_urls_for_localhost_use_docker_host_fallback():
    backend = OllamaBackend("http://127.0.0.1:11434/api/generate", "llama3.1:8b")

    assert backend.candidate_urls() == [
        "http://127.0.0.1:11434/api/generate",
        "http://host.docker.internal:11434/api/generate",
    ]


@pytest.mark.anyio
async def test_generate_falls_back_to_host_docker_internal(monkeypatch):
    calls = []
    local_url = "http://127.0.0.1:11434/api/generate"
    docker_host_url = "http://host.docker.internal:11434/api/generate"
    backend = OllamaBackend(local_url, "llama3.1:8b")

    responses_by_url = {
        local_url: httpx.ConnectError("connection refused", request=httpx.Request("POST", local_url)),
        docker_host_url: _FakeResponse({"response": "ready"}),
    }

    def fake_client_factory(*args, **kwargs):
        return _FakeAsyncClient(responses_by_url, calls)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    text, model_name = await backend.generate("hello", Subsystem.AEGIS)

    assert text == "ready"
    assert model_name == "llama3.1:8b"
    assert calls == [local_url, docker_host_url]


@pytest.mark.anyio
async def test_generate_raises_after_all_candidate_urls_fail(monkeypatch):
    calls = []
    local_url = "http://127.0.0.1:11434/api/generate"
    docker_host_url = "http://host.docker.internal:11434/api/generate"
    backend = OllamaBackend(local_url, "llama3.1:8b")

    responses_by_url = {
        local_url: httpx.ConnectError("local unavailable", request=httpx.Request("POST", local_url)),
        docker_host_url: httpx.ConnectError(
            "docker host unavailable", request=httpx.Request("POST", docker_host_url)
        ),
    }

    def fake_client_factory(*args, **kwargs):
        return _FakeAsyncClient(responses_by_url, calls)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    with pytest.raises(BackendUnavailableError) as exc_info:
        await backend.generate("hello", Subsystem.AEGIS)

    assert "Failed to contact model backend" in str(exc_info.value)
    assert calls == [local_url, docker_host_url]
