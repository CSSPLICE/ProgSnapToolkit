
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

    def __str__(self):
        warnings = '\n'.join(self.warnings) if self.warnings else 'None'
        errors = '\n'.join(self.errors) if self.errors else 'None'
        return f"LogResult(\n  success={self.success},\n  warnings={warnings},\n  errors={errors})"

class DBWriter(ABC):
    pass