# Architecture: Add `--version` Flag to Launcher

**Issue:** Add a `--version` flag that prints the version and exits 0 without starting the kernel, shell loader, or any LLM provider.

**Date:** 2026-07-28

---

## Current Architecture

### Entry Point: `main.py`

`main.py` is the single entry point that orchestrates TUSK's startup:

1. Parses command-line arguments via `StartupOptions.from_sources(sys.argv[1:])`
2. Builds config from environment via `Config.from_env()`
3. Creates a logger, tracer, and status reporter
4. Builds the kernel and all LLM provider slots via `_build_kernel()`
5. Publishes LLM model labels to the status reporter
6. Starts the shell loader, which initializes STT, TTS, and MCP adapters

### Argument Parsing: `startup_options.py`

- Located: `tusk/shared/config/startup_options.py`
- Uses `argparse.ArgumentParser` in `build_parser()`
- Currently supports `--show-logs` and `--llm-log-preview-chars` flags
- `StartupOptions.from_sources()` parses argv and returns a frozen dataclass

### Version Constant Location

The version should be defined in `tusk/` (the public package root). Three options:

1. **Define in `tusk/__init__.py`** (chosen): Single, obvious location; version is a public API constant like `tusk.__version__`
2. **Define in a new `tusk/version.py`** module: Separates version logic, but adds a file for minimal content
3. **Define in `main.py`**: Couples launcher version to tusk version; less reusable

### Early-Exit Pattern

The current flow builds many expensive resources:
- Config loading from environment
- Logger and tracer initialization
- Kernel build with all agent profiles and LLM provider instantiation
- Shell loader setup

For `--version`, we need to exit *after* parsing arguments but *before* any of these expensive operations. The flag must be checked in `main()`, not in `StartupOptions.from_sources()`, because:
- Parsing happens inside the class method; flag checking should stay in the caller (main.py)
- Allows main() to control flow and exit behavior cleanly
- Avoids mixing startup configuration with launcher-specific flags

---

## Integration Points and Contracts

### 1. Argument Parser Integration
- **File**: `tusk/shared/config/startup_options.py`
- **Contract**: `build_parser()` must add `--version` flag
- **Decision**: Add the flag to the existing parser, not create a separate one
- **Rationale**: Keeps argument parsing centralized; `--version` is a valid startup option

### 2. Version Availability
- **Export**: `tusk.__version__` constant (string, e.g., `"0.1.0"`)
- **Import**: `main.py` imports from `tusk` to access version
- **Visibility**: Public API; may be used by deployment/monitoring scripts

### 3. Early Exit in `main()`
- **Flow**: Parse args → Check `--version` → Print and exit OR continue startup
- **Exit Code**: `0` on success
- **Output**: Single line, version string only (no extra formatting)
- **Side Effects**: None; no kernel, LLM providers, or logging initialized

---

## Design Decisions and Alternatives

### Decision 1: Version Constant Location

**Chosen:** `tusk/__init__.py`

**Alternatives Rejected:**
- **`tusk/version.py`**: Adds a file for a single constant; `__version__` in `__init__.py` is the Python convention.
- **`main.py`**: Couples the launcher's version to TUSK's version; less reusable if the version is ever needed by other callers.

### Decision 2: Where to Check the Flag

**Chosen:** In `main()` after `StartupOptions.from_sources()` returns

**Alternatives Rejected:**
- **Inside `StartupOptions.from_sources()`**: Would require the class method to know about launcher-specific behavior (printing, exiting). Violates single responsibility.
- **Separate parser before `StartupOptions`**: Adds duplicate argument parsing logic; error-prone if the two parsers diverge.

### Decision 3: Argument Handling Pattern

**Chosen:** Add `--version` to `build_parser()` in `startup_options.py`; check in `main()` via `args.version` (or similar attribute set by argparse)

**How argparse Handles `--version`:**
- By default, argparse doesn't include `--version`; we add it as a flag
- When `--version` is present, argparse stores a signal (e.g., `args.version = True` or calls an action)
- Two approaches:
  1. **Simple flag**: `parser.add_argument("--version", action="store_true")` → `args.version` is True/False
  2. **Version action**: `parser.add_argument("--version", action="version", version="0.1.0")` → argparse prints and exits automatically

**Chosen Approach: Simple Flag (`action="store_true"`)**
- Add `--version` flag via `parser.add_argument("--version", action="store_true")`
- Check `if args.version:` in `main()` after parsing, before any other initialization
- Print version and call `sys.exit(0)` explicitly in main()
- Rationale:
  - Explicit control flow: readers can immediately see where and why the program exits
  - Testable: can mock `sys.exit()` to verify the exit code and printed output
  - Minimal: only three lines of code in main()
  - Consistency: main() owns the launcher-level flow; argparse owns just parsing, not control flow

**Rejected: argparse `version` Action**
- argparse's `version` action prints to stdout and automatically calls `sys.exit(0)`
- Makes exit point implicit and harder to trace in main()
- Harder to test: argparse exits directly, bypassing test framework's ability to inspect exit code
- Less flexible: if we ever need to clean up resources before exiting (e.g., closing connections), we can't hook into the exit

---

## Risks and Unknowns

### Risk 1: Parser Extension Compatibility

**Risk**: Adding `--version` to the parser might conflict with existing flags or validation logic.

**Mitigation**:
- The parser currently only has `--show-logs` and `--llm-log-preview-chars`.
- `--version` is orthogonal; validation logic in `_groups()` does not affect it.
- The flag is boolean; no parsing errors expected.

### Risk 2: Version Consistency

**Risk**: If the version constant is defined in `tusk/__init__.py` but isn't updated when releasing a new version, the flag will print stale data.

**Mitigation**:
- This is a manual process; there is no build-time derivation (as requested).
- The constant is in a highly visible location (`tusk/__init__.py`); updates to it show in git history and in any review of version-related changes.
- The unit test `test_main_version_flag_prints_and_exits` verifies the flag outputs the exact version string; developers must update `__version__` in git commits when releasing.
- This mirrors standard Python package versioning (`package.__version__`).

### Risk 3: Test Coverage Gap

**Risk**: The --version flag won't be exercised by existing tests (which all mock StartupOptions).

**Mitigation**:
- Add a new unit test under `tests/` specifically for the --version flow.
- The test must verify:
  1. `--version` flag is recognized (no parse error)
  2. Version is printed to stdout
  3. The process exits with code 0
  4. Kernel is not built (no LLM providers initialized)


---

## Proposed Implementation

### Files to Create/Modify

| File | Change | Reason |
|------|--------|--------|
| `tusk/__init__.py` | Add `__version__ = "0.1.0"` constant | Single source of truth for version |
| `tusk/shared/config/startup_options.py` | Add `--version` flag to `build_parser()` | Centralized argument parsing |
| `main.py` | Check `args.version` and print + exit | Early-exit logic before expensive initialization |
| `tests/test_main_version.py` | New test file | Cover --version flag behavior |

### Test Plan

**Test:** `test_main_version_flag_prints_and_exits`
- Set up argv with `["--version"]`
- Call `main()` in a test context that captures stdout and mocks `sys.exit()`
- Assert:
  1. Stdout is exactly `"0.1.0\n"` (version constant + newline)
  2. `sys.exit(0)` was called (not `sys.exit()` with non-zero code)
  3. Kernel build (`_build_kernel()`) was never called (verified by monkeypatch)
  4. Config, logger, tracer, and shell loader were never initialized

**Test:** `test_main_version_flag_combined_with_other_flags`
- Verify that `--version` combined with other valid flags still prints version and exits
- Example: `["--version", "--show-logs"]` should print version and exit, ignoring `--show-logs`
- Assert: `sys.exit(0)` called with version printed to stdout

**Test:** `test_main_normal_flow_without_version_flag`
- Ensure existing behavior is unchanged when `--version` is not present
- Use current test pattern (mocked `_build_kernel`, `ShellLoader.start()`, etc.)
- Assert: normal flow proceeds (expensive initialization happens)

---

## Acceptance Criteria

The architecture addresses all requirements from the issue. Each criterion will be verified during implementation.

**Functional Requirements:**
- [x] Version constant defined in `tusk/` (single location, importable, manually maintained)
- [x] `python main.py --version` prints the version on one line (bare version, e.g., `0.1.0`)
- [x] Process exits with code 0 (explicit `sys.exit(0)` in main())
- [x] Kernel, shell loader, and LLM providers are never initialized when `--version` is used (check before any expensive initialization)
- [x] All existing invocations without `--version` work unchanged (no changes to other argument parsing)

**Test & Scope:**
- [x] One unit test covers the flag (three tests, actually: version output, precedence over other flags, regression)
- [x] No CLI framework added (uses existing argparse in startup_options.py)
- [x] No build-time version derivation (version is a hardcoded string constant)
- [x] No changelog added (as requested)

---

## Decisions Finalized from Review

1. **Version string format:** Bare version number (e.g., `0.1.0`), no prefix or extra text.
   - Rationale: Matches standard CLI convention (e.g., `python --version` prints `Python 3.11.0`); parseable by scripts without regex.
   - Initial value: `"0.1.0"`. Developers will increment manually when releasing new versions.

2. **Version constant:** `tusk.__version__ = "0.1.0"` defined in `tusk/__init__.py`.
   - Rationale: Single source of truth; reusable by deployment/monitoring scripts via `import tusk; print(tusk.__version__)`.
   - Maintained manually; version bumps are explicit in commit history.

3. **Interaction with other flags:** `--version` takes precedence over all other flags.
   - Rationale: Standard CLI behavior (e.g., `python --version --dont-write-bytecode` prints version only).
   - If `--version` is present, parse succeeds, but main() checks for it before processing other flags.
