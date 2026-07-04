# Voice Shell

The voice shell is a composable six-stage pipeline that converts raw microphone audio into
a text command delivered to `CommandWorker`, which calls `kernel.submit(text)` off the
capture path. Each stage has one responsibility and passes its result forward or drops it.

Capture and VAD run on a producer thread feeding a queue (sub-millisecond handoff); STT,
gatekeeper, and dispatch run on the consumer; agent/TTS work runs on `CommandWorker`, so
speech during an agent run is still captured and classified.

---

## Pipeline Diagram

```
Microphone
    │  PCM frames
    ▼
┌──────────┐
│  Audio   │
└────┬─────┘
     │ Utterance (PCM)
     ▼
┌──────────┐
│ Detector │  VAD + boundary buffering
└────┬─────┘
     │ Utterance (PCM)              ← DROP: silence
     ▼
┌─────────────┐
│ Transcriber │  STT engine
└──────┬──────┘
       │ Utterance (text)
       ▼
┌───────────┐
│ Sanitizer │  hallucination filter ← DROP: phantom/ghost phrase
└─────┬─────┘
      │ Utterance (clean)
      ▼
┌────────┐
│ Buffer │  rolling window + gate-state tracking
└───┬────┘  (pending → forwarded | dropped | recovered | consumed)
    │ BufferedUtterance + recent[] + recoverable candidates[]
    ▼
┌─────────────┐
│ Gatekeeper  │  primary LLM classify
└──────┬──────┘
       │
       ├─ command ─────────────────────────────── CommandWorker.enqueue(text)
       │
       ├─ conversation + wake word ────────────── CommandWorker.enqueue(text)
       │
       ├─ ambiguous → recovery LLM call over dropped candidates
       │       ├─ recover ──────────── CommandWorker.enqueue(prior text)
       │       ├─ ambiguous ─────────── CommandWorker.enqueue(current text)
       │       └─ none ───────────────────────────────── DROP
       │
       ├─ interrupt ─────────── request_interrupt() + flush queued commands
       │
       └─ ambient ────────────────────────────────────── DROP

CommandWorker ── kernel.submit(text) ── reply ── optional TTS/SpeechPlayback
```

**Drop points:**

| Stage | Drop reason |
|---|---|
| Detector | Silence / below VAD threshold |
| Sanitizer | Hallucinated or ghost phrase |
| Gatekeeper (primary) | Ambient speech — no wake word, no command intent |
| Gatekeeper (recovery) | Ambiguous but no recoverable candidate identified |

---

## Stages

### Audio (`stages/audio_capture.py`)

Captures raw PCM from the system microphone at a configured sample rate and frame duration.
Yields fixed-size byte frames consumed by the Detector.

### Detector (`stages/utterance_detector.py`)

Runs WebRTC VAD on each frame and buffers frames while speech is active. Emits an
`Utterance` (PCM bytes + metadata) when speech ends. VAD and boundary detection are one
stage because frame classification and boundary buffering are tightly coupled — splitting
them would require shared mutable state.

### Transcriber (`stages/transcriber.py`)

Passes the PCM utterance to an `STTEngine` (injected, implements the shared ABC). Returns
the same `Utterance` enriched with transcribed text and confidence. Swapping the STT
provider requires only a different `STTEngine` instance at startup.

### Sanitizer (`stages/sanitizer.py`)

Provider-agnostic hallucination and ghost-phrase filter. Drops utterances whose text matches
known phantom outputs from STT engines (e.g., "Thank you for watching", blank transcriptions).
Extracted from individual STT implementations so every provider benefits.

### Buffer (`stages/transcription_buffer.py`)

Rolling window of all surviving utterances. Every clean utterance is appended. The Gatekeeper
reads the last N utterances via `recent(n)` to build context for its classification prompt.
The buffer also tracks gate state for each utterance (`pending`, `forwarded`, `dropped`,
`recovered`, `consumed`). Recent utterances dropped by the gatekeeper remain eligible for
retrospective recovery within a bounded window, so a later correction like "that previous
one was for TUSK" can recover the earlier dropped text. Implements `TranscriptionBuffer`
ABC (`interfaces/transcription_buffer.py`).

### Gatekeeper (`stages/gatekeeper.py`)

Cheap LLM call that classifies each utterance as `command`, `conversation`, `ambient`, or
`interrupt`. Commands/conversations are enqueued; interrupts set the shared interrupt token;
ambient speech is dropped. Implements `Gatekeeper` ABC (`interfaces/gatekeeper.py`).

**Follow-up window** — the gatekeeper tracks `_last_forwarded_at` internally. When it
forwarded something recently (within `follow_up_window_seconds`, default 30 s), it includes
recent context in the classification prompt so conversational follow-ups work without a
wake word. No external clock or side channel is involved; the pipeline is fully linear.

**Retrospective recovery** — when the current utterance is not a clear command, the
gatekeeper can make one extra structured LLM call over recent dropped candidates from the
buffer. If it can identify exactly one earlier dropped utterance, it forwards that prior
text to the kernel instead of the current correction phrase.

---

## Assembly

`VoiceShell` builds the pipeline in `_build_pipeline`; `CommandWorker.start(submit)` owns
the kernel callback. `VoicePipeline.run()` drives the capture/dispatch loop:

```python
for utterance in detector.stream_utterances():
    transcribed = transcriber.process(utterance)
    sanitized   = sanitizer.process(transcribed)             # None → drop
    if sanitized is None: continue
    buffered    = buffer.process(sanitized)                  # BufferedUtterance
    recent      = buffer.recent(7)[:-1]                      # context window
    candidates  = buffer.recoverable(limit, window)          # dropped, age-bounded
    dispatch    = gatekeeper.process(buffered, recent, candidates)  # GateDispatch
    # PipelineDispatcher marks buffer state, enqueues commands, or requests interrupt
```

`GateDispatch.action` values: `forward_current`, `forward_recovered`, `forward_clarification`,
`interrupt`, `drop`.

Stages are injected into `VoicePipeline` as plain objects. Any stage can be replaced with
a test double or an alternative implementation without touching the others.

---

## Interfaces

| ABC | File | Key methods |
|---|---|---|
| `Gatekeeper` | `interfaces/gatekeeper.py` | `evaluate(utterance, recent)`, `process(utterance, recent, candidates) → GateDispatch` |
| `TranscriptionBuffer` | `interfaces/transcription_buffer.py` | `process(utterance) → BufferedUtterance`, `recent(n)`, `recoverable(n, secs)`, `mark_*(id)` |

---

## Directory Layout

```
shells/voice/
├── command_worker.py        # CommandWorker — async submit/TTS worker
├── pipeline.py              # VoicePipeline — captures and consumes utterances
├── pipeline_dispatcher.py   # PipelineDispatcher — queue/drop/interrupt dispatch
├── playback_gate.py         # PlaybackGate — stop-vs-echo classifier while speaking
├── queued_command.py        # QueuedCommand — deferred interrupt-clear state
├── voice_shell.py           # VoiceShell — entry point, builds pipeline, pause/resume
├── buffered_utterance.py    # BufferedUtterance — Utterance + id + gate_state
├── gate_dispatch.py         # GateDispatch — action + text + recovered_id
├── gatekeeper_slot.py       # GatekeeperSlot — swaps active mode gatekeeper
├── recovery_decision.py     # RecoveryDecision — action + candidate_id + reason
├── interfaces/
│   ├── gatekeeper.py        # Gatekeeper ABC
│   └── transcription_buffer.py  # TranscriptionBuffer ABC
└── stages/
    ├── audio_capture.py         # AudioCapture — raw PCM from microphone
    ├── utterance_detector.py    # UtteranceDetector — VAD + boundary buffering
    ├── transcriber.py           # Transcriber — wraps STTEngine
    ├── speech_playback.py       # SpeechPlayback — interruptible paplay wrapper
    ├── sanitizer.py             # Sanitizer — hallucination filter
    ├── transcription_buffer.py  # TranscriptionBuffer — rolling window + state tracking
    ├── gatekeeper.py            # LLMGatekeeper — primary classify + recovery
    ├── gatekeeper_parser.py     # JSON parsing for gate and recovery LLM responses
    ├── gatekeeper_support.py    # Helpers: schemas, dispatch builders, wake-word check
    ├── command_gate_prompt.py   # Prompt builder for the primary classification call
    ├── recovery_gate_prompt.py  # Prompt builder for the recovery LLM call
    └── recent_context_formatter.py  # Formats recent utterances for context
```

---

## Dependencies

The voice shell depends only on the **shared** layer:

- `tusk.shared.schemas` — `Utterance`, `GateResult`
- `tusk.shared.llm` — `LLMProvider` ABC (used by `LLMGatekeeper`)
- `tusk.shared.logging` — `LogPrinter` ABC
- `tusk.shared.stt` — `STTEngine` ABC (injected into `Transcriber`)

It does **not** import from `tusk.kernel`. The kernel is reached only through the
`submit(text)` callable passed to `VoiceShell.start()`.
