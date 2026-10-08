# Overview — Issue #77: `TTS_SPEED=inf` hangs the voice shell

Setting the spoken-reply playback speed to an infinite value freezes speech playback forever
and eventually crashes the whole assistant by exhausting memory, instead of being rejected or
falling back to normal-speed playback the way an invalid speed (zero or negative) already
does; the fix closes that one remaining gap so every value that reaches the speed-adjustment
step either produces a working audio filter or fails safely, with no input able to make it
loop indefinitely. Note for the approver: the playback-speed feature this issue concerns is
part of a separate, not-yet-merged change (issue #47); this fix depends on that change landing
first or being merged together with it.

## Invariants This Change Establishes

- Adjusting playback speed for a spoken reply always terminates in bounded time, for every
  possible configured speed value, including infinite or otherwise non-finite ones.
- An unusable or unsupported speed value never crashes or freezes the assistant — it falls
  back to unstretched, normal-speed playback, matching how invalid speeds are already handled.
