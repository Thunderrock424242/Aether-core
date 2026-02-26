import asyncio

import httpx

from .models import Subsystem

SYSTEM_PROMPTS = {
    Subsystem.AEGIS: "You are Aegis, focused on safety and hazard prevention in Minecraft.",
    Subsystem.ECLIPSE: "You are Eclipse, focused on anomaly and rift risk interpretation.",
    Subsystem.TERRA: "You are Terra, focused on terrain, scouting, and restoration.",
    Subsystem.HELIOS: "You are Helios, focused on power systems and atmosphere stability.",
    Subsystem.ENFORCER: "You are Enforcer, focused on combat readiness and security.",
    Subsystem.REQUIEM: "You are Requiem, focused on lore, archives, and continuity.",
}


class BaseBackend:
    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        raise NotImplementedError


class BackendUnavailableError(RuntimeError):
    """Raised when the configured model backend cannot be reached."""


class OllamaBackend(BaseBackend):
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float = 20.0,
        subsystem_models: dict[Subsystem, str] | None = None,
        connect_timeout_seconds: float = 5.0,
        max_retries: int = 3,
        retry_base_backoff_seconds: float = 0.25,
        retry_max_backoff_seconds: float = 2.0,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.subsystem_models = subsystem_models or {}
        self.connect_timeout_seconds = max(0.1, connect_timeout_seconds)
        self.max_retries = max(1, max_retries)
        self.retry_base_backoff_seconds = max(0.0, retry_base_backoff_seconds)
        self.retry_max_backoff_seconds = max(0.0, retry_max_backoff_seconds)
        request_timeout = httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=self.connect_timeout_seconds,
        )
        self.client = httpx.AsyncClient(timeout=request_timeout)

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.model_name)

    async def _request(self, prompt: str, subsystem: Subsystem, model_name: str) -> str:
        resp = await self.client.post(
            self.base_url,
            json={
                "model": model_name,
                "prompt": f"{SYSTEM_PROMPTS.get(subsystem, SYSTEM_PROMPTS[Subsystem.AEGIS])}\n\nUser request:\n{prompt}",
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("response") or "").strip() or "No model response."

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        model_name = self.model_for_subsystem(subsystem)
        last_error: httpx.RequestError | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                text = await self._request(prompt, subsystem, model_name)
                return text, model_name
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break

                backoff_cap = min(
                    self.retry_max_backoff_seconds,
                    self.retry_base_backoff_seconds * (2 ** (attempt - 1)),
                )
                if backoff_cap > 0:
                    await asyncio.sleep(backoff_cap)

        raise BackendUnavailableError(
            f"Failed to contact model backend at {self.base_url} after {self.max_retries} attempt(s): {last_error}"
        ) from last_error
