import asyncio

import httpx
import pytest

from aether_sidecar.backends import BackendUnavailableError, OllamaBackend
from aether_sidecar.models import Subsystem


class StubResponse:
    def __init__(self, payload: dict[str, str]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return self._payload


def test_ollama_backend_retries_then_succeeds(monkeypatch):
    backend = OllamaBackend(
        "http://127.0.0.1:11434/api/generate",
        "llama3.1:8b",
        max_retries=3,
        retry_base_backoff_seconds=0.0,
        retry_max_backoff_seconds=0.0,
    )

    attempts = {"count": 0}

    async def fake_post(*args, **kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise httpx.ConnectError("connection refused")
        return StubResponse({"response": "ready"})

    monkeypatch.setattr(backend.client, "post", fake_post)

    text, model = asyncio.run(backend.generate("ping", Subsystem.AEGIS))
    assert text == "ready"
    assert model == "llama3.1:8b"
    assert attempts["count"] == 3


def test_ollama_backend_raises_after_max_retries(monkeypatch):
    backend = OllamaBackend(
        "http://127.0.0.1:11434/api/generate",
        "llama3.1:8b",
        max_retries=2,
        retry_base_backoff_seconds=0.0,
        retry_max_backoff_seconds=0.0,
    )

    async def always_fail(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(backend.client, "post", always_fail)

    with pytest.raises(BackendUnavailableError) as exc:
        asyncio.run(backend.generate("ping", Subsystem.AEGIS))

    assert "after 2 attempt" in str(exc.value)
