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

## Teaching playground shortcut
Use the helper scripts to avoid crafting raw `curl`/JSON each time you want to teach a lesson.

```bash
./scripts/teach_lesson.sh -s player-uuid -l "I am building Minecraft NeoForge mods with Gradle."
```

```powershell
.\scripts\teach_lesson.ps1 -SessionId player-uuid -Lesson "I am building Minecraft NeoForge mods with Gradle."
```
