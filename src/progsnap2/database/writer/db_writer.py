
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class LogResult:
    success: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DBWriter(ABC):
    pass