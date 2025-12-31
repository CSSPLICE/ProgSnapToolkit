import logging
logger = logging.getLogger(__name__)

from enum import Enum
import uuid
from sqlalchemy import insert
from progsnap2.database.codestate.codestate_writer import CodeStateEntry, CodeStateWriter, ContextualCodeStateEntry
from progsnap2.database.writer.db_writer import DBWriter, LogResult
from progsnap2.database.sql_context import SQLContext
from progsnap2.spec.codestate import BLANK_CODESTATE_ID
from progsnap2.spec.datatypes import get_current_timestamp
from progsnap2.spec.enums import MainTableColumns as Cols

EventList = list[dict[str, any]]
CodeStatesMap = dict[str, CodeStateEntry]

# TODO: When stable, move non-SQL-specific methods to DBWriter
class SQLWriter(DBWriter):

    def __init__(self, context: SQLContext, codestate_writer: CodeStateWriter):
        super().__init__()
        self.context = context
        self.codestate_writer: CodeStateWriter = codestate_writer

    @property
    def session(self):
        return self.context.session

    def add_server_timestamps(self, events: EventList) -> None:
        for event in events:
            if Cols.ServerTimestamp not in event:
                event[Cols.ServerTimestamp] = get_current_timestamp()

    def generate_event_id(self) -> str:
        return str(uuid.uuid4())

    def add_events(self, events: EventList) -> LogResult:
        # logger.info("starting insert")

        result = LogResult(True)

        for event in events:
            if Cols.EventID not in event:
                event[Cols.EventID] = self.generate_event_id()
            # Convert any enums to their values
            for col in event.keys():
                if isinstance(event[col], Enum):
                    event[col] = event[col].value
            result.warnings.extend([str(warning) for warning in self.context.event_validator.validate_event(event)])

        main_table = self.context.table_manager.main_table

        try:
            stmt = insert(main_table)
            self.session.execute(stmt, events)  # batch insert
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            result.errors.append(f"Error inserting events: {e}")
            result.success = False

        return result

    def add_events_with_codestates(self, events: EventList, codestates: CodeStatesMap) -> LogResult:
        result = LogResult(True)

        # Must come before optimizing!
        self._contextualize_codestates(events, codestates, result)

        # TODO: I wonder if we should pass the result to append warnings
        if self.context.data_config.optimize_codestate_ids:
            self._optimize_codestate_ids(events, codestates, result)
        else:
            for codestate_id, codestate in codestates.items():
                self.codestate_writer.add_codestate_with_id(codestate, codestate_id)

        result.extend(self.add_events(events))

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
            if not isinstance(codestate, ContextualCodeStateEntry):
                project_id = project_id_map.get(id)
                subject_id = subject_id_map.get(id)
                if self.codestate_writer.requires_project_id() and project_id is None:
                    result.warnings.append(f"CodeState format requires a ProjectID but none provided for CodeStateID {id}. Using default.")
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
                temp_codestate_id = event[Cols.CodeStateID]
                if temp_codestate_id not in temp_codestate_id_map:
                    result.warnings.append(f"CodeStateID {temp_codestate_id} not found in temp_codestate_id_map.")
                    continue

                event[Cols.CodeStateID] = temp_codestate_id_map[temp_codestate_id]

    # NOTE: No try/catch here - let exceptions propagate
    def add_link_table_entry(self, table_name: str, entry: dict[str, any]) -> None:
        link_table = self.context.table_manager.get_table(table_name)
        statement = insert(link_table).values(**entry)
        self.session.execute(statement)
        self.session.commit()

    def initialize_database(self, force=False) -> None:
        if not force and self.context.table_manager.have_tables_been_created(self.session):
            return
        self.context.table_manager.create_tables(self.session)
        self.context.table_manager.update_metadata_values(self.session)

    def update_database(self):
        self.context.table_manager.update_tables(self.session)