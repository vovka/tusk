# TUSK — Development Guardrails

These rules apply to all code in this repository. Claude must follow them without exception.

---

## Code Size Limits

- **Max 100 lines per file** (excluding blank lines and comments). If a file grows beyond this, split it.
- **Max 10 lines per function/method**. If logic is longer, extract named helper methods.
- **One class per file**. Filename must match the class name in snake_case (e.g., `VoiceCapture` → `voice_capture.py`).

## OOP Principles

- **Classes first.** Model every meaningful concept as a class, not a loose collection of functions.
- **Single Responsibility.** Each class does one thing. Its purpose must be describable in one sentence.
- **Depend on abstractions.** Classes depend on interfaces (abstract base classes), not concrete implementations.
- **Composition over inheritance.** Prefer composing small objects over deep inheritance chains.
- **Encapsulate state.** No public mutable attributes. Use properties or explicit setters with validation.

## Modularity

- **Interface before implementation.** Define the ABC/protocol before writing the concrete class.
- **No circular imports.** Module dependencies flow in one direction: `core → interfaces ← extensions`.
- **Dependency injection.** Pass dependencies in `__init__`. Never instantiate dependencies inside a class.
- **No global state.** No module-level variables that mutate at runtime. Use a config/registry object.

## Code Readability (for Humans)

- **Name things explicitly.** `transcribed_text` not `txt`, `is_directed_at_tusk` not `flag`.
- **No clever tricks.** If it needs a comment to explain *what* it does, rewrite it. Comments explain *why*.
- **No abbreviations** in names unless universally known (e.g., `stt`, `llm`, `api`).
- **Flat is better than nested.** Max 2 levels of indentation inside a function. Use early returns.
- **Explicit over implicit.** No `*args/**kwargs` on public interfaces. Every parameter is named and typed.

## Python-Specific Rules

- **Type hints on every function signature** — parameters and return types, always.
- **Abstract base classes** for every swappable component (STT engine, LLM provider, extension, etc.).
- **No bare `except`.** Always catch a specific exception type.
- **`dataclass` or `NamedTuple`** for data containers — no plain dicts passed between modules.
- **`__all__`** defined in every `__init__.py` to make public API explicit.

## Architecture Rules (TUSK-specific)

- **Core knows nothing about extensions.** The core emits events and consumes context via defined schemas — never imports from extension modules.
- **Every swappable component implements an ABC.** STT engine, gatekeeper, main agent, LLM provider, and each extension must have a matching interface class.
- **Events and context use typed schemas.** No untyped dicts passed through the event bus or context pipeline.
- **Latency is a first-class concern.** Any new component that sits on the hot path (STT → gatekeeper → agent) must document its expected latency impact.

## What Claude Must Not Do

- Do not add features, logging, error handling, or abstractions not explicitly requested.
- Do not refactor code that is not part of the current task.
- Do not add docstrings or comments to code that was not changed.
- Do not create utility helpers "for future use."
- Do not add backwards-compatibility shims for removed code.

## Docker Environment (Mandatory)

All development, testing, and code execution happens **inside Docker**. Never run Python, pytest, or any project command directly on the host.

- **Run tests**: `docker compose exec tusk pytest tests/`
- **Run a single test**: `docker compose exec tusk pytest tests/test_foo.py::TestClass::test_method`
- **Run the app**: `docker compose up`
- **Open a shell**: `docker compose exec tusk bash`

If the container is not running, start it first: `docker compose up -d`

Claude must never suggest or run `python`, `pytest`, or `pip` commands outside of `docker compose exec tusk ...`.

---

## Coding Railguide (TDD Required)

- **Tests first, always.** Before writing or changing production code, add or update unit tests that fail for the intended behavior.
- **Red → Green → Refactor.**
  1. Write a failing test (Red).
  2. Implement the smallest change to pass (Green).
  3. Refactor while keeping tests green.
- **No untested changes.** Every production code change must be covered by unit tests in the same PR.
- **Regression tests required.** Any bug fix must include a unit test that reproduces the bug before the fix.
- **Keep tests focused.** One behavior per test where practical; avoid broad integration-style assertions in unit test files.

