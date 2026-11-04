from typing import Protocol

class DatabaseProbe(Protocol):
    def ready(self) -> bool: ...

