# Architecture Analysis — Issue #77: TTS_SPEED=inf Infinite Loop

## Issue Summary

`SpeechPlayback._atempo_filter_chain(speed)` enters an infinite loop and hangs the voice shell when `TTS_SPEED=inf` is set. The method breaks down an arbitrary playback speed into chained ffmpeg `atempo` filters (each capped at 2.0x), using two while loops. The first loop terminates for all finite speeds but never exits when `remaining` is infinity, because `inf / 2.0 == inf`.

A second loop has a guard (`0.0 < remaining < 0.5`) against zero/negative speeds, which would cause an equivalent hang. The first loop lacks this guard.

Configuration accepts infinity through an unguarded `float()` parse in `ConfigFactory._float()`, allowing `TTS_SPEED=inf` to reach playback.

## Components Affected And How They Fit Together

```
ConfigFactory (env vars)
    ↓ _float("TTS_SPEED", "1.0")
    → accepts float('inf'), float('nan'), any numeric string
    ↓
Config (frozen dataclass)
    ↓ tts_speed: float field
    ↓
ShellLoader._build_worker()
    ↓ self._config.tts_speed
    ↓
SpeechPlayback.__init__(speed=...)
    ↓ self._speed = speed (stored once at construction)
    ↓
SpeechPlayback.play(wav_bytes)
    ↓ if self._speed != 1.0: self._stretch(wav_bytes)
    ↓
SpeechPlayback._stretch(wav_bytes)
    ↓
SpeechPlayback._run_ffmpeg(wav_bytes)
    ↓
SpeechPlayback._spawn_ffmpeg()
    ↓ filter_chain = self._atempo_filter_chain(self._speed)
    ↓
SpeechPlayback._atempo_filter_chain(speed) ← **BUG HERE**
```

**Data Flow for Problematic Input:**

```
TTS_SPEED=inf (environment)
    ↓ float("inf")
    ↓ ConfigFactory._float("TTS_SPEED", "1.0") → inf
    ↓ Config.tts_speed = inf
    ↓ ShellLoader passes inf to SpeechPlayback
    ↓ SpeechPlayback stores speed=inf
    ↓ play() → _stretch() → _run_ffmpeg() → _spawn_ffmpeg() → _atempo_filter_chain(inf)
    ↓
    INFINITE LOOP:
        remaining = inf
        while remaining > 2.0:  # inf > 2.0 is True
            factors.append(2.0)
            remaining /= 2.0     # inf / 2.0 == inf
        # Loop never exits, memory fills with factors
```

### Key Architectural Elements

1. **`ConfigFactory._float(name, default)`** (line 22–23 in config_factory.py):
   - Parses `os.environ.get(name, default)` as a float
   - **No validation**: accepts `float('inf')`, `float('nan')`, negative, zero, etc.
   - Call site: `_audio_values()` → `"tts_speed": self._float("TTS_SPEED", "1.0")`
   - No range checking or finite-value guard

2. **`Config.tts_speed: float`** (frozen dataclass):
   - Stores the parsed value for the lifetime of the shell session
   - Once set, cannot be changed; the value is applied to every TTS playback

3. **`ShellLoader._build_worker()`**:
   - Constructs the audio pipeline: `GroqTTS` → `ChunkedSpeaker` → `SpeechPlayback`
   - Passes `self._config.tts_speed` directly to `SpeechPlayback.__init__(..., speed=...)`
   - No validation or bounds-checking at handoff

4. **`SpeechPlayback.__init__(speed=1.0)`**:
   - Stores speed as `self._speed`
   - Speed is captured once at construction; every call to `play()` uses the same speed
   - No runtime validation of the stored speed

5. **`SpeechPlayback.play(wav_bytes)`**:
   - Fast path: if `self._speed == 1.0`, pipes raw bytes to `paplay` (no processing)
   - Slow path: if `self._speed != 1.0`, calls `self._stretch()`, which invokes ffmpeg

6. **`SpeechPlayback._atempo_filter_chain(speed: float) -> str`**:
   - Decomposes an arbitrary speed into chained `atempo=X` filters
   - `atempo` filter's native range is 0.5–2.0; speeds outside that range must be chained
   - **Implementation**:
     ```python
     factors = []
     remaining = speed
     while remaining > 2.0:                           # ← BUG: no upper guard
         factors.append(2.0)
         remaining /= 2.0
     while 0.0 < remaining < 0.5:                    # ← GUARDED against non-positive
         factors.append(0.5)
         remaining /= 0.5
     factors.append(remaining)
     return ",".join(f"atempo={factor}" for factor in factors)
     ```
   - **The Bug**: First loop hangs when `remaining` is infinity
     - `inf > 2.0` → True, enter loop
     - `inf / 2.0` → `inf` (identity under division)
     - Condition re-evaluates as True, loop repeats forever
     - `factors` list grows without bound until out-of-memory crash

7. **`SpeechPlayback._run_ffmpeg(wav_bytes)`**:
   - Spawns an ffmpeg subprocess with the filter chain (if the method reaches here)
   - Relies on `_atempo_filter_chain()` to produce a valid filter string
   - **In the hang scenario**: code never reaches here because `_spawn_ffmpeg()` doesn't return

## Integration Points And Contracts Crossed

1. **Environment → `ConfigFactory`**: `TTS_SPEED` env var is read and parsed as a float. Contract: the value must be valid for ffmpeg's `atempo` filter (approximately 0.5 to ≥2.0 for common use). Reality: no contract enforcement; accepts any float-parseable string including `"inf"` and `"nan"`.

2. **`ConfigFactory` → `Config` dataclass**: Parsed float is stored in a frozen dataclass field. Contract: the caller must ensure the value is valid before storing. Reality: no validation, value passes through unchanged.

3. **`Config` → `ShellLoader`**: Configuration is read once at app startup. Contract: the value is constant for the lifetime of the shell. Reality: Config is frozen, so mutation is not possible, but the initial value can be invalid.

4. **`ShellLoader` → `SpeechPlayback`**: Speed is passed to the constructor. Contract: speed must be a positive finite number suitable for audio time-stretching. Reality: no bounds check; invalid values are accepted and stored.

5. **`SpeechPlayback.play()` → `_atempo_filter_chain()`**: Speed is assumed to be numeric and finite. Contract: caller must ensure speed is in a valid range. Reality: no pre-condition check; method is static and receives speed as an argument, making the assumption implicit.

6. **`_atempo_filter_chain()` → ffmpeg filter string**: The method returns a comma-separated list of `atempo=X` filters. Contract: the string must be valid ffmpeg syntax and each factor must satisfy ffmpeg's atempo constraints (0.5–2.0 per spec, though higher multiples can be chained). Reality: the method can hang before ever producing output.

## Risks, Unknowns, Things That Could Break

### Critical Risk: Infinite Loop on Infinity

**Failure scenario**: `TTS_SPEED=inf` → ConfigFactory parses to Python `float('inf')` → stored in Config → passed to SpeechPlayback → when first playback is triggered, `play()` calls `_stretch()` → calls `_atempo_filter_chain(inf)` → first while loop enters with `remaining=inf` → `inf > 2.0` is True, divide by 2.0 yields inf, condition stays True, loop never exits. Process consumes memory appending to `factors` until OOM or crash. Voice shell hangs indefinitely.

**Root cause**: First loop lacks a finite-value guard. Second loop has `0.0 < remaining < 0.5`, which excludes zero, negative, and non-positive values, preventing similar hangs for those cases. First loop has no equivalent guard.

**Secondary exposure**: `ConfigFactory._float()` accepts any value that `float()` can parse, including `float('inf')`, `float('-inf')`, `float('nan')`. NaN doesn't hang but produces `atempo=nan`, which is not sensible.

### Design Risk: Configuration Accepts Invalid Values

`ConfigFactory._float()` is a dumb parser with no semantic knowledge of what range each field should accept. Contrast this with:
- `_int()`: also dumb, but integers are less likely to produce IEEE edge cases
- `_bool()`: has explicit checks (`in ("true", "1", "yes", "on")`)
- `_slot()`: delegates to `LLMSlotConfig.parse()`, which presumably validates structure

`_float()` should have been:
1. A range check at the `_audio_values()` call site (e.g., `_bounded_float("TTS_SPEED", "1.0", min=0.5, max=4.0)`)
2. Or a dedicated `tts_speed` parser that enforces finite positive values
3. Or range checking in `Config.__post_init__()` if using dataclass validators (Python 3.10+)

This pattern (dumb parsing + late validation) creates a window where invalid configuration is silently accepted, then crashes at an unpredictable point deep in the call stack.

### Edge Cases Accepted Today

- `TTS_SPEED=0` → remaining becomes 0, neither loop enters, `factors = [0.0]` → `atempo=0.0` → ffmpeg rejects (invalid speed) → play() catches and falls back to normal speed ✓
- `TTS_SPEED=-5.0` → remaining becomes -5.0, first loop skipped, second loop skipped (condition `0.0 < remaining < 0.5` is False), `factors = [-5.0]` → `atempo=-5.0` → ffmpeg rejects → fallback ✓
- `TTS_SPEED=inf` → HANG ✗
- `TTS_SPEED=-inf` → first loop skipped (`-inf > 2.0` is False), second loop skipped (`0.0 < -inf` is False), `factors = [-inf]` → `atempo=-inf` → ffmpeg behavior unknown, likely rejects → fallback; no hang ✓
- `TTS_SPEED=nan` → first loop enters (`nan > 2.0` is always False in IEEE 754!), second loop enters (`0.0 < nan < 0.5` is always False), `factors = [nan]` → `atempo=nan` → ffmpeg rejects or ignores → no hang but nonsensical ✓

The hang is specific to `+inf` because `inf > 2.0` is True (unlike `nan > 2.0`, which is always False).

### Latency Implications

Currently none — `ChunkedSpeaker.play()` → `SpeechPlayback.play()` → either fast-path (1.0x) or subprocess (ffmpeg + paplay). The hang prevents playback entirely, not just delays it, so latency is moot.

## Approach Chosen And Alternatives Rejected

### Chosen: Validate in `ConfigFactory._float()` or dedicated parser

Add a finite-value guard at the configuration parsing layer:
```python
def _float(self, name: str, default: str) -> float:
    value = float(os.environ.get(name, default))
    if not math.isfinite(value):
        raise ValueError(f"{name}={value} must be a finite number")
    return value
```

Or add a dedicated parser:
```python
def _tts_speed(self) -> float:
    value = self._float("TTS_SPEED", "1.0")
    if value <= 0.0 or not math.isfinite(value):
        raise ValueError(f"TTS_SPEED={value} must be a positive finite number")
    return value
```

**Rationale**:
- **Fails fast**: Invalid configuration is caught at startup (app initialization), not deep in playback
- **Prevents all three cases**: rejects `inf`, `-inf`, and `nan` in one guard
- **Configurable boundary**: if ranges change (e.g., allow 0.1–10.0 in future), the guard is the single source of truth
- **Pattern match**: `_bool()` already does explicit checks; this extends that pattern
- **Zero production overhead**: guard runs once at startup, not on every play() call

### Alternative 1: Guard in `_atempo_filter_chain()` only

Add a finite-value check inside the method:
```python
@staticmethod
def _atempo_filter_chain(speed: float) -> str:
    if not math.isfinite(speed) or speed <= 0.0:
        raise ValueError(f"speed must be a positive finite number, got {speed}")
    # ... rest of logic
```

**Rejected because**:
- Bug manifests deep in the call stack (audio playback), not at configuration time
- Exception is harder to diagnose without context (developer must trace back through ChunkedSpeaker, SpeechPlayback, etc.)
- The root issue is that configuration accepted the invalid value in the first place
- Doesn't follow the principle of "fail fast, fail loud"

### Alternative 2: Guard in `_atempo_filter_chain()` and return fallback

Catch infinity and return a neutral filter string:
```python
@staticmethod
def _atempo_filter_chain(speed: float) -> str:
    if not math.isfinite(speed):
        return ""  # or "atempo=1.0", or raise
    # ... rest
```

**Rejected because**:
- Silently falling back obscures the configuration error; user doesn't know TTS_SPEED was ignored
- Inconsistent with the existing fallback behavior: `_stretch()` catches subprocess failures and returns raw bytes, not silently returning "normal speed" on bad config
- Configuration errors should fail loudly; playback errors should fail gracefully

### Alternative 3: Guard both loops with identical bounds

Add `math.isfinite(remaining)` to both loop conditions:
```python
while remaining > 2.0 and math.isfinite(remaining):
    factors.append(2.0)
    remaining /= 2.0
while 0.0 < remaining < 0.5 and math.isfinite(remaining):
    factors.append(0.5)
    remaining /= 0.5
```

**Rejected because**:
- Fixes the symptom (infinite loop) but not the disease (invalid configuration is accepted)
- Leaves `nan` case unguarded: `nan > 2.0` is False, so the loop doesn't hang, but `atempo=nan` is still nonsensical
- Doesn't prevent OOM crash (although the loop does exit for `nan`)
- Requires runtime checks on every call to `play()`, even when using default speed
- Fails to enforce the invariant that `tts_speed` must be valid; subsequent logic assumes it is

### Alternative 4: Bound the loop differently

Rewrite the loop to not divide:
```python
factors = []
remaining = speed
while remaining > 2.0:
    factors.append(2.0)
    remaining -= 2.0  # Subtract instead of divide
    # ... or: factors.append(min(remaining, 2.0)); remaining -= min(remaining, 2.0)
```

**Rejected because**:
- Misses the mathematical intent: the method is decomposing speed into factors (e.g., 16x = 2.0 * 2.0 * 2.0 * 2.0), not summing steps
- Subtraction would produce incorrect filter chains (e.g., 16x would become `[2.0, 2.0, 2.0, 2.0, ...]` with many small remainders)
- Doesn't solve the configuration issue; just masks it with wrong audio processing

## Invariants This Change Establishes

1. **`Config.tts_speed` is always a positive finite number** (or 1.0 by default). Configuration validation ensures this at startup; no check needed at runtime.

2. **`SpeechPlayback` can assume speed is finite**: no need for defensive checks in `play()`, `_stretch()`, or `_atempo_filter_chain()`. The speed invariant is established upstream.

3. **`_atempo_filter_chain()` terminates for any input**: with positive finite speed guaranteed, both loop conditions eventually become false.

4. **Invalid configuration fails at startup, not during playback**: user sees the error immediately with context ("TTS_SPEED must be..."), not as a mysterious hang or subprocess failure.

## Testing Strategy

**Existing test** (inherited from issue #47, to be fixed in issue #77):
- `tests/shell/test_tts_playback.py::test_atempo_filter_chain_terminates_for_non_positive_speed`
  - Tests that zero and negative speeds don't hang (they don't, because first loop skips them)
  - Verifies fallback to normal speed works

**New tests for issue #77**:
1. **`ConfigFactory` rejects non-finite values**:
   ```python
   def test_config_factory_rejects_infinite_tts_speed():
       os.environ["TTS_SPEED"] = "inf"
       with pytest.raises(ValueError, match="finite"):
           ConfigFactory().build()
   
   def test_config_factory_rejects_nan_tts_speed():
       os.environ["TTS_SPEED"] = "nan"
       with pytest.raises(ValueError, match="finite"):
           ConfigFactory().build()
   ```

2. **`_atempo_filter_chain` terminates for infinity** (if validation is added at method level as a safety net):
   ```python
   def test_atempo_filter_chain_rejects_infinity():
       with pytest.raises(ValueError):
           SpeechPlayback._atempo_filter_chain(float('inf'))
   ```

3. **Playback with default config (1.0x) has no timeout issues**:
   - Existing test; should pass with any fix

4. **Integration test with invalid env var**:
   - Set TTS_SPEED=inf and attempt to start a shell → expect startup failure with diagnostic message
   - Harder to automate (requires forked subprocess), but essential for CI

The test pattern mirrors existing guardrails in the codebase (e.g., `tests/style_guardrails/directory_guardrails.py`).
