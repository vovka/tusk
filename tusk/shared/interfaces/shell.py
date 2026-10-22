from abc import ABC, abstractmethod
from collections.abc import Callable

from tusk.shared.schemas.kernel_response import KernelResponse

__all__ = ["Shell"]


class Shell(ABC):
    @abstractmethod
    def start(self, submit: Callable[[str], KernelResponse]) -> None:
        ...
