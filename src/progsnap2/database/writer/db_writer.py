
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

@dataclass
class LogResult:
    success: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def extend(self, other: 'LogResult'):
        self.warnings.extend(other.warnings)
        self.errors.extend(other.errors)
        self.success = self.success and other.success


class DBWriter(ABC):
    pass