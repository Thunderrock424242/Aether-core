# A.E.T.H.E.R Implemented Local Sidecar

This repository now includes a runnable, non-Java AI runtime in `aether_sidecar/`.

## What is implemented
- FastAPI sidecar endpoints: `POST /generate`, `GET /health`, `GET /version`, `GET /metrics`
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

## Generate response payload (now includes keyword alerts)
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
