# Plan: Fully-Local Privacy Profile

**Branch:** `feature/local-llm`, `feature/local-tts` (parallel) · **Depends on:** nothing ·
**Unblocks:** `local-private` preset in [vertical-packaging](../vertical-packaging/README.md).

Two small provider PRs, a compose PR, then a validation campaign. The plumbing is
deliberately boring — the deciding work is Milestone D's measurements, which produce the
shippable "known-good local config". Intermediate deliverable after A alone: *local speech*
profile (local STT + local gatekeeper, cloud agents) — private audio without waiting for
local agent quality.

## Milestone A — Local LLM provider

### A1. `LocalOpenAILLM`
- **Tests:** `tests/providers/llm/` with a faked OpenAI client — `complete`,
  `complete_structured` (try `json_schema` → fall back to `json_object` → plain, reusing
  the `OpenRouterLLM` approach), `complete_tool_call`; label `local/<model>`; base URL from
  config; no API key required (dummy accepted).
- **Change:** `tusk/providers/llm/local_openai_llm.py` (~60 lines, one class);
  factory case in `configurable_llm_factory.py` for the `local/` prefix;
  `LOCAL_LLM_BASE_URL` in `ConfigFactory` (default `http://localhost:11434/v1`).
- **Verify:** `switch_model` by voice to `local/<model>` against a running Ollama and back.

## Milestone B — Local TTS

### B1. `TTSEngineFactory`
- **Tests:** selects `groq` (default) / `piper` by `TTS_ENGINE`; `ShellLoader` consumes the
  factory (today it constructs `GroqTTS` directly — this is the only wiring change).
- **Change:** `tusk/providers/tts/tts_engine_factory.py`, mirroring `STTEngineFactory`.

### B2. `PiperTTS`
- **Tests:** fake synthesizer → WAV bytes flow into the existing `SpeechPlayback` path;
  long text synthesizes in one pass (no Orpheus 200-char chunking — `TextChunker` stays
  Groq-specific).
- **Change:** `tusk/providers/tts/piper_tts.py` (`piper-tts` dependency, CPU-friendly);
  voice/model path via `PIPER_VOICE` config; model fetched at build or first start.

## Milestone C — Runtime packaging

### C1. Compose + image
- **Change:** `docker-compose.local.yml` override — `ollama` service with a model volume
  (+ optional GPU reservation block, commented); piper + local-whisper deps in the image
  (build stays lean: piper is small; whisper weights land in a mounted cache volume, not
  image layers).
- **Verify:** `docker compose -f docker-compose.yml -f docker-compose.local.yml up` on a
  clean checkout → fully local turn works end-to-end (emulator shell).

### C2. Example config
- **Change:** `.env.local.example` — complete slot set for full-local and for the
  intermediate local-speech profile, with comments. (Graduates into
  `profiles/local-private.env` once vertical-packaging lands — don't build the profile
  mechanism here.)

## Milestone D — Validation campaign (the real work)

### D1. Latency measurement
- **Method:** Phoenix tracing is already wired (`TRACING_OTLP_ENDPOINT`); run the e2e
  harness per candidate model and read per-slot spans. Compare scenario-for-scenario
  against the cloud baseline (the harness has known Groq flakiness — never compare raw
  pass rates).
- **Candidates:** small instruct models for `gatekeeper`/`stop_gate` (the hot path);
  mid-size for `planner`/`executor`; document CPU-only vs GPU numbers separately.

### D2. Structured-output reliability
- **Method:** scripted run of N=50 gatekeeper classifications + 20 planner plans per model
  via the emulator; count schema-parse failures surviving the existing fallback chain.
  Acceptance: gatekeeper ≥ 99% parse success, planner ≥ 95% valid-plan rate.

### D3. Publish results
- **Change:** results table in this directory (`validated-models.md`): model → slot →
  latency p50/p95 → parse rate → verdict. The known-good set becomes the preset default;
  models that fail stay listed as failed (saves the next person the experiment).
  The gpt-oss-empty-completion incident is the cautionary precedent: model choice is
  config, but only *validated* config ships.

## Acceptance criteria
- One documented full-local configuration completes the standard e2e scenarios with
  gatekeeper p95 within 2× the cloud baseline, on stated hardware.
- Local-speech intermediate profile documented and validated on CPU-only hardware.
- No provider class exceeds 100 lines; no kernel/shell file changed except `ShellLoader`
  (TTS factory) and `ConfigFactory` (new keys).

## Out of scope
- Model quantization/serving tuning (users bring their Ollama setup); GPU driver docs
  beyond a pointer; local *conversation quality* tuning (prompt work is per-slot config,
  not this plan); TTS voice cloning.

## Risks
- CPU-only agent slots may be unusably slow → the intermediate local-speech profile is the
  honest fallback deliverable; say so in docs rather than shipping a bad full-local default.
- Ollama structured-output support varies by model — the fallback chain absorbs it, but
  planner quality gates on D2, not hope.
