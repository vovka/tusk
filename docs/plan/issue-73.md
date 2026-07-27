# Issue #73 — Implementation plan: configurable TTS playback speed

Implements `docs/architecture/issue-73.md` (approved). Approach: **seam 1** — `GroqTTS`
sends `speed` to the Groq speech API, sourced from a new `tts_speed` config field, and
omits the parameter entirely at `1.0`.

All commands run inside Docker: `docker compose exec tusk pytest tests/`. TDD is mandatory
in this repo — every task below writes its failing test first.

## Task order

| # | Task | Depends on | Risk |
|---|---|---|---|
| T1 | `TUSK_TTS_SPEED` reaches `Config.tts_speed` | — | low |
| T2 | `GroqTTS` sends `speed`, omits it at `1.0` | — | low |
| T3 | `ShellLoader` passes the configured speed | T1, T2 | medium |
| T4 | Document the setting | T1–T3 | low |
| T5 | **Gate:** verify against the live Groq API | T1–T3 | high |
| T6 | Contingency: client-side time-stretch — **only if T5 fails** | T5 (negative) | high |

T1 and T2 are independent of each other and each leaves the suite fully green on its own.
T5 is a gate, not a formality: a green unit suite proves only that the parameter was sent
(architecture §5.1).

---

## T1 — `TUSK_TTS_SPEED` reaches `Config.tts_speed`

**Goal.** A new float setting, read from the environment the way every other numeric TUSK
setting is read, defaulting to `1.0`. Nothing consumes it yet.

**Affected paths**
- `tusk/shared/config/config.py` — add `tts_speed: float` immediately after `tts_enabled`
- `tusk/shared/config/config_factory.py` — add `"tts_speed": self._float("TUSK_TTS_SPEED", "1.0")` to `_audio_values()`
- `tests/shared/test_config_factory.py` — a default test and an override test, beside the existing `TUSK_TTS` / `TUSK_ACK` pair

**Allowed paths.** Exactly the three files above.

**Dependencies.** None.

**Acceptance criteria**
1. `Config` is still a frozen dataclass constructed only via `Config(**values)`; the new
   field is produced by `_audio_values()`, so `ConfigFactory().build()` does not raise
   `TypeError`.
2. With `TUSK_TTS_SPEED` unset, `ConfigFactory().build().tts_speed == 1.0`.
3. With `TUSK_TTS_SPEED=1.5`, `ConfigFactory().build().tts_speed == 1.5`.
4. `_audio_values()` still fits the ≤10-line function guardrail.
5. No range check, clamp, or bespoke error path: `TUSK_TTS_SPEED=abc` raises `ValueError`
   at startup exactly as `AUDIO_SAMPLE_RATE=abc` does today (architecture §5.3).

**Tests expected to pass.** `tests/shared/test_config_factory.py` (including the two new
tests), `tests/test_style_guardrails.py`, `tests/test_package_exports.py`, and the full
suite — this task breaks nothing, because no consumer reads the field yet.

**Exclusions.** Do not touch `GroqTTS`, `shell_loader.py`, `.env.example`, or any doc. Do
not add validation, clamping, or a new parsing helper — `self._float` already exists. Do
not reorder or reformat neighbouring config fields.

**Risk.** Low.

---

## T2 — `GroqTTS` sends `speed`, and omits it at `1.0`

**Goal.** The provider can speak faster on request, and at the default builds exactly the
request it builds today.

**Affected paths**
- `tusk/providers/tts/groq_tts.py` — `speed: float = 1.0` keyword on `__init__`, stored as `self._speed`; extract the request kwargs into a `_request(text) -> dict` helper that adds `speed` only when `self._speed != 1.0`
- `tests/providers/test_groq_tts.py` — two new tests using the existing `_recording_client` fake

**Allowed paths.** Exactly the two files above.

**Dependencies.** None — the default keeps the class constructible with one argument.

**Acceptance criteria**
1. `GroqTTS("test-key")` produces request kwargs with **no** `speed` key, and otherwise
   identical to today's four (`model`, `voice`, `input`, `response_format`). This is the
   "default 1.0 unchanged" guarantee, and it is why `speed` is omitted rather than sent as
   `1.0` (architecture §3).
2. `GroqTTS("test-key", speed=1.5)` produces kwargs where `captured["speed"] == 1.5`.
3. The four existing tests in `tests/providers/test_groq_tts.py` pass unmodified.
4. `TTSEngine` (`tusk/shared/tts/interfaces/tts_engine.py`) is untouched;
   `synthesize_chunks(text)` keeps its signature.
5. Guardrails hold: `groq_tts.py` ≤100 code lines, every function ≤10 lines, and the
   widened `__init__` signature is wrapped to stay within the 120-char line target.

**Tests expected to pass.** `tests/providers/test_groq_tts.py`,
`tests/test_style_guardrails.py`, `tests/test_style_guardrail_exclusions.py`,
`tests/test_text_chunkers.py`, and the full suite.

**Exclusions.** No environment access and no `Config` import inside the provider — speed
arrives as a constructor argument. Do not validate the value (a bad one is the API's to
reject). Do not change the model, voice, or `response_format` defaults. Do not touch
`TextChunker`. Do not add `speed` to the `TTSEngine` ABC or to `synthesize_chunks`
(architecture §6D). No new file, no new class.

**Risk.** Low at the unit level. Whether the API *honours* the parameter is unverified and
is T5's job, not this task's.

---

## T3 — `ShellLoader` passes the configured speed

**Goal.** Close the loop: the sole `GroqTTS` construction site reads `config.tts_speed`.

**Affected paths**
- `shell_loader.py` — `_build_worker`: `GroqTTS(self._config.groq_api_key, speed=self._config.tts_speed)`
- `tests/test_shell_loader.py` — two required stub repairs plus one new test

**Allowed paths.** Exactly the two files above.

**Dependencies.** T1 (the config field must exist) and T2 (the constructor must accept the
keyword).

**Acceptance criteria**
1. `_build_worker` constructs `GroqTTS` with the configured speed, still only when
   `self._config.tts_enabled`, and stays within the ≤10-line function guardrail with the
   line wrapped under 120 chars.
2. `tests/test_shell_loader.py:10-13` — the `_loader` helper's `types.SimpleNamespace`
   config gains `tts_speed=1.0`. Without it, `_build_worker` raises `AttributeError` at
   build time and several tests fail (architecture §4).
3. `tests/test_shell_loader.py:49` — the `GroqTTS` monkeypatch stub, currently
   `lambda key: sentinel`, accepts the new keyword. Without it, the stub raises
   `TypeError`.
4. A new test asserts the wiring, not just that it does not crash: with a recording stub in
   place of `GroqTTS` and a loader configured at a non-default speed, the recorded `speed`
   equals the configured value.
5. The whole suite is green at the end of this task.

**Tests expected to pass.** `tests/test_shell_loader.py`, `tests/test_shell_startup.py`,
`tests/shells/`, `tests/test_style_guardrails.py`, and the full suite.

**Exclusions.** Do not modify `ChunkedSpeaker`, `SpeechPlayback`, `CommandWorker`, the
interrupt path, or `e2e/voice_e2e_harness.py` (it fakes TTS as a `SimpleNamespace` and
bypasses the loader entirely — no change needed). Do not add a second `GroqTTS`
construction site. Do not make TTS enablement depend on the speed value. Do not weaken the
stub to `**kwargs` — name the parameter.

**Risk.** Medium. This is the only task that breaks currently-passing tests, and it breaks
them through a hand-listed `SimpleNamespace` whose failure mode is an `AttributeError`
rather than an obvious signature mismatch.

---

## T4 — Document the setting

**Goal.** `TUSK_TTS_SPEED` is discoverable without reading code.

**Affected paths**
- `.env.example` — a commented `# TUSK_TTS_SPEED=1.0` with a one-line explanation, in the TTS block beside `TUSK_TTS` / `TUSK_ACK` (lines 17-22)
- `docs/specification.md` — one row in the env-var table (§ around line 78, after `TUSK_ACK`): `| TUSK_TTS_SPEED | float | 1.0 | Playback speed of spoken replies; 1.0 sends no speed parameter |`, and one bullet in §22.1 (~line 1129)
- `docs/architecture.md` — one sentence in the TTS section (~line 830) recording the setting and the 1.0-omission
- `docs/class-diagrams.md` — a `speed : float` attribute line on the `GroqTTS` class box (~line 704)

**Allowed paths.** Exactly the four files above.

**Dependencies.** T1–T3 (document what is actually wired).

**Acceptance criteria**
1. Each of the four files names the env var `TUSK_TTS_SPEED`, states the `1.0` default, and
   nothing contradicts the implemented behaviour.
2. The specification table row matches the surrounding rows' column format.
3. Edits are additive; no neighbouring rows, bullets, or diagram entries are rewritten.

**Tests expected to pass.** Full suite (unchanged by documentation), plus a visual check
that the mermaid block in `docs/class-diagrams.md` still parses.

**Exclusions.** Do **not** repair the pre-existing staleness flagged in architecture §4 and
§8: `docs/architecture.md:836` and `docs/specification.md:1129` still describe
`WavConcatenator` and a `synthesize(text) -> bytes` interface, and the `GroqTTS` box in
`docs/class-diagrams.md` still lists `synthesize(text) bytes`. All three are wrong and all
three are out of scope here. Do not create a `docs/features/*.md` file — the architecture's
integration table names the doc set for this change, and one setting does not warrant a new
feature page. Do not touch the README.

**Risk.** Low.

---

## T5 — Gate: verify against the live Groq API

**Goal.** Answer the one load-bearing unknown in the design (architecture §5.1): does
`canopylabs/orpheus-v1-english` accept and honour `speed`?

**Affected paths.** None — this task changes no file. Its output is a written finding
reported with the change.

**Allowed paths.** None. Read-only execution.

**Dependencies.** T1–T3. T4 may be done before or after.

**Acceptance criteria**
1. `docker compose exec tusk pytest tests/` is green.
2. The voice shell is run against the live Groq API with real credentials at
   `TUSK_TTS_SPEED=1.0`, `1.5` and `2.0`, and a spoken reply is **listened to** at each.
3. At `1.0`: indistinguishable from today, and no `speed` key in the outgoing request.
4. At `1.5` and `2.0`: audibly faster, no `tts failed: …` line in the log (that log line is
   how a rejected parameter would surface — `chunked_speaker.py:46-47`), and no obvious
   pitch shift.
5. While at `2.0`, confirm that a reply leaking into the microphone is still dropped by
   `EchoFilter` and not taken as a command (architecture §5.2). Faster speech transcribes
   less accurately and may fall under the 0.75 similarity threshold.
6. The finding is recorded explicitly as one of: honoured / rejected / silently ignored.
   "Silently ignored" is the dangerous outcome — the suite stays green and nothing logs, so
   only listening detects it.
7. If credentials, network, or audio output are unavailable, **report a blocker**. Do not
   mark the issue done on a green unit suite: a green suite here is close to meaningless.

**Tests expected to pass.** The full suite, plus the manual listening checks above.

**Exclusions.** No code changes in this task. If verification fails, stop and open T6 —
do not patch the provider in place or start clamping/retrying values.

**Risk.** High. This is the task that can invalidate the primary mechanism.

---

## T6 — Contingency: client-side time-stretch (**only if T5 is negative**)

**Goal.** Deliver the same setting through seam 2 when the provider will not do it.
Pre-approved in architecture §3, so no redesign and no new architecture gate.

**Do not start this task unless T5 reported "rejected" or "silently ignored".**

**Affected paths**
- `tusk/providers/tts/speed_adjusted_tts.py` — new `SpeedAdjustedTTS(TTSEngine)`, composing an injected inner engine
- `tusk/providers/tts/__init__.py` — export it in `__all__`
- `shell_loader.py` — wrap the inner engine only when `tts_speed != 1.0`
- `tusk/providers/tts/groq_tts.py` — revert T2's `speed` keyword
- `tests/providers/test_speed_adjusted_tts.py` — new
- `tests/providers/test_groq_tts.py`, `tests/test_shell_loader.py` — adjust to the reverted/rewired shape

**Allowed paths.** Exactly the six above. `Config`, `ConfigFactory`, `.env.example`, and the
doc wording from T1 and T4 are shared between both mechanisms and must **not** change.

**Dependencies.** T5, with a negative outcome.

**Acceptance criteria**
0. **Before writing the class:** confirm on a real Orpheus clip that `ffmpeg` reads it to
   EOF rather than truncating. Orpheus streams a placeholder frame count in its WAV headers
   (architecture §5.3) — `paplay` copes; ffmpeg is unverified. If it truncates, that is a
   second blocker to report, not to work around silently.
1. `SpeedAdjustedTTS` implements `TTSEngine`, takes the inner engine in `__init__`
   (dependency injection — it never constructs one), and stretches each clip inside
   `synthesize_chunks`, i.e. on `ChunkedSpeaker`'s prefetch thread.
2. It shells out to `ffmpeg -i pipe:0 -filter:a atempo=<speed> -f wav pipe:1`. ffmpeg is
   already in the image (needed by openai-whisper) — no new dependency. Confirm the
   installed ffmpeg's `atempo` accepts the target values directly; if its range is capped at
   2.0, chain filters rather than silently clipping.
3. `ShellLoader._build_worker` applies the wrapper only when `tts_speed != 1.0`, so the
   `1.0` path is byte-identical to today.
4. Tests use a fake inner engine and a faked subprocess — follow
   `tests/shells/voice/test_speech_playback.py`, which patches `Popen` in the module
   namespace with a fake process class. No real ffmpeg, no network, no real audio in unit
   tests.
5. Guardrails hold: new file ≤100 code lines, one class, functions ≤10 lines,
   `tusk/providers/tts/` stays under 12 files.
6. Re-run T5's listening checks against the new mechanism, including the echo check at
   `2.0`, and note that artefacts become audible past ~1.75x.

**Tests expected to pass.** `tests/providers/`, `tests/test_shell_loader.py`,
`tests/test_package_exports.py`, `tests/test_style_guardrails.py`,
`tests/test_import_guardrails.py`, and the full suite.

**Exclusions.** Do not keep both mechanisms — if the wrapper ships, T2's provider keyword is
removed. Do not change the env var, the `Config` field, the default, or the docs from T1/T4.
Do not touch `SpeechPlayback` or `ChunkedSpeaker`. Do not fall back to rewriting the WAV
sample rate (architecture §6B — it raises pitch).

**Risk.** High: a new process on the reply path, plus the unverified ffmpeg/Orpheus header
interaction in criterion 0.

---

## Out of scope for every task

Voice and model selection; per-utterance speed overrides; anything touching STT, VAD, or
microphone capture; a tray or runtime control for speed; and repairing the pre-existing
documentation staleness noted in T4's exclusions.

---

## Implementation notes (written during the implementation stage)

T1–T4 are done as specified except where noted below. **T5 was not performed — see the
blocker.** T6 was not started: it is gated on a negative T5, and T5 has no outcome yet.

### The 100-code-line file guardrail forced three deviations

`tests/style_guardrails/file_guardrails.py` caps every non-hidden `.py` file — including
files under `tests/` — at 100 code lines (blank and comment-only lines excluded). Neither
the architecture nor this plan checked the three files T1 and T3 had to touch. They were at
**100, 100 and 95** code lines respectively, so the planned edits would have broken
`tests/test_style_guardrails.py`. The mechanism, the env var, the `Config` field, the `1.0`
omission and the docs are all exactly as planned; only the shape of the edits changed.

1. **`shell_loader.py` (was at exactly 100).** The planned wrap of the `GroqTTS(...)` line
   under 120 chars (T3 criterion 1) costs a physical line, which the cap does not allow. The
   local `tts_engine` is renamed to `engine`, keeping the statement on one 119-char line at
   zero net cost. This is why the diff touches the `ChunkedSpeaker(...)` line too.
2. **`tests/test_shell_loader.py` (was at exactly 100).** T3 criterion 4's *new* test could
   not be added — any new test is ≥8 lines. The existing
   `test_command_worker_receives_tts_engine_when_enabled` is instead rewritten in place, at
   the same line count, as
   `test_command_worker_receives_tts_engine_built_at_the_configured_speed`: the `GroqTTS`
   stub returns the engine only when it is called with `speed == 1.5`, so a speed that never
   arrives, or arrives wrong, puts `None` on the speaker and fails the assertion. It still
   asserts the wiring rather than the absence of a crash, but as one test rather than two.
   For the same reason `_loader` keeps its signature: its config namespace carries
   `tts_speed=1.0` (T3 criterion 2, on an existing line) and the test mutates
   `loader._config.tts_speed`, rather than paying a line for a wrapped signature.
3. **`tests/shared/test_config_factory.py` (was at 95, so 5 lines of headroom).** T1's
   planned default/override *pair* costs 8 lines. They are merged into one 5-line
   `test_tts_speed_defaults_to_normal_and_reads_an_override`, which still asserts both
   acceptance criteria 2 and 3. **The `monkeypatch.delenv("TUSK_TTS_SPEED", raising=False)`
   guard was dropped to fit**: the default half of the test therefore trusts that
   `TUSK_TTS_SPEED` is unset in the environment, exactly as the neighbouring
   `test_tts_enabled_by_default` trusts it for `TUSK_TTS`. If a container ever sets
   `TUSK_TTS_SPEED`, this test fails spuriously — the honest fix is to split the file, which
   was outside this task's allowed paths.

`shell_loader.py`, `tests/test_shell_loader.py`, `tests/shared/test_config_factory.py` and
`tusk/shared/config/config_factory.py` now all sit at **exactly 100** code lines. The next
change to any of them has to split the file first.

### Blocker: T5 could not be run, and neither could the unit suite

The implementation stage runs non-interactively with `Bash` behind an approval prompt that
cannot be answered. `docker compose exec tusk pytest tests/`, `docker compose ps` and a
direct `python3 -m pytest` were each attempted and each was refused. So:

- **T5 (the gate) was not performed.** There are no Groq credentials, no network and no
  audio sink in this stage, and the live listening checks are the only thing that can
  distinguish "honoured" from "silently ignored". Its finding is **unrecorded**, not
  negative. Architecture §5.1 is explicit that this is a blocker to report rather than a
  step to skip, and T5 criterion 7 says the same.
- **T1–T4 have not been executed either.** The line counts above were verified by hand;
  everything else — that the new tests pass, that the four existing `GroqTTS` tests still
  pass, that the guardrail suite is green — is **unverified**.

Both need doing before this change ships. Run the suite first; then run T5's listening
checks at `1.0`, `1.5` and `2.0`, including the `EchoFilter` check at `2.0` (architecture
§5.2). If Orpheus rejects or silently ignores `speed`, T6 is pre-approved and unchanged.
