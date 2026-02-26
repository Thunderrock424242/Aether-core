import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse

from .backends import BackendUnavailableError, OllamaBackend
from .config import parse_subsystem_models, settings
from .memory import SessionLearning, SessionMemory
from .models import (
    DevPlaygroundAuthRequest,
    DevPlaygroundAuthResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    HookStatusResponse,
    LearningStatusResponse,
    ModLifecycleHookRequest,
    ModLifecycleHookResponse,
    Subsystem,
    TeachRequest,
    TeachResponse,
    VersionResponse,
    WarmupResponse,
)
from .observability import GENERATE_REQUESTS, metrics_middleware, metrics_response
from .router import detect_subsystem_alerts, is_minecraft_related, pick_subsystem, subsystem_teaching_context
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
learning = SessionLearning(lesson_limit=settings.learning_lesson_limit, log_path=settings.learning_log_path)
activation_registry = ActivationRegistry()
subsystem_models = parse_subsystem_models(settings.subsystem_models)
if settings.model_backend.lower() != "ollama":
    raise RuntimeError("Unsupported model backend. Set AETHER_MODEL_BACKEND=ollama.")

backend = OllamaBackend(
    settings.ollama_url,
    settings.model_name,
    settings.request_timeout_seconds,
    subsystem_models=subsystem_models,
    keep_alive=settings.ollama_keep_alive,
)


def _validate_hook_token(token: str | None) -> None:
    if settings.activation_hook_token and token != settings.activation_hook_token:
        raise HTTPException(status_code=401, detail="invalid hook token")


def _validate_dev_playground_enabled() -> None:
    if not settings.dev_playground_enabled:
        raise HTTPException(status_code=404, detail="dev playground is disabled")


def _validate_dev_playground_token(token: str | None) -> None:
    expected = settings.dev_playground_token
    if not expected:
        return

    provided = (token or "").strip()
    if provided.lower().startswith("bearer "):
        provided = provided[7:].strip()

    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid playground token")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        model_backend=settings.model_backend,
        model_name=settings.model_name,
        keep_alive=settings.ollama_keep_alive,
    )


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




@app.post("/backend/warmup", response_model=WarmupResponse)
async def backend_warmup(subsystem: Subsystem = Subsystem.AEGIS) -> WarmupResponse:
    try:
        model_name = await backend.warmup(subsystem)
    except BackendUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return WarmupResponse(model_name=model_name, subsystem=subsystem)


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.get("/dev/playground", response_class=HTMLResponse)
async def dev_playground() -> HTMLResponse:
    _validate_dev_playground_enabled()

    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>A.E.T.H.E.R Dev Playground</title>
  <style>
    body { font-family: Inter, Arial, sans-serif; margin: 2rem auto; max-width: 860px; padding: 0 1rem; }
    fieldset { margin-bottom: 1rem; border: 1px solid #ccc; border-radius: 8px; }
    label { display: block; margin-top: .6rem; font-weight: 600; }
    input, select, textarea, button { width: 100%; margin-top: .2rem; padding: .55rem; font: inherit; }
    button { cursor: pointer; }
    .row { display: grid; gap: .8rem; grid-template-columns: 1fr 1fr; }
    pre { background: #111; color: #eee; padding: .8rem; border-radius: 8px; overflow: auto; min-height: 120px; }
  </style>
</head>
<body>
  <h1>A.E.T.H.E.R Dev Playground</h1>
  <p>Dev-only UI for teaching and chatting against the sidecar.</p>

  <fieldset>
    <legend>Session + auth</legend>
    <label>Session ID</label><input id="session" value="dev-session">
    <label>Bearer token (optional)</label><input id="token" placeholder="only needed if configured">
  </fieldset>

  <fieldset>
    <legend>Teach</legend>
    <label>Lesson</label><textarea id="lesson" rows="3" placeholder="This model guides NeoForge mod architecture..."></textarea>
    <button id="teachBtn">Save lesson</button>
  </fieldset>

  <fieldset>
    <legend>Chat</legend>
    <div class="row">
      <div><label>Subsystem</label><select id="subsystem"><option>Auto</option><option>Aegis</option><option>Eclipse</option><option>Terra</option><option>Helios</option><option>Enforcer</option><option>Requiem</option></select></div>
      <div><label>Message</label><input id="message" placeholder="Ask the model..."></div>
    </div>
    <button id="chatBtn">Send</button>
  </fieldset>

  <fieldset>
    <legend>Learning state</legend>
    <button id="loadLessons">Load lessons</button>
  </fieldset>

  <pre id="output"></pre>

<script>
const out = document.getElementById('output');
const headers = () => {
  const token = document.getElementById('token').value.trim();
  const h = {'Content-Type': 'application/json'};
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
};
const sid = () => document.getElementById('session').value.trim();
const show = (label, data) => { out.textContent = `${label}\n` + JSON.stringify(data, null, 2); };

document.getElementById('teachBtn').onclick = async () => {
  const lesson = document.getElementById('lesson').value.trim();
  const r = await fetch('/teach', {method:'POST', headers: headers(), body: JSON.stringify({session_id: sid(), lesson})});
  show('POST /teach', await r.json());
};

document.getElementById('chatBtn').onclick = async () => {
  const body = {
    session_id: sid(),
    subsystem: document.getElementById('subsystem').value,
    message: document.getElementById('message').value,
    player_context: {},
    world_context: {},
  };
  const r = await fetch('/generate', {method:'POST', headers: headers(), body: JSON.stringify(body)});
  show('POST /generate', await r.json());
};

document.getElementById('loadLessons').onclick = async () => {
  const r = await fetch(`/learning/${encodeURIComponent(sid())}`, {headers: headers()});
  show('GET /learning', await r.json());
};
</script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.post("/dev/playground/auth", response_model=DevPlaygroundAuthResponse)
async def dev_playground_auth(
    payload: DevPlaygroundAuthRequest,
) -> DevPlaygroundAuthResponse:
    _validate_dev_playground_enabled()
    _validate_dev_playground_token(payload.token)
    return DevPlaygroundAuthResponse()


@app.post("/teach", response_model=TeachResponse)
async def teach(payload: TeachRequest, authorization: str | None = Header(default=None)) -> TeachResponse:
    _validate_dev_playground_token(authorization)
    learning.teach(payload.session_id, payload.lesson.strip())
    return TeachResponse(lessons_count=len(learning.lessons(payload.session_id)))


@app.get("/learning/{session_id}", response_model=LearningStatusResponse)
async def learning_status(session_id: str, authorization: str | None = Header(default=None)) -> LearningStatusResponse:
    _validate_dev_playground_token(authorization)
    return LearningStatusResponse(session_id=session_id, lessons=learning.lessons(session_id))


@app.post("/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest, authorization: str | None = Header(default=None)) -> GenerateResponse:
    _validate_dev_playground_token(authorization)
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
    learned_context = learning.lessons(payload.session_id)
    non_minecraft_request = not is_minecraft_related(message)

    if safety and safety.blocked:
        GENERATE_REQUESTS.labels(subsystem.value, "true").inc()
        return GenerateResponse(
            text=safe_refusal(),
            subsystem_used=subsystem,
            model_used=(subsystem_models.get(subsystem) or settings.model_name),
            subsystem_alerts={k.value: v for k, v in alerts.items()},
            safety_flags=safety.flags,
            learned_context=learned_context,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    history_text = "\n".join(f"{x['role']}: {x['text']}" for x in memory.history(payload.session_id)[-6:])
    lesson_text = "\n".join(f"- {lesson}" for lesson in learned_context)
    subsystem_training = subsystem_teaching_context(subsystem)
    request_scope = "general-conversation" if non_minecraft_request else "minecraft-subsystem"
    full_prompt = (
        f"Session: {payload.session_id}\n"
        f"Request scope: {request_scope}\n"
        f"Subsystem: {subsystem.value}\n"
        f"Subsystem teaching profile: {subsystem_training}\n"
        f"Detected keyword alerts: { {k.value: v for k, v in alerts.items()} }\n"
        f"Player context: {payload.player_context}\n"
        f"World context: {payload.world_context}\n"
        f"Learned preferences/facts:\n{lesson_text}\n"
        f"History:\n{history_text}\n\n"
        f"Player: {message}\n"
        "Assistant guidance: If the request is not Minecraft-related, respond naturally as A.E.T.H.E.R without refusing."
    )

    try:
        text, model_used = await backend.generate(full_prompt, subsystem)
    except BackendUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    memory.append(payload.session_id, "player", message)
    memory.append(payload.session_id, "assistant", text)
    GENERATE_REQUESTS.labels(subsystem.value, "false").inc()

    return GenerateResponse(
        text=text,
        subsystem_used=subsystem,
        model_used=model_used,
        subsystem_alerts={k.value: v for k, v in alerts.items()},
        safety_flags=(safety.flags if safety else []),
        learned_context=learned_context,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
