"""Desktop end-to-end run: real kernel, gnome adapter and Groq; scripted voice input.

Host prerequisites: a GNOME/X session and launcher/tusk_host_launcher.py running.
Run inside Docker:  docker compose run --rm -T --no-deps tusk python -m e2e.run_desktop_e2e
"""
import sys
import time
from collections.abc import Callable

from e2e.desktop_app_factory import build_desktop_app
from e2e.desktop_probe import DesktopProbe
from e2e.desktop_scenarios import SCENARIOS
from e2e.voice_e2e_harness import VoiceE2EHarness


def _wire_echo_filter(h: VoiceE2EHarness) -> bool:
    # the harness builds its pipeline without the filter, so poke it in where the branch provides one
    try:
        from shells.voice.stages.echo_filter import EchoFilter
    except ImportError:
        return False
    h._shell._pipeline._echo_filter = EchoFilter(lambda: h.worker.recent_speech, h._log)
    return True


def main() -> int:
    kernel, tool_registry, token, log = build_desktop_app()
    harness = VoiceE2EHarness(kernel, token, log)
    harness.playback.seconds_per_play = 2.0
    print(f"echo filter wired: {_wire_echo_filter(harness)}", flush=True)
    harness.start()
    probe = DesktopProbe(tool_registry)
    failures = sum(_run_one(harness, probe, scenario) for scenario in SCENARIOS)
    harness.detector.close()
    print(f"desktop e2e result: {len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios passed")
    return 1 if failures else 0


def _run_one(harness: VoiceE2EHarness, probe: DesktopProbe, scenario: Callable[[VoiceE2EHarness, DesktopProbe], str]) -> int:
    print(f"--- {scenario.__name__}", flush=True)
    try:
        outcome = scenario(harness, probe)
    except Exception as exc:
        print(f"FAIL {scenario.__name__}: {exc.__class__.__name__}: {exc}", flush=True)
        return 1
    print(f"PASS {scenario.__name__}: {outcome}", flush=True)
    time.sleep(1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
