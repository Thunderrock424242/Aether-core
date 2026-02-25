# A.E.T.H.E.R Implemented Local Sidecar

This repository now includes a runnable, non-Java AI runtime in `aether_sidecar/`.

## What is implemented
- FastAPI sidecar endpoints: `POST /generate`, `GET /health`, `GET /version`, `GET /metrics`
- Mod lifecycle hook endpoints: `POST /hooks/mod-lifecycle`, `GET /hooks/status`
- Keyword-driven subsystem alert detection for Aegis/Eclipse/Terra/Helios/Enforcer/Requiem
- Subsystem auto-routing based on detected keyword matches
- Bounded session memory
- Safety pre-check + refusal behavior
- Pluggable backend (`template` and `ollama`)
- Optional per-subsystem model routing (`AETHER_SUBSYSTEM_MODELS`) for specialist sub-models
- Unit tests for routing/safety/app endpoints

## Quick start
```bash
./scripts/run_sidecar_dev.sh
```

The dev script now bootstraps/reuses `.venv`, installs dependencies, and runs Uvicorn with hot reload by default.

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
  "latency_ms": 42
}
```

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
