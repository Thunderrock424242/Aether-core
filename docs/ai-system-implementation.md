# A.E.T.H.E.R Implemented Local Sidecar

This repository now includes a runnable, non-Java AI runtime in `aether_sidecar/`.

## What is implemented
- FastAPI sidecar endpoints: `POST /generate`, `POST /teach`, `GET /learning/{session_id}`, `GET /health`, `GET /version`, `GET /metrics`
- Mod lifecycle hook endpoints: `POST /hooks/mod-lifecycle`, `GET /hooks/status`
- Keyword-driven subsystem alert detection for Aegis/Eclipse/Terra/Helios/Enforcer/Requiem
- Subsystem auto-routing based on detected keyword matches
- Bounded session memory
- Teachable per-session learning notes for user preferences/facts
- Optional persisted teaching log (`AETHER_LEARNING_LOG_PATH`) so lessons survive sidecar restarts
- Safety pre-check + refusal behavior
- Ollama backend (`ollama`)
- Optional per-subsystem model routing (`AETHER_SUBSYSTEM_MODELS`) for specialist sub-models
- Unit tests for routing/safety/app endpoints

## Quick start
```bash
./scripts/run_sidecar_dev.sh
```

PowerShell:
```powershell
.\scripts\run_sidecar_dev.ps1
```

The dev script now bootstraps/reuses `.venv`, installs dependencies, and runs Uvicorn with hot reload by default.

## Making Ollama reliable on user/dev machines
To keep local inference stable whenever Ollama is running, use these defaults:

- Ensure Ollama is started before sidecar startup (`ollama serve`) and keep it as a background service where possible.
- Prefer loopback URLs (`http://127.0.0.1:11434/api/generate`) on non-container installs.
- Configure retries/backoff in sidecar:
  - `AETHER_OLLAMA_MAX_RETRIES` (default `3`)
  - `AETHER_OLLAMA_RETRY_BASE_BACKOFF_SECONDS` (default `0.25`)
  - `AETHER_OLLAMA_RETRY_MAX_BACKOFF_SECONDS` (default `2.0`)
  - `AETHER_OLLAMA_CONNECT_TIMEOUT_SECONDS` (default `5.0`)
- Keep a slightly larger end-to-end request timeout for larger models via `AETHER_REQUEST_TIMEOUT_SECONDS` (default `20.0`).
- Pre-pull required models (`ollama pull <model>`) so the first request does not fail while pulling.
- Validate health before gameplay sessions with `curl http://127.0.0.1:8765/health` and a quick `POST /generate` smoke test.

These settings make transient connection errors (startup races, brief socket resets, local CPU pressure) automatically recover without user-visible failures.

## NeoForge integration payload
```json
{
  "message": "player text",
  "subsystem": "Auto",
  "player_context": {"health": 16, "armor": 6},
  "world_context": {"biome": "taiga", "weather": "rain"},
  "session_id": "player-uuid"
}
```

## Generate response payload (includes keyword alerts)
```json
{
  "text": "assistant response",
  "subsystem_used": "Eclipse",
  "model_used": "aether-eclipse-v1",
  "subsystem_alerts": {"Eclipse": ["rift", "anomaly"]},
  "safety_flags": [],
  "learned_context": ["Use concise responses"],
  "latency_ms": 42
}
```


## Teachable learning playground API
Dev-only browser UI endpoint: `GET /dev/playground` (disabled unless `AETHER_DEV_PLAYGROUND_ENABLED=true`).

Enable from PowerShell:
```powershell
$env:AETHER_DEV_PLAYGROUND_ENABLED = "true"
.\scripts\run_sidecar_dev.ps1
```

Use `POST /teach` to store facts/preferences per session.

```json
POST /teach
{
  "lesson": "I am building Minecraft NeoForge mods with Gradle.",
  "session_id": "player-uuid"
}
```

Read stored lessons with `GET /learning/{session_id}`. These notes are injected into `/generate` prompts and echoed back as `learned_context` in responses.
Set `AETHER_LEARNING_LOG_PATH` (for example `.aether/learning_lessons.jsonl`) to append every `POST /teach` lesson as JSONL and reload it when the sidecar starts.

If `AETHER_DEV_PLAYGROUND_TOKEN` is set, send it as `Authorization: Bearer <token>` for `/generate`, `/teach`, and `/learning/{session_id}`.

## Mod lifecycle activation hook (for bundled Java mods)
When `AETHER_ACTIVATION_HOOK_ENABLED=true`, the sidecar requires at least one active mod instance before `/generate` will respond.

### Activate on mod startup
```json
POST /hooks/mod-lifecycle
{
  "action": "activate",
  "mod_id": "your.mod.id",
  "mod_version": "1.2.3",
  "instance_id": "player-or-client-id",
  "token": "optional-if-AETHER_ACTIVATION_HOOK_TOKEN-is-set"
}
```

### Deactivate on mod shutdown
```json
POST /hooks/mod-lifecycle
{
  "action": "deactivate",
  "mod_id": "your.mod.id",
  "mod_version": "1.2.3",
  "instance_id": "player-or-client-id",
  "token": "optional-if-AETHER_ACTIVATION_HOOK_TOKEN-is-set"
}
```

### Minimal NeoForge Java sketch
```java
public final class AetherLifecycleHook {
    private static final HttpClient HTTP = HttpClient.newHttpClient();

    public static void onModStarted(String instanceId) {
        postLifecycle("activate", instanceId);
    }

    public static void onModStopping(String instanceId) {
        postLifecycle("deactivate", instanceId);
    }

    private static void postLifecycle(String action, String instanceId) {
        String json = """
            {
              "action": "%s",
              "mod_id": "your.mod.id",
              "mod_version": "1.0.0",
              "instance_id": "%s"
            }
            """.formatted(action, instanceId);

        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:8765/hooks/mod-lifecycle"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();

        HTTP.sendAsync(request, HttpResponse.BodyHandlers.discarding());
    }
}
```
