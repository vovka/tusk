# Voice latency: speech end → first tool call

Last updated: 2026-10-01

## Measurement

- `LatencyMeter` (`tusk/shared/status/latency_meter.py`) is created in `main.py` and shared by the voice shell and kernel.
- `UtteranceDetector` calls `on_speech_end(seconds_ago)` when it emits an utterance. `seconds_ago` is the trailing
  silence it waited for, so the stamp marks the real end of speech and endpointing is part of the number.
- `ConfirmationGate.execute` (every real tool call goes through it) calls `mark_tool_call()`. The first call after a
  stamp logs `latency speech_end→first_tool_call: N ms` (log group `latency`) and pushes the rolling median (last 20)
  through `StatusReporter.set_latency_median_ms` into the tray tooltip ("median latency 1.4 s").
- Utterances that never reach a tool (conversation, ambient) leave a stamp that the next utterance overwrites.

## Hot path

1. VAD endpointing: `VAD_SILENCE_MS` of trailing silence (was a hard-coded 600 ms, now 400 ms by default).
2. Groq STT (`whisper-large-v3-turbo`, `language="en"`).
3. Gate LLM (`GATEKEEPER_LLM`, llama-3.1-8b-instant). The recovery LLM call only runs for non-commands.
4. Command agent LLM (`COMMAND_AGENT_LLM`, gpt-oss-120b) with all planner-visible tools (~5.8 kB of schemas,
   ~0.7 kB system prompt). In the profile it always called a real tool directly: no planner/run_agent hops.

## Numbers (offline, real Groq calls in Docker, fake recording tools, no desktop)

Medians; command figures over 5 commands × 3 runs (open Firefox, maximize terminal, ctrl+s, type text, workspace).

| Stage | Before | After |
| --- | --- | --- |
| Endpoint silence | 600 ms (fixed) | 400 ms (fixed) |
| STT | 1116 ms (610–1421) | 519 ms (262–924) |
| Gate LLM | 552 ms (497–737) | 530 ms (504–724) |
| Command LLM → first tool | 1867 ms (466–9220) | 469 ms (221–2548) |

Only the endpoint change (−200 ms) and the removed retry hop are code effects. The STT and command differences
between runs are Groq variance: other "before" runs of the same command set gave medians of 903, 557 and 3718 ms.
Sporadic 7–15 s calls happened even for a trivial `done` call, so the tail is queueing at Groq, not prompt size.

## Changes

- `VAD_SILENCE_MS` (default 400). Raise it if people get cut off mid-sentence.
- The dispatcher resolves a tool name missing its adapter prefix (`switch_workspace` → `gnome.switch_workspace`)
  when exactly one tool matches. Before, the model hit "unknown tool" and retried, costing one extra LLM call
  (0.3–9 s). It happened in 4 of 10 workspace commands.

## Tried, no gain

- `reasoning_effort=low` for gpt-oss: median 3718 ms in that run, no visible tail reduction.
- `COMMAND_AGENT_LLM=groq/openai/gpt-oss-20b`: median 6332 ms vs 557 ms for 120b in back-to-back runs.
- Trimming tool schemas: they are already terse (one-line descriptions), about 1.5k tokens in total.
- STT and gate can't run in parallel: the gate needs the transcript.

## What remains (why ≤1 s is not reached)

The path is three serial network calls (STT ~0.5 s, gate ~0.5 s, command ~0.5 s) plus 0.4 s endpointing, so it
takes about 1.9 s on a good Groq day. Getting to ≤1 s needs riskier changes:
- Skip the gate LLM when the transcript starts with the wake word ("Tusk, …"), saving about 0.5 s on explicit
  commands.
- Start the command agent speculatively in parallel with the gate and drop the result if the gate says
  non-command.
- Use streaming/local STT, or a local gate classifier.
- Find a provider or model with steadier time-to-first-token. The multi-second tail comes from Groq, not from code.
