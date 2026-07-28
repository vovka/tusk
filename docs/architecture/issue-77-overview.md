# Issue-77: Fix TTS Speed Infinity Hang

## What's Changing

When a user sets `TTS_SPEED=inf` (or `nan`) via environment variable, TUSK hangs in an infinite loop during audio playback, eventually consuming all available memory. The fix adds validation at configuration startup to reject non-finite TTS speed values, failing immediately with a clear error message rather than hanging during playback. The configuration layer now refuses to accept infinity or NaN, and as a defensive layer, the audio playback code also guards against non-finite speeds so that invalid values cannot silently corrupt the ffmpeg filter chain.

---

## Invariants

The fix establishes and maintains:

1. **Configuration fails fast at startup** for invalid TTS speed (non-finite or out-of-range values), before any voice interaction
2. **TTS speed 1.0 optimization holds** — speed of 1.0 continues to skip ffmpeg processing entirely  
3. **Non-positive speeds remain handled as designed** — zero and negative speeds fall through to ffmpeg, which rejects them and triggers fallback to normal playback
4. **Valid finite speeds decompose correctly** — positive finite speeds continue to decompose into atempo factors as implemented in issue-47
5. **ffmpeg filter chains never contain inf or nan tokens** — even if invalid config somehow bypasses startup validation, playback code guards against it

---

## No Process/External System Changes

This fix is purely internal: configuration validation and audio processing logic. No new processes, external systems, or daemon interactions are introduced. The system block diagram and integration with ffmpeg subprocess remain unchanged.
