import argparse
import os
from dataclasses import dataclass

__all__ = ["StartupOptions", "build_parser"]

_LOG_GROUPS = ("vad", "stt", "gate", "llm", "llm-with-payload", "agent", "tool", "pipeline", "dictation", "wait")


@dataclass(frozen=True)
class StartupOptions:
    log_groups: frozenset[str]

    @classmethod
    def from_sources(cls, argv: list[str] | None = None, environ: dict[str, str] | None = None) -> "StartupOptions":
        env = environ or os.environ
        args = build_parser().parse_args(argv)
        groups = _parse_groups(args.show_logs) | _parse_groups(env.get("SHOW_LOGS", ""))
        _validate_groups(groups)
        if "llm-with-payload" in groups:
            groups.add("llm")
        return cls(frozenset(groups))


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
