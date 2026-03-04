from urllib.parse import urlparse, urlunparse

import os
import socket
import time
from dataclasses import dataclass
from ipaddress import IPv4Address
from ipaddress import ip_address

import httpx

from .models import Subsystem
from .observability import BACKEND_ATTEMPT_LATENCY_SECONDS, BACKEND_ATTEMPTS

SYSTEM_PROMPTS = {
    Subsystem.AEGIS: "You are Aegis, focused on safety and hazard prevention in Minecraft.",
    Subsystem.ECLIPSE: "You are Eclipse, focused on anomaly and rift risk interpretation.",
    Subsystem.TERRA: "You are Terra, focused on terrain, scouting, and restoration.",
    Subsystem.HELIOS: "You are Helios, focused on power systems and atmosphere stability.",
    Subsystem.ENFORCER: "You are Enforcer, focused on combat readiness and security.",
    Subsystem.REQUIEM: "You are Requiem, focused on lore, archives, and continuity.",
}


@dataclass
class BackendAttemptSummary:
    attempts: int = 0
    failed_attempts: int = 0
    fallback_hops: int = 0


class BaseBackend:
    async def warmup(self, subsystem: Subsystem = Subsystem.AEGIS) -> str:
        raise NotImplementedError

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str, BackendAttemptSummary]:
        raise NotImplementedError


class BackendUnavailableError(RuntimeError):
    """Raised when the configured model backend cannot be reached."""


class OllamaBackend(BaseBackend):
    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: float = 20.0,
        connect_timeout_seconds: float = 1.0,
        subsystem_models: dict[Subsystem, str] | None = None,
        keep_alive: str = "15m",
        fallback_urls: list[str] | None = None,
        failure_backoff_seconds: float = 30.0,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.connect_timeout_seconds = max(0.1, connect_timeout_seconds)
        self.subsystem_models = subsystem_models or {}
        self.keep_alive = keep_alive
        self.fallback_urls = fallback_urls or []
        self.failure_backoff_seconds = max(0.0, failure_backoff_seconds)
        self._preferred_url: str | None = None
        self._url_backoff_until: dict[str, float] = {}
        self._url_failure_counts: dict[str, int] = {}
        self._preferred_model_name: str | None = None


    @staticmethod
    def _looks_like_missing_model_error(exc: httpx.HTTPStatusError) -> bool:
        if exc.response.status_code != 404:
            return False

        body = (exc.response.text or "").lower()
        return "model" in body and "not found" in body

    @staticmethod
    def _tags_url_from_generate_url(generate_url: str) -> str:
        parsed = urlparse(generate_url)
        path = parsed.path or ""
        if path.endswith("/api/generate"):
            path = f"{path[:-len('/api/generate')]}/api/tags"
        elif path.endswith("/generate"):
            path = f"{path[:-len('/generate')]}/tags"
        else:
            path = "/api/tags"
        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))

    @staticmethod
    def _extract_tag_names(payload: dict) -> list[str]:
        models = payload.get("models")
        if not isinstance(models, list):
            return []

        names: list[str] = []
        for model in models:
            if isinstance(model, dict):
                name = model.get("name")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())

        deduped: list[str] = []
        for name in names:
            if name not in deduped:
                deduped.append(name)
        return deduped

    async def _discover_available_models(self, candidate_url: str) -> list[str]:
        tags_url = self._tags_url_from_generate_url(candidate_url)
        try:
            async with httpx.AsyncClient(timeout=self._client_timeout()) as client:
                response = await client.get(tags_url)
                response.raise_for_status()
                payload = response.json()
            if isinstance(payload, dict):
                return self._extract_tag_names(payload)
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError):
            return []

        return []

    @staticmethod
    def _pick_fallback_model(requested_model: str, available_models: list[str]) -> str | None:
        if not available_models:
            return None

        if requested_model in available_models:
            return requested_model

        requested_repo = requested_model.split(":", 1)[0].strip().lower()
        if requested_repo:
            same_repo = [model for model in available_models if model.split(":", 1)[0].strip().lower() == requested_repo]
            if same_repo:
                return same_repo[0]

        preferences = [
            "aether-ollama-v1",
            "qwen2.5-coder:14b",
            "qwen2.5-coder:7b",
            "llama3.1:8b",
        ]
        for preferred in preferences:
            if preferred in available_models:
                return preferred

        return available_models[0]

    async def _resolve_retry_model(self, candidate_url: str, requested_model: str) -> str | None:
        available_models = await self._discover_available_models(candidate_url)
        fallback_model = self._pick_fallback_model(requested_model, available_models)
        if fallback_model and fallback_model != requested_model:
            self._preferred_model_name = fallback_model
            return fallback_model
        return None

    def _client_timeout(self) -> httpx.Timeout:
        """
        Build timeout profile tuned for local-model backends.

        Connection attempts to a wrong host should fail quickly so fallback
        URLs are tried promptly, while successful connections should tolerate
        slower first-token/model-load latency.
        """
        return httpx.Timeout(connect=self.connect_timeout_seconds, read=self.timeout_seconds, write=10.0, pool=10.0)

    @staticmethod
    def _is_containerized_runtime() -> bool:
        """Best-effort check for containerized runtime contexts."""
        if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
            return True

        container_env = os.getenv("container", "").strip().lower()
        if container_env in {"docker", "podman", "container"}:
            return True

        return bool(os.getenv("KUBERNETES_SERVICE_HOST"))

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

    @staticmethod
    def _candidate_from_host_token(token: str, parsed_base) -> str | None:
        value = token.strip()
        if not value:
            return None

        if "://" in value:
            parsed = urlparse(value)
            if not parsed.netloc:
                return None
            path = parsed.path or parsed_base.path
            return urlunparse(
                (parsed.scheme or parsed_base.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment)
            )

        host_port = value.split("/", 1)[0]
        if not host_port:
            return None

        normalized = host_port.strip().lower()
        if normalized in {"::", "[::]"} or normalized.startswith("[::]:"):
            return None

        host_only = host_port.split(":", 1)[0].lower()
        if host_only in {"0.0.0.0", "::"}:
            return None

        if ":" not in host_port and parsed_base.port:
            host_port = f"{host_port}:{parsed_base.port}"

        return urlunparse(
            (parsed_base.scheme, host_port, parsed_base.path, parsed_base.params, parsed_base.query, parsed_base.fragment)
        )

    def _env_discovered_candidates(self, parsed_base) -> list[str]:
        discovered: list[str] = []
        for env_key in ("AETHER_OLLAMA_URL", "OLLAMA_URL", "OLLAMA_HOST"):
            raw = os.getenv(env_key, "")
            candidate = self._candidate_from_host_token(raw, parsed_base)
            if candidate:
                discovered.append(candidate)

        fallback_env = os.getenv("AETHER_OLLAMA_FALLBACK_URLS", "")
        if fallback_env:
            for token in fallback_env.split(","):
                candidate = self._candidate_from_host_token(token, parsed_base)
                if candidate:
                    discovered.append(candidate)

        return self._dedupe_urls(discovered)

    @staticmethod
    def _dedupe_urls(urls: list[str]) -> list[str]:
        deduped: list[str] = []
        for url in urls:
            if url and url not in deduped:
                deduped.append(url)
        return deduped

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

        candidates = []
        if self._preferred_url:
            candidates.append(self._preferred_url)
        candidates.append(self.base_url)

        discovered_from_env = self._env_discovered_candidates(parsed)
        if discovered_from_env:
            candidates.extend(discovered_from_env)

        if self.fallback_urls:
            candidates.extend(self.fallback_urls)

        local_aliases = {
            "127.0.0.1",
            "localhost",
            "host.docker.internal",
            "gateway.docker.internal",
            "host.containers.internal",
            "ollama",
            "aether-ollama",
            "172.17.0.1",
            "192.168.65.1",
        }
        if hostname not in local_aliases:
            return self._dedupe_urls(candidates)

        hostnames = [
            "ollama",
            "aether-ollama",
            "host.docker.internal",
            "gateway.docker.internal",
            "host.containers.internal",
            "127.0.0.1",
            "localhost",
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

        for docker_host in hostnames:
            is_numeric_host = False
            try:
                ip_address(docker_host)
                is_numeric_host = True
            except ValueError:
                is_numeric_host = False

            if not is_numeric_host:
                try:
                    socket.getaddrinfo(docker_host, parsed.port or 80)
                except socket.gaierror:
                    continue

            try:
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
                candidates.append(candidate_url)
            except ValueError:
                continue

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

        return self._dedupe_urls(candidates)


    def _mark_url_failure(self, url: str) -> None:
        if self.failure_backoff_seconds <= 0:
            return

        failures = self._url_failure_counts.get(url, 0) + 1
        self._url_failure_counts[url] = failures
        backoff_seconds = min(self.failure_backoff_seconds * (2 ** (failures - 1)), 300.0)
        self._url_backoff_until[url] = time.monotonic() + backoff_seconds

    def _mark_url_success(self, url: str) -> None:
        self._url_backoff_until.pop(url, None)
        self._url_failure_counts.pop(url, None)

    def _eligible_candidate_urls(self) -> list[str]:
        candidates = self.candidate_urls()
        now = time.monotonic()
        eligible = [url for url in candidates if self._url_backoff_until.get(url, 0.0) <= now]
        return eligible or candidates

    def model_for_subsystem(self, subsystem: Subsystem) -> str:
        return self.subsystem_models.get(subsystem, self.model_name)

    def connection_attempt_chain(self) -> list[str]:
        """Return backend URLs in the same order generate/warmup will try them."""
        return self._eligible_candidate_urls()

    @staticmethod
    def _format_request_failures(request_failures: list[tuple[str, httpx.RequestError]]) -> str:
        details = ", ".join(
            f"{url} -> {type(error).__name__}: {str(error) or repr(error)}" for url, error in request_failures
        )
        return f"Failed to contact model backend. Attempts: {details}"

    @staticmethod
    def _record_attempt_metric(operation: str, url: str, outcome: str, elapsed_seconds: float) -> None:
        BACKEND_ATTEMPTS.labels(operation, url, outcome).inc()
        BACKEND_ATTEMPT_LATENCY_SECONDS.labels(operation, url, outcome).observe(max(0.0, elapsed_seconds))

    async def warmup(self, subsystem: Subsystem = Subsystem.AEGIS) -> str:
        model_name = self.model_for_subsystem(subsystem)
        if self._preferred_model_name and self._preferred_model_name != model_name:
            model_candidates = [self._preferred_model_name, model_name]
        else:
            model_candidates = [model_name]

        request_failures: list[tuple[str, httpx.RequestError]] = []
        for candidate_url in self._eligible_candidate_urls():
            model_index = 0
            while model_index < len(model_candidates):
                requested_model = model_candidates[model_index]
                attempt_started = time.perf_counter()
                try:
                    async with httpx.AsyncClient(timeout=self._client_timeout()) as client:
                        resp = await client.post(
                            candidate_url,
                            json={
                                "model": requested_model,
                                "prompt": "Warmup request. Reply with: ready.",
                                "stream": False,
                                "keep_alive": self.keep_alive,
                            },
                        )
                        resp.raise_for_status()
                    self._preferred_url = candidate_url
                    self._mark_url_success(candidate_url)
                    self._preferred_model_name = requested_model
                    self._record_attempt_metric("warmup", candidate_url, "success", time.perf_counter() - attempt_started)
                    return requested_model
                except httpx.HTTPStatusError as exc:
                    if self._looks_like_missing_model_error(exc):
                        retry_model = await self._resolve_retry_model(candidate_url, requested_model)
                        if retry_model and retry_model not in model_candidates:
                            model_candidates.append(retry_model)
                            model_index += 1
                            continue
                    self._record_attempt_metric("warmup", candidate_url, "http_error", time.perf_counter() - attempt_started)
                    raise BackendUnavailableError(
                        f"Model backend at {candidate_url} returned {exc.response.status_code}: {exc.response.text}"
                    ) from exc
                except httpx.RequestError as exc:
                    self._mark_url_failure(candidate_url)
                    request_failures.append((candidate_url, exc))
                    self._record_attempt_metric("warmup", candidate_url, "request_error", time.perf_counter() - attempt_started)
                    break

                model_index += 1

        if request_failures:
            raise BackendUnavailableError(self._format_request_failures(request_failures)) from request_failures[-1][1]

        raise BackendUnavailableError(f"Failed to contact model backend at {self.base_url}")

    async def generate(self, prompt: str, subsystem: Subsystem) -> tuple[str, str, BackendAttemptSummary]:
        model_name = self.model_for_subsystem(subsystem)
        if self._preferred_model_name and self._preferred_model_name != model_name:
            model_candidates = [self._preferred_model_name, model_name]
        else:
            model_candidates = [model_name]

        request_failures: list[tuple[str, httpx.RequestError]] = []
        attempt_summary = BackendAttemptSummary()
        for attempt_index, candidate_url in enumerate(self._eligible_candidate_urls()):
            model_index = 0
            while model_index < len(model_candidates):
                requested_model = model_candidates[model_index]
                attempt_summary.attempts += 1
                attempt_started = time.perf_counter()
                try:
                    async with httpx.AsyncClient(timeout=self._client_timeout()) as client:
                        resp = await client.post(
                            candidate_url,
                            json={
                                "model": requested_model,
                                "prompt": f"{SYSTEM_PROMPTS.get(subsystem, SYSTEM_PROMPTS[Subsystem.AEGIS])}\n\nUser request:\n{prompt}",
                                "stream": False,
                                "keep_alive": self.keep_alive,
                            },
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        text = (data.get("response") or "").strip()
                        if not text:
                            self._record_attempt_metric("generate", candidate_url, "empty", time.perf_counter() - attempt_started)
                            raise BackendUnavailableError(
                                f"Model backend at {candidate_url} returned an empty response for model {requested_model}."
                            )
                        self._preferred_url = candidate_url
                        self._mark_url_success(candidate_url)
                        self._preferred_model_name = requested_model
                        attempt_summary.fallback_hops = attempt_index
                        self._record_attempt_metric("generate", candidate_url, "success", time.perf_counter() - attempt_started)
                        return text, requested_model, attempt_summary
                except httpx.HTTPStatusError as exc:
                    if self._looks_like_missing_model_error(exc):
                        retry_model = await self._resolve_retry_model(candidate_url, requested_model)
                        if retry_model and retry_model not in model_candidates:
                            model_candidates.append(retry_model)
                            model_index += 1
                            continue
                    self._record_attempt_metric("generate", candidate_url, "http_error", time.perf_counter() - attempt_started)
                    raise BackendUnavailableError(
                        f"Model backend at {candidate_url} returned {exc.response.status_code}: {exc.response.text}"
                    ) from exc
                except httpx.RequestError as exc:
                    self._mark_url_failure(candidate_url)
                    request_failures.append((candidate_url, exc))
                    attempt_summary.failed_attempts += 1
                    self._record_attempt_metric("generate", candidate_url, "request_error", time.perf_counter() - attempt_started)
                    break

                model_index += 1

        if request_failures:
            raise BackendUnavailableError(self._format_request_failures(request_failures)) from request_failures[-1][1]

        raise BackendUnavailableError(f"Failed to contact model backend at {self.base_url}")
