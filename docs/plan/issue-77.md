# Implementation Plan — Issue #77: `TTS_SPEED=inf` hangs the voice shell

Approved architecture: `docs/architecture/issue-77.md`. Chosen approach: bound
`SpeechPlayback._atempo_filter_chain`'s first (`> 2.0`) loop against non-finite input the
same way its second (`< 0.5`) loop is already bounded against non-positive input.

## Prerequisite — base branch (read before starting either task)

The buggy code does not exist on `main` or on this plan's own branch. It exists only on
`origin/factory/issue-47/implementation` (the `TTS_SPEED` feature branch, not yet merged).
Both tasks below must be authored against that branch's tree — either by implementing
directly on top of `factory/issue-47/implementation`, or after issue-47 has landed on `main`
and this work has been rebased onto it. All paths, line contents, and test names below are
quoted from `origin/factory/issue-47/implementation` as of this plan. If the implementation
stage instead touches this branch's current `shells/voice/stages/speech_playback.py` (which
has no `speed` parameter and no `_atempo_filter_chain`), both tasks will silently no-op —
that is a signal the prerequisite was missed, not that the work is done.

---

## Task 1 — Add a bounded-timeout regression test for the `inf` hang

**Goal.** Add a test that reproduces the hang described in the issue and fails fast (via a
wall-clock timeout) rather than hanging the test run, following the Red step of TDD before
any production code changes.

**Affected paths.**
- `tests/shells/voice/test_speech_playback.py`

**Allowed paths.** `tests/shells/voice/test_speech_playback.py` only. No other file may be
created or edited by this task.

**Dependencies.** None (first task).

**Acceptance criteria.**
- A new test, `test_atempo_filter_chain_terminates_for_infinite_speed`, is added next to the
  existing `test_atempo_filter_chain_*` tests in this file.
- The test runs `SpeechPlayback._atempo_filter_chain(float("inf"))` on a background
  `threading.Thread` (daemon) and calls `thread.join(timeout=...)` with a short, fixed
  timeout (recommend 2 seconds), then asserts `not thread.is_alive()`. This is the only way
  to turn an unbounded loop into a bounded, failing assertion instead of a hung test process
  — matching the issue's own note that a regression test for `inf` "would need a timeout."
  No new test dependency (e.g. `pytest-timeout`) is introduced; `threading` is stdlib and
  already implicitly available (the production code under test uses it).
- Run against the current, unfixed `_atempo_filter_chain` on `factory/issue-47/implementation`,
  this test fails its `not thread.is_alive()` assertion within the timeout window (confirms
  Red: the test reproduces the bug without hanging CI).
- All other tests already in `tests/shells/voice/test_speech_playback.py` and
  `tests/shells/voice/test_speech_playback_speed.py` still pass unmodified.

**Tests expected to pass.** All pre-existing tests in
`tests/shells/voice/test_speech_playback.py` and `tests/shells/voice/test_speech_playback_speed.py`.
(`test_atempo_filter_chain_terminates_for_infinite_speed` itself is expected to **fail** at
the end of this task — that failure is the deliverable, confirming the bug is reproduced.)

**Explicit exclusions.**
- Do not modify `shells/voice/stages/speech_playback.py` or any other production file.
- Do not add `pytest-timeout` or any other new dependency; use stdlib `threading`.
- Do not use `signal.alarm` (not portable, not used elsewhere in this test suite).
- Do not add a test for `float("nan")` — out of scope per the architecture (nan already
  terminates and is not part of this issue).
- Do not assert on the *content* of the filter-chain string in this task — only on
  termination. Content is covered once Task 2 fixes the loop.

**Risk classification.** Low. Test-only change; worst case is a flaky timeout threshold on a
very slow CI runner, not a correctness risk.

---

## Task 2 — Bound the first loop against non-finite `remaining`

**Goal.** Make `_atempo_filter_chain` terminate for `speed=inf` by adding a finiteness guard
to the first loop's condition, mirroring the existing guard on the second loop, so Task 1's
regression test (and all existing tests) pass.

**Affected paths.**
- `shells/voice/stages/speech_playback.py`

**Allowed paths.** `shells/voice/stages/speech_playback.py` only. No test file may be edited
by this task — Task 1 already added the coverage this task must satisfy.

**Dependencies.** Task 1 (the regression test must exist and be observed failing before this
task changes production code — Red before Green).

**Acceptance criteria.**
- The first loop's condition, currently `while remaining > 2.0:`, gains a finiteness check
  (e.g. `while remaining > 2.0 and math.isfinite(remaining):`) so it cannot iterate when
  `remaining` is `inf`. `math` is imported for this if not already.
- The second loop (`while 0.0 < remaining < 0.5:`) and its guarding comment are unchanged
  except, if needed, a one-line extension of the comment to note the first loop now carries
  its own equivalent guard — do not rewrite or relocate the existing comment beyond that.
- `SpeechPlayback._atempo_filter_chain(float("inf"))` returns promptly (no loop iterations)
  and produces `"atempo=inf"` — a single-factor chain, the same shape `nan` already produces
  today. This value is not treated as valid by this task; it is left to reach ffmpeg and be
  rejected there, exactly as zero/negative/`nan` already are (per the architecture's chosen,
  minimal, loop-level fix — no new validation is added at this layer).
- Every previously passing case is byte-for-byte unchanged: `_atempo_filter_chain(1.5)`,
  `(2.0)`, `(0.0)`, `(-1.0)`, `(3.0)`, `(4.0)` all return exactly what they return today.
- The function body stays within this repository's 10-line-per-method guardrail.

**Tests expected to pass.**
- `tests/shells/voice/test_speech_playback.py::test_atempo_filter_chain_terminates_for_infinite_speed`
  (added in Task 1) — now passes.
- `tests/shells/voice/test_speech_playback.py::test_atempo_filter_chain_within_native_range`
- `tests/shells/voice/test_speech_playback.py::test_atempo_filter_chain_terminates_for_non_positive_speed`
- `tests/shells/voice/test_speech_playback.py::test_atempo_filter_chain_above_native_range`
- `tests/shells/voice/test_speech_playback.py::test_playback_speed_one_skips_ffmpeg`
- All tests in `tests/shells/voice/test_speech_playback_speed.py`
  (`test_playback_speed_stretches_through_ffmpeg`,
  `test_playback_falls_back_to_original_bytes_when_ffmpeg_exits_non_zero`,
  `test_playback_falls_back_to_original_bytes_when_ffmpeg_missing`)

**Explicit exclusions.**
- Do not modify `ConfigFactory._float` (`tusk/shared/config/config_factory.py`) or any other
  config-layer file — rejected alternative per the architecture; `_float` is shared by
  unrelated settings and this is out of scope.
- Do not modify `ShellLoader._build_worker`, `Config.tts_speed`, or any construction-site
  validation — rejected alternative per the architecture.
- Do not change behavior for `speed=nan` — explicitly out of scope per the issue and
  architecture; it already terminates and already falls through to ffmpeg's rejection.
- Do not replace the `while` loop with a bounded `for _ in range(N):` counter — rejected
  alternative per the architecture (changes the loop's shape, introduces a magic number).
- Do not touch `_stretch`, `_run_ffmpeg`, `_spawn_ffmpeg`, `play()`, `_await`,
  `_interrupted`, or `_feed` — none of these own the non-termination hazard.
- Do not edit any test file.

**Risk classification.** Low. Single-condition change to one loop in one already-tested
static method; behavior for every finite input is preserved by the added finiteness
conjunct being a no-op whenever `remaining` is finite.
