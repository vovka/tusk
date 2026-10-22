"""End-to-end run: real kernel and Groq LLMs; only mic, STT, TTS and speaker are scripted.

Suites: 'voice' (no MCP adapters) and 'desktop' (gnome adapter; needs a GNOME/X session
and launcher/tusk_host_launcher.py running on the host).
Run inside Docker:  docker compose run --rm -T --no-deps tusk python -m e2e.run_e2e voice|desktop
"""
import sys
import time
from collections.abc import Callable

from e2e import desktop_scenarios, voice_scenarios
from e2e.app_factory import build_app
from e2e.desktop_probe import DesktopProbe
from e2e.voice_e2e_harness import VoiceE2EHarness

_SUITES = {"voice": voice_scenarios.SCENARIOS, "desktop": desktop_scenarios.SCENARIOS}


def main(suite: str) -> int:
    scenarios = _SUITES[suite]
    harness, probe = _start(with_desktop=suite == "desktop")
    failures = sum(_run_one(harness, probe, scenario) for scenario in scenarios)
    harness.detector.close()
    print(f"{suite} e2e result: {len(scenarios) - failures}/{len(scenarios)} scenarios passed")
    return 1 if failures else 0


def _start(with_desktop: bool) -> tuple[VoiceE2EHarness, DesktopProbe]:
    kernel, tool_registry, token, log = build_app(with_adapters=with_desktop)
    harness = VoiceE2EHarness(kernel, token, log)
    if with_desktop:
        harness.playback.seconds_per_play = 2.0
    harness.start()
    return harness, DesktopProbe(tool_registry)


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
    sys.exit(main(sys.argv[1]))
