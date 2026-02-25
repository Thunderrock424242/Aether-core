import time

from fastapi import FastAPI, HTTPException

from .backends import OllamaBackend, TemplateBackend
from .config import settings
from .memory import SessionMemory
from .models import GenerateRequest, GenerateResponse, HealthResponse, Subsystem, VersionResponse
from .observability import GENERATE_REQUESTS, metrics_middleware, metrics_response
from .router import detect_subsystem_alerts, pick_subsystem
from .safety import evaluate_message, safe_refusal

app = FastAPI(title="A.E.T.H.E.R Sidecar", version=settings.app_version)
app.middleware("http")(metrics_middleware)

memory = SessionMemory(turn_limit=settings.memory_turn_limit)
backend = (
    OllamaBackend(settings.ollama_url, settings.model_name, settings.request_timeout_seconds)
    if settings.model_backend.lower() == "ollama"
    else TemplateBackend()
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(model_backend=settings.model_backend, model_name=settings.model_name)


@app.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(version=settings.app_version, model_name=settings.model_name)


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    started = time.perf_counter()
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
