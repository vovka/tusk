# TUSK — Task Unified Speech Kernel

An always-listening desktop AI voice assistant for Linux/GNOME.

## How it works

```
Microphone → Whisper STT → Gatekeeper LLM → Main Agent LLM → Desktop Action
```

1. Captures microphone audio continuously
2. Detects speech utterances via voice activity detection (VAD)
3. Transcribes each utterance with Whisper
4. A fast gatekeeper LLM filters out ambient speech (only passes commands directed at TUSK)
5. A capable main agent LLM converts the command + desktop context into a semantic action
6. The action is executed on your GNOME desktop

**Supported actions (v1):** launch application, close window

## Prerequisites

- Docker
- An [OpenRouter](https://openrouter.ai) API key
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

### 3. Build the Docker image

```bash
docker build -t tusk .
```

> First build takes a few minutes — it downloads Whisper model weights (~140 MB for the default `base` model).

## Running

```bash
docker run --rm \
  -e OPENROUTER_API_KEY="your_key_here" \
  -e DISPLAY="$DISPLAY" \
  -e PULSE_SERVER="unix:/run/user/1000/pulse/native" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /run/user/1000/pulse/native:/run/user/1000/pulse/native \
  --device /dev/snd \
  tusk
```

Replace `your_key_here` with your OpenRouter API key. Once running, you should see:

```
TUSK listening...
```

## Usage

Speak naturally. TUSK responds to:

- **"Tusk, open Firefox"** → launches Firefox
- **"Tusk, close this window"** → closes the active window
- **"Hey Tusk, launch the terminal"** → opens gnome-terminal
- **"Open gedit"** (no prefix needed for obvious desktop commands)

Ambient speech, background conversation, and TV audio are silently discarded by the gatekeeper.

## Configuration

All settings are configured via environment variables passed to `docker run`:

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `GATEKEEPER_MODEL` | `anthropic/claude-haiku-4-5` | Fast model for intent filtering |
| `MAIN_AGENT_MODEL` | `anthropic/claude-sonnet-4-5` | Capable model for action resolution |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model: `tiny`, `base`, `small`, `medium` |
| `AUDIO_SAMPLE_RATE` | `16000` | Microphone sample rate (Hz) |
| `VAD_AGGRESSIVENESS` | `2` | VAD sensitivity: `0` (least) to `3` (most aggressive) |

### Example: use a smaller/faster Whisper model

```bash
docker run --rm \
  -e OPENROUTER_API_KEY="your_key_here" \
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
├── interfaces/     # Abstract base classes (STTEngine, Gatekeeper, etc.)
├── schemas/        # Typed dataclasses (Utterance, SemanticAction, etc.)
├── core/           # Pipeline orchestration + audio capture/VAD
├── providers/      # Whisper STT + OpenRouter LLM implementations
└── gnome/          # GNOME-specific context provider + action executor
main.py             # Entry point — wires all components together
```

See `docs/brief.md` for the full project vision and architecture spec.
