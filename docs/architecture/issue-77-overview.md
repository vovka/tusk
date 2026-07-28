# Issue #77 Overview: TTS_SPEED=inf Infinite Loop

## What Is Changing

When `TTS_SPEED=inf` is set, the voice shell enters an infinite loop in audio playback and hangs. The bug is in the `SpeechPlayback._atempo_filter_chain()` method, which decomposes a playback speed into a series of ffmpeg time-stretch filters. The first decomposition loop (`while remaining > 2.0`) has no guard against infinity, so when the speed is infinity, dividing infinity by 2.0 yields infinity again, and the loop never exits. The fix adds a finite-value check at the configuration layer (`ConfigFactory._float()`) to reject invalid speeds (including infinity, negative infinity, and NaN) at application startup, before they can reach playback. This fails fast with a clear error message instead of hanging the app.

## Invariants

1. **`Config.tts_speed` is always a positive finite number** — configuration validation at startup ensures no invalid value ever enters the playback pipeline.

2. **`_atempo_filter_chain()` terminates for any speed it receives** — with finite positive speeds guaranteed by configuration, both loop conditions in the method are guaranteed to eventually become false.

3. **Invalid configuration fails at startup** — if a user sets `TTS_SPEED=inf` or similar, the app exits with a diagnostic error ("TTS_SPEED must be...") rather than hanging inside audio playback.

4. **The 1.0x fast path remains unaffected** — when speed is 1.0 (the default), audio bypasses ffmpeg entirely and pipes directly to the speaker, so configuration validation adds no new latency to the common case.

## No Diagram

This change modifies configuration validation at startup and adds a guard in one filter-building method. It does not add, remove, or reconnect any running process or external system, so no diagram is needed.
