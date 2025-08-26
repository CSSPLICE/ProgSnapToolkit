import datetime
from sqlalchemy import insert
from database.codestate.codestate_writer import CodeStateEntry, CodeStateWriter, ContextualCodeStateEntry
from database.writer.db_writer import DBWriter, LogResult
from database.sql_context import SQLContext
from spec.codestate import BLANK_CODESTATE_ID
from spec.datatypes import get_current_timestamp
from spec.enums import MainTableColumns as Cols

EventList = list[dict[str, any]]
CodeStatesMap = dict[str, CodeStateEntry]

# TODO: When stable, move non-SQL-specific methods to DBWriter
class SQLWriter(DBWriter):

    def __init__(self, context: SQLContext, codestate_writer: CodeStateWriter):
        super().__init__()
        self.context = context
        self.codestate_writer: CodeStateWriter = codestate_writer

    @property
    def conn(self):
        return self.context.conn

    def add_server_timestamps(self, events: EventList) -> None:
        for event in events:
            if Cols.ServerTimestamp not in event:
                event[Cols.ServerTimestamp] = get_current_timestamp()

    def add_events_with_codestates(self, events: EventList, codestates: CodeStatesMap) -> LogResult:
        result = LogResult(True)

        for event in events:
            result.warnings.extend([str(warning) for warning in self.context.event_validator.validate_event(event)])

        # Must come before optimizing!
        self._contextualize_codestates(events, codestates, result)

        # TODO: I wonder if we should pass the result to append warnings
        if self.context.data_config.optimize_codestate_ids:
            self._optimize_codestate_ids(events, codestates, result)
        else:
            for codestate_id, codestate in codestates.items():
                self.codestate_writer.add_codestate_with_id(codestate, codestate_id)

        main_table = self.context.table_manager.main_table

        for event in events:
            try:
                print("Insert!")
                print(event)
                statement = insert(main_table).values(**event)
                self.conn.execute(statement)
            except Exception as e:
                result.errors.append(f"Error inserting events: {e}")
                self.conn.rollback()
                result.success = False
                break

        if result.success:
            self.conn.commit()

        return result

    def _contextualize_codestates(self, events: EventList, codestates: CodeStatesMap, result: LogResult) -> None:

        # Figure out which project_id and subject_id to use for each codestate
        # Usually this will be the same for all events, but in theory multiple projects' events
        # could be sent in one batch.
        project_id_map = {}
        subject_id_map = {}
        for event in events:
            if not Cols.CodeStateID in event:
                continue
            codestate_id = event[Cols.CodeStateID]
            if Cols.ProjectID in event:
                if codestate_id in project_id_map and project_id_map[codestate_id] != event[Cols.ProjectID]:
                    result.warnings.append(f"CodeStateID {codestate_id} matches multiple ProjectIDs! {project_id_map[codestate_id]} vs {event[Cols.ProjectID]}")
                project_id_map[codestate_id] = event[Cols.ProjectID]
            if Cols.SubjectID in event:
                if codestate_id in subject_id_map and subject_id_map[codestate_id] != event[Cols.SubjectID]:
                    result.warnings.append(f"CodeStateID {codestate_id} matches multiple SubjectIDs! {subject_id_map[codestate_id]} vs {event[Cols.SubjectID]}")
                subject_id_map[codestate_id] = event[Cols.SubjectID]

        # Add the needed information to codestates
        for id, codestate in codestates.items():
            print(id)
            if not isinstance(codestate, ContextualCodeStateEntry):
                project_id = project_id_map.get(id)
                subject_id = subject_id_map.get(id)
                print(project_id, subject_id)
                if self.codestate_writer.requires_project_id() and project_id is None:
                    print("Adding warning")
                    result.warnings.append(f"CodeState format requires a ProjectID but none provided for CodeStateID {codestate_id}. Using default.")
                    project_id = self.codestate_writer.get_default_project_id()
                codestate = ContextualCodeStateEntry.from_codestate_entry(codestate, subject_id, project_id)
                codestates[id] = codestate

    def _optimize_codestate_ids(self, events: EventList, codestates: CodeStatesMap, result: LogResult) -> None:
        temp_codestate_id_map = {}
        for temp_id, codestate in codestates.items():
            if codestate.is_blank:
                code_state_id = BLANK_CODESTATE_ID
            else:
                code_state_id = self.codestate_writer.add_codestate_and_get_id(codestate)
            temp_codestate_id_map[temp_id] = code_state_id

        for event in events:
            if Cols.CodeStateID in event:
                if event[Cols.CodeStateID] not in temp_codestate_id_map:
                    result.warnings.append(f"CodeStateID {event[Cols.CodeStateID]} not found in temp_codestate_id_map.")
                    continue

                event[Cols.CodeStateID] = temp_codestate_id_map[event[Cols.CodeStateID]]

    def initialize_database(self, force=False) -> None:
        if not force and self.context.table_manager.have_tables_been_created(self.conn):
            return
        self.context.table_manager.create_tables(self.conn)
        self.context.table_manager.update_metadata_values(self.conn)