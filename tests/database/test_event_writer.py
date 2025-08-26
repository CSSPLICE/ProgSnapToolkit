

import sqlite3
from progsnap2.database.helper.event_state import EventState
from progsnap2.database.helper.event_writer import CODESTATE, EventWriterBase
from progsnap2.spec.enums import EventType, MainTableColumns as Cols, CodeStatesTableColumns as CodeCols
from tests.database.conftest import cleanup_temp_dir

def test_event_writer_one_event(sqlite_writer_factory):

    # Initialize the SQLite writer
    with sqlite_writer_factory.create_writer() as writer:

        writer.initialize_database()

        initial_state = EventState(
            SubjectID="test_subject",
            ToolInstances="test_instances",
        )

        event_writer = EventWriterBase(writer, initial_state)

        test_code = "test_code"
        event = {
            Cols.SessionID: "test_session",
            CODESTATE: test_code,
        }

        # Add the event to the database
        event_writer.write_event(EventType.SessionStart, event)

        conn = writer.conn
        mt = writer.context.table_manager.main_table
        cst = writer.context.table_manager.codestates_table

        result = conn.execute(mt.select()).mappings().fetchall()

        # Ensure there is only one event in the database
        assert len(result) == 1, f"Expected one event, got: {len(result)}"

        # Ensure the event has the correct attributes
        first_mt_row = result[0]
        assert first_mt_row[Cols.SessionID] == event[Cols.SessionID], f"Expected SessionID {event[Cols.SessionID]}, got: {first_mt_row[Cols.SessionID]}"
        assert first_mt_row[Cols.EventType] == EventType.SessionStart, f"Expected EventType {EventType.SessionStart}, got: {first_mt_row[Cols.EventType]}"

        result = conn.execute(cst.select()).mappings().fetchall()

        # Ensure there is only one code state in the database
        assert len(result) == 1, f"Expected one code state, got: {len(result)}"
        # Ensure the code state has the correct attributes
        first_cst_row = result[0]
        assert first_cst_row[Cols.CodeStateID] == first_mt_row[Cols.CodeStateID], f"Expected CodeStateID {first_mt_row[Cols.CodeStateID]}, got: {first_cst_row[Cols.CodeStateID]}"
        assert first_cst_row[CodeCols.Code] == test_code, f"Expected CodeState {test_code}, got: {first_cst_row[CodeCols.CodeState]}"
