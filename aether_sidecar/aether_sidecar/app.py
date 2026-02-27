import time
from dataclasses import dataclass, field

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from .backends import BackendUnavailableError, OllamaBackend
from .config import parse_ollama_fallback_urls, parse_subsystem_models, resolve_model_name, settings
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
    ModelStatusResponse,
    StatusResponse,
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
fallback_urls = parse_ollama_fallback_urls(settings.ollama_fallback_urls)
resolved_model_name = resolve_model_name(settings)
if settings.model_backend.lower() != "ollama":
    raise RuntimeError("Unsupported model backend. Set AETHER_MODEL_BACKEND=ollama.")

backend = OllamaBackend(
    settings.ollama_url,
    resolved_model_name,
    settings.request_timeout_seconds,
    subsystem_models=subsystem_models,
    keep_alive=settings.ollama_keep_alive,
    fallback_urls=fallback_urls,
)


started_at = time.monotonic()


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


@app.get("/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    status_start = time.perf_counter()
    try:
        checked_model = await backend.warmup(Subsystem.AEGIS)
        model_status = ModelStatusResponse(
            status="online",
            checked_model=checked_model,
            latency_ms=int((time.perf_counter() - status_start) * 1000),
        )
    except BackendUnavailableError as exc:
        model_status = ModelStatusResponse(
            status="offline",
            detail=str(exc),
            checked_model=resolved_model_name,
            latency_ms=int((time.perf_counter() - status_start) * 1000),
        )

    return StatusResponse(
        model_backend=settings.model_backend,
        model_name=resolved_model_name,
        keep_alive=settings.ollama_keep_alive,
        uptime_seconds=int(time.monotonic() - started_at),
        activation_required=settings.activation_hook_enabled,
        active_instances=activation_registry.status(),
        model=model_status,
    )


@app.get("/status/page", response_class=HTMLResponse)
async def status_page() -> HTMLResponse:
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>A.E.T.H.E.R API Status</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --card: #111a32;
      --border: #1f2a47;
      --text: #e8ecf8;
      --muted: #9da9c5;
      --ok: #3ddc97;
      --bad: #ff6b6b;
      --warn: #ffd166;
      --accent: #5da9ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      background: linear-gradient(180deg, #0b1020 0%, #111937 100%);
      color: var(--text);
      min-height: 100vh;
      padding: 2rem 1rem;
    }
    .container { max-width: 960px; margin: 0 auto; }
    .header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
    h1 { margin: 0; font-size: 1.8rem; }
    .sub { color: var(--muted); margin-top: .4rem; }
    .badge {
      border: 1px solid var(--border);
      background: #0f1730;
      padding: .55rem .85rem;
      border-radius: 999px;
      white-space: nowrap;
      font-size: .9rem;
    }
    .grid { margin-top: 1.2rem; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: .8rem; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: .95rem;
    }
    .label { color: var(--muted); font-size: .82rem; text-transform: uppercase; letter-spacing: .03em; }
    .value { font-size: 1.05rem; margin-top: .4rem; }
    .pill {
      display: inline-block;
      padding: .2rem .55rem;
      border-radius: 999px;
      font-size: .78rem;
      margin-left: .5rem;
      border: 1px solid transparent;
    }
    .pill.ok { background: rgba(61,220,151,.18); color: var(--ok); border-color: rgba(61,220,151,.45); }
    .pill.bad { background: rgba(255,107,107,.15); color: var(--bad); border-color: rgba(255,107,107,.45); }
    .section-title { margin: 1.4rem 0 .7rem; font-size: 1rem; color: var(--muted); }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .timeline { list-style: none; padding: 0; margin: 0; }
    .timeline li { padding: .55rem 0; border-bottom: 1px dashed var(--border); color: #c6d0ea; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <main class="container">
    <header class="header">
      <div>
        <h1>A.E.T.H.E.R API Status</h1>
        <p class="sub">Live service health for inference and activation hooks.</p>
      </div>
      <div id="headline" class="badge">Checking status…</div>
    </header>

    <section class="grid" aria-label="service summary">
      <article class="card">
        <div class="label">Model Backend</div>
        <div id="modelBackend" class="value">—</div>
      </article>
      <article class="card">
        <div class="label">Model</div>
        <div id="modelName" class="value mono">—</div>
      </article>
      <article class="card">
        <div class="label">Backend Latency</div>
        <div id="latency" class="value">—</div>
      </article>
      <article class="card">
        <div class="label">Uptime</div>
        <div id="uptime" class="value">—</div>
      </article>
    </section>

    <h2 class="section-title">Components</h2>
    <section class="grid" aria-label="component status">
      <article class="card">
        <div class="label">Inference API</div>
        <div class="value">/generate <span id="inferencePill" class="pill">unknown</span></div>
      </article>
      <article class="card">
        <div class="label">Activation Hooks</div>
        <div class="value"><span id="hooksSummary">—</span><span id="hooksPill" class="pill">unknown</span></div>
      </article>
      <article class="card">
        <div class="label">Keep Alive</div>
        <div id="keepAlive" class="value">—</div>
      </article>
    </section>

    <h2 class="section-title">Latest Events</h2>
    <article class="card">
      <ul id="events" class="timeline">
        <li>Waiting for first status check…</li>
      </ul>
      <p class="sub">Raw JSON: <a href="/status" target="_blank" rel="noopener">/status</a></p>
    </article>
  </main>

  <script>
    const formatUptime = (seconds) => {
      const d = Math.floor(seconds / 86400);
      const h = Math.floor((seconds % 86400) / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      const s = seconds % 60;
      const parts = [];
      if (d) parts.push(`${d}d`);
      if (h || d) parts.push(`${h}h`);
      if (m || h || d) parts.push(`${m}m`);
      parts.push(`${s}s`);
      return parts.join(' ');
    };

    const setPill = (el, ok, okText, badText) => {
      el.classList.remove('ok', 'bad');
      el.classList.add(ok ? 'ok' : 'bad');
      el.textContent = ok ? okText : badText;
    };

    const addEvent = (msg) => {
      const events = document.getElementById('events');
      if (events.children.length === 1 && events.children[0].textContent.includes('Waiting')) {
        events.innerHTML = '';
      }
      const li = document.createElement('li');
      const ts = new Date().toLocaleTimeString();
      li.textContent = `[${ts}] ${msg}`;
      events.prepend(li);
      while (events.children.length > 6) {
        events.removeChild(events.lastElementChild);
      }
    };

    const refresh = async () => {
      try {
        const response = await fetch('/status', { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();

        document.getElementById('modelBackend').textContent = data.model_backend;
        document.getElementById('modelName').textContent = data.model.checked_model || data.model_name;
        document.getElementById('latency').textContent = `${data.model.latency_ms} ms`;
        document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
        document.getElementById('keepAlive').textContent = data.keep_alive || 'default';

        const online = data.model.status === 'online';
        const headline = document.getElementById('headline');
        headline.textContent = online ? 'All systems operational' : 'Partial outage detected';
        setPill(document.getElementById('inferencePill'), online, 'operational', 'degraded');

        const hookEnabled = data.activation_required;
        const hookActive = !hookEnabled || (data.active_instances && data.active_instances.length > 0);
        document.getElementById('hooksSummary').textContent = hookEnabled
          ? `${data.active_instances.length} active instance(s)`
          : 'Not required';
        setPill(document.getElementById('hooksPill'), hookActive, 'healthy', 'waiting');

        addEvent(
          online
            ? `Model backend responded in ${data.model.latency_ms} ms.`
            : `Model backend offline: ${data.model.detail || 'unavailable'}`
        );
      } catch (error) {
        document.getElementById('headline').textContent = 'Status check failed';
        setPill(document.getElementById('inferencePill'), false, 'operational', 'degraded');
        addEvent(`Unable to fetch /status: ${error.message}`);
      }
    };

    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.get("/heath")
async def heath_redirect() -> RedirectResponse:
    return RedirectResponse(url="/status", status_code=307)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        model_backend=settings.model_backend,
        model_name=resolved_model_name,
        keep_alive=settings.ollama_keep_alive,
    )


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/generate", status_code=307)


@app.get("/generate", response_class=HTMLResponse)
async def generate_home() -> HTMLResponse:
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>A.E.T.H.E.R Chat</title>
  <style>
    body { font-family: Inter, Arial, sans-serif; margin: 2rem auto; max-width: 860px; padding: 0 1rem; }
    textarea, input, button { width: 100%; margin-top: .4rem; padding: .55rem; font: inherit; }
    button { cursor: pointer; }
    .chatlog { background: #0d1117; color: #e6edf3; padding: .8rem; border-radius: 8px; min-height: 120px; margin-top: 1rem; }
    .chatlog p { margin: .4rem 0; white-space: pre-wrap; }
    .muted { color: #666; }
  </style>
</head>
<body>
<h1>A.E.T.H.E.R Chat</h1>
<p class="muted">Use this page for regular website chat at <code>/generate</code>. API clients can POST to <code>/generate</code>.</p>
<label for="session">Session ID</label>
<input id="session" value="web-user-session">
<label for="message">Message</label>
<textarea id="message" rows="4" placeholder="Ask A.E.T.H.E.R anything..."></textarea>
<button id="send">Send</button>
<div id="chatlog" class="chatlog"></div>
<script>
const chatlog = document.getElementById('chatlog');

const addMessage = (role, text) => {
  const p = document.createElement('p');
  p.textContent = `${role}: ${text}`;
  chatlog.appendChild(p);
};

document.getElementById('send').onclick = async () => {
  const message = document.getElementById('message').value.trim();
  if (!message) {
    addMessage('System', 'message is required');
    return;
  }

  const response = await fetch('/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      session_id: document.getElementById('session').value || 'web-user-session',
      subsystem: 'Auto',
      message,
      player_context: {},
      world_context: {},
    }),
  });

  const data = await response.json();
  addMessage('You', message);
  addMessage('A.E.T.H.E.R', data.text || data.detail || 'No response text');
  document.getElementById('message').value = '';
};
</script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(version=settings.app_version, model_name=resolved_model_name)


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
    .chatlog { background: #0d1117; color: #e6edf3; padding: .8rem; border-radius: 8px; min-height: 120px; }
    .chatlog p { margin: .4rem 0; white-space: pre-wrap; }
    .muted { font-size: .9rem; color: #666; }
    .inline { display: flex; align-items: center; gap: .5rem; margin-top: .7rem; }
    .inline input[type=checkbox] { width: auto; margin: 0; }
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
    <div class="inline">
      <input id="teachBeforeChat" type="checkbox">
      <label for="teachBeforeChat">Teach the current message before sending it to chat</label>
    </div>
    <button id="chatBtn">Send</button>
  </fieldset>

  <fieldset>
    <legend>Conversation</legend>
    <div class="chatlog" id="chatlog"><p class="muted">No messages yet.</p></div>
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
  const h = {'Content-Type': 'application/json', 'X-Aether-Dev-Playground': 'true'};
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
};
const sid = () => document.getElementById('session').value.trim();
const show = (label, data) => { out.textContent = `${label}\n` + JSON.stringify(data, null, 2); };
const chatlog = document.getElementById('chatlog');
let hasMessages = false;

const addMessage = (role, text) => {
  if (!hasMessages) {
    chatlog.innerHTML = '';
    hasMessages = true;
  }
  const p = document.createElement('p');
  p.textContent = `${role}: ${text}`;
  chatlog.appendChild(p);
};

const maybeTeachFromChatMessage = async (message) => {
  if (!document.getElementById('teachBeforeChat').checked) {
    return;
  }
  const teachResponse = await fetch('/teach', {
    method:'POST',
    headers: headers(),
    body: JSON.stringify({session_id: sid(), lesson: message})
  });
  show('POST /teach (from chat)', await teachResponse.json());
};

document.getElementById('teachBtn').onclick = async () => {
  const lesson = document.getElementById('lesson').value.trim();
  const r = await fetch('/teach', {method:'POST', headers: headers(), body: JSON.stringify({session_id: sid(), lesson})});
  show('POST /teach', await r.json());
};

document.getElementById('chatBtn').onclick = async () => {
  const message = document.getElementById('message').value.trim();
  if (!message) {
    show('validation', {detail: 'message is required'});
    return;
  }

  await maybeTeachFromChatMessage(message);
  const body = {
    session_id: sid(),
    subsystem: document.getElementById('subsystem').value,
    message,
    player_context: {},
    world_context: {},
  };
  const r = await fetch('/generate', {method:'POST', headers: headers(), body: JSON.stringify(body)});
  const data = await r.json();
  show('POST /generate', data);
  addMessage('Player', message);
  if (data.text) {
    addMessage('A.E.T.H.E.R', data.text);
  }
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
async def generate(
    payload: GenerateRequest,
    authorization: str | None = Header(default=None),
    x_aether_dev_playground: str | None = Header(default=None),
) -> GenerateResponse:
    _validate_dev_playground_token(authorization)
    started = time.perf_counter()
    dev_playground_bypass = settings.dev_playground_enabled and (x_aether_dev_playground or "").strip().lower() == "true"

    if not activation_registry.is_active() and not dev_playground_bypass:
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
            model_used=(subsystem_models.get(subsystem) or resolved_model_name),
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
