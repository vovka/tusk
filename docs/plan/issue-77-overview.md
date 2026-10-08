# Plan Overview — Issue #77: `TTS_SPEED=inf` hangs the voice shell

## What's changing

Voice playback can be sped up or slowed down through the `TTS_SPEED` setting, which is
turned into an `ffmpeg` filter before each utterance is played; today, setting it to an
infinite value freezes that preparation step in an unbounded loop, which grows memory until
the whole voice-shell process is killed rather than just producing a bad or rejected speed
value. This plan closes that loop so an infinite speed setting fails to build a filter and is
rejected the same way already-handled bad settings (like zero or negative speed) are, instead
of spinning forever — no new configuration validation is introduced, and every currently
working speed setting keeps behaving exactly as it does today. Because the speed-control
feature this bug lives in hasn't reached `main` yet (it's on a separate, not-yet-merged
branch for issue #47), this fix is written against that branch's code and needs to land
together with it rather than as a standalone change to what's on `main` right now.

## Invariants

- Preparing the speed filter for playback always finishes in bounded time, for any speed
  setting — no value can make it loop forever.
- Every speed setting that already worked correctly continues to produce exactly the same
  result as before.
- An infinite speed setting is treated as an unusable value at playback time, the same way
  an already-unusable setting (zero, negative, or not-a-number) is: it's rejected further
  downstream and playback falls back to the original, unstretched audio, rather than being
  caught earlier by new validation.
