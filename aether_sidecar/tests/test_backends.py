import socket
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
async def test_candidate_urls_for_localhost_use_docker_host_fallbacks(monkeypatch):
    monkeypatch.delenv("AETHER_DOCKER_HOST_GATEWAY", raising=False)
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    backend = OllamaBackend("http://127.0.0.1:11434/api/generate", "llama3.1:8b")

    assert backend.candidate_urls() == [
        "http://127.0.0.1:11434/api/generate",
        "http://host.docker.internal:11434/api/generate",
        "http://gateway.docker.internal:11434/api/generate",
        "http://host.containers.internal:11434/api/generate",
        "http://localhost:11434/api/generate",
        "http://172.17.0.1:11434/api/generate",
        "http://192.168.65.1:11434/api/generate",
    ]


@pytest.mark.anyio
async def test_candidate_urls_include_gateway_override(monkeypatch):
    monkeypatch.setenv("AETHER_DOCKER_HOST_GATEWAY", "172.17.0.1")
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: "172.17.0.1"))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    backend = OllamaBackend("http://localhost:11434/api/generate", "llama3.1:8b")

    assert backend.candidate_urls() == [
        "http://localhost:11434/api/generate",
        "http://host.docker.internal:11434/api/generate",
        "http://gateway.docker.internal:11434/api/generate",
        "http://host.containers.internal:11434/api/generate",
        "http://127.0.0.1:11434/api/generate",
        "http://172.17.0.1:11434/api/generate",
        "http://192.168.65.1:11434/api/generate",
    ]


@pytest.mark.anyio
async def test_candidate_urls_include_detected_linux_gateway_when_aliases_do_not_resolve(monkeypatch):
    monkeypatch.delenv("AETHER_DOCKER_HOST_GATEWAY", raising=False)
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: "172.17.0.1"))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        if host in {"host.docker.internal", "gateway.docker.internal", "host.containers.internal"}:
            raise socket.gaierror("name not known")
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    backend = OllamaBackend("http://127.0.0.1:11434/api/generate", "llama3.1:8b")

    assert backend.candidate_urls() == [
        "http://127.0.0.1:11434/api/generate",
        "http://localhost:11434/api/generate",
        "http://172.17.0.1:11434/api/generate",
        "http://192.168.65.1:11434/api/generate",
    ]


@pytest.mark.anyio
async def test_generate_falls_back_to_host_docker_internal(monkeypatch):
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    calls = []
    local_url = "http://127.0.0.1:11434/api/generate"
    docker_host_url = "http://host.docker.internal:11434/api/generate"
    containers_host_url = "http://host.containers.internal:11434/api/generate"
    gateway_host_url = "http://gateway.docker.internal:11434/api/generate"
    backend = OllamaBackend(local_url, "llama3.1:8b")

    responses_by_url = {
        local_url: httpx.ConnectError("connection refused", request=httpx.Request("POST", local_url)),
        docker_host_url: _FakeResponse({"response": "ready"}),
        containers_host_url: _FakeResponse({"response": "should not be called"}),
        gateway_host_url: _FakeResponse({"response": "should not be called"}),
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
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    calls = []
    local_url = "http://127.0.0.1:11434/api/generate"
    docker_host_url = "http://host.docker.internal:11434/api/generate"
    containers_host_url = "http://host.containers.internal:11434/api/generate"
    gateway_host_url = "http://gateway.docker.internal:11434/api/generate"
    localhost_alias_url = "http://localhost:11434/api/generate"
    linux_bridge_url = "http://172.17.0.1:11434/api/generate"
    docker_desktop_url = "http://192.168.65.1:11434/api/generate"
    backend = OllamaBackend(local_url, "llama3.1:8b")

    responses_by_url = {
        local_url: httpx.ConnectError("local unavailable", request=httpx.Request("POST", local_url)),
        docker_host_url: httpx.ConnectError(
            "docker host unavailable", request=httpx.Request("POST", docker_host_url)
        ),
        containers_host_url: httpx.ConnectError(
            "containers host unavailable", request=httpx.Request("POST", containers_host_url)
        ),
        gateway_host_url: httpx.ConnectError(
            "gateway host unavailable", request=httpx.Request("POST", gateway_host_url)
        ),
        localhost_alias_url: httpx.ConnectError(
            "localhost alias unavailable", request=httpx.Request("POST", localhost_alias_url)
        ),
        linux_bridge_url: httpx.ConnectError(
            "linux bridge unavailable", request=httpx.Request("POST", linux_bridge_url)
        ),
        docker_desktop_url: httpx.ConnectError(
            "docker desktop unavailable", request=httpx.Request("POST", docker_desktop_url)
        ),
    }

    def fake_client_factory(*args, **kwargs):
        return _FakeAsyncClient(responses_by_url, calls)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    with pytest.raises(BackendUnavailableError) as exc_info:
        await backend.generate("hello", Subsystem.AEGIS)

    assert "Failed to contact model backend" in str(exc_info.value)
    assert calls == [
        local_url,
        docker_host_url,
        gateway_host_url,
        containers_host_url,
        localhost_alias_url,
        linux_bridge_url,
        docker_desktop_url,
    ]


def test_detect_resolv_conf_nameserver_returns_private_ipv4(tmp_path, monkeypatch):
    resolv_conf = tmp_path / "resolv.conf"
    resolv_conf.write_text("nameserver 10.0.0.1\n", encoding="utf-8")

    monkeypatch.setattr("os.path.exists", lambda path: path == "/etc/resolv.conf")

    import builtins

    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if path == "/etc/resolv.conf":
            return real_open(resolv_conf, *args, **kwargs)
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    assert OllamaBackend._detect_resolv_conf_nameserver() == "10.0.0.1"


@pytest.mark.anyio
async def test_candidate_urls_include_explicit_fallback_urls_first(monkeypatch):
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    backend = OllamaBackend(
        "http://127.0.0.1:11434/api/generate",
        "llama3.1:8b",
        fallback_urls=[
            "http://10.0.2.2:11434/api/generate",
            "http://host.docker.internal:11434/api/generate",
        ],
    )

    assert backend.candidate_urls()[:3] == [
        "http://127.0.0.1:11434/api/generate",
        "http://10.0.2.2:11434/api/generate",
        "http://host.docker.internal:11434/api/generate",
    ]


@pytest.mark.anyio
async def test_generate_remembers_last_successful_url(monkeypatch):
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)

    local_url = "http://127.0.0.1:11434/api/generate"
    docker_host_url = "http://host.docker.internal:11434/api/generate"
    backend = OllamaBackend(local_url, "llama3.1:8b")

    calls = []

    responses_by_url = {
        local_url: httpx.ConnectError("local unavailable", request=httpx.Request("POST", local_url)),
        docker_host_url: _FakeResponse({"response": "ok"}),
    }

    def fake_client_factory(*args, **kwargs):
        return _FakeAsyncClient(responses_by_url, calls)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    await backend.generate("hello", Subsystem.AEGIS)
    await backend.generate("hello again", Subsystem.AEGIS)

    assert calls[:2] == [local_url, docker_host_url]
    assert calls[2] == docker_host_url


@pytest.mark.anyio
async def test_candidate_urls_for_host_docker_internal_still_tries_other_local_aliases(monkeypatch):
    monkeypatch.delenv("AETHER_DOCKER_HOST_GATEWAY", raising=False)
    monkeypatch.setattr(OllamaBackend, "_detect_linux_docker_gateway", staticmethod(lambda: None))
    monkeypatch.setattr(OllamaBackend, "_detect_resolv_conf_nameserver", staticmethod(lambda: None))

    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, (host, port))]

    monkeypatch.setattr("socket.getaddrinfo", fake_getaddrinfo)
    backend = OllamaBackend("http://host.docker.internal:11434/api/generate", "llama3.1:8b")

    assert backend.candidate_urls() == [
        "http://host.docker.internal:11434/api/generate",
        "http://gateway.docker.internal:11434/api/generate",
        "http://host.containers.internal:11434/api/generate",
        "http://127.0.0.1:11434/api/generate",
        "http://localhost:11434/api/generate",
        "http://172.17.0.1:11434/api/generate",
        "http://192.168.65.1:11434/api/generate",
    ]
