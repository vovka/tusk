__all__ = ["SimpleSchemaValidator"]


class SimpleSchemaValidator:
    def validate(self, schema: dict[str, object], value: object) -> str | None:
        if not isinstance(schema, dict):
            return None
        if schema.get("type") == "object":
            return self._object(schema, value)
        if schema.get("type") == "array":
            return self._array(schema, value)
        return self._scalar(schema, value)

    def _array(self, schema: dict[str, object], value: object) -> str | None:
        if not isinstance(value, list):
            return "expected array"
        item_schema = schema.get("items")
        return next((self.validate(item_schema, item) for item in value if self.validate(item_schema, item)), None)

    def _object(self, schema: dict[str, object], value: object) -> str | None:
        if not isinstance(value, dict):
            return "expected object"
        return self._required(schema, value) or self._extra(schema, value) or self._properties(schema, value)

    def _properties(self, schema: dict[str, object], value: dict[str, object]) -> str | None:
        props = schema.get("properties", {})
        for key, item in value.items():
            message = self.validate(props[key], item) if key in props else None
            if message is not None:
                return f"{key}: {message}"
        return None

    def _required(self, schema: dict[str, object], value: dict[str, object]) -> str | None:
        names = [str(name) for name in schema.get("required", []) if str(name) not in value]
        return None if not names else f"missing required fields: {', '.join(names)}"

    def _extra(self, schema: dict[str, object], value: dict[str, object]) -> str | None:
        if schema.get("additionalProperties", True):
            return None
        names = [key for key in value if key not in schema.get("properties", {})]
        return None if not names else f"unexpected fields: {', '.join(sorted(names))}"

    def _scalar(self, schema: dict[str, object], value: object) -> str | None:
        if "enum" in schema and value not in schema["enum"]:
            return f"expected one of {schema['enum']}"
        kind = schema.get("type")
        return None if self._matches(kind, value) else f"expected {kind}"

    def _matches(self, kind: object, value: object) -> bool:
        mapping = {"boolean": bool, "integer": int, "number": (int, float), "object": dict, "string": str}
        return kind not in mapping or isinstance(value, mapping[str(kind)])
