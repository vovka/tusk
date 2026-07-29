# Issue #77 Architecture: TTS Speed Control and inf-Loop Hazard

## Issue Summary

`SpeechPlayback._atempo_filter_chain` enters an infinite loop when `TTS_SPEED=inf`, attempting to decompose a speed factor into powers of 2 without ever terminating. The first loop (`while remaining > 2.0`) never exits because `inf / 2.0 == inf`. Additionally, `ConfigFactory._float` is unguarded and accepts `inf` and `nan` at the system boundary, allowing unparseable values to propagate into audio processing.

## Components Affected

### Primary

**`shells/voice/stages/speech_playback.py:SpeechPlayback`**
- Current: Pipes WAV bytes to `paplay` subprocess via stdin.
- Proposed: Add optional speed adjustment via ffmpeg atempo filter chains.
- Key method: `_atempo_filter_chain(speed: float) -> str` — constructs ffmpeg filter string.
- Risk: First while loop has no guard for non-finite values; second loop has a bound for zero/negative but first does not.

### Secondary

**`tusk/shared/config/config_factory.py:ConfigFactory._float`**
- Current: `return float(os.environ.get(name, default))` — bare cast, no validation.
- Issue: `float("inf")` and `float("nan")` parse successfully and propagate into config.
- Related: `_int` and `_bool` also lack input validation, though integer bounds are less hazardous.

**`tusk/shared/config/config.py:Config`**
- Current: No `tts_speed` field; would need to be added.
- Impact: All consumers of Config (e.g., `shell_loader.py:_build_worker`) would gain access to the new knob.

### Tertiary

**`shells/voice/stages/chunked_speaker.py:ChunkedSpeaker`**
- Calls `SpeechPlayback.play(wav_clip)` for each synthesized chunk.
- If speed adjustment moves into `SpeechPlayback`, chunk playback is unaffected; speed is applied at playback time, not synthesis time.

**`tusk/providers/tts/groq_tts.py:GroqTTS`**
- Generates WAV bytes via Groq API.
- No changes needed; TTS output is speed-agnostic.

**`shell_loader.py:ShellLoader._build_worker`**
- Instantiates `SpeechPlayback(token)` and `ChunkedSpeaker(tts_engine, playback, ...)`.
- Would pass `tts_speed` from `Config` to `SpeechPlayback.__init__` if implemented.

## Integration Points

### Configuration Flow

```
os.environ.get("TTS_SPEED") 
  → ConfigFactory._float("TTS_SPEED", "1.0") 
  → Config.tts_speed 
  → ShellLoader._build_worker() 
  → SpeechPlayback(token, speed=config.tts_speed) 
```

### Playback Flow

```
ChunkedSpeaker._play_clips()
  → for wav_clip in clips: SpeechPlayback.play(wav_clip)
    → _atempo_filter_chain(self.speed)  [proposed]
    → subprocess.Popen(["ffmpeg", "-i", "pipe:", "-af", filter_str, "-f", "wav", "pipe:"], ...)
    → paplay
```

## Current Architecture (Audio Playback)

1. **Synthesis**: GroqTTS.synthesize_chunks() yields WAV bytes (one per ~200 char chunk).
2. **Buffering**: ChunkedSpeaker._prefetched() runs synthesis in a background thread, yields chunks via a queue.
3. **Playing**: ChunkedSpeaker._play_clips() calls SpeechPlayback.play() once per chunk; chunks play sequentially.
4. **Process**: SpeechPlayback.play() opens paplay, writes WAV bytes to stdin, polls until process exits.
5. **Interrupt**: InterruptToken polled every 0.1 s (default); SpeechPlayback.terminate() kills paplay if interrupted.

If audio speed control is added, ffmpeg would be inserted as a filter between stdin and paplay:
```
SpeechPlayback.play() → subprocess.Popen(["ffmpeg", "-i", "pipe:", "-af", "atempo=X.X", "-f", "wav", "pipe:"])
                         ↓ filtered WAV ↓
                       paplay
```

## The Bug and Failure Modes

### Infinite Loop (speed=inf)

```python
def _atempo_filter_chain(speed: float) -> str:
    factors = []
    remaining = speed
    while remaining > 2.0:       # ← BUG: no upper bound
        factors.append(2.0)
        remaining /= 2.0          # inf / 2.0 == inf, so loop never exits
    # ... second loop, etc.
```

**Symptom**: Process consumes memory indefinitely as `factors` list grows; system becomes unresponsive.

**Precondition**: `TTS_SPEED=inf` in environment, or any code path passing `float("inf")` to speed.

### nan Passthrough (speed=nan)

```python
remaining = float("nan")
while remaining > 2.0:     # False (nan comparisons always false)
    # skipped
while 0.0 < remaining < 0.5:  # False
    # skipped
return f"atempo={remaining}"   # "atempo=nan"
```

**Symptom**: ffmpeg rejects `atempo=nan` filter; playback falls back to normal speed (by design).

**Severity**: Low — no crash, just silent fallback.

### Zero/Negative (speed ≤ 0)

```python
remaining = 0.0
while remaining > 2.0:         # False, skipped
    # ...
while 0.0 < remaining < 0.5:   # False, skipped
    # ...
return f"atempo={remaining}"   # "atempo=0.0"
```

**Symptom**: ffmpeg rejects non-positive atempo values; playback falls back to normal speed.

**Severity**: Low — by design, ffmpeg error is caught and fallback applied.

## Risks and Unknowns

### Configuration Boundary

**Risk**: `ConfigFactory._float` has no validation. Any string that `float()` accepts is loaded into Config.

- `TTS_SPEED=inf` → accepted and stored.
- `TTS_SPEED=nan` → accepted and stored.
- `TTS_SPEED=-1.5` → accepted (caught later by ffmpeg, not at config time).
- `TTS_SPEED=1.0e308` → accepted (very large but finite; may behave differently than inf).

**Unknown**: Where should validation occur? Options:
1. In `ConfigFactory._float` (generic, but then _all_ float configs become strict).
2. At the `tts_speed` call site in `ConfigFactory` (local, checked before Config creation).
3. In `SpeechPlayback.__init__` (late, fails on first playback attempt).

**Implication**: Validation choice affects error timing and user experience (fail-fast at startup vs. at first speech).

### Test Coverage

**Current**: `test_speech_playback.py` mocks `paplay` and tests interrupt logic, stdin feeding, and process lifecycle.

**Missing**: 
- No unit test for `_atempo_filter_chain` (method does not yet exist).
- No test for `inf`, `nan`, or negative speeds.
- No integration test with actual ffmpeg (would slow down test suite).

**Suggested Pattern** (from issue): Regression test with a timeout, since failure is a hang not a wrong answer (matching `test_atempo_filter_chain_terminates_for_non_positive_speed` pattern if it exists).

### Latency Impact

**Current**: SpeechPlayback.play() blocks until paplay exits (~duration of WAV). No noticeable overhead.

**Proposed**: If ffmpeg is inserted, one additional pipe fork and filter overhead (~5–10 ms per chunk, likely imperceptible).

**Unknown**: Overhead with large atempo values or very fast/slow speeds; ffmpeg efficiency at extremes.

## Approach and Alternatives

### Chosen Approach (Inferred from Issue)

1. **Guard first loop**: Add `and remaining.is_finite()` or similar to first while loop, matching the reasoning for the second loop.
2. **Validate at config boundary**: Guard `ConfigFactory._float` to reject non-finite values, or add a `_tts_speed` method that wraps `_float` with validation.
3. **Add regression test**: Test with `inf` and `nan` inputs; verify they either fail fast (preferred) or fall through without hanging.

**Rationale**: Boundary validation is cleaner than per-component guards; explicit method for TTS speed signals intent.

### Rejected Alternatives

**Alt 1: Rely on ffmpeg to reject bad values**
- Pros: Minimal changes to TUSK code.
- Cons: Doesn't help with infinite loop (ffmpeg never reached). Defers error detection to runtime.
- **Rejected**: Doesn't solve the hang.

**Alt 2: Bounds-check inside _atempo_filter_chain only**
- Pros: Localized fix.
- Cons: Still allows `inf`/`nan` to reach SpeechPlayback; no early error signal. Doesn't prevent nan→atempo=nan fallback.
- **Rejected**: Doesn't address root cause in ConfigFactory.

**Alt 3: Skip atempo filter entirely for edge cases**
- Pros: Simplest code.
- Cons: Silent fallback (user sets `TTS_SPEED=2.0`, expects 2x, gets 1x for invalid input). Confusing.
- **Rejected**: Fails user intent.

## Key Files and Implementation Scope

| File | Role | Change |
|---|---|---|
| `tusk/shared/config/config_factory.py` | Configuration parsing | Guard `_float` or add `_tts_speed` method |
| `tusk/shared/config/config.py` | Config dataclass | Add `tts_speed: float` field |
| `shells/voice/stages/speech_playback.py` | Audio playback | Add `__init__(speed)`, `_atempo_filter_chain(speed)`, integrate ffmpeg |
| `shell_loader.py` | Dependency wiring | Pass `config.tts_speed` to `SpeechPlayback` |
| `tests/shells/voice/test_speech_playback.py` | Unit tests | Add timeout-based regression tests for inf/nan |

## Rules Worth Knowing

- **atempo bounds**: ffmpeg atempo filter accepts 0.5–2.0 natively; larger ranges require chaining (e.g., 4.0 = 2.0 × 2.0).
- **Second loop guard**: The existing comment notes zero/negative speeds would never terminate the second loop; the first loop has no such guard.
- **Fallback behavior**: If ffmpeg rejects the filter or exits with error, existing code should fall back to unstretched audio (catching the subprocess exception).
- **InterruptToken**: Speed adjustment doesn't change interrupt semantics; token is still polled by SpeechPlayback._await().

---
**Last updated**: 2026-07-29 · **Status**: Architecture Analysis · **Issue**: #77
