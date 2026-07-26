# Implementation Plan — Issue #47: TTS Playback Speed

Source: `docs/architecture/issue-47.md` (approved). Chosen approach: a session-wide
`tts_speed` setting, read from a new `TTS_SPEED` env var, threaded through
`Config` → `ShellLoader` → `SpeechPlayback`, applied via `ffmpeg -af atempo` inside
`SpeechPlayback.play(...)` — bypassed entirely at the `1.0` default. `GroqTTS` and
`TTSEngine` are never touched.

Every task follows this repo's TDD railguide: write/extend the failing test(s) listed
under "Tests expected to pass" first, then implement the smallest change to pass them.

---

## Task 1 — Add `tts_speed` to `Config` and `ConfigFactory`

**Goal:** Make the playback speed configurable via the `TTS_SPEED` env var, following
the exact pattern `TUSK_TTS` already uses, with a default that reproduces today's
behavior (`1.0`).

**Affected paths:**
- `tusk/shared/config/config.py`
- `tusk/shared/config/config_factory.py`
- `tests/shared/test_config_factory.py`

**Allowed paths:** same three files above. No other file may be touched.

**Dependencies:** none. This task can start immediately.

**Acceptance criteria:**
- `Config` gains one new frozen field: `tts_speed: float`.
- `ConfigFactory._audio_values()` reads `TTS_SPEED` via the existing `self._float(...)`
  helper, defaulting to `"1.0"`, and adds `tts_speed` to the returned dict, next to
  `tts_enabled`.
- No other `ConfigFactory` method changes; no new helper methods are introduced (the
  existing `_float` helper already covers this).
- With `TTS_SPEED` unset, `ConfigFactory().build().tts_speed == 1.0`.
- With `TTS_SPEED=1.5` (or `2.0`, etc.) set, `ConfigFactory().build().tts_speed` reflects
  the parsed float.

**Tests expected to pass:**
- New test in `tests/shared/test_config_factory.py`: `TTS_SPEED` unset defaults
  `tts_speed` to `1.0`.
- New test in `tests/shared/test_config_factory.py`: `TTS_SPEED=1.5` yields
  `tts_speed == 1.5`.
- All existing tests in `tests/shared/test_config_factory.py` and
  `tests/shared/test_config_factory_codex.py` continue to pass unchanged (adding a
  required positional-equivalent dataclass field must not break other field
  construction, since `ConfigFactory.build()` always passes a complete `**values` dict).

**Explicit exclusions:**
- Do not touch `GroqTTS`, `TTSEngine`, `SpeechPlayback`, or `ShellLoader` in this task.
- Do not add a `speed` kwarg anywhere near the Groq SDK call — that is confirmed
  non-functional per the architecture doc and out of scope for this repo entirely.
- Do not validate or clamp the parsed float (e.g. reject negative or zero values) —
  the architecture doc leaves range validation as an open concern for the
  `SpeechPlayback`/`ffmpeg` boundary (Task 2), not for config parsing.
- Do not rename or restructure existing `ConfigFactory` methods.

**Risk classification:** low. Purely additive dataclass field and env-var read,
following an existing pattern exactly; no behavioral change to any existing field.

---

## Task 2 — Add speed-aware playback to `SpeechPlayback`

**Goal:** `SpeechPlayback` accepts a `speed` setting at construction and, when it is not
`1.0`, time-stretches WAV bytes through `ffmpeg -af <atempo-filter-chain>` (chaining
`atempo` stages as needed for speeds outside `0.5`–`2.0`) before handing them to
`paplay`, falling back to the unstretched bytes if that step fails. At `speed == 1.0`
playback is byte-for-byte identical to today (no `ffmpeg` process spawned at all).

**Affected paths:**
- `shells/voice/stages/speech_playback.py`
- `tests/shells/voice/test_speech_playback.py`

**Allowed paths:** same two files above. No other file may be touched.

**Dependencies:** none — this task is independent of Task 1 (it only needs a `speed`
constructor parameter, not the `Config` wiring) and can proceed in parallel.

**Acceptance criteria:**
- `SpeechPlayback.__init__` gains a `speed: float = 1.0` parameter (keyword-compatible
  with existing `interrupt_token` and `poll_seconds` parameters; existing call sites
  that omit it keep today's behavior).
- At `speed == 1.0`: `play(wav_bytes)` behaves exactly as today — a single
  `subprocess.Popen(["paplay"], stdin=subprocess.PIPE)` call, raw bytes fed directly.
  No `ffmpeg` process is spawned.
- At `speed != 1.0`: `play(wav_bytes)` first pipes `wav_bytes` through
  `ffmpeg -af <atempo-filter-chain> -f wav -` (via `subprocess.Popen`, consistent with the
  existing `paplay` integration style), and the stretched stdout is what gets fed to
  `paplay`. The existing interrupt/timeout guard (`_await`, 30 s cap, `InterruptToken`
  polling) continues to govern the `paplay` process exactly as before.
- Because `ffmpeg`'s single `atempo` filter only accepts `0.5`–`2.0`, a small helper
  (e.g. `_atempo_filter_chain(speed) -> str`) decomposes any requested `speed` into a
  chain of factors each within `0.5`–`2.0` and joins them with commas — e.g. `1.5` →
  `"atempo=1.5"`, `2.0` → `"atempo=2.0"`, `3.0` → `"atempo=2.0,atempo=1.5"`, `4.0` →
  `"atempo=2.0,atempo=2.0"`. This closes the failure mode where a documented, in-scope
  speed value (the issue's "x2, and so on" covers values above `2.0`) would otherwise be
  rejected by `ffmpeg` outright.
- If the `ffmpeg` stretch step fails for any reason (non-zero exit, `OSError`, or any
  other error obtaining stretched bytes), `play()` falls back to feeding the original,
  unstretched `wav_bytes` to `paplay` and logs the failure — it must never result in no
  audio being played at all.
- Each new unit of logic stays within the 10-line-per-method guideline in this
  repo's `CLAUDE.md`; extract helpers (e.g. `_stretch(wav_bytes)`,
  `_atempo_filter_chain(speed)`) rather than growing `play()` past that.

**Tests expected to pass:**
- Existing tests in `tests/shells/voice/test_speech_playback.py`
  (`test_playback_pipes_wav_bytes_to_paplay`,
  `test_playback_completes_without_terminate_when_uninterrupted`,
  `test_playback_terminates_when_token_interrupted`,
  `test_feed_closes_stdin_when_write_fails`) continue to pass unchanged — they construct
  `SpeechPlayback` without a `speed` argument, so must exercise the `1.0` no-op path.
- New test: at `speed == 1.0`, only one `subprocess.Popen` call is made (asserting
  today's behavior is preserved byte-for-byte, matching the architecture doc's explicit
  "must be a true no-op" requirement).
- New test: at `speed == 2.0` (or similar), two `subprocess.Popen` calls are made — one
  for `ffmpeg` with `atempo=2.0` in its argument list, one for `paplay` — and the bytes
  fed to `paplay`'s stdin are the `ffmpeg` process's stdout, not the raw input bytes.
- New unit tests for `_atempo_filter_chain(speed)` covering `1.5` (`"atempo=1.5"`), `2.0`
  (`"atempo=2.0"`), `3.0` (`"atempo=2.0,atempo=1.5"`), and `4.0`
  (`"atempo=2.0,atempo=2.0"`).
- New test: when the `ffmpeg` stretch step fails (non-zero exit / `OSError`), `play()`
  does not raise, and `paplay`'s stdin still receives the original, unstretched
  `wav_bytes` (not empty bytes, not a raised exception) — asserting the fallback path,
  not a swallowed failure.

**Explicit exclusions:**
- Do not read `TTS_SPEED` or `Config` from this file — `speed` arrives purely as a
  constructor parameter; wiring it from config is Task 3.
- Do not add speed validation/clamping for values `ffmpeg` cannot represent at all (e.g.
  `0` or negative) beyond whatever `ffmpeg` itself does — out of scope per the
  architecture doc's "left to implementation" note. This is distinct from the
  `atempo` chain-decomposition above: chaining is required so that in-range positive
  speeds (including anything above `2.0`, which the issue's "x2, and so on" covers) are
  actually played, not silently dropped; do not gold-plate beyond that with rejecting
  values the issue never asks for.
- Do not change `ChunkedSpeaker` or any other caller of `SpeechPlayback`.
- Do not touch `GroqTTS` or send any `speed` kwarg to the Groq SDK.

**Risk classification:** medium. Adds a new subprocess (`ffmpeg`) and a new code path
inside a component on the hot playback path; the `1.0` no-op path must be verified not
to regress, and the new `ffmpeg` path introduces a new external-process failure mode.

---

## Task 3 — Wire `Config.tts_speed` through `ShellLoader` into `SpeechPlayback`

**Goal:** Connect the configured speed to the component that applies it, so the feature
is actually reachable at runtime.

**Affected paths:**
- `shell_loader.py`
- `tests/test_shell_loader.py`

**Allowed paths:** same two files above. No other file may be touched.

**Dependencies:** Task 1 (needs `Config.tts_speed` to exist) and Task 2 (needs
`SpeechPlayback.__init__` to accept `speed`). Must land after both.

**Acceptance criteria:**
- `ShellLoader._build_worker` constructs `SpeechPlayback(token, speed=self._config.tts_speed)`
  (or equivalent keyword form) instead of `SpeechPlayback(token)`.
- No other line in `_build_worker` changes; `GroqTTS(self._config.groq_api_key)` and the
  `ChunkedSpeaker`/`CommandWorker` construction are untouched.

**Tests expected to pass:**
- Existing tests in `tests/test_shell_loader.py` continue to pass. The `_loader(...)`
  test helper's `types.SimpleNamespace(...)` config stub must gain a `tts_speed` field
  (e.g. defaulting to `1.0`) so existing tests that build a voice shell keep working —
  this is a test-fixture update, not new test-file scope creep.
- New test: with a stubbed config where `tts_speed=2.0`, the `SpeechPlayback` instance
  built inside `_build_worker` (reachable via the constructed `CommandWorker`/`ChunkedSpeaker`,
  or via a monkeypatched `SpeechPlayback` constructor spy) is constructed with `speed=2.0`.

**Explicit exclusions:**
- Do not change how `tts_engine`/`GroqTTS` is constructed or gated by `tts_enabled`.
- Do not add speed-related logic to `ChunkedSpeaker`, `CommandWorker`, or `VoiceShell`.
- Do not introduce a new `_build_worker` helper method beyond what's needed to pass
  `speed` through — keep the diff to the single construction line plus the test fixture
  update.

**Risk classification:** low. A single-argument wiring change at a well-tested
construction site; both inputs (`Config.tts_speed`, `SpeechPlayback(speed=...)`) are
already verified independently by Tasks 1 and 2.

---

## Task 4 — Document `TTS_SPEED` in the environment variable reference

**Goal:** Keep `docs/specification.md`'s configuration reference accurate, matching how
`TUSK_TTS`/`TUSK_ACK` are already documented there.

**Affected paths:**
- `docs/specification.md`

**Allowed paths:** `docs/specification.md` only.

**Dependencies:** Task 1 (the env var and default must be finalized before documenting
them). Can proceed independently of Tasks 2 and 3, but should land after Task 1 to avoid
documenting a var name/default that changes during review.

**Acceptance criteria:**
- The env var table (around `docs/specification.md:78`, next to the `TUSK_TTS` row)
  gains a `TTS_SPEED` row: type `float`, default `1.0`, one-line description matching
  the issue's intent (playback speed multiplier for spoken replies; `1.0` = unchanged).
- No other prose in `docs/specification.md` is rewritten; this is an additive table row
  plus, if the existing `SpeechPlayback` section (around line 1151) already narrates
  `paplay` behavior, a short factual addition noting the `ffmpeg` time-stretch step when
  speed is not `1.0`.

**Tests expected to pass:** none — this is a documentation-only change with no test
suite coverage. Verification is a manual read-through confirming the new row matches
the actual default/behavior implemented in Tasks 1–3.

**Explicit exclusions:**
- Do not modify `docs/architecture.md`, `docs/architecture/issue-47.md`, or any other
  doc file — only `docs/specification.md` is in scope.
- Do not add new sections, diagrams, or restructure existing ones — a table row (and
  optionally one sentence in the existing `SpeechPlayback` narrative) is the entire
  change.
- Do not document the rejected Groq API-side `speed` kwarg as if it were an option.

**Risk classification:** low. Documentation-only, no code or test impact.
