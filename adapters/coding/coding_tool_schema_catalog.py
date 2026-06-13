__all__ = ["CodingToolSchemaCatalog"]


class CodingToolSchemaCatalog:
    def build(self) -> list[dict]:
        return [
            self._schema("start_coding_session", {"initial_buffer": "string"}),
            self._schema("process_intent", {"session_id": "string", "intent": "string"}),
            self._schema("stop_coding_session", {"session_id": "string"}),
        ]

    def _schema(self, name: str, properties: dict[str, str]) -> dict:
        fields = {key: {"type": value} for key, value in properties.items()}
        return {"name": name, "description": name.replace("_", " "), "inputSchema": {"type": "object", "properties": fields}}
