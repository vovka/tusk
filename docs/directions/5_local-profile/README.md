# Direction: Fully-Local Privacy Profile

**Research basis:** "local privacy" is one of the three adoption factors; users explicitly
fear data harvesting (r/accessibility) and ask for on-device execution
([market research](../../market-research-reddit-2026-07.md)).
**Verdict:** zero architectural change required — every engine already sits behind an ABC
with a factory, and one local engine (`WhisperSTT`) already exists. The work is two new
provider classes, config plumbing, and — the actual hard part — empirical validation of
latency and structured-output quality on local models.

**Diagram:** [engine seams — cloud vs local](engine-seams.md) · **Plan:** [PLAN.md](PLAN.md)

## What the architecture already provides

- **LLM seam.** `LLMProvider` ABC + `ConfigurableLLMFactory` parsing `"provider/model"`
  strings per slot; `OpenRouterLLM` is already an `openai.OpenAI` client against a custom
  `base_url` — an OpenAI-compatible local server (Ollama, llama.cpp, vLLM) is the same class
  shape with a different URL.
- **Per-role slots.** Six independent LLM slot env vars mean mixed profiles are already
  expressible: e.g. local gatekeeper (latency-critical, simple task) + cloud agents, or
  fully local. `switch_model` swaps slots at runtime by voice.
- **STT seam.** `STTEngineFactory` selects `groq` or `whisper`; `WhisperSTT` runs fully
  local today (`WHISPER_MODEL_SIZE`).
- **TTS seam.** `TTSEngine` ABC exists; playback (`paplay`) is already local.
- **Weak-model tolerance.** The gatekeeper/mode-gate fallback chain
  (`complete_structured` → plain `complete` → literal forward) and `GroqLLM`'s
  `json_schema`/`json_object` split already handle models with shaky structured output.

## Gaps

- No local LLM provider class — the factory knows only `groq` and `openrouter`.
- No local TTS — `GroqTTS` is the only implementation, and there is no TTS factory
  (`ShellLoader` constructs `GroqTTS` directly; STT has a factory, TTS does not).
- Docker: no local-model runtime in the image, no GPU passthrough in compose, whisper
  model weights downloaded at first start.
- **Latency risk is the real blocker.** The gatekeeper sits on the documented hot path and
  runs on every utterance; a slow local model there degrades the whole experience. Latency
  is a first-class concern per the architecture rules — this needs measurement, not hope.

## Required changes

1. **[providers/llm]** `LocalOpenAILLM` (slot syntax `local/<model>`, base URL from
   `LOCAL_LLM_BASE_URL`, default `http://localhost:11434/v1` for Ollama) + a factory case.
   Reuse `OpenRouterLLM`'s structured-output fallback approach.
2. **[providers/tts]** `PiperTTS` implementing `TTSEngine` (WAV output drops into the
   existing `SpeechPlayback`/`TextChunker` pipeline) + a `TTSEngineFactory` mirroring the
   STT one, selected by `TTS_ENGINE`.
3. **[config]** `TTS_ENGINE`, `LOCAL_LLM_BASE_URL`; document a complete local slot set.
4. **[docker]** Optional compose service for Ollama with a model volume; document RAM/VRAM
   requirements per model tier; pre-fetch whisper/piper models at build or first start.
5. **Validation pass (the real work).** Run the e2e harness against candidate local models
   per slot; record latency and structured-output failure rates; publish a "known-good local
   config" in the profile preset (ties into the vertical-packaging direction). The
   gpt-oss-empty-completion incident showed model swaps are config-level and must be
   validated empirically — same discipline here.

## Risks & notes

- A fully-local profile on CPU-only hardware may be unusable for the agent slots; the honest
  intermediate offering is "local audio + local gatekeeper, cloud agents" — private *speech*,
  cloud *actions* — which the slot system supports today.
- Local structured output varies wildly by model; the planner's JSON contract is the most
  demanding consumer — prefer larger local models for `planner_agent` or keep it cloud.
- Piper voices are lower quality than Orpheus — acceptable for a privacy profile, worth
  stating in docs rather than hiding.
