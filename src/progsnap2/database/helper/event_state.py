from dataclasses import dataclass
from progsnap2.spec.enums import EventType

# TODO: Autogenerate with optional fields
@dataclass
class EventState():
    SubjectID: str
    ToolInstances: str