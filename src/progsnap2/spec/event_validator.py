
from dataclasses import dataclass
from enum import Enum
from spec.datatypes import timestamp_has_timezone
from api.events import MainTableEventBase
from spec.spec_definition import ProgSnap2Spec, Requirement
from spec.enums import MainTableColumns as Cols

class ErrorType(Enum):
    MissingRequiredColumn = "MissingRequiredColumn"
    UnexpectedColumn = "UnexpectedColumn"
    InvalidEventType = "InvalidEventType"
    InvalidValueForDatatype = "InvalidValueForDatatype"

@dataclass
class ValidationError:
    column: str
    type: ErrorType

    def __str__(self):
        if self.type == ErrorType.MissingRequiredColumn:
            return f"Missing required column: {self.column}"
        elif self.type == ErrorType.UnexpectedColumn:
            return f"Unexpected column: {self.column}"
        elif self.type == ErrorType.InvalidEventType:
            return f"Invalid event type: {self.column}"
        elif self.type == ErrorType.InvalidValueForDatatype:
            return f"Invalid value for datatype: {self.column}"
        else:
            return f"Unknown error: {self.column}"

class EventValidator():

    def __init__(self, spec: ProgSnap2Spec):
        self.spec = spec

    def validate_event(self, event: dict[str, any]) -> list[ValidationError]:
        """
        Validate the event against the schema.
        """
        errors = []

        spec = self.spec

        # Get all columns that are not None
        # Requires columns can never be None; we use the empty string for some "not present" values
        provided_columns = [key for key in event.keys() if event[key] is not None]

        for col in provided_columns:
            datatype = spec.main_table.get_column(col).datatype
            try:
                datatype.validate_value(event[col])
            except ValueError as e:
                errors.append(ValidationError(column=col, type=ErrorType.InvalidValueForDatatype))

        for timestamp_col in (Cols.ServerTimestamp, Cols.ClientTimestamp):
            # TODO: If we add a timezone column, for check that it's not present first
            if timestamp_col in provided_columns:
                if not timestamp_has_timezone(event[timestamp_col]):
                    errors.append(ValidationError(column=timestamp_col, type=ErrorType.InvalidValueForDatatype))

        required_column_names = [
            col.name for col in spec.main_table.columns
            if col.requirement == Requirement.Required
        ]
        optional_column_names = [
            col.name for col in spec.main_table.columns
            if col.requirement == Requirement.Optional
        ]

        event_type = spec.main_table.get_event_type(event[Cols.EventType])
        if event_type is None:
            errors.append(ValidationError(column=event[Cols.EventType], type=ErrorType.InvalidEventType))
        else:
            required_column_names.extend(
                event_type.required_columns or []
            )
            optional_column_names.extend(
                event_type.optional_columns or []
            )


        # Check if all required fields are present
        for col in required_column_names:
            if col not in provided_columns:
                errors.append(ValidationError(column=col, type=ErrorType.MissingRequiredColumn))

        all_expected_columns = set(required_column_names + optional_column_names)
        for col in provided_columns:
            if col not in all_expected_columns:
                errors.append(ValidationError(column=col, type=ErrorType.UnexpectedColumn))

        return errors