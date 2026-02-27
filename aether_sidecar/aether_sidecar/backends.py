from urllib.parse import urlparse, urlunparse

import os
import socket
from ipaddress import IPv4Address

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

    def _client_timeout(self) -> httpx.Timeout:
        """
        Build timeout profile tuned for local-model backends.

        Connection attempts to a wrong host should fail quickly so fallback
        URLs are tried promptly, while successful connections should tolerate
        slower first-token/model-load latency.
        """
        return httpx.Timeout(connect=3.0, read=self.timeout_seconds, write=10.0, pool=10.0)

    @staticmethod
    def _detect_linux_docker_gateway() -> str | None:
        """Best-effort detection of Docker bridge gateway IP on Linux."""
        route_file = "/proc/net/route"
        if not os.path.exists(route_file):
            return None

        try:
            with open(route_file, encoding="utf-8") as handle:
                next(handle, None)
                for line in handle:
                    fields = line.strip().split()
                    if len(fields) < 3:
                        continue
                    destination, gateway_hex = fields[1], fields[2]
                    if destination != "00000000":
                        continue
                    gateway_bytes = bytes.fromhex(gateway_hex)
                    gateway_ip = str(IPv4Address(gateway_bytes[::-1]))
                    return gateway_ip
        except (OSError, ValueError):
            return None

        return None

    @staticmethod
    def _detect_resolv_conf_nameserver() -> str | None:
        """Best-effort fallback for devcontainer/WSL host gateway detection."""
        resolv_conf = "/etc/resolv.conf"
        if not os.path.exists(resolv_conf):
            return None

        try:
            with open(resolv_conf, encoding="utf-8") as handle:
                for line in handle:
                    parts = line.strip().split()
                    if len(parts) == 2 and parts[0] == "nameserver":
                        candidate = parts[1]
                        try:
                            ip = IPv4Address(candidate)
                        except ValueError:
                            continue

                        if ip.is_private:
                            return str(ip)
        except OSError:
            return None

        return None

    def candidate_urls(self) -> list[str]:
        """
        Return backend URLs to try in order.

        In containerized/devcontainer setups, ``127.0.0.1`` resolves to the
        container itself rather than the user's host machine where Ollama is
        often running. When the configured URL points at localhost, add common
        Docker host aliases as secondary candidates.
        """
        parsed = urlparse(self.base_url)
        hostname = (parsed.hostname or "").lower()

        if hostname not in {"127.0.0.1", "localhost"}:
            return [self.base_url]

        hostnames = [
            "host.docker.internal",
            "gateway.docker.internal",
            "host.containers.internal",
        ]
        fallback_ips = ["172.17.0.1", "192.168.65.1"]
        docker_host_override = os.getenv("AETHER_DOCKER_HOST_GATEWAY", "").strip()
        if docker_host_override:
            hostnames.append(docker_host_override)

        linux_gateway_ip = self._detect_linux_docker_gateway()
        if linux_gateway_ip:
            hostnames.append(linux_gateway_ip)

        resolv_conf_ip = self._detect_resolv_conf_nameserver()
        if resolv_conf_ip:
            hostnames.append(resolv_conf_ip)

        hostnames.extend(fallback_ips)

        candidates = [self.base_url]
        for docker_host in hostnames:
            try:
                socket.getaddrinfo(docker_host, parsed.port or 80)
            except socket.gaierror:
                continue

            host_port = docker_host
            if parsed.port:
                host_port = f"{host_port}:{parsed.port}"

            candidate_url = urlunparse(
                (
                    parsed.scheme,
                    host_port,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
            if candidate_url not in candidates:
                candidates.append(candidate_url)

        if len(candidates) == 1 and linux_gateway_ip:
            host_port = linux_gateway_ip if not parsed.port else f"{linux_gateway_ip}:{parsed.port}"
            candidates.append(
                urlunparse(
                    (
                        parsed.scheme,
                        host_port,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            )

        return candidates

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.model_name)

    @staticmethod
    def _format_request_failures(request_failures: list[tuple[str, httpx.RequestError]]) -> str:
        details = ", ".join(
            f"{url} -> {type(error).__name__}: {str(error) or repr(error)}" for url, error in request_failures
        )
        return f"Failed to contact model backend. Attempts: {details}"

    async def warmup(self, subsystem: Subsystem = Subsystem.AEGIS) -> str:
        model_name = self.model_for_subsystem(subsystem)
        request_failures: list[tuple[str, httpx.RequestError]] = []
        for candidate_url in self.candidate_urls():
            try:
                async with httpx.AsyncClient(timeout=self._client_timeout()) as client:
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
                request_failures.append((candidate_url, exc))

        if request_failures:
            raise BackendUnavailableError(self._format_request_failures(request_failures)) from request_failures[-1][1]

        raise BackendUnavailableError(f"Failed to contact model backend at {self.base_url}")

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str]:
        model_name = self.model_for_subsystem(subsystem)
        request_failures: list[tuple[str, httpx.RequestError]] = []
        for candidate_url in self.candidate_urls():
            try:
                async with httpx.AsyncClient(timeout=self._client_timeout()) as client:
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
                request_failures.append((candidate_url, exc))

        if request_failures:
            raise BackendUnavailableError(self._format_request_failures(request_failures)) from request_failures[-1][1]

        raise BackendUnavailableError(f"Failed to contact model backend at {self.base_url}")
