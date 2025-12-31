
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from progsnap2.database.config import PS2DataConfig
from progsnap2.database.sql_table_manager import SQLTableManager, SQLWriterTableManager
from progsnap2.spec.event_validator import EventValidator
from progsnap2.spec.spec_definition import ProgSnap2Spec

@dataclass
class IOContext:
    data_config: PS2DataConfig
    ps2_spec: ProgSnap2Spec

    event_validator: EventValidator = field(init=False)

    def __post_init__(self):
        self.event_validator = EventValidator(self.ps2_spec)

@dataclass
class SQLContext(IOContext):
    session: Session
    table_manager: SQLTableManager
