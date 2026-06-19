from tests.recording_backend import RecordingBackend


class FactoryStub:
    instances: list["FactoryStub"] = []

    def __init__(self, agent: object, config: object, log: object) -> None:
        self.agent = agent
        self.config = config
        self.log = log
        self.backend = RecordingBackend()
        self.instances.append(self)

    def create(self) -> RecordingBackend:
        return self.backend
