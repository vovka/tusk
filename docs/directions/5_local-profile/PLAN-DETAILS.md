# Local Profile — Fine-Grained Execution Plan

Commit-by-commit detail for [PLAN.md](PLAN.md), grounded against `main` @ `3fb169d`.
Tests: `docker compose exec tusk pytest tests/providers/`.

## Grounding notes

- `ConfigurableLLMFactory` keys dict is `{groq, openrouter}` and `create()` raises on a
  missing key (`configurable_llm_factory.py:13-23`) — the local provider needs a
  key-optional branch.
- `OpenRouterLLM` is the template class: `openai.OpenAI(base_url=...)`, tool-call with
  `required`→`auto` fallback, `complete_structured` delegating to plain `complete`
  (`open_router_llm.py:17-56`). `LocalOpenAILLM` is this shape minus the OpenRouter
  headers.
- The factory has a third call site besides `startup.py`: the coding adapter builds its
  own (`adapters/coding/server.py:57-61`, positional args) — a constructor change must
  update it.
- TTS has no factory: `ShellLoader._build_worker` constructs `GroqTTS` inline
  (`shell_loader.py:70`). `TTSEngine`'s contract is `synthesize_chunks(text) ->
  Iterator[bytes]` of WAV clips (`groq_tts.py`); chunking is Orpheus-specific and lives
  inside `GroqTTS` — Piper needs none.

## Milestone A — Local LLM provider

### Commit A1 — `LocalOpenAILLM`
- **Tests** (`tests/providers/llm/`, faked OpenAI client):
  - `label == "local/<model>"`; requests go to the configured base URL;
  - `complete_tool_call`: `tool_choice="required"` first, `"auto"` retry on
    tool-fallback errors (mirror the `OpenRouterLLM` tests);
  - `complete_structured`: sends `response_format={"type": "json_object"}` and appends
    the schema to the system prompt (Ollama's OpenAI compat honors `json_object`;
    `json_schema` support is inconsistent across local servers — the gates' existing
    parse-fallback chain absorbs imperfect output);
  - no API key required (client constructed with a dummy key).
- **Change:** `tusk/providers/llm/local_openai_llm.py` (~65 lines, one class; shares
  `_chat_payload`-style helpers by keeping its own — no cross-provider utils module).

### Commit A2 — factory + config
- **Tests:**
  - `create("local", model)` works with no key; unknown provider still raises
    (`configurable_llm_factory.py:19-23` behavior preserved);
  - base URL flows from config; default `http://localhost:11434/v1`.
- **Change:** `configurable_llm_factory.py` — `_LOCAL = "local"` branch (key check
  skipped for it); constructor gains `local_base_url: str = "http://localhost:11434/v1"`.
  Update both call sites: `startup.py` (passes `config.local_llm_base_url`) and
  `adapters/coding/server.py:60` (env read
  `LOCAL_LLM_BASE_URL`, keeping the adapter standalone). `ConfigFactory`:
  `local_llm_base_url` in `_llm_values` (`config_factory.py:37-38`); `Config` frozen
  field.
- **Verify live:** with Ollama running: `.env` slot `GATEKEEPER_LLM=local/<model>` →
  utterances classify; `switch_model` by voice to `local/...` and back (the
  `SwitchModelTool` path goes through `LLMRegistry.swap` → factory — no further change).

## Milestone B — Local TTS

### Commit B1 — `TTSEngineFactory`
- **Tests:** `create("groq")` → `GroqTTS` (default); `create("piper")` → `PiperTTS`;
  unknown → `ValueError` (mirror `stt_engine_factory.py:13-18` exactly);
  `ShellLoader._build_worker` uses the factory (`shell_loader.py:70` is the only line
  that changes there — still `None` when `tts_enabled` is off).
- **Change:** `tusk/providers/tts/tts_engine_factory.py`; `ConfigFactory` key
  `tts_engine` (`TUSK_TTS_ENGINE`, default `groq` — namespaced to avoid colliding with
  the existing `TUSK_TTS` on/off switch).

### Commit B2 — `PiperTTS`
- **Tests** (fake synthesizer object):
  - `synthesize_chunks(text)` yields exactly one WAV clip (no 200-char chunking — that
    cap is Orpheus's, `groq_tts.py:_MAX_INPUT_CHARS`);
  - empty text → yields nothing;
  - WAV bytes carry a RIFF header (SpeechPlayback/`paplay` compatibility is a
    byte-format contract, cheap to assert).
- **Change:** `tusk/providers/tts/piper_tts.py` (~50 lines) — `piper-tts` package,
  voice model path from `PIPER_VOICE` (default `en_US-lessac-medium`), model auto-download
  on first use into `.tusk_runtime/piper/` (mounted volume — not image layers).
- **Latency note (hot-path rule):** TTS runs on the `CommandWorker` thread, off the
  STT→gatekeeper hot path; Piper on CPU is ~0.5–1× realtime — document measured numbers
  in the PR.

## Milestone C — Runtime packaging

### Commit C1 — compose override
- **Change:** `docker-compose.local.yml` — `ollama` service (official image, model
  volume, `OLLAMA_KEEP_ALIVE=-1` so slot models stay resident; commented GPU
  `deploy.resources.reservations` block); tusk service env override
  `LOCAL_LLM_BASE_URL=http://ollama:11434/v1`. README section: model pull one-liners for
  the validated set (D3).
- **Verify:** clean checkout, `docker compose -f docker-compose.yml -f
  docker-compose.local.yml up`, `TUSK_SHELLS=emulator` transcript completes with all
  slots `local/*`.

### Commit C2 — example env
- **Change:** `.env.local.example` — two documented blocks using the real slot names
  (`config_factory.py:46-60`): **local-speech** (`STT_ENGINE=whisper`,
  `GATEKEEPER_LLM=local/...`, `STOP_GATE_LLM=local/...`, `TUSK_TTS_ENGINE=piper`, agent
  slots stay cloud) and **full-local** (all of `CONVERSATION_AGENT_LLM`,
  `COMMAND_AGENT_LLM`, `PLANNER_AGENT_LLM`, `EXECUTOR_AGENT_LLM`, `DEFAULT_AGENT_LLM`,
  `UTILITY_LLM` → `local/...`). Graduates to `profiles/local-private.env` when direction
  6's mechanism lands.

## Milestone D — Validation campaign

### D1 — latency
- **Method:** Phoenix tracing is already wired (`TRACING_OTLP_ENDPOINT` in compose);
  per-slot spans hang under the `kernel.request` span (`kernel_api.py:55`). Per candidate
  model: run the standard e2e scenarios 5×, read p50/p95 per slot from Phoenix, compare
  scenario-for-scenario against a same-day cloud-baseline run (the harness's Groq
  flakiness makes absolute pass rates meaningless — compare latency of *successful*
  steps).
- **Hot-path gate:** gatekeeper fires on every utterance — a candidate gatekeeper model
  must hold p95 ≤ 2× the cloud baseline on the stated hardware, else it's recorded as
  failed for that slot (it may still pass for planner/executor where turns are rarer).

### D2 — structured-output reliability
- **Method:** scripted probe `tools/local_model_probe.py` (dev tooling): N=50 gatekeeper
  classifications from a fixture utterance set + 20 planner runs against the live local
  server; counts schema-parse failures *after* the existing fallback chain
  (`complete_structured` → plain → literal). Gates: gatekeeper ≥ 99% parse success,
  planner ≥ 95% valid-plan rate (validated by `planner.ResultValidator`, not by eye).
- **Note:** the probe reuses `LocalOpenAILLM` + real prompts from the profiles — probing
  the production path, not a synthetic one.

### D3 — publish
- **Change:** `validated-models.md` in this directory: table
  `model → slot → hardware → p50/p95 → parse rate → verdict`, failed candidates included
  (negative results save the next experiment). The best full-local and local-speech sets
  become the documented defaults in C1/C2. Precedent for the discipline: the
  gpt-oss-empty-completion incident — model choice is config, but only *validated*
  config ships.

## Edge cases

| Case | Behavior |
|---|---|
| Ollama down mid-session | `LLMProxy` retry (3×) then failed turn — same UX as a Groq outage; `switch_model` back to cloud by voice works because gatekeeper/utility slots keep their own provider |
| Model not pulled | first request errors with the server's message → surfaced in the failed reply; README pull commands |
| Slow cold model load | first-turn latency spike; `OLLAMA_KEEP_ALIVE=-1` prevents repeats; note in docs |
| Mixed profile confusion | `.env.local.example` blocks are copy-paste-whole; the guardrail test from direction 6 later pins key validity |

## Explicitly not building (v1)
GPU tuning/quantization guidance beyond a pointer; llama.cpp/vLLM-specific docs (any
OpenAI-compatible URL works by construction); local TTS voice cloning; offline model
bundling into the image; per-slot automatic model selection.

## Open items to confirm during implementation
1. Ollama's current `response_format` behavior for the chosen models (A1 assumes
   `json_object` + schema-in-prompt; adjust the test fixtures to reality).
2. `piper-tts` wheel availability for the image's Python/arch — else subprocess the
   `piper` binary behind the same class (contract unchanged, decide in B2).
3. Whether `WhisperSTT` model download at first start needs pre-fetch in the compose
   override (C1) to keep first-run UX sane.
