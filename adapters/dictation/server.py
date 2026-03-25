import json
import os
import sys
import uuid

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

_STOP_WORDS = {"stop dictation", "finish dictation", "end dictation"}
_PROMPT = "Clean up dictated text. Return only the cleaned text."


class DictationServer:
    def __init__(self) -> None:
        self._sessions: dict[str, str] = {}

    def serve(self) -> None:
        for line in sys.stdin:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            if method == "initialize":
                payload = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
            elif method == "tools/list":
                payload = {"tools": self._tools()}
            elif method == "tools/call":
                payload = self._call(params["name"], params.get("arguments", {}))
            else:
                payload = {}
            self._write(request["id"], payload)

    def _tools(self) -> list[dict]:
        return [
            self._schema("start_dictation", {}),
            self._schema("process_segment", {"session_id": "string", "text": "string"}),
            self._schema("stop_dictation", {"session_id": "string"}),
        ]

    def _schema(self, name: str, properties: dict) -> dict:
        return {
            "name": name,
            "description": name.replace("_", " "),
            "inputSchema": {"type": "object", "properties": {key: {"type": value} for key, value in properties.items()}},
        }

    def _call(self, name: str, arguments: dict) -> dict:
        payload = getattr(self, f"_tool_{name}")(arguments)
        return {"content": [{"type": "text", "text": payload["message"]}], "isError": not payload["success"], "data": payload.get("data")}

    def _tool_start_dictation(self, arguments: dict) -> dict:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ""
        return {"success": True, "message": "dictation started", "data": {"session_id": session_id}}

    def _tool_process_segment(self, arguments: dict) -> dict:
        session_id = arguments["session_id"]
        text = arguments["text"].strip()
        if text.lower() in _STOP_WORDS:
            return {
                "success": True,
                "message": "dictation stopped",
                "data": {"operation": "replace", "text": self._sessions.get(session_id, ""), "replace_chars": 0, "should_stop": True},
            }
        previous = self._sessions.get(session_id, "")
        combined = f"{previous} {text}".strip()
        cleaned = self._refine(combined)
        replace_chars = len(previous) if previous else 0
        self._sessions[session_id] = cleaned
        operation = "replace" if previous else "insert"
        return {
            "success": True,
            "message": "dictation updated",
            "data": {"operation": operation, "text": cleaned, "replace_chars": replace_chars, "should_stop": False},
        }

    def _tool_stop_dictation(self, arguments: dict) -> dict:
        self._sessions.pop(arguments["session_id"], None)
        return {"success": True, "message": "dictation stopped"}

    def _refine(self, text: str) -> str:
        provider, model = os.environ.get("DICTATION_LLM", "groq/llama-3.1-8b-instant").split("/", 1)
        if provider == "groq" and Groq is not None and os.environ.get("GROQ_API_KEY"):
            client = Groq(api_key=os.environ["GROQ_API_KEY"])
            response = client.chat.completions.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "system", "content": _PROMPT}, {"role": "user", "content": text}],
            )
            return response.choices[0].message.content.strip()
        if provider == "openrouter" and OpenAI is not None and os.environ.get("OPENROUTER_API_KEY"):
            client = OpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1")
            response = client.chat.completions.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "system", "content": _PROMPT}, {"role": "user", "content": text}],
            )
            return response.choices[0].message.content.strip()
        return text

    def _write(self, request_id: int, payload: dict) -> None:
        response = {"jsonrpc": "2.0", "id": request_id, "result": payload}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    DictationServer().serve()


if __name__ == "__main__":
    main()
