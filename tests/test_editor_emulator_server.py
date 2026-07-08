import io
import json

from demos.editor_emulator.emulated_editor import EmulatedEditor
from demos.editor_emulator.server import EditorEmulatorServer


def test_type_text_updates_buffer_and_snapshot(tmp_path) -> None:
    snapshot = tmp_path / "buffer.txt"
    request = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "type_text", "arguments": {"text": "hi"}},
    })
    output = io.StringIO()
    EditorEmulatorServer(EmulatedEditor(), snapshot, io.StringIO(request + "\n"), output).serve()
    assert "hi" in snapshot.read_text()
    assert json.loads(output.getvalue())["result"]["isError"] is False
