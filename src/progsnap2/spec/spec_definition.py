from dataclasses import dataclass
from typing import Dict, List, Optional
from pydantic import BaseModel, computed_field, field_validator, model_validator
from enum import Enum
from importlib.resources import open_text
import yaml

from spec.datatypes import PS2Datatype

# TODO: These should all probably be immutable
class EnumValue(BaseModel):
    name: str
    description: str = None


class EnumType(BaseModel):
    name: str
    values: List[EnumValue]

class Requirement(Enum):
    Required = "Required"
    Optional = "Optional"
    EventSpecific = "EventSpecific"

class Property(BaseModel):
    name: str
    datatype: PS2Datatype
    description: str = None

    @field_validator("datatype", mode="before")
    def parse_datatype(cls, v):
        if isinstance(v, str):
            return PS2Datatype.from_label(v)
        return v

class Column(Property):
    requirement: Requirement

class MetadataProperty(Property):
    default_value: str | bool = None

class Metadata(BaseModel):
    description: str = None
    properties: List[MetadataProperty]

    def get_property(self, property_name: str) -> Optional[MetadataProperty]:
        for prop in self.properties:
            if prop.name == property_name:
                return prop
        return None


class EventType(BaseModel):
    name: str
    description: str = None
    required_columns: List[str] = None
    optional_columns: List[str] = None

    def is_column_specific_to_event(self, column_name: str) -> bool:
        return self.is_column_required(column_name) or self.is_column_optional(column_name)

    def is_column_required(self, column_name: str) -> bool:
        return self.required_columns and column_name in self.required_columns

    def is_column_optional(self, column_name: str) -> bool:
        return self.optional_columns and column_name in self.optional_columns

class MainTable(BaseModel):
    columns: List[Column]
    event_types: List[EventType]
    description: str = None

    @computed_field
    def _event_type_map(self) -> Dict[str, EventType]:
        return {event_type.name: event_type for event_type in self.event_types}

    def get_event_type(self, event_type_name: str) -> Optional[EventType]:
        return self._event_type_map.get(event_type_name)

    @computed_field
    def _column_map(self) -> Dict[str, Column]:
        return {column.name: column for column in self.columns}

    def get_column(self, column_name: str) -> Optional[Column]:
        return self._column_map.get(column_name)

    @model_validator(mode="after")
    def validate_event_types(cls, values):
        # Check if all required columns are present in the main table
        required_columns = {col.name for col in values.columns}
        for event_type in values.event_types:
            named_columns = set()
            if event_type.required_columns:
                named_columns.update(event_type.required_columns)
            if event_type.optional_columns:
                named_columns.update(event_type.optional_columns)
            missing_columns = named_columns - required_columns
            if missing_columns:
                raise ValueError(f"Named columns in '{event_type.name}' not defined in MainTable: {missing_columns}")
        return values



class LinkTableSpec(BaseModel):
    name: str
    description: str = None
    id_column_names: List[str]
    additional_columns: List[Column]


class ProgSnap2Spec(BaseModel):
    version: str
    metadata: Metadata
    enum_types: List[EnumType]
    main_table: MainTable
    # TODO: Should these be defined in a separate yaml, since you could use 100% PS2 and add
    # LinkTables without deviating from the spec...
    link_tables: List[LinkTableSpec]

    @model_validator(mode="after")
    def validate_link_table_id_cols(cls, values):
        # Check if all ID columns in link tables are present in the main table
        id_columns = {col.name for col in values.main_table.columns}
        for link_table in values.link_tables:
            for id_col in link_table.id_column_names:
                if id_col not in id_columns:
                    raise ValueError(f"ID column '{id_col}' in LinkTable '{link_table.name}' not defined in MainTable")
        return values

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "ProgSnap2Spec":
        with open(yaml_path, "r", encoding='utf-8') as file:
            data = yaml.safe_load(file)
        return cls(**data)


@dataclass(frozen=True)
class ProgSnap2Version():
    name: str
    default: bool = False

    def load(self) -> ProgSnap2Spec:
        versions_package = f"{__package__}.versions"
        prefix = "progsnap2-v"
        suffix = ".yaml"
        with open_text(versions_package, f"{prefix}{self.name}{suffix}") as file:
            return ProgSnap2Spec.from_yaml(file.name)

class PS2Versions(Enum):
    v1_0 = ProgSnap2Version(name="1.0", default=True)

    def load(self) -> ProgSnap2Spec:
        return self.value.load()

    @classmethod
    def load_default(cls) -> ProgSnap2Spec:
        for version in cls:
            if version.value.default:
                return version.value.load()
        raise ValueError("No default version found")

    @classmethod
    def load_from_string(cls, version_str: str) -> ProgSnap2Spec:
        for version in cls:
            if version.value.name.lower() == version_str.lower().strip():
                return version.value.load()
        raise ValueError(f"Version '{version_str}' not found in PS2Versions")


