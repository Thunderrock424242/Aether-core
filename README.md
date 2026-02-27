# Aether-core

A.E.T.H.E.R AI planning + implementation workspace.

## Documentation
- [`docs/ai-purpose-scope.md`](docs/ai-purpose-scope.md) - product purpose, system coverage, and MVP definition.
- [`docs/ai-local-llm-implementation-plan.md`](docs/ai-local-llm-implementation-plan.md) - architecture and phased implementation roadmap.
- [`docs/ai-system-implementation.md`](docs/ai-system-implementation.md) - implemented local sidecar runtime and integration contract.
- [`docs/ai-training-pipeline.md`](docs/ai-training-pipeline.md) - training/fine-tuning pipeline starter code.
- [`docs/ai-production-orchestration.md`](docs/ai-production-orchestration.md) - production deployment + observability stack.

## Implemented runtime
- [`aether_sidecar/`](aether_sidecar/) - runnable non-Java AI sidecar service with subsystem routing, keyword alerts, safety checks, session memory, teachable per-session learning notes, pluggable model backends, and optional per-subsystem model selection.
- [`training_pipeline/`](training_pipeline/) - dataset validation + LoRA fine-tuning starter scripts.
- [`deploy/production/`](deploy/production/) - Docker Compose orchestration with Prometheus/Grafana/Loki.

## Dev quick start
```bash
./scripts/run_sidecar_dev.sh
```

Windows PowerShell quick start:
```powershell
.\scripts\run_sidecar_dev.ps1
```

Helpful environment flags for day-to-day dev:
- `AETHER_DEV_RELOAD=true` (default) to auto-reload when Python files change.
- `AETHER_HOST=0.0.0.0` to expose the sidecar for local network/device testing.
- `AETHER_PORT=8765` to change the API port.
- `AETHER_ACTIVATION_HOOK_ENABLED=true` to require mod lifecycle activation before `/generate` responds.
- `AETHER_LEARNING_LESSON_LIMIT=16` to control how many user-taught facts are retained per session.
- `AETHER_LEARNING_LOG_PATH=.aether/learning_lessons.jsonl` to persist playground teaching lessons across sidecar restarts.
- `AETHER_DEV_PLAYGROUND_ENABLED=false` keeps the dev-only browser playground disabled by default.
- `AETHER_DEV_PLAYGROUND_TOKEN=` optional bearer token required by `/generate`, `/teach`, and `/learning/*` when set.
- `AETHER_OLLAMA_URL=http://127.0.0.1:11434/api/generate` for native host runs; in containers the sidecar auto-tries `host.docker.internal`, `gateway.docker.internal`, and detected Linux bridge gateway IPs.
- `AETHER_DOCKER_HOST_GATEWAY=` optional explicit Docker host gateway (for example `172.17.0.1`) if your environment uses a custom bridge route.
- `AETHER_OLLAMA_KEEP_ALIVE=15m` keeps models warm in Ollama so first-token latency stays low during idle periods.

## Teaching playground shortcut
Use the helper scripts to avoid crafting raw `curl`/JSON each time you want to teach a lesson.

```bash
./scripts/teach_lesson.sh -s player-uuid -l "I am building Minecraft NeoForge mods with Gradle."
```

```powershell
.\scripts\teach_lesson.ps1 -SessionId player-uuid -Lesson "I am building Minecraft NeoForge mods with Gradle."
```


## Dev playground UI (dev-only)
Enable a local browser playground for teaching + chat iteration:

```bash
AETHER_DEV_PLAYGROUND_ENABLED=true ./scripts/run_sidecar_dev.sh
# then open http://127.0.0.1:8765/dev/playground
```

```powershell
$env:AETHER_DEV_PLAYGROUND_ENABLED = "true"
.\scripts\run_sidecar_dev.ps1
# then open http://127.0.0.1:8765/dev/playground
```

Optional token lock-down:

```bash
AETHER_DEV_PLAYGROUND_ENABLED=true AETHER_DEV_PLAYGROUND_TOKEN=dev-secret ./scripts/run_sidecar_dev.sh
```

```powershell
$env:AETHER_DEV_PLAYGROUND_ENABLED = "true"
$env:AETHER_DEV_PLAYGROUND_TOKEN = "dev-secret"
.\scripts\run_sidecar_dev.ps1
```


## Backend warmup endpoint
To proactively keep a subsystem model loaded (idle but ready), call:

```bash
curl -X POST "http://127.0.0.1:8765/backend/warmup?subsystem=Terra"
```

This hits Ollama with `keep_alive` so the model stays resident for the configured window (`AETHER_OLLAMA_KEEP_ALIVE`).
