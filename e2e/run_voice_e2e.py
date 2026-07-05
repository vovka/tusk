"""Voice-interrupt end-to-end run: real Groq LLM calls, scripted audio edges.

Run inside Docker:  docker compose exec tusk python -m e2e.run_voice_e2e
"""
import sys
import time
from collections.abc import Callable

from e2e.app_factory import build_app
from e2e.voice_e2e_harness import VoiceE2EHarness


def scenario_interrupt_during_agent_run(h: VoiceE2EHarness) -> str:
    h.say("Tusk, prepare a detailed step by step plan for organizing all the files on my desktop")
    h.wait(lambda: h.worker.is_busy, 20, "worker busy")
    time.sleep(2.0)
    h.say("no no, forget it, that was a mistake")
    h.wait(lambda: h.interrupts >= 1, 25, "stop intent classified as interrupt")
    h.wait(lambda: not h.worker.is_busy, 60, "worker idle after interrupt")
    return f"interrupt fired; last reply={h.replies[-1] if h.replies else None!r}"


def scenario_interrupt_during_speech(h: VoiceE2EHarness) -> str:
    h.say("Tusk, tell me a story about a whale sailor in about eight sentences")
    h.wait(lambda: h.worker.current_speech_text is not None, 90, "TUSK speaking")
    h.say("okay okay, that is enough, be quiet now")
    h.wait(lambda: h.playback.last["interrupted"], 20, "playback killed")
    h.wait_idle()
    return f"speech cut after {h.playback.last['played']:.1f}s of {h.playback.seconds_per_play:.0f}s"


def scenario_echo_does_not_self_trigger(h: VoiceE2EHarness) -> str:
    interrupts_before, enqueued_before = h.interrupts, len(h.enqueued)
    h.say("Tusk, tell me one more very short story about the sea")
    h.wait(lambda: h.worker.current_speech_text is not None, 90, "TUSK speaking")
    spoken = h.worker.current_speech_text or "the story of the sea continues"
    h.say(" ".join(spoken.split()[:8]), duration=3.0)
    h.wait_idle(timeout=120)
    assert h.interrupts == interrupts_before, "echo triggered an interrupt"
    assert len(h.enqueued) == enqueued_before + 1, "echo was forwarded as a command"
    assert not h.playback.last["interrupted"], "playback did not run to completion"
    return f"echo ignored; playback finished full {h.playback.last['played']:.1f}s"


def scenario_idle_stop_keeps_normal_path(h: VoiceE2EHarness) -> str:
    interrupts_before = h.interrupts
    h.say("stop")
    time.sleep(8.0)
    assert h.interrupts == interrupts_before, "idle stop must not fire an interrupt"
    h.wait_idle()
    return "idle 'stop' did not fire an interrupt"


def scenario_ready_for_next_command(h: VoiceE2EHarness) -> str:
    replies_before = len(h.replies)
    h.say("Tusk, reply with just the single word ready")
    h.wait(lambda: len(h.replies) > replies_before, 60, "reply after all interrupts")
    h.wait_idle()
    return f"reply: {h.replies[-1]!r}"


_SCENARIOS = [
    scenario_interrupt_during_agent_run,
    scenario_interrupt_during_speech,
    scenario_echo_does_not_self_trigger,
    scenario_idle_stop_keeps_normal_path,
    scenario_ready_for_next_command,
]


def main() -> int:
    kernel, token, log = build_app()
    harness = VoiceE2EHarness(kernel, token, log)
    harness.start()
    failures = sum(_run_one(harness, scenario) for scenario in _SCENARIOS)
    harness.detector.close()
    print(f"e2e result: {len(_SCENARIOS) - failures}/{len(_SCENARIOS)} scenarios passed")
    return 1 if failures else 0


def _run_one(harness: VoiceE2EHarness, scenario: Callable[[VoiceE2EHarness], str]) -> int:
    print(f"--- {scenario.__name__}", flush=True)
    try:
        outcome = scenario(harness)
    except AssertionError as exc:
        print(f"FAIL {scenario.__name__}: {exc}", flush=True)
        return 1
    print(f"PASS {scenario.__name__}: {outcome}", flush=True)
    time.sleep(1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
