__all__ = ["DictationToolSchemaCatalog"]


class DictationToolSchemaCatalog:
    def build(self) -> list[dict]:
        return [
            self._schema("start_dictation", {}),
            self._schema("process_segment", {"session_id": "string", "text": "string"}),
            self._schema("stop_dictation", {"session_id": "string"}),
        ]

    def _schema(self, name: str, properties: dict[str, str]) -> dict:
        fields = {key: {"type": value} for key, value in properties.items()}
        return {"name": name, "description": name.replace("_", " "), "inputSchema": {"type": "object", "properties": fields}}
