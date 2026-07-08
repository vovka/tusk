# Mic Echo Cancellation (Acoustic, TUSK-only)

Host-level fix for speaker bleed: while TUSK talks, its own TTS played back on
speakers is picked up by the mic, costing an extra VAD segment + STT + gatekeeper
call per echo (see `voice-interrupt`'s semantic echo defense, which handles this
today at the LLM layer). This closes the gap acoustically, before VAD ever sees it.

## How it works

`docker/pipewire-echo-cancel.conf` loads PipeWire's built-in WebRTC AEC module on
the **host**, creating two virtual nodes (`echo-cancel-source`, `echo-cancel-sink`)
that wrap the real mic/speaker and subtract the playback reference from the
capture signal. `docker-compose.yml` sets `PULSE_SINK`/`PULSE_SOURCE` to those
node names so only the `tusk` container's audio (capture + `paplay` TTS) routes
through the canceller — host default devices, and every other app, are untouched.

```
mic ──▶ [AEC: subtract reference] ──▶ echo-cancel-source ──▶ TUSK capture (PortAudio)
speaker ◀── echo-cancel-sink ◀── TUSK playback (paplay)
                │
                └── reference tap
```

## Setup (one-time, per host)

```bash
mkdir -p ~/.config/pipewire/pipewire.conf.d
cp docker/pipewire-echo-cancel.conf ~/.config/pipewire/pipewire.conf.d/
systemctl --user restart wireplumber pipewire pipewire-pulse
wpctl status | grep -i echo-cancel   # confirm the two virtual nodes exist
docker compose up -d --force-recreate tusk
```

## Key files

| File | Role |
|---|---|
| `docker/pipewire-echo-cancel.conf` | host PipeWire drop-in: loads `libpipewire-module-echo-cancel` (WebRTC AEC backend), pins real mic/speaker as capture/playback targets |
| `docker-compose.yml` | `PULSE_SINK`/`PULSE_SOURCE` scope the effect to the `tusk` container only |

## Known limits

- **Machine-specific config.** `target.object` in the conf pins this host's ALSA
  node names (`alsa_input...sofhdadsp_6__source`, `alsa_output...sofhdadsp__sink`).
  A different machine needs its own names from `wpctl status`.
- **Host-only, opt-in.** Nothing in the container depends on this; without the
  host-side setup step, `PULSE_SINK`/`PULSE_SOURCE` point at names that don't
  exist and libpulse silently falls back to the raw default mic/speaker —
  same behavior as before this change.
- **Residual echo** (nonlinear speaker distortion) can still leak past AEC;
  `voice-interrupt`'s semantic echo defense remains the backstop.
- Requires PipeWire (not plain PulseAudio) with the `aec/libspa-aec-webrtc`
  backend installed.

## Testing

Infra config, not application code — no unit tests. Verify by watching
`docker compose logs -f tusk` while TUSK speaks: `[DETECTR] speech started` /
self-transcriptions of TUSK's own reply should disappear during playback.

---
**Last updated**: 2026-07-08 · **Updated by**: Claude · **Exploration depth**: Moderate
