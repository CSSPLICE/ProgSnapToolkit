from dataclasses import dataclass

import pytest
from progsnap2.spec.event_validator import ErrorType, EventValidator
from progsnap2.api.events import DataModelGenerator
from progsnap2.spec.spec_definition import ProgSnap2Spec
from progsnap2.spec.enums import EventType, MainTableColumns as Cols
from ..conftest import SpecConfig

def create_valid_event(config: SpecConfig):
    event = {
        Cols.EventType: str(EventType.SessionStart),
        Cols.EventID: "test",
        Cols.CodeStateID: "test",
        Cols.SubjectID: "test",
        Cols.ToolInstances: "test",
        Cols.SessionID: "test",
    }
    return event

def test_valid_event(config: SpecConfig):
    # Create an instance of EventValidator
    event_validator = EventValidator(config.spec)

    # Create a sample event
    event = create_valid_event(config)

    # Validate the event
    errors = event_validator.validate_event(event)

    # Check that there are no validation errors
    assert len(errors) == 0, f"Validation errors: {errors}"

def test_invalid_event_type(config):
    # Create an instance of EventValidator
    event_validator = EventValidator(config.spec)

    # Create a sample event
    event = create_valid_event(config)
    event[Cols.EventType] = "InvalidEventType"  # Set an invalid event type

    errors = event_validator.validate_event(event)

    type_errors = [error for error in errors if error.type == ErrorType.InvalidEventType]
    assert len(type_errors) == 1, f"Expected one InvalidEventType error, got: {type_errors}"

def test_missing_required_column(config):
    # Create an instance of EventValidator
    event_validator = EventValidator(config.spec)

    # Create a sample event
    event = create_valid_event(config)
    event[Cols.SessionID] = None  # Set a required column to None

    errors = event_validator.validate_event(event)

    type_errors = [error for error in errors if error.type == ErrorType.MissingRequiredColumn]
    assert len(type_errors) == 1, f"Expected one MissingRequiredColumn error, got: {type_errors}"


def test_unexpected_column(config):
    # Create an instance of EventValidator
    event_validator = EventValidator(config.spec)

    # Create a sample event
    event = create_valid_event(config)
    event[Cols.EditType] = "test"  # Add an unexpected column

    errors = event_validator.validate_event(event)

    type_errors = [error for error in errors if error.type == ErrorType.UnexpectedColumn]
    assert len(type_errors) == 1, f"Expected one UnexpectedColumn error, got: {type_errors}"
