# TUSK — Task Unified Speech Kernel

An always-listening desktop AI voice assistant for Linux/GNOME.

## How it works

```
Microphone → Whisper STT → Gatekeeper LLM → Main Agent LLM → Desktop Action
```

1. Captures microphone audio continuously
2. Detects speech utterances via voice activity detection (VAD)
3. Transcribes each utterance with Whisper (via Groq cloud)
4. A fast gatekeeper LLM filters out ambient speech (only passes commands directed at TUSK)
5. A capable main agent LLM runs a multi-step agentic loop with desktop context and tool calling
6. Actions are executed on your GNOME desktop

**Supported actions:**

- **Window management** — launch, close, focus, maximize, minimize, move/resize windows
- **Input simulation** — press keyboard shortcuts, type text
- **Mouse control** — click, move, drag, scroll
- **Clipboard** — read and write clipboard contents
- **Desktop navigation** — open URLs/files, switch workspaces
- **Dictation mode** — real-time speech-to-text pasting with LLM cleanup
- **AI text transform** — transform selected text (summarize, translate, rewrite)
- **LLM hot-swap** — switch models at runtime by voice

## Prerequisites

- Docker
- A [Groq](https://groq.com) API key
- Linux with GNOME desktop
- PulseAudio or PipeWire-PulseAudio (standard on modern GNOME)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/vovka/tusk.git
cd tusk
```

### 2. Allow Docker to connect to your X11 display

```bash
xhost +local:docker
```

### 3. Create your `.env` file

```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY
```

### 4. Build the Docker image

```bash
docker compose build
```

> First build takes a few minutes — it downloads Whisper model weights (~140 MB for the default `base` model).

## Running

### With Docker Compose (recommended)

```bash
docker compose up
```

To run in the background:

```bash
docker compose up -d
docker compose logs -f   # follow logs
docker compose down      # stop
```

### With plain Docker

```bash
docker run --rm \
  -e GROQ_API_KEY="your_key_here" \
  -e DISPLAY="$DISPLAY" \
  -e PULSE_SERVER="unix:/run/user/1000/pulse/native" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /run/user/1000/pulse/native:/run/user/1000/pulse/native \
  --device /dev/snd \
  tusk
```

Once running, you should see:

```
TUSK listening...
```

## Usage

Speak naturally. TUSK responds to:

- **"Tusk, open Firefox"** — launches Firefox
- **"Tusk, close this window"** — closes the active window
- **"Hey Tusk, launch the terminal"** — opens gnome-terminal
- **"Open gedit"** (no prefix needed for obvious desktop commands)
- **"Tusk, start dictation"** — enters dictation mode, pasting speech as text
- **"Tusk, maximize this window"** — maximizes the active window
- **"Tusk, press ctrl+a"** — sends a keyboard shortcut
- **"Tusk, use Opus for the agent"** — switches the agent LLM at runtime

After a command, TUSK keeps a 30-second follow-up window where you can give contextual
commands without repeating the wake word (e.g., "now close it", "do the same for the other one").

Ambient speech, background conversation, and TV audio are silently discarded by the gatekeeper.

## Configuration

All settings are configured via environment variables:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `OPENROUTER_API_KEY` | `""` | Your OpenRouter API key (optional) |
| `GATEKEEPER_LLM` | `groq/llama-3.1-8b-instant` | Fast model for intent filtering (`provider/model`) |
| `AGENT_LLM` | `groq/openai/gpt-oss-120b` | Capable model for the main agent (`provider/model`) |
| `UTILITY_LLM` | `groq/llama-3.3-70b-versatile` | Model for summaries and text cleanup (`provider/model`) |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model: `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate (Hz) |
| `AUDIO_FRAME_DURATION_MS` | `30` | VAD frame size in ms (`10`, `20`, or `30`) |
| `VAD_AGGRESSIVENESS` | `2` | VAD sensitivity: `0` (least) to `3` (most aggressive) |
| `FOLLOW_UP_TIMEOUT_SECONDS` | `30` | Seconds before follow-up window expires |

### Example: use a smaller/faster Whisper model

```bash
docker run --rm \
  -e GROQ_API_KEY="your_key_here" \
  -e WHISPER_MODEL_SIZE="tiny" \
  -e DISPLAY="$DISPLAY" \
  -e PULSE_SERVER="unix:/run/user/1000/pulse/native" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /run/user/1000/pulse/native:/run/user/1000/pulse/native \
  --device /dev/snd \
  tusk
```

## Troubleshooting

**No audio / "Invalid number of channels" error**

Check that your PulseAudio socket path is correct. On PipeWire systems it may differ:

```bash
ls /run/user/$(id -u)/pulse/native
```

Use the correct path in `-v` and `-e PULSE_SERVER=`.

**"Cannot connect to X server"**

Make sure you ran `xhost +local:docker` before starting the container.

**Commands not recognized**

- Speak clearly and at normal pace
- Try increasing `VAD_AGGRESSIVENESS` to `3` to reduce false utterance detection
- Check the console output — each stage prints what it received

**Actions not executing (wmctrl / xdotool errors)**

The container needs access to your X11 display. Verify with:

```bash
docker run --rm \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  tusk wmctrl -l
```

This should list your open windows.

## Architecture

```
tusk/
├── interfaces/     # Abstract base classes (15 ABCs — extension points)
├── schemas/        # Typed dataclasses (Utterance, ToolCall, ChatMessage, etc.)
├── core/           # Pipeline orchestration, audio, agent, conversation history
├── providers/      # Whisper/Groq STT + Groq/OpenRouter LLM implementations
└── gnome/          # GNOME-specific context, input simulator, clipboard, 19 tools
main.py             # Entry point — wires all components together
```

See `docs/brief.md` for the full project vision and `docs/architecture.md` for the
detailed architecture specification.

## Not Yet Implemented

The following features are described in the project vision (`docs/brief.md`) but are not
yet implemented:

- **Sub-agents subsystem** — the main agent cannot spawn sub-agents for complex or parallel tasks
- **Extension API / runtime discovery** — extensions are hardwired in `main.py`, not discovered or loaded at runtime
- **Dangerous action registry / confirmation prompts** — no safety confirmation before destructive actions
- **Configurable master prompt / personality** — the agent system prompt is hardcoded
- **Screen geometry in desktop context** — not captured by the context provider
- **Workspace layout in desktop context** — not captured by the context provider
- **Cross-session memory** — conversation history is in-memory only, lost on restart
