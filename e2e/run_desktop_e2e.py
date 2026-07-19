"""Desktop end-to-end run: real kernel, gnome adapter and Groq; scripted voice input.

Host prerequisites: a GNOME/X session and launcher/tusk_host_launcher.py running.
Run inside Docker:  docker compose run --rm -T --no-deps tusk python -m e2e.run_desktop_e2e
"""
import sys
import time
from collections.abc import Callable

from e2e.desktop_app_factory import build_desktop_app
from e2e.desktop_probe import DesktopProbe
from e2e.voice_e2e_harness import VoiceE2EHarness


def scenario_status_reply(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    replies_before = len(h.replies)
    h.say("Tusk, how are you doing today?")
    h.wait(lambda: len(h.replies) > replies_before, 90, "spoken status reply")
    h.wait_idle()
    return f"reply: {_speakable(h.replies[-1])!r}"


def scenario_reply_echo_is_ignored(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    echo = h.replies[-1] if h.replies else "I am doing fine, thanks for asking."
    enqueued_before = len(h.enqueued)
    h.say(" ".join(echo.split()[:12]), duration=3.0)
    time.sleep(10.0)
    assert len(h.enqueued) == enqueued_before, f"own speech echoed back was enqueued: {h.enqueued[-1]!r}"
    h.wait_idle()
    return "echoed reply was not treated as a command"


def scenario_open_gedit_with_poem(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    h.say("Tusk, open the gedit application and type your favorite short poem into it")
    _await_command(h, idle_timeout=240)
    windows = probe.windows()
    assert "gedit" in windows.lower(), f"no gedit window open; {windows}"
    return f"gedit open; reply: {_speakable(_last_reply(h))!r}"


def scenario_move_gedit_left(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    h.say("Tusk, move the gedit window to the left half of the screen")
    _await_command(h)
    geometry = probe.geometry("gedit")
    assert geometry is not None, "gedit window disappeared"
    assert geometry[0] <= 150, f"gedit not at the left edge: geometry={geometry}"
    return f"gedit at x={geometry[0]}; reply: {_speakable(_last_reply(h))!r}"


def scenario_move_gedit_right(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    left_x = (probe.geometry("gedit") or (0, 0, 0, 0))[0]
    h.say("Tusk, now move the gedit window to the right half of the screen")
    _await_command(h)
    geometry = probe.geometry("gedit")
    assert geometry is not None, "gedit window disappeared"
    assert geometry[0] > left_x, f"gedit did not move right: geometry={geometry}"
    return f"gedit moved to x={geometry[0]}; reply: {_speakable(_last_reply(h))!r}"


def scenario_maximize_gedit(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    before = probe.geometry("gedit")
    h.say("Tusk, maximize the gedit window")
    _await_command(h)
    after = probe.geometry("gedit")
    assert after is not None, "gedit window disappeared"
    assert before is None or after[2] > before[2], f"width did not grow: {before} -> {after}"
    return f"gedit maximized to {after[2]}x{after[3]}; reply: {_speakable(_last_reply(h))!r}"


def scenario_minimize_gedit(h: VoiceE2EHarness, probe: DesktopProbe) -> str:
    h.say("Tusk, minimize the gedit window")
    _await_command(h)
    active = probe.active_window()
    assert "gedit" not in active.lower(), f"gedit is still the active window: {active}"
    return f"gedit minimized; reply: {_speakable(_last_reply(h))!r}"


_SCENARIOS = [
    scenario_status_reply,
    scenario_reply_echo_is_ignored,
    scenario_open_gedit_with_poem,
    scenario_move_gedit_left,
    scenario_move_gedit_right,
    scenario_maximize_gedit,
    scenario_minimize_gedit,
]


def _await_command(h: VoiceE2EHarness, idle_timeout: float = 300.0) -> None:
    h.wait(lambda: h.worker.is_busy, 45, "command reaches the worker")
    h.wait_idle(timeout=idle_timeout)
    time.sleep(2.0)


def _speakable(reply: str) -> str:
    # a spoken reply must never leak the agent's internal tool/JSON syntax
    assert reply.strip(), "reply is empty"
    assert "[tool:" not in reply, f"tool syntax leaked into the spoken reply: {reply!r}"
    assert not reply.lstrip().startswith("{"), f"JSON leaked into the spoken reply: {reply!r}"
    return reply


def _last_reply(h: VoiceE2EHarness) -> str:
    return h.replies[-1] if h.replies else ""


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
    failures = sum(_run_one(harness, probe, scenario) for scenario in _SCENARIOS)
    harness.detector.close()
    print(f"desktop e2e result: {len(_SCENARIOS) - failures}/{len(_SCENARIOS)} scenarios passed")
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
