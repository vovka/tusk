import threading
import time
import types

from tusk.kernel.api import KernelAPI


def test_concurrent_submits_do_not_overlap() -> None:
    events: list[str] = []
    api = KernelAPI(_slow_command_mode(events), llm_registry=None)
    threads = [threading.Thread(target=api.submit, args=(f"command {index}",)) for index in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert events == ["enter", "exit", "enter", "exit"]


def _slow_command_mode(events: list[str]) -> object:
    def process_command(text: str) -> object:
        events.append("enter")
        time.sleep(0.05)
        events.append("exit")
        return types.SimpleNamespace(handled=True, reply=text)

    return types.SimpleNamespace(process_command=process_command)
