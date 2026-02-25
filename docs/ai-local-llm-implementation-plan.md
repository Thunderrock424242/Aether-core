# A.E.T.H.E.R Local LLM Implementation Plan (Non-Java Model Stack)

This document explains **how to build A.E.T.H.E.R as local, user-hosted AI** for a NeoForge Minecraft mod while keeping the model/AI stack outside Java.

## 1) Recommended architecture

Use a **split architecture**:

1. **Minecraft mod (NeoForge / Java)**
   - Captures player input (chat item + dev command toggles).
   - Sends requests to local AI backend over HTTP.
   - Displays responses in chat/UI.
   - Handles fallback when backend is offline.

2. **Local AI sidecar (Python or Rust, not Java)**
   - Runs on the player machine when enabled.
   - Hosts or proxies a local LLM.
   - Owns routing to Aegis/Eclipse/Terra/Helios/Enforcer/Requiem personalities.
   - Enforces safety rules and token/context limits.

3. **Model/runtime layer (non-Java)**
   - For inference: `llama.cpp`, `vLLM`, `Ollama`, or `Text Generation Inference`.
   - For training/fine-tuning: Python stack (`PyTorch`, `Transformers`, `PEFT/LoRA`, `TRL`, `bitsandbytes`).

Why this works: your mod stays lightweight and stable, while the AI stack can evolve rapidly without touching game code.

## 2) Player interaction design

### A) Talk via item
- Add an item (ex: `aether_comm_link`) that opens a lightweight input flow.
- On submit:
  - mod packages `player message + world summary + selected subsystem`
  - sends to `POST /generate` on localhost
  - renders answer in chat with subsystem label (e.g., `[Aegis]`).

### B) Dev environment toggle via command
- Add a command such as:
  - `/aether ai online` -> start using local sidecar endpoint
  - `/aether ai offline` -> force fallback mode
  - `/aether ai status` -> call `GET /health`
- In dev, you can also support `/aether ai endpoint <url>` to test remote/staging backends.

## 3) Local sidecar API (minimum)

Match the scope doc and keep it minimal:

- `POST /generate`
  - input: `message`, `subsystem`, `player_context`, `world_context`, `session_id`
  - output: `text`, `subsystem_used`, `safety_flags`, `latency_ms`
- `GET /health`
  - liveness/readiness
- `GET /version`
  - model name/build hash

Optional but useful:
- `POST /summarize_memory`
- `POST /classify_subsystem` (if you want backend auto-routing)

## 4) Model strategy (building your own models)

You have two realistic paths:

### Path 1: Fine-tune an open base model (recommended first)
- Start with a small/medium base model (7B-8B class).
- Create instruction data in A.E.T.H.E.R style:
  - survival guidance
  - anomaly/rift analysis
  - lore voice and archive tone
- Use LoRA/QLoRA for cost-efficient tuning.
- Export quantized artifacts for local inference (GGUF/AWQ/GPTQ depending runtime).

### Path 2: Train from scratch (long-term)
- Requires massive dataset + GPU budget + distributed infra.
- Better for a later phase once product direction is proven.

Recommendation: **fine-tune first, train-from-scratch later**.

## 5) Data pipeline for A.E.T.H.E.R behavior

1. Define a schema for training examples:
   - `subsystem`
   - `player_state`
   - `world_state`
   - `prompt`
   - `ideal_response`
   - `safety_label`
2. Generate seed data from design docs + handcrafted exemplars.
3. Add synthetic expansion with strict filtering.
4. Run evaluation suites:
   - role consistency
   - safety violations
   - hallucination checks
   - latency/throughput constraints

## 6) Runtime choices by hardware

- **Low-end PCs**: 3B-7B quantized model via `llama.cpp`/Ollama.
- **Mid/high-end GPUs**: 7B-13B with vLLM/TGI.
- **Server-hosted optional mode**: same API contract, just different endpoint.

Add automatic capability detection in sidecar:
- detect RAM/VRAM
- choose model profile
- expose chosen profile in `GET /version`

## 7) Safety + guardrails

Implement safety in the sidecar (not only prompt text):

- Prompt templates per subsystem with hard boundaries.
- Output filtering/classification step.
- Rate limiting and cooldowns to prevent spam.
- Refusal/fallback patterns for unsafe requests.
- Never expose secrets/config internals in output.

## 8) Packaging and distribution

Because model stack is non-Java, ship two artifacts:

1. NeoForge mod jar.
2. Sidecar bundle:
   - executable/service launcher (Python packaged via PyInstaller or Rust binary)
   - model files (or downloader with first-run setup)
   - config file (`host`, `port`, `model profile`, `timeouts`)

Startup flow:
- game launches -> mod checks sidecar health
- if offline: friendly fallback + instructions
- if online: enable AI item/commands

## 9) Concrete phased roadmap

### Phase 0 (1-2 weeks): Contract + stub
- Finalize API contract.
- Build mock sidecar returning deterministic responses.
- Integrate item + command toggles in mod.

### Phase 1 (2-4 weeks): Local inference MVP
- Use existing open model (no custom training yet).
- Implement subsystem routing and context templating.
- Add async queue + timeout + retry behavior.

### Phase 2 (3-6 weeks): First custom model pass
- Build A.E.T.H.E.R instruction dataset.
- Fine-tune with LoRA/QLoRA.
- Evaluate and ship quantized model profile.

### Phase 3 (ongoing): Quality and tooling
- Memory summarization.
- Better retrieval for lore packets.
- Hardware-aware model selection.
- Optional voice support.

## 10) Suggested tech stack (non-Java AI)

- **Training**: Python + PyTorch + Hugging Face + PEFT/TRL.
- **Inference service**: Python FastAPI (or Rust Axum) + llama.cpp/vLLM/Ollama backend.
- **Model format**: GGUF for widest local support.
- **Observability**: Prometheus-style metrics + structured logs.

## 11) Key risks and mitigations

- **Risk**: low-end hardware cannot run selected model.
  - Mitigation: multi-profile model packs and auto-fallback.
- **Risk**: response latency harms gameplay feel.
  - Mitigation: async requests, token limits, short style defaults.
- **Risk**: hallucinations/lore drift.
  - Mitigation: subsystem prompts + evaluation harness + memory summaries.

---

## Direct answer to your constraint

Yes, you can absolutely do this while avoiding Java for AI/model work:
- keep Java only for NeoForge integration,
- run all LLM logic in a local sidecar process,
- build your custom model with Python tooling,
- expose a stable localhost API the mod talks to.
