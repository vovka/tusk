# Implementation Plan: Add `--version` Flag to Launcher

**Issue:** Add a `--version` flag that prints the version and exits 0 without starting the kernel, shell loader, or any LLM provider.

**Approved Architecture:** `docs/architecture/issue-78.md`

**Date:** 2026-07-28

---

## Overview

This plan decomposes the work into four small, independently verifiable tasks executed in dependency order:

1. Define the version constant in `tusk/__init__.py`
2. Add the `--version` flag to the argument parser in `startup_options.py`
3. Implement version flag handling in `main()` with early exit
4. Add unit tests covering the flag behavior

The implementation is intentionally minimal: no CLI framework, no build-time version derivation, no changelog. The flag is checked *after* argument parsing but *before* any expensive initialization (kernel build, logger, tracer, shell loader).

---

## Task 1: Add Version Constant to `tusk/__init__.py`

**Goal:** Define `__version__` as a public constant in the package root.

**Affected Paths:**
- `tusk/__init__.py`

**Allowed Paths:**
- (none)

**Dependencies:**
- (none)

**Acceptance Criteria:**
- `__version__` is defined as a string constant with value `"0.1.0"`
- The constant is importable: `from tusk import __version__` succeeds
- The constant equals the expected version string
- No other changes to `__init__.py` (existing imports, `__all__`, etc. remain unchanged)

**Tests Expected to Pass:**
- Any existing test that imports from `tusk` (regression)
- New test in Task 4: `test_main_version_flag_prints_and_exits()` will later verify the constant is used

**Explicit Exclusions:**
- Do not add docstrings, comments, or multi-line formatting
- Do not modify any other module-level code in `__init__.py`
- Do not add version derivation logic (e.g., reading from pyproject.toml or git tags)
- Do not initialize the version from environment variables

**Risk Classification:** **Low**

**Rationale:** Adding a single string constant is the simplest, least risky change. The constant is in a highly visible location, making version updates obvious in git history.

---

## Task 2: Add `--version` Flag to Argument Parser

**Goal:** Extend `build_parser()` in `startup_options.py` to recognize the `--version` flag.

**Affected Paths:**
- `tusk/shared/config/startup_options.py` (in the `build_parser()` function)

**Allowed Paths:**
- (none)

**Dependencies:**
- Task 1 (version constant must exist; this task may import it to document where the version comes from, but the parser itself does not use it—that happens in main.py)

**Acceptance Criteria:**
- `build_parser()` adds a `--version` flag using `action="store_true"`
- The flag is recognized without parse errors: `parser.parse_args(["--version"])` succeeds
- The parsed args object has a `version` attribute (or similar, per argparse behavior) that is `True` when `--version` is provided, `False` otherwise
- All existing flags (`--show-logs`, `--llm-log-preview-chars`) continue to work unchanged
- Existing validation logic in `_groups()` is unaffected

**Tests Expected to Pass:**
- Existing test suite for `startup_options.py` (regression; no changes to existing behavior expected)
- New test in Task 4: `test_version_flag_recognized_by_parser()` will verify the flag is accepted

**Explicit Exclusions:**
- Do not print the version or exit (that happens in main.py)
- Do not use argparse's `version` action (which auto-exits); use `action="store_true"` only
- Do not modify argument parsing logic for other flags
- Do not add validation that requires the version constant to be imported

**Risk Classification:** **Low**

**Rationale:** Adding one flag to an existing argparse parser is a mechanical change. argparse is well-tested and stable. The flag is orthogonal to existing validation logic.

---

## Task 3: Implement Version Flag Handling in `main()`

**Goal:** Check for the `--version` flag after parsing and exit with code 0, printing the version, before any expensive initialization.

**Affected Paths:**
- `main.py`

**Allowed Paths:**
- (none)

**Dependencies:**
- Task 1 (to import `__version__` from `tusk`)
- Task 2 (to know the flag is parsed as `args.version`)

**Acceptance Criteria:**
- After `StartupOptions.from_sources(sys.argv[1:])` returns, check if `args.version` is `True`
- If `True`: print `__version__` to stdout (with a single newline, e.g., `print(__version__)`)
- Call `sys.exit(0)` immediately after printing
- If `False`: continue with existing initialization (Config.from_env(), logger, tracer, kernel build, shell loader)
- The check happens *before* any of: `Config.from_env()`, logger initialization, tracer initialization, kernel build, or shell loader start
- No other changes to `main()` flow when `--version` is not present

**Tests Expected to Pass:**
- Existing `main()` tests continue to pass (regression; normal flow unchanged)
- New test in Task 4: `test_main_version_flag_prints_and_exits()` will verify the flag behavior
- New test in Task 4: `test_main_normal_flow_without_version_flag()` will verify regression

**Explicit Exclusions:**
- Do not modify argument parsing (already done in Task 2)
- Do not initialize Config, logger, tracer, kernel, or shell loader when `--version` is present
- Do not add other command-line logic or special cases
- Do not modify the signature or behavior of any other function in `main.py`
- Do not catch exceptions that shouldn't be caught (let parsing errors propagate as before)

**Risk Classification:** **Low**

**Rationale:** The check is a simple `if` statement placed early in `main()`, before any complex initialization. Early exit with `sys.exit(0)` is a standard pattern. No side effects or resource cleanup are needed because nothing expensive has been initialized yet.

---

## Task 4: Add Unit Tests for `--version` Flag

**Goal:** Write comprehensive tests verifying the `--version` flag behavior and ensuring no regression in normal flow.

**Affected Paths:**
- `tests/test_main_version.py` (new file)

**Allowed Paths:**
- (none; existing test files are not modified)

**Dependencies:**
- Task 1 (to verify the constant is correctly printed)
- Task 2 (to verify the flag is recognized)
- Task 3 (to verify the exit behavior in main.py)

**Acceptance Criteria:**
- New test file `tests/test_main_version.py` exists under `tests/`
- Contains at least the following three tests:

  1. **`test_main_version_flag_prints_and_exits()`**
     - Set up `sys.argv = ["main.py", "--version"]`
     - Call `main()` in a test context that captures stdout and mocks `sys.exit()`
     - Assert stdout equals `tusk.__version__` with a newline (e.g., `"0.1.0\n"`)
     - Assert `sys.exit(0)` was called
     - Assert `_build_kernel()` was never called (verify no kernel initialization)
     - Assert Config.from_env(), logger, tracer, and shell loader were never initialized

  2. **`test_version_flag_combined_with_other_flags()`**
     - Set up `sys.argv = ["main.py", "--version", "--show-logs"]`
     - Call `main()`
     - Assert the version is printed and `sys.exit(0)` is called (other flags are ignored when `--version` is present)
     - Verifies that `--version` takes precedence

  3. **`test_main_normal_flow_without_version_flag()` (Regression Test)**
     - Set up `sys.argv = ["main.py"]` (no `--version`)
     - Use existing test pattern (mocked `_build_kernel()`, `ShellLoader.start()`, etc.)
     - Call `main()`
     - Assert normal initialization flow proceeds (Config, kernel, shell loader)
     - Assert `sys.exit()` was NOT called
     - Verifies that existing behavior is unchanged

- All tests use the existing test infrastructure (fakes for Shell, mocked collaborators per pattern in `tests/test_lifecycle.py`)
- Tests run with pytest and pass
- Tests do not hit the network, subprocess, git, or `gh`

**Tests Expected to Pass:**
- The three tests above
- Existing test suite (`pytest tests/`)—no regressions

**Explicit Exclusions:**
- Do not test argument parsing logic (already tested in `tests/test_startup_options.py`)
- Do not add integration tests that start the real kernel or shell loader
- Do not test other flags in detail (focused on `--version` behavior)
- Do not add fixtures or utilities not needed for these specific tests
- Do not add docstrings beyond a single line per test (if any)
- Do not mock `sys.exit` in ways that hide the exit code (must verify `sys.exit(0)` specifically)

**Risk Classification:** **Low**

**Rationale:** Unit tests with mocked dependencies are standard and low-risk. Tests verify behavior without touching external systems. The pattern follows existing test infrastructure (`test_lifecycle.py`, `test_poller.py`).

---

## Dependency Graph

```
Task 1 (Version Constant)
  ↓
Task 2 (Parser Flag)
  ↓
Task 3 (main.py Logic)
  ↓
Task 4 (Tests)
```

All tasks are sequential with clear dependencies. No parallel work is possible because each layer depends on the previous one being complete.

---

## Verification and Acceptance

**Manual Smoke Test (after all tasks complete):**
```bash
python main.py --version
# Expected output: 0.1.0 (or whatever version is set in __version__)
# Expected exit code: 0
```

**Automated Verification:**
```bash
pytest tests/test_main_version.py -v
# All three tests pass
pytest tests/ -q
# Full suite passes; no regressions
```

**Checklist Before Marking Complete:**
- [ ] `tusk/__init__.py` defines `__version__ = "0.1.0"`
- [ ] `tusk/shared/config/startup_options.py` adds `--version` flag to `build_parser()`
- [ ] `main.py` checks `args.version` and exits with code 0 before expensive initialization
- [ ] `tests/test_main_version.py` contains three passing tests
- [ ] `pytest tests/ -q` passes with no new failures
- [ ] Manual smoke test confirms `python main.py --version` prints version and exits 0
- [ ] All existing functionality (normal startup without `--version`) works unchanged

---

## Risk Summary

| Task | Risk | Mitigation |
|------|------|-----------|
| 1. Add constant | Low | Single string constant; minimal change; obvious location for updates |
| 2. Add parser flag | Low | Orthogonal to existing validation; well-tested argparse; simple flag addition |
| 3. Implement logic | Low | Early exit before complex logic; no resource cleanup needed; standard pattern |
| 4. Add tests | Low | Mocked dependencies; follows existing test infrastructure; no external calls |

**Overall Risk:** **Low**. All changes are small, focused, and follow established patterns. No complex logic, no new dependencies, no system interactions.

---

## Out of Scope (Explicit Exclusions)

These items are NOT part of this implementation plan:

- Adding a CLI framework (use existing argparse only)
- Build-time version derivation (version is a hardcoded constant)
- Changelog or release notes
- Updating version in pyproject.toml, setup.py, or other build files
- Version validation or semver parsing
- Handling multiple versions or version compatibility
- Auto-incrementing version based on git commits or other metadata
- Printing version in verbose or formatted output (bare string only)
- Handling `--version` in any location other than `main()` (not in subcommands, extensions, etc.)
- Modifying existing argument parsing for other flags
- Adding new command-line options beyond `--version`

---

## Implementation Order

Execute tasks in the order listed (1 → 2 → 3 → 4). Each task is small enough to be completed and verified independently, yet each depends on the previous one being correct.

---

## Review Status

**Feedback Received:** "Address codex review comments"

**Note:** The feedback block did not include specific review comments or details about what "codex review comments" refers to. This plan document is for adding a `--version` flag to the main launcher and does not involve Codex (the agent backend) directly. If there are specific codex-related concerns or other review feedback, please provide them explicitly so they can be addressed in this plan or, if outside scope, recorded separately.

The plan as currently written follows all project guidelines from CLAUDE.md and the implementation plan template from `docs/plan/` and is ready for implementation pending clarification on the referenced review feedback.

