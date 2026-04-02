import argparse
import os
from dataclasses import dataclass

__all__ = ["StartupOptions", "build_parser"]

_LOG_GROUPS = (
    "ready", "detector", "transcriber", "sanitizer", "buffer", "gatekeeper",
    "kernel-input", "llm-request", "llm-payload", "llm-wait",
    "agent", "tool", "pipeline", "dictation",
    "vad", "stt", "gate", "llm", "llm-with-payload", "wait",
)
_ALIASES = {
    "vad": {"detector"},
    "stt": {"transcriber"},
    "gate": {"gatekeeper"},
    "llm": {"llm-request"},
    "llm-with-payload": {"llm-request", "llm-payload"},
    "wait": {"llm-wait"},
}


@dataclass(frozen=True)
class StartupOptions:
    log_groups: frozenset[str]

    @classmethod
    def from_sources(cls, argv: list[str] | None = None, environ: dict[str, str] | None = None) -> "StartupOptions":
        env = environ or os.environ
        args = build_parser().parse_args(argv)
        groups = _parse_groups(args.show_logs) | _parse_groups(env.get("SHOW_LOGS", ""))
        _validate_groups(groups)
        return cls(frozenset(_expand(groups)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the TUSK voice assistant.")
    parser.add_argument("--show-logs", default="", help="Extra log groups to show. Supported values: " + ", ".join((*_LOG_GROUPS, "all")))
    return parser


def _parse_groups(value: str) -> set[str]:
    groups = set()
    for item in value.split(","):
        name = item.strip().lower()
        if name == "all":
            groups.update(_LOG_GROUPS)
        elif name:
            groups.add(name)
    return groups


def _validate_groups(groups: set[str]) -> None:
    invalid = sorted(groups.difference(_LOG_GROUPS))
    if invalid:
        raise SystemExit("unknown log groups: " + ", ".join(invalid) + ". Supported values: " + ", ".join((*_LOG_GROUPS, "all")))


def _expand(groups: set[str]) -> set[str]:
    expanded = set()
    for name in groups:
        expanded.update(_ALIASES.get(name, {name}))
    return expanded
