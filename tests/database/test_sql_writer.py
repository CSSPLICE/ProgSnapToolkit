
import os
import pytest
import sqlite3

from progsnap2.database.codestate.git_codestate_writer import GitCodeStateWriter
from progsnap2.database.writer.db_writer import LogResult
from progsnap2.database.writer.db_writer_factory import SQLIOFactory
from progsnap2.database.writer.sql_writer import SQLWriter
from progsnap2.spec.codestate import CodeStateEntry
from .conftest import cleanup_temp_dir
from .test_codestate_writers import CodestateGenerator
from .test_event_validator import create_valid_event
from progsnap2.spec.enums import MainTableColumns as MTC, EventType

def test_sqlite_writer_init(sqlite_writer_factory, sqlite_config):
    with sqlite_writer_factory.create_writer() as writer:
        writer.initialize_database()

    db_path = sqlite_writer_factory.db_config.sqlalchemy_url.split(":///")[-1]
    assert os.path.exists(db_path), f"Database file {db_path} should exist after initialization"

    n_metadata_fields = len(sqlite_config.metadata.model_dump())

    db = sqlite3.connect(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT property, value FROM Metadata;")
    metadata = cursor.fetchall()
    assert len(metadata) == n_metadata_fields, f"Metadata table should have {n_metadata_fields} field, not {len(metadata)}"

def test_sqlite_writer_add_events(sqlite_writer_factory, sqlite_config, config):
    with sqlite_writer_factory.create_writer() as writer:
        writer.initialize_database()

        codestate_gen = CodestateGenerator()
        codestate = codestate_gen.codestate1

        event = create_valid_event(config)
        temp_codestate_id = "abc123"
        event[MTC.CodeStateID] = temp_codestate_id
        codestates_dict = {temp_codestate_id: codestate}

        writer.add_events_with_codestates([event], codestates_dict)

        # TODO: Do actualy checks (e.g. the CodeStateID is correct - it's not right now)


def test_add_context_git(sqlite_writer_factory, config):
    # Create a non-contextual codestate
    codestate = CodeStateEntry.from_code("test code!!")

    event = create_valid_event(config)
    temp_codestate_id = "abc123"
    event[MTC.CodeStateID] = temp_codestate_id
    event[MTC.ProjectID] = "test_project"
    codestates_dict = {temp_codestate_id: codestate}

    result = LogResult(True)

    with sqlite_writer_factory.create_writer() as writer:
        writer._contextualize_codestates([event], codestates_dict, result)

    assert result.success, "Contextualization should succeed"
    assert result.warnings == [], "There should be no warnings"

    new_codestate = codestates_dict[temp_codestate_id]
    assert new_codestate != codestate, "Codestate should now be contextualized"
    assert new_codestate.grouping_id == event[MTC.SubjectID], "Grouping ID should match the event's SubjectID"
    assert new_codestate.ProjectID == event[MTC.ProjectID], "Project ID should match the event's ProjectID"


def test_add_context_warnings(sqlite_writer_factory, config):
    do_warning_test(sqlite_writer_factory, config, with_git=False)

def test_add_context_git_warnings(sqlite_writer_factory, config):
    do_warning_test(sqlite_writer_factory, config, with_git=True)

def do_warning_test(sqlite_writer_factory, config, with_git):
    # Create a non-contextual codestate
    codestate = CodeStateEntry.from_code("test code!!")

    event = create_valid_event(config)
    temp_codestate_id = "abc123"
    event[MTC.CodeStateID] = temp_codestate_id
    # Remove the ProjectID to trigger a warning
    event[MTC.ProjectID] = None
    codestates_dict = {temp_codestate_id: codestate}

    git_writer = GitCodeStateWriter(sqlite_writer_factory.db_config.codestates_dir)
    assert git_writer.requires_project_id(), "GitCodeStateWriter should require a ProjectID"

    result = LogResult(True)
    with sqlite_writer_factory.create_writer() as writer:
        if with_git:
            # Use the GitCodeStateWriter
            writer.codestate_writer = git_writer
        writer._contextualize_codestates([event], codestates_dict, result)

    assert result.success, "Contextualization should succeed"
    expected_warnings = 1 if with_git else 0
    assert len(result.warnings) == expected_warnings, f"There should be {expected_warnings} warning"