# Voice Shell

The voice shell is a composable six-stage pipeline that converts raw microphone audio into
a text command delivered to the kernel via `kernel.submit(text)`. Each stage has a single
responsibility and passes its result forward or drops it. A developer can omit any stage by
simply not wiring it into `VoicePipeline`.

---

## Pipeline Diagram

```
Microphone
    │
    ▼
┌─────────┐   PCM frames
│  Audio  │──────────────────────────────────────────────────┐
└─────────┘                                                   │
                                                              ▼
                                                       ┌──────────────┐
                                                       │   Detector   │  VAD + boundary
                                                       └──────┬───────┘  buffering
                                                              │ Utterance
                                                              ▼
                                                       ┌──────────────┐
                                                       │  Transcriber │  STT engine
                                                       └──────┬───────┘
                                                              │ Utterance (text)
                                                              ▼
                                                       ┌──────────────┐
                                                       │  Sanitizer   │  hallucination
                                                       └──────┬───────┘  filter  ─ DROP
                                                              │ Utterance (clean)
                                                              ▼
                                                       ┌──────────────┐
                                                       │    Buffer    │  rolling window
                                                       └──────┬───────┘  of utterances
                                                              │ Utterance + recent context
                                                              ▼
                                                       ┌──────────────┐
                                                       │  Gatekeeper  │  LLM classify
                                                       └──────┬───────┘  ─ DROP (ambient)
                                                              │ command text
                                                              ▼
                                                       kernel.submit(text)
```

**Three drop points:**

| Stage | Drop reason |
|---|---|
| Detector | Silence / below VAD threshold |
| Sanitizer | Hallucinated or ghost phrase |
| Gatekeeper | Ambient speech not directed at TUSK |

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
The buffer also enables retrospective recovery when the user refers back to something said
earlier. Implements `TranscriptionBuffer` ABC (`interfaces/transcription_buffer.py`).

### Gatekeeper (`stages/gatekeeper.py`)

Cheap LLM call that classifies each utterance as `command`, `conversation`, or `ambient`.
Only `command` and `conversation` are forwarded to the kernel; `ambient` is silently dropped.
Implements `Gatekeeper` ABC (`interfaces/gatekeeper.py`).

**Follow-up window** — the gatekeeper tracks `_last_forwarded_at` internally. When it
forwarded something recently (within `follow_up_window_seconds`, default 30 s), it includes
recent context in the classification prompt so conversational follow-ups work without a
wake word. No external clock or side channel is involved; the pipeline is fully linear.

---

## Assembly

`VoiceShell` builds the pipeline in `_build_pipeline` and passes `kernel.submit` as the
callback. `VoicePipeline.run()` drives the loop:

```python
for utterance in detector.stream_utterances():
    transcribed = transcriber.process(utterance)
    sanitized   = sanitizer.process(transcribed)   # None → drop
    buffered    = buffer.process(sanitized)         # None → drop
    command     = gatekeeper.process(buffered, buffer.recent(6))  # None → drop
    submit(command)
```

Stages are injected into `VoicePipeline` as plain objects. Any stage can be replaced with
a test double or an alternative implementation without touching the others.

---

## Interfaces

| ABC | File | Implemented by |
|---|---|---|
| `Gatekeeper` | `interfaces/gatekeeper.py` | `LLMGatekeeper` |
| `TranscriptionBuffer` | `interfaces/transcription_buffer.py` | `TranscriptionBuffer` stage |

---

## Directory Layout

```
shells/voice/
├── pipeline.py            # VoicePipeline — assembles and runs the six stages
├── voice_shell.py         # VoiceShell — entry point, builds pipeline, calls submit()
├── interfaces/
│   ├── gatekeeper.py      # Gatekeeper ABC
│   └── transcription_buffer.py  # TranscriptionBuffer ABC
└── stages/
    ├── audio_capture.py       # AudioCapture — raw PCM from microphone
    ├── utterance_detector.py  # UtteranceDetector — VAD + boundary buffering
    ├── transcriber.py         # Transcriber — wraps STTEngine
    ├── sanitizer.py           # Sanitizer — hallucination filter
    ├── transcription_buffer.py # TranscriptionBuffer — rolling utterance window
    ├── gatekeeper.py          # LLMGatekeeper — LLM-based classification
    ├── command_gate_prompt.py # Prompt builder for the gatekeeper LLM call
    └── recent_context_formatter.py  # Formats recent utterances for the prompt
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
