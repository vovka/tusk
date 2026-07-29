# Issue #77 Overview: TTS Playback Speed Control

## What's Changing

TUSK's speech playback is gaining optional speed control: a new `TTS_SPEED` environment variable will let users adjust playback tempo (e.g., `TTS_SPEED=2.0` for double speed). The implementation inserts ffmpeg's atempo filter between incoming WAV bytes and the paplay audio sink, decomposing arbitrary speeds into chained 2× and 0.5× factors. However, the current code would hang indefinitely if `TTS_SPEED=inf`, and the configuration layer accepts non-finite values (`inf`, `nan`) without validation, allowing bad inputs to corrupt downstream logic.

## Invariants

1. **ConfigFactory must validate numeric inputs** — `_float` should reject non-finite floats (`inf`, `nan`) at the configuration boundary, not deeper in playback logic. Fail fast with a clear error message at startup, not at first speech.

2. **atempo factors must be bounded** — The decomposition loop (`while remaining > 2.0`) must have an upper bound guard (matching the existing lower bound in the second loop) to prevent infinite loops on non-finite inputs. The guard should be explicit (`if not math.isfinite(speed)`) so that future readers see the hazard was reasoned about.

3. **Fallback on ffmpeg error is expected** — If the filter is invalid or ffmpeg exits with an error, playback should fall back to unstretched audio (normal speed). This is already the pattern in the codebase.

4. **Interrupt semantics unchanged** — The `InterruptToken` behavior stays the same; speed adjustment doesn't affect cancellation or polling.

---
**Last updated**: 2026-07-29 · **Status**: Architecture Analysis
