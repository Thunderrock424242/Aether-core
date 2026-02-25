import time
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException

from .backends import OllamaBackend, TemplateBackend
from .config import settings
from .memory import SessionMemory
from .models import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    HookStatusResponse,
    ModLifecycleHookRequest,
    ModLifecycleHookResponse,
    Subsystem,
    VersionResponse,
)
from .observability import GENERATE_REQUESTS, metrics_middleware, metrics_response
from .router import detect_subsystem_alerts, pick_subsystem
from .safety import evaluate_message, safe_refusal


@dataclass
class ActivationRegistry:
    active_instances: set[str] = field(default_factory=set)

    def activate(self, instance_id: str) -> None:
        self.active_instances.add(instance_id)

    def deactivate(self, instance_id: str) -> None:
        self.active_instances.discard(instance_id)

    def is_active(self) -> bool:
        return not settings.activation_hook_enabled or bool(self.active_instances)

    def status(self) -> list[str]:
        return sorted(self.active_instances)


app = FastAPI(title="A.E.T.H.E.R Sidecar", version=settings.app_version)
app.middleware("http")(metrics_middleware)

memory = SessionMemory(turn_limit=settings.memory_turn_limit)
activation_registry = ActivationRegistry()
backend = (
    OllamaBackend(settings.ollama_url, settings.model_name, settings.request_timeout_seconds)
    if settings.model_backend.lower() == "ollama"
    else TemplateBackend()
)


def _validate_hook_token(token: str | None) -> None:
    if settings.activation_hook_token and token != settings.activation_hook_token:
        raise HTTPException(status_code=401, detail="invalid hook token")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(model_backend=settings.model_backend, model_name=settings.model_name)


@app.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(version=settings.app_version, model_name=settings.model_name)


@app.get("/hooks/status", response_model=HookStatusResponse)
async def hook_status() -> HookStatusResponse:
    return HookStatusResponse(
        activation_required=settings.activation_hook_enabled,
        active_instances=activation_registry.status(),
    )


@app.post("/hooks/mod-lifecycle", response_model=ModLifecycleHookResponse)
async def mod_lifecycle_hook(payload: ModLifecycleHookRequest) -> ModLifecycleHookResponse:
    _validate_hook_token(payload.token)

    if payload.action.value == "activate":
        activation_registry.activate(payload.instance_id)
    else:
        activation_registry.deactivate(payload.instance_id)

    return ModLifecycleHookResponse(
        activation_required=settings.activation_hook_enabled,
        active_instances=activation_registry.status(),
    )


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    started = time.perf_counter()

    if not activation_registry.is_active():
        raise HTTPException(
            status_code=503,
            detail="AETHER activation required: call /hooks/mod-lifecycle with action=activate",
        )

    message = payload.message.strip()
    if len(message) > settings.max_message_chars:
        raise HTTPException(status_code=400, detail=f"message exceeds {settings.max_message_chars} chars")

    safety = evaluate_message(message) if settings.safety_enabled else None
    alerts = detect_subsystem_alerts(message)
    subsystem = payload.subsystem if payload.subsystem != Subsystem.AUTO else pick_subsystem(message)

    if safety and safety.blocked:
        GENERATE_REQUESTS.labels(subsystem.value, "true").inc()
        return GenerateResponse(
            text=safe_refusal(),
            subsystem_used=subsystem,
            subsystem_alerts={k.value: v for k, v in alerts.items()},
            safety_flags=safety.flags,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    history_text = "\n".join(f"{x['role']}: {x['text']}" for x in memory.history(payload.session_id)[-6:])
    full_prompt = (
        f"Session: {payload.session_id}\n"
        f"Subsystem: {subsystem.value}\n"
        f"Detected keyword alerts: { {k.value: v for k, v in alerts.items()} }\n"
        f"Player context: {payload.player_context}\n"
        f"World context: {payload.world_context}\n"
        f"History:\n{history_text}\n\n"
        f"Player: {message}"
    )

    text = await backend.generate(full_prompt, subsystem)
    memory.append(payload.session_id, "player", message)
    memory.append(payload.session_id, "assistant", text)
    GENERATE_REQUESTS.labels(subsystem.value, "false").inc()

    return GenerateResponse(
        text=text,
        subsystem_used=subsystem,
        subsystem_alerts={k.value: v for k, v in alerts.items()},
        safety_flags=(safety.flags if safety else []),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
