from dataclasses import dataclass


@dataclass
class BackendConfig:
    agent_backend: str
    agent_backend_fallback: str = ""
