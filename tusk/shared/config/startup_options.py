import argparse
import os
from dataclasses import dataclass

__all__ = ["StartupOptions", "build_parser"]

_GROUPS = (
    "ready", "tusk", "error", "detector", "transcriber", "sanitizer", "buffer", "gatekeeper",
    "gate-recovery", "kernel-input", "llm-request", "llm-payload", "llm-tools", "llm-response",
    "llm-wait", "llm-payload-full", "llm-tools-full", "llm-response-full", "agent", "tool",
    "pipeline", "dictation", "vad", "stt", "gate", "llm", "llm-tool", "llm-tool-full",
    "llm-with-payload", "wait",
)
_ALL = tuple(name for name in _GROUPS if name not in {"vad", "stt", "gate", "llm", "llm-tool", "llm-tool-full", "llm-with-payload", "wait"} and not name.endswith("-full"))
_ALIASES = {
    "vad": {"detector"},
    "stt": {"transcriber"},
    "gate": {"gatekeeper", "gate-recovery"},
    "llm": {"llm-request", "llm-response"},
    "llm-tool": {"llm-tools"},
    "llm-tool-full": {"llm-tools-full"},
    "llm-with-payload": {"llm-request", "llm-payload", "llm-tools", "llm-response"},
    "wait": {"llm-wait"},
}


@dataclass(frozen=True)
class StartupOptions:
    log_groups: frozenset[str]
    hidden_groups: frozenset[str] = frozenset()
    llm_log_preview_chars: int = 120

    @classmethod
    def from_sources(cls, argv: list[str] | None = None, environ: dict[str, str] | None = None) -> "StartupOptions":
        env = environ or os.environ
        args = build_parser().parse_args(argv)
        shown, hidden = _groups(args.show_logs, env.get("SHOW_LOGS", ""))
        return cls(frozenset(shown), frozenset(hidden), _preview(args.llm_log_preview_chars, env))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the TUSK voice assistant.")
    parser.add_argument("--show-logs", default="", help="Extra log groups to show. Supported values: " + ", ".join((*_GROUPS, "all")))
    parser.add_argument("--llm-log-preview-chars", type=int, default=None, help="Compact LLM log preview length.")
    return parser


def _groups(cli: str, env: str) -> tuple[set[str], set[str]]:
    include, exclude = _tokens(cli) | _tokens(env), _hidden(cli) | _hidden(env)
    _validate(include | exclude)
    hidden = _expand(exclude)
    return _expand(include).difference(hidden), hidden


def _tokens(value: str) -> set[str]:
    items = {item.strip().lower() for item in value.split(",") if item.strip() and not item.strip().startswith("-")}
    return items.difference({"all"}) | _all(value)


def _hidden(value: str) -> set[str]:
    return {item.strip()[1:].lower() for item in value.split(",") if item.strip().startswith("-")}


def _all(value: str) -> set[str]:
    return set(_ALL) if "all" in {item.strip().lower() for item in value.split(",") if item.strip()} else set()


def _validate(groups: set[str]) -> None:
    invalid = sorted(groups.difference(_GROUPS).difference({"all"}))
    if invalid:
        raise SystemExit("unknown log groups: " + ", ".join(invalid) + ". Supported values: " + ", ".join((*_GROUPS, "all")))


def _expand(groups: set[str]) -> set[str]:
    return {item for name in groups for item in _ALIASES.get(name, {name})}


def _preview(cli_value: int | None, env: dict[str, str]) -> int:
    return cli_value if cli_value is not None else int(env.get("LLM_LOG_PREVIEW_CHARS", "120"))
