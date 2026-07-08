# Spoken Acknowledgment Refrain

## Overview
Before TUSK runs a spoken command, it speaks a brief refrain of what was asked
(e.g. "open gedit and insert a poem" → "Opening gedit and inserting a poem"), so the
user hears the kernel engage instead of waiting in silence for the full result.

## Purpose
The agent run can take several seconds. A short, spoken paraphrase confirms the request
reached the kernel and is being worked on. It is a regular reply on the normal TTS path:
silent when TTS is off, spoken when it is on, and toggleable independently.

## Key Files And Structure
- `shells/voice/stages/gate/command_gate_prompt.py`: instructs the gatekeeper to emit `intent`.
- `shells/voice/stages/gate/gatekeeper_support.py`: `PRIMARY_SCHEMA` includes `intent`; `fallback_dispatch` carries it for conversation turns.
- `shells/voice/stages/gate/gatekeeper_parser.py`: parses `intent` into `GateResult`.
- `tusk/shared/schemas/gate_result.py`, `shells/voice/gate_dispatch.py`: `intent` field.
- `shells/voice/pipeline.py`: forwards `(text, refrain)` to the worker.
- `shells/voice/command_worker.py`: speaks the refrain before `submit` when `ack_enabled`.
- `tusk/shared/config/config_factory.py`: reads `TUSK_ACK`.

## How It Works
1. The gatekeeper already makes one fast LLM call per utterance. It now also returns
   `intent`, a terse present-continuous refrain — a free ride, no extra call, no extra
   hot-path latency.
2. `intent` flows `GateResult` → `GateDispatch` → `VoicePipeline` → `CommandWorker.enqueue(text, refrain)`.
3. On the worker thread, `_announce` speaks the refrain via the existing `_speak` path
   (which is a no-op when the TTS engine is absent), then `submit` runs.

## Important Patterns And Pitfalls
- **Both directed classifications need it.** Commands forward via `_command_dispatch`;
  conversation turns forward via `fallback_dispatch`. Both must attach `intent`, or
  conversational replies lose the refrain.
- **Schema must list `intent`.** `PRIMARY_SCHEMA` uses `additionalProperties: false`; a
  strict structured-output provider would drop `intent` if it is not declared and required.
- **Empty is graceful.** A missing/empty `intent` (e.g. ambient) simply means no refrain.
- **Toggle is worker-side.** `TUSK_ACK` gates speaking; the gatekeeper always requests
  `intent` (negligible cost).

## Testing Strategy
- `tests/test_gatekeeper_parser.py`, `tests/test_command_gate_prompt.py`: `intent` parsing and prompt.
- `tests/test_gatekeeper_support.py`, `tests/test_gatekeeper_follow_up.py`: command and conversation dispatch carry `intent`; schema requires it.
- `tests/test_command_worker_refrain.py`: refrain spoken before submit, skipped when disabled/empty, logged when TTS off.
- `tests/test_pipeline.py`, `tests/test_config_factory.py`: refrain forwarding and `TUSK_ACK` parsing.

## Known Issues Or Future Improvements
- The refrain is spoken serially before `submit` (~1s), not overlapped with the work.
  Add concurrency only if that pre-work pause becomes noticeable.
