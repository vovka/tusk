# Issue-77 Architecture: TTS Speed Infinity Hang

## Overview

Issue-77 is a critical bug where setting `TTS_SPEED=inf` causes `SpeechPlayback._atempo_filter_chain()` to enter an infinite loop, eventually exhausting process memory. The bug is rooted in two separate validation gaps: (1) unguarded float parsing in `ConfigFactory._float()` allows non-finite values through configuration, and (2) the first loop in `_atempo_filter_chain()` lacks a termination guard that exists in the second loop.

---

## Components Affected

### 1. ConfigFactory (`tusk/shared/config/config_factory.py`)

**Current implementation:**
```python
def _float(self, name: str, default: str) -> float:
    return float(os.environ.get(name, default))
```

**Issue:** Accepts any value parseable by Python's `float()`, including `"inf"`, `"-inf"`, and `"nan"`. These are valid Python floats but meaningless in audio processing context.

**Where it's used:**
- `_audio_values()` line 76: `"tts_speed": self._float("TTS_SPEED", "1.0"),`
- Also used for: `FOLLOW_UP_TIMEOUT_SECONDS`, `MAX_FOLLOW_UP_TIMEOUT_SECONDS`, `GATE_RECOVERY_WINDOW_SECONDS`

**Risk:** Configuration parsing is the system boundary where external input (environment) meets trusted code. Accepting invalid values here delays error detection until runtime (audio playback), making the failure harder to diagnose.

### 2. SpeechPlayback (`shells/voice/stages/speech_playback.py`)

**Current state (main branch):** The class exists but lacks speed parameter and audio stretching logic.

**Expected state (from issue-47/implementation branch):**
```python
class SpeechPlayback:
    def __init__(self, interrupt_token: object | None = None, poll_seconds: float = 0.1,
                 speed: float = 1.0) -> None:
        self._speed = speed
        ...

    def _atempo_filter_chain(speed: float) -> str:
        factors = []
        remaining = speed
        while remaining > 2.0:        # ← BUG: No guard against infinity
            factors.append(2.0)
            remaining /= 2.0
        while 0.0 < remaining < 0.5:  # ← OK: Guard against non-positive
            factors.append(0.5)
            remaining /= 0.5
        factors.append(remaining)
        return ",".join(f"atempo={factor}" for factor in factors)
```

**The bug:** When `speed = inf`:
- `remaining = inf`
- First loop condition: `inf > 2.0` is `True` (always)
- Inside loop: `remaining /= 2.0` → `inf / 2.0 = inf` (stays infinite)
- Loop never terminates; `factors` list grows unbounded until OOM

**Why the comment is incomplete:** The comment above the loops acknowledges the termination hazard for zero/negative speeds in the second loop (correctly guarded by `0.0 < remaining`), but does not address the analogous hazard in the first loop for values ≥ infinity.

### 3. ShellLoader (`shell_loader.py`)

**Lines 72-76:** Wires configuration to audio playback:
```python
def _build_worker(self) -> CommandWorker:
    tts_engine = GroqTTS(...) if self._config.tts_enabled else None
    token = self._kernel.interrupt_token
    speaker = ChunkedSpeaker(tts_engine, 
                             SpeechPlayback(token, speed=self._config.tts_speed), 
                             self._log, token)
    return CommandWorker(...)
```

**Integration point:** Configuration value flows directly to `SpeechPlayback` constructor. No validation occurs at this boundary.

### 4. ChunkedSpeaker (`shells/voice/stages/chunked_speaker.py`)

**Role:** Orchestrates TTS synthesis and playback. Holds a `SpeechPlayback` instance (dependency injected).

**Impact:** When `SpeechPlayback.play()` hangs, the speaker thread blocks, freezing audio output. User must forcibly interrupt.

---

## Data Flow

```
┌─────────────────────┐
│ Environment Vars    │
│ TTS_SPEED=inf       │
└──────────┬──────────┘
           │
           ↓
┌──────────────────────────────────────┐
│ ConfigFactory.build()                │
│  → _audio_values()                   │
│    → _float("TTS_SPEED", "1.0")      │
│       float("inf") returns inf ✗     │
└──────────┬───────────────────────────┘
           │
           ↓
┌──────────────────────────────────────┐
│ Config object                        │
│ {tts_speed: inf, ...}                │
└──────────┬───────────────────────────┘
           │
           ↓
┌──────────────────────────────────────┐
│ ShellLoader._build_worker()          │
│  → SpeechPlayback(token, speed=inf)  │
└──────────┬───────────────────────────┘
           │
           ↓
┌──────────────────────────────────────┐
│ SpeechPlayback.play(wav_bytes)       │
│  → _stretch(wav_bytes)               │
│    → _run_ffmpeg()                   │
│      → _spawn_ffmpeg()               │
│        → _atempo_filter_chain(inf)   │
└──────────┬───────────────────────────┘
           │
           ↓
┌──────────────────────────────────────┐
│ while remaining > 2.0:               │
│     factors.append(2.0)              │
│     remaining /= 2.0                 │
│ ← INFINITE LOOP, OOM crash ✗         │
└──────────────────────────────────────┘
```

---

## Integration Points & Contracts

### 1. Configuration Boundary (Environment → ConfigFactory)

**Current contract:** No validation. Any string that parses as `float()` succeeds.

**Expected responsibilities:**
- ConfigFactory should reject non-finite values (inf, -inf, nan) for parameters that require finite positive/negative numbers
- Alternatives: Validation could occur at the call site (`_audio_values()`) or downstream (ShellLoader)

### 2. ShellLoader Boundary (Config → SpeechPlayback)

**Current contract:** No validation. Speed value passed directly to SpeechPlayback constructor.

**Expected responsibility:** Either trust config is valid, or add a guard at wiring time.

### 3. SpeechPlayback Boundary (speed parameter → _atempo_filter_chain)

**Current contract (expected):** Speed should be positive and finite.

**Implementation responsibility:** The method should handle edge cases defensively, or reject invalid inputs upfront in `__init__`.

---

## Risks & Invariants

### Invariants that the fix must maintain:

1. **Speed 1.0 skips ffmpeg** (optimization): `speed == 1.0` → no subprocess call
2. **Non-positive speeds fall through to ffmpeg:** Zero and negative speeds reach the ffmpeg subprocess, which rejects them with a sensible error
3. **Finite positive speeds decompose into atempo factors:** The atempo filter supports 0.5–2.0 range natively; values outside are decomposed into chained factors

### Risks introduced by each fix approach:

#### Approach A: Guard the first loop (defensive)
```python
while remaining > 2.0 and remaining != float('inf'):
    factors.append(2.0)
    remaining /= 2.0
```
- **Pros:** Minimal code change; stays close to the second loop's pattern
- **Cons:** Doesn't address NaN; doesn't prevent invalid config from reaching playback; if inf or nan reaches this point, they silently pass through to `factors` and create invalid ffmpeg filter strings like `"atempo=inf"` or `"atempo=nan"`
- **Invariant risk:** Low. Speeds ≥ 2.0 still decompose; speeds that don't fit still reach ffmpeg

#### Approach B: Guard at _atempo_filter_chain() entry (defensive)
```python
@staticmethod
def _atempo_filter_chain(speed: float) -> str:
    if not math.isfinite(speed):
        raise ValueError(f"speed must be finite, got {speed}")
    ...
```
- **Pros:** Catches the bug early; clear error message; documents the contract
- **Cons:** Failure occurs at playback time, not configuration time; postpones error until voice reply starts
- **Invariant risk:** None. Rejects non-finite upfront

#### Approach C: Guard at ConfigFactory (validating entry point)
```python
def _float(self, name: str, default: str) -> float:
    value = float(os.environ.get(name, default))
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value}")
    return value
```
- **Pros:** Catches bad config at startup (fail-fast); error occurs before any playback attempt; single-point validation
- **Cons:** Affects other uses of `_float()` (timeouts, delays); may be too broad if some callers do want to allow inf (e.g., "infinite timeout")
- **Invariant risk:** None. Rejects non-finite upfront

#### Approach D: Guard at tts_speed site in _audio_values() (targeted)
```python
def _audio_values(self) -> dict:
    tts_speed = self._float("TTS_SPEED", "1.0")
    if not (0 < tts_speed <= 2.0):  # or other sensible bounds
        raise ValueError(f"TTS_SPEED must be in (0, 2.0], got {tts_speed}")
    return {
        "tts_speed": tts_speed,
        ...
    }
```
- **Pros:** Targeted to audio speed only; fail-fast at config time; can apply domain-specific bounds (e.g., ffmpeg's actual range limits)
- **Cons:** Duplicates bounds logic if SpeechPlayback also validates
- **Invariant risk:** Low, if bounds are chosen to match atempo's actual range

---

## Testing Strategy

Current `test_atempo_filter_chain_terminates_for_non_positive_speed()` covers zero and negative, but **does not test infinity**. A regression test must be added:

```python
def test_atempo_filter_chain_terminates_for_infinite_speed() -> None:
    # Must not hang; requires a timeout to verify
    result = SpeechPlayback._atempo_filter_chain(float('inf'))
    # Assertion depends on fix approach:
    # - If Approach A/B: result should be valid (inf rejected or decomposed gracefully)
    # - If Approach C/D: should raise ValueError before this test runs
```

Additionally:
- If validation is added at ConfigFactory or ShellLoader, test that `TTS_SPEED=inf` raises an error at startup
- Regression test for `TTS_SPEED=nan` (also hangs or produces invalid filter)

---

## Recommended Approach

**Approach D (targeted validation at _audio_values())** provides the best balance:

1. **Fail-fast at configuration time** (startup), before any playback attempt
2. **Minimal scope** (affects only audio speed, not other float configs like timeouts)
3. **Testable** (config construction can be unit-tested without spawning audio processes)
4. **Explicit** (bounds documented in one place; readers can understand the contract)
5. **Defensive in depth** (even if config is somehow bypassed, Approach B guard at SpeechPlayback handles it)

A follow-up can add Approach B (guard in `_atempo_filter_chain()`) as a defensive layer if SpeechPlayback is ever instantiated outside this loader path.

---

## Files to Change

1. **`tusk/shared/config/config_factory.py`:** Add validation in `_audio_values()` for `tts_speed`
2. **`shells/voice/stages/speech_playback.py`:** (Already part of issue-47; include Approach B guard in this issue if adopting defensive depth)
3. **`tests/shared/test_config_factory.py`:** Add test for TTS_SPEED invalid values (inf, nan, negative, zero)
4. **`tests/shells/voice/test_speech_playback.py`:** Add timeout-based regression test for infinity

---

## References

- **Issue-47 diff:** Introduced `_atempo_filter_chain()` and speed parameter
- **Related issue:** Automated review of #47 diff caught the guard for non-positive speeds but missed infinity
- **Prior art:** Second loop in `_atempo_filter_chain()` already demonstrates the defensive pattern with `0.0 < remaining < 0.5`
