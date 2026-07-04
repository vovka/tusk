# Voice Interrupt (Immediate Semantic Stop)

## Overview
Stop TUSK by voice, in any wording, while it executes a task or reads a reply aloud; it becomes ready for the next command immediately.

## Purpose
Long agent turns (3 LLM profiles + MCP tools) and long TTS replies used to be uninterruptible: the pipeline consumer thread ran STT → gatekeeper → submit → TTS serially, and the mic was hard-muted during playback.

## Key Files & Structure
- `tusk/shared/interrupt/interrupt_token.py` — `InterruptToken`, shared cooperative-cancellation flag (threading.Event wrapper)
- `shells/voice/command_worker.py` — `CommandWorker`: daemon thread + queue; runs `kernel.submit` + TTS + playback off the consumer thread; `enqueue/flush/is_busy/current_speech_text`; clears token at job start
- `shells/voice/playback_gate.py` — `Gatekeeper` decorator: while speaking, forward-all modes (dictation/coding) only interrupt-or-drop
- `shells/voice/stages/speech_stop_gate.py` — `SpeechStopGate`: yes/no LLM classifier "does this utterance ask TUSK to stop?" with the spoken text as context
- `shells/voice/stages/speech_playback.py` — `paplay` via Popen; polls token every 100 ms; `terminate()` cuts speech mid-word
- `shells/voice/stages/command_gate_prompt.py` — busy clause (stop intent → `interrupt`) and speaking clause (echoes of the spoken sentence → ambient)
- `shells/voice/stages/gatekeeper.py` + `gate_llm_client.py` — busy-aware `LLMGatekeeper`; LLM call/parse plumbing extracted to `GateLLMClient`
- `tusk/kernel/api.py` — `request_interrupt()`, `interrupt_token` property
- `tusk/kernel/agent/agent_runtime.py` — token check at each `_loop` step top → `AgentResult(status="cancelled")`
- `tusk/kernel/agent/tool_sequence_executor.py` — token check between sequence steps
- `tusk/shared/llm/llm_retry_runner.py` — token aborts pending retries
- `tusk/kernel/main_agent.py` — cancelled → reply "Stopped."

## How It Works
```
mic → capture thread → VAD → [consumer] STT → sanitize → buffer → gatekeeper
      (busy/speaking-aware prompt; PlaybackGate in coding/dictation)
        ├─ "interrupt" → kernel.request_interrupt() + worker.flush()
        └─ "command"   → CommandWorker.enqueue(text)
                              ▼ (worker thread)
              kernel.submit → AgentRuntime (token per step)
              then TTS → SpeechPlayback (token polled → paplay killed)
```
- Interrupt is honored only while the worker is busy; an idle "stop" keeps normal classification.
- Commands spoken while busy are queued and run in order (user decision); `flush()` drops them on interrupt.
- Step-boundary cancellation (user decision): in-flight LLM/tool calls finish, results discarded (~1.5–3.5 s); playback stop is near-instant.

## Important Patterns & Conventions
- **Echo defense is semantic, not acoustic**: the gatekeeper prompt contains the exact sentence TUSK is speaking; the old `_play_muted` mic mute was removed.
- One `InterruptToken` instance, created in `main.py`, injected everywhere (KernelAPI, AgentOrchestrator → runtime + sequence executor, agent LLM proxies, SpeechPlayback, CommandWorker).
- Gatekeeper/utility LLM slots deliberately get **no** token — they must stay usable while an interrupt is pending.
- `GateDispatch("interrupt")` is a new action string on the frozen dataclass; pipeline handles it first (its `text` is None, so it must precede the drop branch).

## Integration Points
- Wiring lives in `ShellLoader._build_voice/_build_worker/_gatekeeper/_guarded` and `main.py`.
- Mode gates: `DictationGatekeeper`/`CodingGatekeeper` are wrapped in `PlaybackGate` at slot-swap time.

## Testing
`docker compose exec tusk pytest tests/` — see `test_interrupt_token`, `test_speech_playback`, `test_command_worker`, `test_gatekeeper_interrupt`, `test_playback_gate`, `test_speech_stop_gate`, `test_pipeline_interrupt`, `test_voice_shell_worker`, `test_agent_runtime_cancellation`, `test_llm_retry_interrupt`, `test_kernel_api_interrupt`.

## Known Limits / Follow-ups
- Coding-mode edit-driver internals not token-covered (own stop flow exists).
- CLI shell not interruptible; no undo of executed desktop actions.
- Optional env upgrade for speaker bleed: PulseAudio `module-echo-cancel`.

---
**Last updated**: 2026-07-04 · **Updated by**: Claude · **Exploration depth**: Deep
