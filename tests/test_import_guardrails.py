from pathlib import Path

from tests.style_guardrails.import_guardrails import ImportGuardrails


def _write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n")


def test_repository_respects_import_boundaries() -> None:
    assert ImportGuardrails().violations() == []


def test_import_guardrails_flag_shell_importing_kernel(tmp_path: Path) -> None:
    _write(tmp_path, "shells/voice/bad.py", "from tusk.kernel.core.kernel_api import KernelAPI")
    violations = ImportGuardrails(tmp_path).violations()
    assert violations == [
        f"{Path('shells') / 'voice' / 'bad.py'}: imports tusk.kernel.core.kernel_api (allowed: shells, tusk.shared)"
    ]


def test_import_guardrails_flag_relative_import_escaping_shared(tmp_path: Path) -> None:
    _write(tmp_path, "tusk/shared/llm/bad.py", "from ...providers.llm import GroqLLM")
    violations = ImportGuardrails(tmp_path).violations()
    assert violations == [
        f"{Path('tusk') / 'shared' / 'llm' / 'bad.py'}: imports tusk.providers.llm (allowed: tusk.shared)"
    ]


def test_import_guardrails_allow_own_tree_shared_and_third_party(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "adapters/gnome/ok.py",
        "import json\nfrom tusk.shared.schemas.app_status import AppStatus\nfrom adapters.gnome.server import main",
    )
    _write(tmp_path, "tusk/kernel/ok.py", "from tusk.kernel.tools.tool_registry import ToolRegistry")
    assert ImportGuardrails(tmp_path).violations() == []
