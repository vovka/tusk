import threading
import time

from tusk.shared.mcp.mcp_client import MCPClient

# Answers "slow" late and everything else at once, so replies leave in the opposite order of the requests.
_OUT_OF_ORDER_SERVER = (
    "import json, sys, threading, time\n"
    "def reply(request):\n"
    "    if request.get('params', {}).get('name') == 'slow':\n"
    "        time.sleep(0.5)\n"
    "    name = request.get('params', {}).get('name', '')\n"
    "    body = {'jsonrpc': '2.0', 'id': request['id'], 'result': {'content': [{'type': 'text', 'text': name}]}}\n"
    "    sys.stdout.write(json.dumps(body) + '\\n')\n"
    "    sys.stdout.flush()\n"
    "for line in sys.stdin:\n"
    "    threading.Thread(target=reply, args=(json.loads(line),)).start()\n"
)


def _call(client: MCPClient, name: str, results: dict) -> None:
    results[name] = client.call_tool(name, {}).content


def _start(client: MCPClient, name: str, results: dict) -> threading.Thread:
    thread = threading.Thread(target=_call, args=(client, name, results))
    thread.start()
    return thread


def test_concurrent_calls_each_receive_their_own_reply() -> None:
    client = MCPClient(response_timeout_seconds=5.0)
    client.connect_stdio(["python", "-c", _OUT_OF_ORDER_SERVER], cwd=".")
    results: dict = {}
    slow = _start(client, "slow", results)
    time.sleep(0.1)
    fast = _start(client, "fast", results)
    slow.join()
    fast.join()
    client.shutdown()
    assert results == {"slow": "slow", "fast": "fast"}
