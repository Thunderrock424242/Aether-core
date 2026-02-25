# A.E.T.H.E.R Implemented Local Sidecar

This repository now includes a runnable, non-Java AI runtime in `aether_sidecar/`.

## What is implemented
- FastAPI sidecar endpoints: `POST /generate`, `GET /health`, `GET /version`
- Subsystem auto-routing (Aegis/Eclipse/Terra/Helios/Enforcer/Requiem)
- Bounded session memory
- Safety pre-check + refusal behavior
- Pluggable backend (`template` and `ollama`)
- Unit tests for routing/safety

## Quick start
```bash
./scripts/run_sidecar_dev.sh
```

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
