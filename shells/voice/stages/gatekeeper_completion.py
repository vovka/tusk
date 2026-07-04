__all__ = ["GatekeeperCompletion"]


class GatekeeperCompletion:
    def __init__(self, llm_provider: object, log_printer: object) -> None:
        self._llm = llm_provider
        self._log = log_printer

    def complete(self, prompt: str, text: str, name: str, schema: dict) -> str:
        try:
            return self._llm.complete_structured(prompt, text, name, schema, 512)
        except Exception as exc:
            self._log.log("GATEKEEPER", f"{name} structured output failed: {exc}", "gatekeeper")
        return self._fallback(prompt, text, name)

    def _fallback(self, prompt: str, text: str, name: str) -> str:
        try:
            return self._llm.complete(prompt, text, 256)
        except Exception as exc:
            self._log.log("ERROR", f"{name} fallback completion failed: {exc}")
            return ""
