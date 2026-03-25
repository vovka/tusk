# TUSK — Task Unified Speech Kernel

An always-listening desktop AI assistant with a three-layer architecture: kernel, shells, and MCP adapters.

## How it works

```
Shell → Kernel → MCP Adapter
voice shell → STT/gatekeeper/agent → gnome adapter
cli shell   → direct command path   → dictation/desktop adapters
```

1. Shells collect user input (`voice` for always-on audio, `cli` for direct text input)
2. The kernel handles STT, gatekeeping, tool selection, conversation history, and model switching
3. Desktop control and dictation refinement run through hot-pluggable MCP adapters in `adapters/`

The agent request is intentionally compact. TUSK does not pre-send a full desktop snapshot or every tool schema on
each request. Instead, the kernel sends native tool definitions for the broker tools (`find_tools`, `describe_tool`,
`run_tool`) plus the top 3 most-used real tools learned from previous successful executions.

**Supported actions:**

- **Window management** — launch, close, focus, maximize, minimize, move/resize windows
- **Input simulation** — press keyboard shortcuts, type text
- **Mouse control** — click, move, drag, scroll
- **Clipboard** — read and write clipboard contents
- **Desktop navigation** — open URLs/files, switch workspaces
- **Dictation mode** — adapter-driven speech cleanup/refinement applied back through the desktop adapter
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
| `TUSK_SHELLS` | `voice` | Comma-separated shells to start (`voice`, `cli`) |
| `TUSK_ADAPTER_ENV_CACHE_DIR` | `.tusk_runtime/adapters` | Cache for managed adapter environments |
| `TUSK_TOOL_USAGE_FILE` | `.tusk_runtime/tool_usage.json` | Persistent usage stats used to inject the top 3 direct tools into the agent prompt |
| `DICTATION_LLM` | `groq/llama-3.1-8b-instant` | Model used by the dictation adapter |

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
├── tusk/kernel/    # Pure agent/kernel runtime
├── shells/         # Startup-loaded user interfaces
├── adapters/       # MCP servers (gnome, dictation)
└── main.py         # Startup wiring
```

See `docs/brief.md` for the full project vision and `docs/architecture.md` for the
detailed architecture specification.

The current runtime uses a brokered native-tool surface:

- No automatic desktop snapshot is injected into the agent conversation
- Every agent request includes native tool definitions for `find_tools`, `describe_tool`, and `run_tool`
- Every agent request also includes native tool definitions for the top 3 most-used real tools from `TUSK_TOOL_USAGE_FILE`
- Less common tools remain available through brokered lookup and execution

## Not Yet Implemented

The following features are described in the project vision (`docs/brief.md`) but are not
yet implemented:

- **Sub-agents subsystem** — the main agent cannot spawn sub-agents for complex or parallel tasks
- **Dangerous action registry / confirmation prompts** — no safety confirmation before destructive actions
- **Configurable master prompt / personality** — the agent system prompt is hardcoded
- **Cross-session memory** — conversation history is in-memory only, lost on restart
