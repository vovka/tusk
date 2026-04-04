# TUSK — Task Unified Speech Kernel

An always-listening desktop AI voice assistant for Linux/GNOME.

## Demo

https://github.com/user-attachments/assets/f3990dbc-00ba-4a89-81d9-af1919ff2f6d

Click the preview image to open the demo video.

## How it works

1. The **voice shell** captures microphone audio, runs VAD, and feeds speech segments to the kernel. The **CLI shell** accepts typed text directly.
2. The **hallucination filter** rejects STT artifacts (ghost phrases, sub-400 ms segments, punctuation-only output).
3. The **gatekeeper** classifies the utterance as `command`, `conversation`, or `ambient` (discarded) using a fast LLM with structured output.
4. The **conversation agent** maintains dialogue history and calls `execute_task` when a desktop action or dictation is needed.
5. The **planner** receives a compact `name: description` catalog of all registered tools and returns a JSON list of tool names required for the task.
6. The **execution agent** receives only the selected tool schemas and drives an MCP tool-call loop against the desktop adapter.
7. **MCP adapters** (`adapters/gnome`, `adapters/dictation`) run as out-of-process stdio servers, hot-plugged at startup via `adapter.json` manifests.

The agent request is intentionally compact — no full desktop snapshot or complete tool schema set is sent on each
request. The planner selects only the tools needed per task, keeping each LLM call focused and low-latency.

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
| `PLANNER_LLM` | `groq/openai/gpt-oss-20b` | Strict-schema planner model for one-shot tool subset selection (`provider/model`) |
| `AGENT_LLM` | `groq/openai/gpt-oss-120b` | Capable model for the main agent (`provider/model`) |
| `UTILITY_LLM` | `groq/llama-3.3-70b-versatile` | Model for summaries and text cleanup (`provider/model`) |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model: `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate (Hz) |
| `AUDIO_FRAME_DURATION_MS` | `30` | VAD frame size in ms (`10`, `20`, or `30`) |
| `VAD_AGGRESSIVENESS` | `2` | VAD sensitivity: `0` (least) to `3` (most aggressive) |
| `FOLLOW_UP_TIMEOUT_SECONDS` | `30` | Base seconds for the adaptive follow-up window |
| `MAX_FOLLOW_UP_TIMEOUT_SECONDS` | `120` | Maximum seconds for the adaptive follow-up window |
| `TUSK_SHELLS` | `voice` | Comma-separated shells to start (`voice`, `cli`) |
| `TUSK_ADAPTER_ENV_CACHE_DIR` | `.tusk_runtime/adapters` | Cache for managed adapter environments |

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
├── tusk/
│   ├── kernel/         # Business logic: pipeline, agents, gatekeeper, planner, tool registry
│   └── lib/            # Infrastructure: LLM providers, STT providers, MCP client, config
│       ├── llm/        # LLMProxy, LLMRegistry, retry, provider implementations
│       ├── stt/        # STT ABC, GroqSTT, WhisperSTT
│       ├── mcp/        # MCPClient (stdio JSON-RPC 2.0)
│       └── config/     # Config dataclass, ConfigFactory (env vars)
├── shells/
│   ├── voice/          # AudioCapture, UtteranceDetector (VAD), VoiceShell
│   └── cli/            # CliShell (REPL)
├── adapters/
│   ├── gnome/          # GNOME desktop MCP server (21 tools: windows, input, mouse, clipboard)
│   └── dictation/      # Dictation refinement MCP server
└── main.py             # Startup wiring: build kernel, attach shells, run adapters
```

See `docs/brief.md` for the project vision, `docs/architecture.md` for the current runtime
architecture, and `docs/specification.md` for the concrete technical contract.

The current runtime uses a planner/executor split:

- No automatic desktop snapshot is injected into the agent conversation
- The conversation agent sees only `execute_task` plus terminal tools
- The planner sees the full tool catalog as compact text only
- The execution agent sees only the selected native tool schemas for the current task
- If execution lacks capability, it returns `need_tools` and the kernel replans with the missing capability

## Not Yet Implemented

The following features are described in the project vision (`docs/brief.md`) but are not
yet implemented:

- **Sub-agents subsystem** — the main agent cannot spawn sub-agents for complex or parallel tasks
- **Dangerous action registry / confirmation prompts** — no safety confirmation before destructive actions
- **Configurable master prompt / personality** — the agent system prompt is hardcoded
- **Cross-session memory** — conversation history is in-memory only, lost on restart

The following items from the original vision have been resolved:

- **Extension API / runtime discovery** — resolved via MCP adapter model (`adapter.json` manifests, stdio JSON-RPC, hot-plug at startup)
