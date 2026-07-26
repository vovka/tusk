# Architecture Analysis — Issue #47: TTS Playback Speed

## Issue Summary
Add a configurable spoken-reply playback speed (`1.0` default, `1.5`, `2.0`, ...),
set once for the whole session via TUSK's normal env-var configuration, applied through
the existing `GroqTTS` provider. No voice/model changes, no per-utterance override, no
STT/microphone impact.

## Components Affected And How They Fit Together Today

```
ConfigFactory (env vars) --> Config (frozen dataclass)
                                   |
ShellLoader._build_worker() -------+--> GroqTTS(api_key)              [tusk/providers/tts/groq_tts.py]
                                   |         implements
                                   |    TTSEngine.synthesize_chunks(text) -> Iterator[bytes]
                                   |         [tusk/shared/tts/interfaces/tts_engine.py]
                                   |
                                   +--> ChunkedSpeaker(tts_engine, playback, log, token)
                                              [shells/voice/stages/chunked_speaker.py]
                                              calls tts.synthesize_chunks(text), prefetches
                                              clips on a worker thread, feeds each WAV clip to:
                                              |
                                              +--> SpeechPlayback.play(wav_bytes)
                                                     [shells/voice/stages/speech_playback.py]
                                                     pipes raw WAV bytes to `paplay` via subprocess
```

- **`Config` / `ConfigFactory`** (`tusk/shared/config/config.py`,
  `tusk/shared/config/config_factory.py`): the single source of runtime settings. A frozen
  dataclass built once at startup from environment variables (`os.environ`), with typed
  helpers (`_int`, `_float`, `_bool`, `_slot`) for parsing. `tts_enabled` already follows
  this pattern (`TUSK_TTS` env var, boolean).
- **`TTSEngine`** (ABC, `tusk/shared/tts/interfaces/tts_engine.py`): one abstract method,
  `synthesize_chunks(text: str) -> Iterator[bytes]`. `GroqTTS` is the only implementor.
- **`GroqTTS`** (`tusk/providers/tts/groq_tts.py`): wraps the Groq SDK
  (`Groq().audio.speech.create(model=..., voice=..., input=..., response_format="wav")`),
  splitting long text into ≤200-char chunks (`TextChunker`, Orpheus's input cap) and
  yielding one WAV clip per chunk lazily.
- **`ChunkedSpeaker`** (`shells/voice/stages/chunked_speaker.py`): orchestrates synthesis
  and playback — prefetches the next clip on a background thread while the current one
  plays, tracks "recently spoken" text for the echo filter, and handles interruption. It
  is TTS-engine-agnostic; it only calls `synthesize_chunks(text)`.
- **`SpeechPlayback`** (`shells/voice/stages/speech_playback.py`): plays a single WAV clip
  by piping its raw bytes to the `paplay` CLI via `subprocess.Popen`. No decoding, no
  resampling, no rate control — it is a dumb byte pipe with an interrupt/timeout guard.
- **`ShellLoader._build_worker`** (`shell_loader.py:72-76`): the sole construction site —
  `GroqTTS(self._config.groq_api_key) if self._config.tts_enabled else None`, wired into a
  `ChunkedSpeaker`. This is where any new session-wide setting must be threaded through.

## Integration Points And Contracts Crossed

1. **Env var → `ConfigFactory` → `Config`.** Adding a setting means: a new env var read in
   `ConfigFactory._audio_values()` (next to `TUSK_TTS`), a new field on the `Config`
   dataclass, and a default that reproduces today's behavior exactly.
2. **`Config` → `ShellLoader`.** `ShellLoader._build_worker` reads config fields and passes
   them into provider constructors. Currently `GroqTTS` only receives `groq_api_key`; a
   speed setting must be passed in alongside it.
3. **`ShellLoader` → `GroqTTS.__init__`.** `GroqTTS`'s constructor already takes optional
   `model` and `voice` with defaults — the established pattern for "configured once at
   construction, applies to every call" settings on this provider.
4. **`GroqTTS` → Groq SDK `audio.speech.create(...)`.** This is the contract with the
   external API. `synthesize_chunks(text)` builds the `create()` kwargs per chunk today
   (`model`, `voice`, `input`, `response_format`). A speed setting would add one more kwarg
   here, applied identically to every chunk of every reply in the session.
5. **`TTSEngine` ABC contract.** `synthesize_chunks(text: str) -> Iterator[bytes]` takes no
   speed argument today. The issue's "one setting for the whole session, no per-utterance
   override" requirement maps naturally onto *construction-time* configuration (like
   `model`/`voice` already are) rather than changing this method's signature — the ABC
   would not need to change at all.
6. **Test contracts.** `tests/providers/test_groq_tts.py` asserts the exact `kwargs` dict
   captured from `audio.speech.create` (`model`, `response_format`, `voice`). Any new kwarg
   sent unconditionally would need this test updated; at default speed it must be provable
   that today's captured request is unaffected (either the kwarg is omitted at `1.0`, or the
   API treats `1.0` as a true no-op).

## Risks, Unknowns, Things That Could Break

- **Unverified: does Groq's `audio.speech.create` accept a `speed` parameter for the
  `canopylabs/orpheus-v1-english` model used here?** This repo has no vendored copy of the
  `groq` SDK or its API docs available for inspection in this environment, and OpenAI-style
  TTS speed parameters are not universally supported by every provider/model combination.
  This is the central technical unknown: if the API/model doesn't support a `speed` kwarg,
  "speed" must instead be achieved by resampling/time-stretching the returned WAV audio
  client-side, which is a materially different (and larger) change.
- **No audio post-processing in the stack today.** `requirements.txt` has no `ffmpeg`,
  `sox`, or `pydub`, and `SpeechPlayback` pipes raw bytes straight to `paplay`. If
  server-side speed control turns out to be unsupported, client-side speed changes would
  require either a new dependency (e.g., shelling out to `ffmpeg`/`sox` with an `atempo`-style
  filter) or a pure-Python resampler — both are new integration points and new failure modes
  (missing binary, format edge cases) that the issue's "works with the existing Groq TTS
  provider" framing doesn't obviously anticipate.
- **Valid speed range is unknown.** If the Groq API does support a `speed` kwarg, its
  accepted range/granularity (e.g. clamped to 0.5–2.0 vs free-form) is unconfirmed. An
  out-of-range value could be silently clamped by the API, rejected with an error, or
  produce degraded audio — behavior to confirm empirically before locking down validation
  in config parsing.
- **`Config` already carries 30+ flat fields** with no grouping; adding one more scalar
  (e.g. `tts_speed: float`) is consistent with the existing style (`tts_enabled: bool` is a
  direct sibling) and keeps the dataclass a simple, flat, positional-argument-free contract.
  No new nested schema is warranted for a single float.
- **Chunk-level consistency.** `GroqTTS.synthesize_chunks` issues one `create()` call per
  ≤200-char chunk; a speed setting captured once at construction and applied uniformly to
  every chunk call keeps pacing consistent across a multi-chunk reply — a setting that could
  vary per chunk would risk audible speed jumps mid-reply, but nothing in the current design
  invites that failure since chunking is purely a length-limit mechanism, not a per-chunk
  configuration boundary.
- **Blast radius is otherwise small.** `ChunkedSpeaker`, `SpeechPlayback`, `TTSEngine`, the
  echo filter, and the voice shell's pipeline never need to know about speed if it is
  resolved entirely inside `GroqTTS` construction — they only ever see WAV bytes in, bytes
  played out.

## Approach Chosen

Treat speed as a **session-wide, construction-time setting on the Groq provider**, sourced
through the existing `Config`/`ConfigFactory` pipeline, exactly mirroring how `model` and
`voice` are already handled on `GroqTTS`:

1. `ConfigFactory` reads a new env var (e.g. `TTS_SPEED`, default `"1.0"`) via the existing
   `_float` helper, next to `TUSK_TTS` in `_audio_values()`.
2. `Config` gains one new field, e.g. `tts_speed: float`.
3. `ShellLoader._build_worker` passes `self._config.tts_speed` into `GroqTTS(...)`.
4. `GroqTTS.__init__` accepts a `speed` parameter (default `1.0`) alongside `model`/`voice`,
   and `_synthesize_chunk` forwards it to `audio.speech.create(...)`, contingent on
   confirming the Groq API/model actually accepts this kwarg (see Risks above) — if it
   doesn't accept the parameter at all, that same construction-time value would instead need
   to drive a client-side post-processing step inserted between synthesis and playback.

This keeps the change local to `ConfigFactory`, `Config`, `ShellLoader`, and `GroqTTS`,
touches no interfaces (`TTSEngine` is unchanged), and guarantees default behavior is
unchanged when `speed == 1.0`, satisfying the issue's explicit requirement.

## Alternatives Considered And Rejected

- **Per-call speed parameter — `synthesize_chunks(text, speed)`.** Rejected: the issue
  explicitly scopes this to one setting for the whole session, not per-utterance overrides.
  Threading a parameter through the `TTSEngine` ABC and every call site (`ChunkedSpeaker`,
  tests) is unnecessary churn for a value that never changes within a session, and it would
  be the only method parameter on an otherwise single-purpose interface.
- **Client-side time-stretching in `SpeechPlayback` (e.g. via `ffmpeg`/`sox` `atempo`).**
  Rejected as the default approach because it introduces a new external dependency and a new
  post-synthesis processing stage for a stack that currently has none, when the issue frames
  this as working "with the existing Groq TTS provider" — i.e. as a synthesis-time setting.
  It remains the fallback if the Groq API turns out not to support a native speed parameter,
  but shouldn't be built speculatively before that unknown is resolved.
- **A dedicated `SpeedAdjustingTTS` decorator wrapping any `TTSEngine`.** Rejected as
  overengineering for the current scope: there is exactly one `TTSEngine` implementation, no
  indication a second is imminent, and the plain constructor-parameter approach on `GroqTTS`
  already matches how `model`/`voice` are configured on the same class. A decorator would add
  an abstraction with no second caller to justify it.
- **Nested `TTSConfig` value object instead of a flat `Config` field.** Rejected: `Config` is
  a flat dataclass of scalars throughout (`tts_enabled`, `ack_enabled`, `audio_sample_rate`,
  ...); a single new float field (`tts_speed`) fits that existing convention, and introducing
  a nested schema for one value would be inconsistent with the rest of the file for no
  benefit.
