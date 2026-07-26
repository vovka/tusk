# Architecture Analysis — Issue #47: TTS Playback Speed

## Issue Summary
Add a configurable spoken-reply playback speed (`1.0` default, `1.5`, `2.0`, ...),
set once for the whole session via TUSK's normal env-var configuration, applied through
the existing `GroqTTS` provider. No voice/model changes, no per-utterance override, no
STT/microphone impact.

## Revision Note

A prior version of this document proposed sending a `speed` kwarg to Groq's
`audio.speech.create(...)` as the primary approach, with client-side time-stretching held
in reserve as a fallback. Review against the live API showed that ordering was backwards
(see "Confirmed: Groq's `speed` parameter is accepted but has no effect" under Risks). This
revision makes client-side time-stretching in `SpeechPlayback` the primary — and only —
design; the API-side approach is now rejected outright rather than deferred. The call-path
trace, integration points, and the per-call/decorator alternatives from the original
analysis are otherwise unchanged and retained below.

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
                                   |          [shells/voice/stages/chunked_speaker.py]
                                   |          calls tts.synthesize_chunks(text), prefetches
                                   |          clips on a worker thread, feeds each WAV clip to:
                                   |
                                   +--> SpeechPlayback(speed)
                                              [shells/voice/stages/speech_playback.py]
                                              if speed == 1.0: pipes raw WAV bytes to `paplay`
                                                unchanged (today's behavior, untouched)
                                              else: pipes WAV bytes through `ffmpeg -af atempo=speed`
                                                first, then pipes the stretched output to `paplay`
```

- **`Config` / `ConfigFactory`** (`tusk/shared/config/config.py`,
  `tusk/shared/config/config_factory.py`): the single source of runtime settings. A frozen
  dataclass built once at startup from environment variables (`os.environ`), with typed
  helpers (`_int`, `_float`, `_bool`, `_slot`) for parsing. `tts_enabled` already follows
  this pattern (`TUSK_TTS` env var, boolean).
- **`TTSEngine`** (ABC, `tusk/shared/tts/interfaces/tts_engine.py`): one abstract method,
  `synthesize_chunks(text: str) -> Iterator[bytes]`. `GroqTTS` is the only implementor.
  **Unaffected by this feature** — speed is a playback concern, not a synthesis concern.
- **`GroqTTS`** (`tusk/providers/tts/groq_tts.py`): wraps the Groq SDK
  (`Groq().audio.speech.create(model=..., voice=..., input=..., response_format="wav")`),
  splitting long text into ≤200-char chunks (`TextChunker`, Orpheus's input cap) and
  yielding one WAV clip per chunk lazily. **Unaffected by this feature** — no `speed` kwarg
  is sent (see Risks: it would be silently ignored by the API even if sent).
- **`ChunkedSpeaker`** (`shells/voice/stages/chunked_speaker.py`): orchestrates synthesis
  and playback — prefetches the next clip on a background thread while the current one
  plays, tracks "recently spoken" text for the echo filter, and handles interruption. It
  is TTS-engine-agnostic; it only calls `synthesize_chunks(text)` and hands the resulting
  bytes to `SpeechPlayback.play(...)`. Unaffected beyond continuing to pass bytes through —
  it does not need to know a speed setting exists.
- **`SpeechPlayback`** (`shells/voice/stages/speech_playback.py`): plays a single WAV clip
  by piping its raw bytes to the `paplay` CLI via `subprocess.Popen`. No decoding, no
  resampling, no rate control today — it is a dumb byte pipe with an interrupt/timeout
  guard. **This is where the feature lives**: it is the only component that ever touches
  raw audio bytes, so it is the natural (and now sole) home for time-stretching.
- **`ShellLoader._build_worker`** (`shell_loader.py:72-76`): the sole construction site —
  `GroqTTS(self._config.groq_api_key) if self._config.tts_enabled else None`, wired into a
  `ChunkedSpeaker`. This is also where `SpeechPlayback` is constructed, and where the new
  session-wide speed setting must be threaded through to it.

## Integration Points And Contracts Crossed

1. **Env var → `ConfigFactory` → `Config`.** Adding a setting means: a new env var read in
   `ConfigFactory._audio_values()` (next to `TUSK_TTS`), a new field on the `Config`
   dataclass, and a default that reproduces today's behavior exactly.
2. **`Config` → `ShellLoader`.** `ShellLoader._build_worker` reads config fields and passes
   them into the components it constructs. Currently `GroqTTS` only receives
   `groq_api_key`; the speed setting is passed into `SpeechPlayback` instead, alongside
   whatever it already receives today.
3. **`ShellLoader` → `SpeechPlayback.__init__`.** `SpeechPlayback` gains an optional `speed`
   constructor parameter (default `1.0`), captured once at construction — the same
   "configured once, applies to every call" pattern `GroqTTS` already uses for `model` and
   `voice`, just relocated to the component that actually acts on it.
4. **`SpeechPlayback` → `paplay` / `ffmpeg` subprocesses.** This is the contract with
   external tooling. At `speed == 1.0`, `SpeechPlayback.play(wav_bytes)` behaves exactly as
   it does today: raw bytes piped straight to `paplay`, no intermediate process. At any
   other speed, the WAV bytes are first piped through `ffmpeg -af atempo=<speed> -f wav -`
   and the stretched output is what gets piped to `paplay`. **`GroqTTS` sends no `speed`
   kwarg to Groq at all** — the API-side parameter is confirmed to have no effect (see
   Risks) and must not be used.
5. **`TTSEngine` ABC contract.** `synthesize_chunks(text: str) -> Iterator[bytes]` is
   unchanged and stays unchanged. Speed is resolved entirely downstream of synthesis, so
   the ABC needs no new method or parameter.
6. **Test contracts.** `tests/providers/test_groq_tts.py` needs no changes — `GroqTTS`'s
   `audio.speech.create` kwargs (`model`, `response_format`, `voice`) are untouched by this
   feature. The tests that matter for this feature are new ones on `SpeechPlayback`:
   asserting that at `speed == 1.0` the `ffmpeg` step is skipped entirely (byte-for-byte
   today's behavior) and that at other speeds the WAV bytes are routed through `ffmpeg`
   before `paplay`.

## Risks, Unknowns, Things That Could Break

- **Confirmed: Groq's `speed` parameter is accepted but has no effect.** Tested directly
  against the live API for `canopylabs/orpheus-v1-english`: `speed` is a *recognised*
  parameter (sending it returns HTTP 200, whereas an invented parameter like
  `totally_bogus_param` returns HTTP 400), but it changes nothing. The same input text at
  `speed=1.0` and `speed=3.0` returns byte-identical output — same MD5, same 203590 bytes,
  same 4.24s duration — and this holds across 0.5, 2.0, and 4.0 as well. Sending `speed` to
  this API would ship a setting that appears to work, changes nothing audible, and fails
  silently for every value. **`GroqTTS` must never send a `speed` kwarg.** This note exists
  so nobody re-adds it later believing it to be a live parameter.
- **Dependency choice: `ffmpeg -af atempo` vs. `sox tempo` vs. pure-Python resampling.**
  - Naive resampling (e.g. dropping/duplicating samples, or a pure-Python/`scipy`
    resampler without a dedicated time-stretch algorithm) changes pitch along with speed —
    a 2x speedup sounds like a chipmunk. The issue asks for faster speech, not pitch-shifted
    speech, so this family is **rejected outright**: it fails the requirement regardless of
    implementation quality.
  - Both `ffmpeg`'s `atempo` filter and `sox`'s `tempo` effect are phase-vocoder-style
    time-stretchers that change duration while preserving pitch — either would satisfy the
    requirement.
  - **`ffmpeg` is chosen over `sox`.** `SpeechPlayback` already shells out to an external
    CLI binary (`paplay`) via `subprocess.Popen` and pipes bytes through stdin/stdout —
    adding `ffmpeg` as a second external-binary dependency follows the same pattern already
    established in this file, rather than introducing a new integration style. `ffmpeg` is
    also more commonly preinstalled/available in typical deployment environments than
    `sox`, reducing the chance this feature silently breaks on missing-binary grounds. Note
    `atempo`'s native single-filter range is 0.5–2.0; speeds above 2.0 (not required by the
    issue's examples but plausible future asks) would need chained `atempo` filters — worth
    flagging for whoever implements this if a value above `2.0` is ever requested, but not
    a blocker for `1.0`/`1.5`/`2.0`.
- **New runtime dependency.** Neither `ffmpeg` nor `sox` is currently vendored or required
  by this repo (`requirements.txt` has no audio-processing tool). Choosing `ffmpeg` means
  the deployment environment must have the `ffmpeg` binary on `PATH`, the same way it
  already must have `paplay`. This is a new operational requirement, not just a code
  change, and should be documented wherever `paplay`'s system dependency is documented (if
  anywhere) so deployment/setup docs stay accurate.
- **`speed == 1.0` must be a true no-op.** Per the issue's explicit requirement and per
  review feedback, the `1.0` case must not round-trip audio through `ffmpeg` at all — it
  should bypass the processing step entirely and behave byte-for-byte as today's code does.
  This also sidesteps most of the failure modes below when the feature is effectively
  unused (default configuration).
- **Chunk-level consistency.** `ChunkedSpeaker` feeds `SpeechPlayback.play(wav_bytes)` once
  per ≤200-char chunk. A speed setting captured once at `SpeechPlayback` construction and
  applied uniformly to every `play()` call keeps pacing consistent across a multi-chunk
  reply, matching the issue's "one setting for the whole session" requirement exactly.
- **`Config` already carries 30+ flat fields** with no grouping; adding one more scalar
  (e.g. `tts_speed: float`) is consistent with the existing style (`tts_enabled: bool` is a
  direct sibling) and keeps the dataclass a simple, flat, positional-argument-free contract.
  No new nested schema is warranted for a single float.
- **Valid speed range and `ffmpeg` invocation failures.** Unlike the rejected API-side
  approach, there is no server to silently clamp or reject an out-of-range value — an
  invalid or extreme `speed` is entirely this process's problem. `ffmpeg` exiting
  non-zero, producing malformed output, or hanging on a bad `atempo` value are new failure
  modes `SpeechPlayback` doesn't have today and would need a defined behavior (e.g.
  treat as a subprocess/interrupt error the same way a `paplay` failure is already handled)
  — left to implementation, but worth flagging here since it's new blast radius introduced
  by this feature, unlike the API-side approach which had none.
- **Blast radius stays otherwise small.** `TTSEngine`, `GroqTTS`, `ChunkedSpeaker`, and the
  echo filter never need to know speed exists — they only ever see WAV bytes in, bytes
  played out, exactly as today. All new complexity is contained inside `SpeechPlayback` and
  the `Config`/`ConfigFactory`/`ShellLoader` wiring that feeds it a single float.

## Approach Chosen

Treat speed as a **session-wide, construction-time setting on `SpeechPlayback`**, sourced
through the existing `Config`/`ConfigFactory` pipeline, applied via client-side time-stretch
using `ffmpeg -af atempo` — the only component that touches raw audio bytes today:

1. `ConfigFactory` reads a new env var (e.g. `TTS_SPEED`, default `"1.0"`) via the existing
   `_float` helper, next to `TUSK_TTS` in `_audio_values()`.
2. `Config` gains one new field, e.g. `tts_speed: float`.
3. `ShellLoader._build_worker` passes `self._config.tts_speed` into `SpeechPlayback(...)`
   at construction.
4. `SpeechPlayback.__init__` accepts a `speed` parameter (default `1.0`). `play(wav_bytes)`
   checks it: at `1.0`, the method behaves exactly as today (bytes piped straight to
   `paplay`, no `ffmpeg` involved). At any other value, the WAV bytes are first piped
   through `ffmpeg -af atempo=<speed> -f wav -` via `subprocess.Popen`, and the stretched
   output is what gets piped to `paplay`.
5. `GroqTTS` and `TTSEngine` are not touched. No `speed` kwarg is ever sent to Groq's
   `audio.speech.create` — it is confirmed accepted-but-ignored by the API (see Risks) and
   using it would ship a feature that silently does nothing.

This keeps the change local to `ConfigFactory`, `Config`, `ShellLoader`, and
`SpeechPlayback`, touches no interfaces (`TTSEngine` is unchanged), and guarantees default
behavior is byte-for-byte unchanged when `speed == 1.0` by bypassing the processing step
entirely rather than round-tripping audio through `ffmpeg` at a no-op value.

## Alternatives Considered And Rejected

- **Sending `speed` to Groq's `audio.speech.create(...)` as a synthesis-time parameter.**
  Rejected, confirmed by testing against the live API: `canopylabs/orpheus-v1-english`
  accepts a `speed` kwarg (HTTP 200, unlike an invented parameter which returns HTTP 400)
  but it has zero effect on the returned audio — identical MD5/byte length/duration across
  `speed` values from 0.5 to 4.0. This is not a deferred fallback; it is confirmed
  non-functional and must not be implemented, since it would appear to work while silently
  doing nothing for every user who sets it.
- **Per-call speed parameter — `synthesize_chunks(text, speed)` or `play(wav_bytes, speed)`.**
  Rejected: the issue explicitly scopes this to one setting for the whole session, not
  per-utterance overrides. Threading a parameter through a call site that never varies
  within a session is unnecessary churn for a value fixed at startup.
- **A dedicated `SpeedAdjustingPlayback` decorator wrapping `SpeechPlayback`.** Rejected as
  overengineering for the current scope: there is exactly one playback implementation, no
  indication a second is imminent, and a plain constructor parameter on `SpeechPlayback`
  already matches how `model`/`voice` are configured on `GroqTTS`. A decorator would add an
  abstraction with no second caller to justify it.
- **Nested `TTSConfig` value object instead of a flat `Config` field.** Rejected: `Config` is
  a flat dataclass of scalars throughout (`tts_enabled`, `ack_enabled`, `audio_sample_rate`,
  ...); a single new float field (`tts_speed`) fits that existing convention, and introducing
  a nested schema for one value would be inconsistent with the rest of the file for no
  benefit.
- **Pure-Python audio resampling instead of an external time-stretch tool.** Rejected: naive
  resampling changes pitch along with speed (a 2x speedup sounds pitch-shifted, not just
  faster), which fails the issue's intent even though it would avoid a new binary
  dependency. Pitch preservation is a requirement, not a nice-to-have, so this family of
  approaches is out regardless of the dependency tradeoff.
- **`sox tempo` instead of `ffmpeg atempo`.** Considered as an equally valid pitch-preserving
  time-stretcher, but not chosen: `ffmpeg` is more likely to already be present in typical
  deployment environments than `sox`, and choosing `ffmpeg` keeps this feature to a single
  new external-binary dependency of the same kind `SpeechPlayback` already has (`paplay`)
  rather than introducing an unrelated audio toolkit.
