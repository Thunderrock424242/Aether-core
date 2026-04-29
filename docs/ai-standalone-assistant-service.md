# Standalone Aether Assistant Service (Minecraft-agnostic)

Yes—Aether Core can run as a separate personal-assistant service that is **not coupled to Minecraft**.

## What already exists
The `aether_sidecar` runtime is already a standalone FastAPI service. Minecraft integration is just one client path.

## Recommended split
1. **Assistant service (new/primary runtime role)**
   - Keep the current HTTP API (`/generate`, `/teach`, `/learning/*`, `/health`, `/metrics`).
   - Add a client identity field (`client_app`) so prompts can be routed differently for Minecraft vs. personal assistant use.

2. **Minecraft adapter (thin client layer)**
   - Keep all game lifecycle/activation hooks and mod-specific context in the NeoForge/JVM client.
   - Send normalized requests to the assistant service.

3. **Optional non-Minecraft clients**
   - CLI tool
   - Desktop/electron app
   - Discord/Telegram bot

## Service-mode profile
For personal-assistant mode, run with:
- `AETHER_ACTIVATION_HOOK_ENABLED=false` (no mod lifecycle requirement)
- `AETHER_DEV_PLAYGROUND_ENABLED=true` (local testing UI)
- `AETHER_LEARNING_LOG_PATH` pointing to persistent storage

## Minimal implementation plan
1. Add `client_app` to request model and telemetry labels.
2. Add prompt templates per client (`minecraft`, `assistant`).
3. Add auth for non-local use (token/JWT).
4. Add per-client rate limits.
5. Add optional calendar/tasks connector layer for assistant workflows.

## Why this works
This preserves one inference + memory backend while letting Minecraft become only one consumer. You avoid duplicating model hosting and can evolve assistant features independently.
