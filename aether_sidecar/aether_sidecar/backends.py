from urllib.parse import urlparse, urlunparse

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
    async def warmup(self, subsystem: Subsystem = Subsystem.AEGIS) -> str:
        raise NotImplementedError

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
        keep_alive: str = "15m",
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.subsystem_models = subsystem_models or {}
        self.keep_alive = keep_alive

    def candidate_urls(self) -> list[str]:
        """
        Return backend URLs to try in order.

        In containerized/devcontainer setups, ``127.0.0.1`` resolves to the
        container itself rather than the user's host machine where Ollama is
        often running. When the configured URL points at localhost, add a
        secondary ``host.docker.internal`` candidate.
        """
        parsed = urlparse(self.base_url)
        hostname = (parsed.hostname or "").lower()

        if hostname not in {"127.0.0.1", "localhost"}:
            return [self.base_url]

        host_port = "host.docker.internal"
        if parsed.port:
            host_port = f"{host_port}:{parsed.port}"

        docker_host_url = urlunparse(
            (
                parsed.scheme,
                host_port,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

        if docker_host_url == self.base_url:
            return [self.base_url]

        return [self.base_url, docker_host_url]

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.model_name)

    async def warmup(self, subsystem: Subsystem = Subsystem.AEGIS) -> str:
        model_name = self.model_for_subsystem(subsystem)
        request_error: httpx.RequestError | None = None
        for candidate_url in self.candidate_urls():
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(
                        candidate_url,
                        json={
                            "model": model_name,
                            "prompt": "Warmup request. Reply with: ready.",
                            "stream": False,
                            "keep_alive": self.keep_alive,
                        },
                    )
                    resp.raise_for_status()
                return model_name
            except httpx.HTTPStatusError as exc:
                raise BackendUnavailableError(
                    f"Model backend at {candidate_url} returned {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                request_error = exc

        raise BackendUnavailableError(
            f"Failed to contact model backend at {self.base_url}: {request_error}"
        ) from request_error

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        model_name = self.model_for_subsystem(subsystem)
        request_error: httpx.RequestError | None = None
        for candidate_url in self.candidate_urls():
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(
                        candidate_url,
                        json={
                            "model": model_name,
                            "prompt": f"{SYSTEM_PROMPTS.get(subsystem, SYSTEM_PROMPTS[Subsystem.AEGIS])}\n\nUser request:\n{prompt}",
                            "stream": False,
                            "keep_alive": self.keep_alive,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    text = (data.get("response") or "").strip() or "No model response."
                    return text, model_name
            except httpx.HTTPStatusError as exc:
                raise BackendUnavailableError(
                    f"Model backend at {candidate_url} returned {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                request_error = exc

        raise BackendUnavailableError(
            f"Failed to contact model backend at {self.base_url}: {request_error}"
        ) from request_error
